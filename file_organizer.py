import argparse
import logging
import os
import shutil
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

from ai_categorizer import (
    AICategorizer,
    AICategorizerConfig,
    AICategorizerError,
    PROVIDER_ENV_VARS,
)
from vector_store import SimpleVectorStore

# Optional imports for web UI
try:
    import webbrowser
    from flask import Flask, jsonify, render_template, request

    FLASK_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    FLASK_AVAILABLE = False

if load_dotenv:
    load_dotenv()


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_env_ai_defaults() -> Dict[str, Optional[str]]:
    return {
        "enabled": _parse_bool(os.getenv("FILE_ORGANIZER_ENABLE_AI")),
        "provider": os.getenv("FILE_ORGANIZER_AI_PROVIDER"),
        "scope": os.getenv("FILE_ORGANIZER_AI_SCOPE") or "fallback",
        "model": os.getenv("FILE_ORGANIZER_AI_MODEL") or None,
        "timeout": os.getenv("FILE_ORGANIZER_AI_TIMEOUT") or None,
    }


class FileOrganizer:
    def __init__(
        self,
        downloads_path: Optional[str] = None,
        ai_config: Optional[AICategorizerConfig] = None,
    ):
        self.downloads_path = downloads_path or os.path.join(os.path.expanduser("~"), "Downloads")
        self.ai_config = ai_config
        self.ai_categorizer: Optional[AICategorizer] = None

        self.state_dir = Path(self.downloads_path) / "file_organizer_state"
        self.state_dir.mkdir(exist_ok=True)
        self.vector_store = SimpleVectorStore(self.state_dir / "vector_store.json")

        self.setup_logging()

        self.categories = {
            "Pictures": [
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".tiff",
                ".svg",
                ".webp",
                ".ico",
                ".avif",
            ],
            "Video": [
                ".mp4",
                ".avi",
                ".mkv",
                ".mov",
                ".wmv",
                ".flv",
                ".webm",
                ".m4v",
                ".3gp",
            ],
            "Music": [
                ".mp3",
                ".wav",
                ".flac",
                ".aac",
                ".ogg",
                ".wma",
                ".m4a",
            ],
            "Documents": [
                ".pdf",
                ".doc",
                ".docx",
                ".txt",
                ".rtf",
                ".odt",
                ".pages",
                ".xls",
                ".xlsx",
                ".csv",
                ".ods",
                ".numbers",
                ".ppt",
                ".pptx",
                ".odp",
                ".key",
            ],
            "Compressed": [
                ".zip",
                ".rar",
                ".7z",
                ".tar",
                ".gz",
                ".bz2",
                ".xz",
                ".tgz",
                ".iso",
                ".ini",
            ],
            "Programs": [
                ".exe",
                ".msi",
                ".deb",
                ".dmg",
                ".pkg",
                ".app",
            ],
            "Code": [
                ".py",
                ".js",
                ".html",
                ".css",
                ".java",
                ".cpp",
                ".c",
                ".php",
                ".rb",
                ".go",
                ".rs",
            ],
            "Others": [],
        }

        if self.ai_config:
            self._initialize_ai()

    def setup_logging(self):
        log_dir = Path(self.downloads_path) / "file_organizer_logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_dir / f"organizer_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def _initialize_ai(self):
        try:
            self.ai_categorizer = AICategorizer(self.ai_config)
            self.logger.info(
                "AI categorization enabled using provider %s (%s mode)",
                self.ai_config.provider,
                self.ai_config.scope,
            )
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("Failed to initialize AI categorizer: %s", exc)
            self.ai_categorizer = None

    def get_file_category(self, file_extension):
        for category, extensions in self.categories.items():
            if file_extension.lower() in extensions:
                return category
        return "Others"

    def _maybe_use_ai(self, file_path: Path, default_category: str) -> tuple[Optional[str], Optional[str]]:
        if not self.ai_categorizer:
            return None, None

        scope = (self.ai_categorizer.scope or "fallback").lower()
        if scope == "fallback" and default_category != "Others":
            return None, None
        if scope not in {"fallback", "always"}:
            self.logger.warning(
                "Unsupported AI scope '%s'. Falling back to rule-based categorization.",
                scope,
            )
            return None, None

        try:
            file_size = file_path.stat().st_size
        except OSError:
            file_size = None

        try:
            category, subfolder = self.ai_categorizer.suggest_category_and_subfolder(
                file_name=file_path.name,
                file_extension=file_path.suffix,
                categories=self.categories.keys(),
                default_category=default_category,
                file_size=file_size,
            )
        except AICategorizerError as error:
            self.logger.error("AI categorization failed for %s: %s", file_path.name, error)
            return None, None

        if category and category not in self.categories:
            self.logger.warning(
                "AI suggested unknown category '%s' for %s. Keeping %s.",
                category,
                file_path.name,
                default_category,
            )
            return None, None

        return category, subfolder

    def create_category_folders(self):
        for category in self.categories.keys():
            category_path = Path(self.downloads_path) / category
            category_path.mkdir(exist_ok=True)
            self.logger.info("Ensured category folder exists: %s", category_path)

    def organize_files(self):
        downloads_path = Path(self.downloads_path)
        if not downloads_path.exists():
            self.logger.error("Downloads folder not found: %s", downloads_path)
            return

        run_timestamp = datetime.now().isoformat()
        existing_folders = {
            folder.name
            for folder in downloads_path.iterdir()
            if folder.is_dir() and not folder.name.startswith(".")
        }
        self.logger.info("Found existing folders: %s", existing_folders)

        self.create_category_folders()
        moved_files = 0
        skipped_files = 0
        category_counts: Dict[str, int] = defaultdict(int)
        moved_details: List[Dict[str, str]] = []

        for file_path in downloads_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith("."):
                if file_path.parent.name in self.categories or file_path.parent.name in existing_folders:
                    skipped_files += 1
                    self.logger.debug("Skipped: %s (already in folder)", file_path.name)
                    continue

                file_extension = file_path.suffix
                initial_category = self.get_file_category(file_extension)
                ai_category, ai_subfolder = self._maybe_use_ai(file_path, initial_category)

                if ai_category and ai_category != initial_category:
                    self.logger.info(
                        "AI reassigned %s from %s to %s", file_path.name, initial_category, ai_category
                    )
                    category = ai_category
                    subfolder = ai_subfolder
                elif ai_category and ai_subfolder:
                    # Same category but AI suggested a subfolder
                    category = ai_category
                    subfolder = ai_subfolder
                    self.logger.info(
                        "AI suggested subfolder %s for %s", ai_subfolder, file_path.name
                    )
                else:
                    category = initial_category
                    subfolder = None

                destination_folder = downloads_path / category
                if subfolder:
                    destination_folder = destination_folder / subfolder
                    destination_folder.mkdir(exist_ok=True)
                destination_path = destination_folder / file_path.name
                source_path = str(file_path)

                if destination_path.exists():
                    base_name = file_path.stem
                    extension = file_path.suffix
                    counter = 1
                    while destination_path.exists():
                        new_name = f"{base_name}_{counter}{extension}"
                        destination_path = destination_folder / new_name
                        counter += 1

                try:
                    shutil.move(str(file_path), str(destination_path))
                    moved_files += 1
                    category_counts[category] += 1
                    moved_details.append(
                        {
                            "file_name": destination_path.name,
                            "category": category,
                            "timestamp": run_timestamp,
                            "original_path": source_path,
                            "destination_path": str(destination_path),
                        }
                    )
                    folder_display = f"{category}/{subfolder}" if subfolder else category
                    self.logger.info("Moved: %s -> %s/", destination_path.name, folder_display)
                except Exception as exc:  # pragma: no cover - defensive logging
                    self.logger.error("Error moving %s: %s", file_path.name, exc)

        self.vector_store.log_run(
            run_timestamp=run_timestamp,
            folder_path=str(downloads_path),
            moved_files=moved_details,
            category_counts=dict(category_counts),
            skipped_files=skipped_files,
        )

        self.logger.info(
            "Organization complete! Moved %s files, skipped %s files.", moved_files, skipped_files
        )
        return moved_files

    def answer_question(self, question: str) -> str:
        ai_config = self.ai_config if self.ai_categorizer else None
        return self.vector_store.answer_question(question, ai_config=ai_config)


