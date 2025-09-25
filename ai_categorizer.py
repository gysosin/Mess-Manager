"""AI-powered categorization helpers for the File Organizer."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import requests

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "perplexity": "llama-3.1-sonar-small-128k-chat",
    "mistral": "mistral-small-latest",
}

API_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "perplexity": "https://api.perplexity.ai/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
}

PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}


class AICategorizerError(RuntimeError):
    """Raised when a call to an AI provider cannot be fulfilled."""


@dataclass
class AICategorizerConfig:
    provider: str
    api_key: str
    model: Optional[str] = None
    scope: str = "fallback"
    temperature: float = 0.0
    timeout: int = 15

    def normalized_provider(self) -> str:
        return self.provider.lower().strip()


def call_chat_completion(
    config: AICategorizerConfig,
    messages: Sequence[dict],
    *,
    max_tokens: int = 200,
    temperature: Optional[float] = None,
) -> dict:
    """Issue a chat completion request to the configured LLM provider."""

    provider = config.normalized_provider()
    if provider not in API_URLS:
        raise ValueError(f"Unsupported AI provider: {config.provider}")
    if not config.api_key:
        raise ValueError("API key is required when calling AI providers")

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": config.model or DEFAULT_MODELS[provider],
        "messages": list(messages),
        "temperature": config.temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
    }

    if provider == "perplexity":
        body["search_domain_filter"] = []
        body["return_search_results"] = False

    response = requests.post(
        API_URLS[provider],
        headers=headers,
        json=body,
        timeout=config.timeout,
    )
    response.raise_for_status()
    return response.json()


def extract_message(raw_response: dict) -> str:
    """Extract the assistant message text from a chat completion response."""

    choices = raw_response.get("choices", [])
    if not choices:
        raise AICategorizerError("No choices returned by AI provider")

    message = choices[0].get("message")
    if not message:
        raise AICategorizerError("Malformed response: missing message payload")

    content = message.get("content")
    if not content:
        raise AICategorizerError("Malformed response: empty message content")

    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    return str(content).strip()


def answer_question_with_ai(
    config: AICategorizerConfig,
    question: str,
    context: str,
    *,
    max_tokens: int = 220,
) -> str:
    """Use an AI provider to answer a question about organizer history."""

    system_prompt = (
        "You help users understand activity from a file organizer tool. "
        "Use the provided context only. If the context does not contain the answer, "
        "respond that the information is unavailable."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}\nAnswer succinctly:",
        },
    ]

    try:
        raw_response = call_chat_completion(config, messages, max_tokens=max_tokens, temperature=0.2)
    except requests.RequestException as exc:
        raise AICategorizerError(f"AI question request failed: {exc}") from exc

    return extract_message(raw_response)


class AICategorizer:
    """Wrapper around supported LLM providers to suggest file categories."""

    def __init__(self, config: AICategorizerConfig):
        provider = config.normalized_provider()
        if provider not in API_URLS:
            raise ValueError(f"Unsupported AI provider: {config.provider}")
        if not config.api_key:
            raise ValueError("API key is required when enabling AI categorization")

        self.config = config
        self.provider = provider
        self.scope = config.scope
        self.logger = logging.getLogger(__name__)

    def suggest_category(
        self,
        *,
        file_name: str,
        file_extension: str,
        categories: Iterable[str],
        default_category: str,
        file_size: Optional[int] = None,
    ) -> Optional[str]:
        """Return the category suggested by the language model, if any."""
        return self._suggest_category_only(
            file_name=file_name,
            file_extension=file_extension,
            categories=categories,
            default_category=default_category,
            file_size=file_size,
        )

    def suggest_category_and_subfolder(
        self,
        *,
        file_name: str,
        file_extension: str,
        categories: Iterable[str],
        default_category: str,
        file_size: Optional[int] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """Return the category and subfolder suggested by the language model."""

        category_list = list(categories)
        prompt_lines = [
            "You help organize files into predefined folders with intelligent subfolders.",
            "Analyze the file name to suggest both a category and a descriptive subfolder.",
            "Respond in this exact format: 'Category: [category] | Subfolder: [subfolder]'",
            "If no specific subfolder is needed, use 'General' as the subfolder.",
            "Available categories: " + ", ".join(category_list),
            f"File name: {file_name}",
            f"Extension: {file_extension or 'none'}",
            f"Default category from rules: {default_category}",
        ]
        if file_size is not None:
            prompt_lines.append(f"File size (bytes): {file_size}")

        prompt_lines.append("\nExamples:")
        prompt_lines.append("- vacation_photos.zip → Category: Pictures | Subfolder: Vacation")
        prompt_lines.append("- meeting_notes.pdf → Category: Documents | Subfolder: Work")
        prompt_lines.append("- game_soundtrack.mp3 → Category: Music | Subfolder: Games")
        prompt_lines.append("- python_installer.exe → Category: Programs | Subfolder: Development")

        user_prompt = "\n".join(prompt_lines)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant for organizing download folders with intelligent subfolders. "
                    "Always respond in the exact format: 'Category: [category] | Subfolder: [subfolder]'"
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

        try:
            raw_response = call_chat_completion(
                self.config,
                messages,
                max_tokens=30,
                temperature=0.1,
            )
        except requests.RequestException as exc:
            raise AICategorizerError(f"Request to {self.provider} failed: {exc}") from exc

        message_content = extract_message(raw_response)
        return self._parse_category_and_subfolder(message_content, category_list)

    def _suggest_category_only(
        self,
        *,
        file_name: str,
        file_extension: str,
        categories: Iterable[str],
        default_category: str,
        file_size: Optional[int] = None,
    ) -> Optional[str]:
        """Return the category suggested by the language model, if any."""

        category_list = list(categories)
        prompt_lines = [
            "You help organize files into predefined folders.",
            "Choose the single best matching category for the file from the provided list.",
            "Respond with exactly one category name and nothing else.",
            "Available categories: " + ", ".join(category_list),
            f"File name: {file_name}",
            f"Extension: {file_extension or 'none'}",
            f"Default category from rules: {default_category}",
        ]
        if file_size is not None:
            prompt_lines.append(f"File size (bytes): {file_size}")

        user_prompt = "\n".join(prompt_lines)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant for organizing download folders. "
                    "Only respond with a category name from the provided list."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

        try:
            raw_response = call_chat_completion(
                self.config,
                messages,
                max_tokens=10,
                temperature=self.config.temperature,
            )
        except requests.RequestException as exc:
            raise AICategorizerError(f"Request to {self.provider} failed: {exc}") from exc

        message_content = extract_message(raw_response)
        suggestion = self._extract_category_name(message_content, category_list)
        if suggestion:
            return suggestion

        self.logger.debug(
            "AI provider %s returned an unrecognized category: %s", self.provider, message_content
        )
        return None

    @staticmethod
    def _parse_category_and_subfolder(message: str, categories: Iterable[str]) -> tuple[Optional[str], Optional[str]]:
        """Parse the AI response to extract category and subfolder."""
        if not message:
            return None, None

        # Look for the expected format: "Category: [category] | Subfolder: [subfolder]"
        import re
        pattern = r"Category:\s*([^|]+?)\s*\|\s*Subfolder:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, message.strip(), re.IGNORECASE)

        if match:
            suggested_category = match.group(1).strip()
            suggested_subfolder = match.group(2).strip()

            # Validate category exists
            for category in categories:
                if suggested_category.lower() == category.lower():
                    return category, suggested_subfolder if suggested_subfolder.lower() != 'general' else None

        # Fallback - try to extract just the category
        for category in categories:
            if category.lower() in message.lower():
                return category, None

        return None, None

    @staticmethod
    def _extract_category_name(message: str, categories: Iterable[str]) -> Optional[str]:
        if not message:
            return None

        first_line = message.strip().splitlines()[0]
        normalized_first_line = first_line.strip().lower()
        for category in categories:
            if normalized_first_line == category.lower():
                return category

        normalized_message = message.lower()
        for category in categories:
            if category.lower() in normalized_message:
                return category

        return None
