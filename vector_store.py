"""Simple vector-backed storage for file organization history."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from ai_categorizer import AICategorizerConfig, AICategorizerError, answer_question_with_ai

_CATEGORY_KEYWORDS = {
    "Pictures": {"picture", "pictures", "photo", "photos", "image", "images"},
    "Video": {"video", "videos", "movie", "movies"},
    "Music": {"music", "song", "songs", "audio"},
    "Documents": {"document", "documents", "doc", "docs", "pdf", "spreadsheet", "presentation"},
    "Compressed": {"archive", "compressed", "zip", "rar", "tar"},
    "Programs": {"program", "programs", "installer", "setup", "exe", "msi"},
    "Code": {"code", "script", "scripts", "source", "project"},
    "Others": {"other", "others", "misc", "miscellaneous"},
}


class SimpleVectorStore:
    """A lightweight in-process vector store for run summaries and file history."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = {
            "documents": [],
            "files": [],
            "stats": {"total_files": 0, "by_category": {}, "run_history": []},
        }
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        self.data.update({key: loaded.get(key, self.data[key]) for key in self.data})
        self.data.setdefault("documents", [])
        self.data.setdefault("files", [])
        self.data.setdefault("stats", {})
        self.data["stats"].setdefault("total_files", 0)
        self.data["stats"].setdefault("by_category", {})
        self.data["stats"].setdefault("run_history", [])

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Vector operations
    # ------------------------------------------------------------------
    @staticmethod
    def _text_to_vector(text: str) -> Dict[str, float]:
        tokens = re.findall(r"\b\w+\b", text.lower())
        counts = Counter(tokens)
        if not counts:
            return {}
        norm = math.sqrt(sum(value * value for value in counts.values()))
        if not norm:
            return {}
        return {token: count / norm for token, count in counts.items()}

    @staticmethod
    def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        intersection = set(vec_a.keys()) & set(vec_b.keys())
        return sum(vec_a[token] * vec_b[token] for token in intersection)

    def _add_document(self, text: str, metadata: Dict[str, object]) -> None:
        self.data["documents"].append(
            {
                "text": text,
                "metadata": metadata,
                "vector": self._text_to_vector(text),
            }
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def log_run(
        self,
        *,
        run_timestamp: str,
        folder_path: str,
        moved_files: Sequence[Dict[str, object]],
        category_counts: Dict[str, int],
        skipped_files: int,
    ) -> None:
        """Persist run metadata and update aggregates."""

        stats = self.data["stats"]
        per_category = {category: int(count) for category, count in category_counts.items() if count}
        moved_count = len(moved_files)

        stats["total_files"] = int(stats.get("total_files", 0)) + moved_count
        category_totals = stats.setdefault("by_category", {})
        for category, count in per_category.items():
            category_totals[category] = int(category_totals.get(category, 0)) + count

        stats.setdefault("run_history", []).append(
            {
                "timestamp": run_timestamp,
                "folder": folder_path,
                "moved": moved_count,
                "skipped": skipped_files,
                "by_category": per_category,
            }
        )

        summary_parts = [
            f"Run on {run_timestamp} organized folder {folder_path}.",
            f"Moved {moved_count} files and skipped {skipped_files} items.",
        ]
        if per_category:
            summary_parts.append(
                "Category breakdown: "
                + ", ".join(f"{cat}={count}" for cat, count in sorted(per_category.items()))
            )
        summary_text = " ".join(summary_parts)
        self._add_document(
            summary_text,
            {
                "type": "run_summary",
                "timestamp": run_timestamp,
                "folder": folder_path,
                "moved": moved_count,
                "skipped": skipped_files,
            },
        )

        for record in moved_files:
            file_record = {
                "file_name": str(record.get("file_name")),
                "category": str(record.get("category")),
                "timestamp": str(record.get("timestamp", run_timestamp)),
                "destination_path": record.get("destination_path"),
                "original_path": record.get("original_path"),
            }
            self.data.setdefault("files", []).append(file_record)
            doc_text = (
                f"File {file_record['file_name']} categorized as {file_record['category']} "
                f"on {file_record['timestamp']}."
            )
            self._add_document(doc_text, {"type": "file", **file_record})

        self.save()

    def query(self, text: str, top_k: int = 5) -> List[Dict[str, object]]:
        if not text.strip():
            return []
        if not self.data["documents"]:
            return []
        vector = self._text_to_vector(text)
        if not vector:
            return []

        scored: List[tuple[float, Dict[str, object]]] = []
        for document in self.data["documents"]:
            score = self._cosine_similarity(vector, document.get("vector", {}))
            if score > 0:
                scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def answer_question(
        self,
        question: str,
        *,
        ai_config: Optional[AICategorizerConfig] = None,
    ) -> str:
        normalized = question.strip()
        if not normalized:
            return "Please ask a non-empty question."

        if not self.data["stats"]["run_history"]:
            return "No organization history yet. Run the organizer first."

        lower_question = normalized.lower()
        detected_category = self._detect_category(lower_question)
        stats = self.data["stats"]

        if "how many" in lower_question and "file" in lower_question:
            if detected_category:
                count = stats["by_category"].get(detected_category, 0)
                return f"{count} files have been categorized as {detected_category} so far."
            return f"{stats['total_files']} files have been moved so far."

        if any(keyword in lower_question for keyword in ("which", "list", "show")) and detected_category:
            matching = [
                entry["file_name"]
                for entry in self.data["files"]
                if entry.get("category") == detected_category
            ]
            if not matching:
                return f"No files categorized as {detected_category} yet."
            recent = matching[-10:]
            suffix = "" if len(matching) <= 10 else f" (showing {len(recent)} of {len(matching)} entries)"
            return ", ".join(recent) + suffix

        if "last run" in lower_question or "recent run" in lower_question:
            last_run = stats["run_history"][-1]
            breakdown = last_run.get("by_category", {})
            if breakdown:
                parts = ", ".join(f"{cat}={count}" for cat, count in breakdown.items())
                return (
                    f"Last run moved {last_run['moved']} files (skipped {last_run['skipped']}). "
                    f"Categories: {parts}."
                )
            return f"Last run moved {last_run['moved']} files and skipped {last_run['skipped']}."

        context = self._build_context(lower_question)
        if ai_config:
            try:
                return answer_question_with_ai(ai_config, normalized, context)
            except AICategorizerError as error:
                return f"AI response failed: {error}"

        return context or "Not enough data to answer that question yet. Try enabling AI support."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_context(self, question: str, top_k: int = 5) -> str:
        stats = self.data["stats"]
        lines: List[str] = [f"Total files moved: {stats['total_files']}"]

        if stats["by_category"]:
            category_summary = ", ".join(
                f"{cat}={count}" for cat, count in sorted(stats["by_category"].items())
            )
            lines.append(f"Category totals: {category_summary}")

        if stats["run_history"]:
            recent_runs = stats["run_history"][-5:]
            for run in reversed(recent_runs):
                run_summary = ", ".join(
                    f"{cat}={count}" for cat, count in run.get("by_category", {}).items()
                )
                lines.append(
                    f"Run {run['timestamp']} moved {run['moved']} files (skipped {run['skipped']})."
                    + (f" Categories: {run_summary}." if run_summary else "")
                )

        top_documents = self.query(question, top_k=top_k)
        if top_documents:
            lines.append("Relevant entries:")
        for doc in top_documents:
            metadata = doc.get("metadata", {})
            if metadata.get("type") == "file":
                lines.append(
                    f"- File {metadata.get('file_name')} in {metadata.get('category')} (logged {metadata.get('timestamp')})."
                )
            else:
                lines.append(f"- {doc.get('text')}")

        return "\n".join(lines)

    @staticmethod
    def _detect_category(question: str) -> Optional[str]:
        for category, keywords in _CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question:
                    return category
        return None