def build_ai_config(args: argparse.Namespace) -> Optional[AICategorizerConfig]:
    env_defaults = get_env_ai_defaults()
    provider = args.ai_provider or env_defaults.get("provider")
    env_enabled = env_defaults.get("enabled")

    if args.ai_provider:
        enable_ai = True
    elif env_enabled is True:
        enable_ai = True
    elif env_enabled is False:
        enable_ai = False
    else:
        enable_ai = bool(provider)

    if not enable_ai:
        return None

    if not provider:
        raise ValueError(
            "AI provider is not configured. Set --ai-provider or FILE_ORGANIZER_AI_PROVIDER."
        )

    provider = provider.lower()
    scope = args.ai_scope or env_defaults.get("scope") or "fallback"
    model = args.ai_model or env_defaults.get("model")

    timeout_value: Optional[int]
    if args.ai_timeout is not None:
        timeout_value = args.ai_timeout
    elif env_defaults.get("timeout") is not None:
        try:
            timeout_value = int(env_defaults["timeout"])
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("FILE_ORGANIZER_AI_TIMEOUT must be an integer.") from exc
    else:
        timeout_value = 15

    env_var = PROVIDER_ENV_VARS.get(provider)
    api_key = args.ai_api_key or (os.getenv(env_var) if env_var else None)
    if not api_key:
        raise ValueError(
            f"API key missing for provider '{provider}'. Provide --ai-api-key or set {env_var}."
        )

    return AICategorizerConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        scope=scope,
        timeout=timeout_value,
    )


# Flask Web UI (only if Flask is available)
if FLASK_AVAILABLE:
    app = Flask(__name__)
    organizer_instance: Optional[FileOrganizer] = None

    def get_or_create_organizer():
        global organizer_instance
        if organizer_instance is None:
            # Create a default organizer instance to enable queries
            defaults = get_env_ai_defaults()
            ai_config = None
            if defaults.get("enabled") and defaults.get("provider"):
                try:
                    from types import SimpleNamespace
                    args = SimpleNamespace()
                    args.ai_provider = defaults.get("provider")
                    args.ai_scope = defaults.get("scope") or "fallback"
                    args.ai_model = defaults.get("model")
                    args.ai_api_key = None
                    args.ai_timeout = int(defaults.get("timeout") or 15)
                    ai_config = build_ai_config(args)
                except (ValueError, TypeError):
                    pass  # Fall back to no AI
            organizer_instance = FileOrganizer(ai_config=ai_config)
        return organizer_instance

    @app.route("/")
    def index():
        defaults = get_env_ai_defaults()
        if organizer_instance and organizer_instance.ai_config:
            ai_enabled = organizer_instance.ai_categorizer is not None
            active_provider = organizer_instance.ai_config.provider
            active_scope = organizer_instance.ai_config.scope
        else:
            ai_enabled = bool(defaults.get("enabled")) and bool(defaults.get("provider"))
            active_provider = defaults.get("provider")
            active_scope = defaults.get("scope") or "fallback"

        return render_template(
            "index.html",
            default_folder=os.path.join(os.path.expanduser("~"), "Downloads"),
            ai_providers=sorted(PROVIDER_ENV_VARS.keys()),
            ai_enabled=ai_enabled,
            active_ai_provider=active_provider,
            active_ai_scope=active_scope,
        )

    @app.route("/organize", methods=["POST"])
    def organize():
        folder_path = request.form.get("folder_path")
        if not folder_path or not os.path.exists(folder_path):
            return jsonify({"error": "Invalid folder path"}), 400

        ai_provider = request.form.get("ai_provider") or None
        ai_scope = request.form.get("ai_scope") or "fallback"
        ai_model = request.form.get("ai_model") or None
        ai_api_key = request.form.get("ai_api_key") or None

        class Args:
            pass

        args = Args()
        args.ai_provider = ai_provider
        args.ai_scope = ai_scope
        args.ai_model = ai_model
        args.ai_api_key = ai_api_key
        args.ai_timeout = 15

        try:
            ai_config = build_ai_config(args) if ai_provider else None
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

        global organizer_instance
        organizer_instance = FileOrganizer(folder_path, ai_config=ai_config)
        moved_files = organizer_instance.organize_files()

        return jsonify(
            {
                "success": True,
                "message": f"Successfully organized {moved_files} files!",
                "folder": folder_path,
            }
        )

    @app.route("/ask", methods=["POST"])
    def ask():
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json()
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "Question is required"}), 400

        try:
            organizer = get_or_create_organizer()
        except Exception as exc:
            return jsonify({"error": f"Failed to initialize organizer: {exc}"}), 500

        try:
            answer = organizer.answer_question(question)
            return jsonify({"success": True, "answer": answer})
        except Exception as exc:
            return jsonify({"error": f"Failed to answer question: {exc}"}), 500

    @app.route("/browse")
    def browse():
        folder_path = request.args.get("path", os.path.expanduser("~"))
        try:
            items = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    items.append(
                        {
                            "name": item,
                            "path": item_path,
                            "type": "folder",
                        }
                    )

            parent_path = os.path.dirname(folder_path) if folder_path != os.path.dirname(folder_path) else None

            return jsonify(
                {
                    "current_path": folder_path,
                    "parent_path": parent_path,
                    "items": sorted(items, key=lambda x: x["name"].lower()),
                }
            )
        except PermissionError:
            return jsonify({"error": "Permission denied"}), 403
        except Exception as exc:  # pragma: no cover - defensive
            return jsonify({"error": str(exc)}), 500

    def run_web_server(port=5000, debug=False):
        app.run(host="127.0.0.1", port=port, debug=debug)


def main():
    parser = argparse.ArgumentParser(
        description="File Organizer - Organize files into categories with optional AI assistance"
    )
    parser.add_argument(
        "--folder",
        "-f",
        type=str,
        help="Folder path to organize (default: Downloads folder)",
    )
    parser.add_argument(
        "--web",
        "-w",
        action="store_true",
        help="Start web UI server",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=5000,
        help="Port for web server (default: 5000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open browser when starting web UI",
    )
    parser.add_argument(
        "--ask",
        type=str,
        help="Ask a question about prior runs using stored metadata",
    )
    parser.add_argument(
        "--ai-provider",
        choices=sorted(PROVIDER_ENV_VARS.keys()),
        help="Enable AI-assisted categorization using the selected provider",
    )
    parser.add_argument(
        "--ai-model",
        type=str,
        help="Override the default model for the selected AI provider",
    )
    parser.add_argument(
        "--ai-scope",
        choices=["fallback", "always"],
        help="When to invoke AI suggestions",
    )
    parser.add_argument(
        "--ai-api-key",
        type=str,
        help="API key for the selected AI provider (falls back to environment variable)",
    )
    parser.add_argument(
        "--ai-timeout",
        type=int,
        help="Timeout in seconds for AI requests (default: 15)",
    )

    args = parser.parse_args()

    if args.web:
        if args.ask:
            print("Error: --ask cannot be combined with --web mode.")
            return
        if not FLASK_AVAILABLE:
            print("Error: Flask is required for web UI mode.")
            print("Install Flask with: pip install flask")
            print("Or use CLI mode without --web flag")
            return

        print(f"Starting File Organizer Web UI on http://127.0.0.1:{args.port}")
        print("Press Ctrl+C to stop the server")

        if not args.no_browser:
            def open_browser():
                time.sleep(1)
                webbrowser.open(f"http://127.0.0.1:{args.port}")

            threading.Thread(target=open_browser, daemon=True).start()

        try:
            run_web_server(port=args.port)
        except KeyboardInterrupt:
            print("\nShutting down web server...")
        return

    try:
        ai_config = build_ai_config(args)
    except ValueError as error:
        print(f"Error: {error}")
        return

    folder_path = args.folder
    organizer = FileOrganizer(folder_path, ai_config=ai_config)

    if args.ask:
        print(organizer.answer_question(args.ask))
        return

    moved_files = organizer.organize_files()
    print(f"Organization complete! Moved {moved_files} files.")


if __name__ == "__main__":
    main()
