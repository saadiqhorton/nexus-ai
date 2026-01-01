import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote

from nexus.utils.errors import PromptSecurityError
from nexus.utils.logging import get_logger

logger = get_logger("prompts.manager")


class PromptManager:
    """Manages reusable system prompts (patterns) stored in markdown files."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path.resolve()
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize prompt name to prevent path traversal attacks.

        Args:
            name: User-provided prompt name

        Returns:
            Sanitized name safe for filesystem operations

        Raises:
            PromptSecurityError: If name is empty or contains no valid characters
        """
        if not name or not isinstance(name, str):
            logger.warning(f"Invalid prompt name type: {type(name)}")
            raise PromptSecurityError("Prompt name must be a non-empty string")

        # Remove any whitespace from edges
        name = name.strip()

        if not name:
            logger.warning("Prompt name is empty after stripping whitespace")
            raise PromptSecurityError("Prompt name cannot be empty")

        for _ in range(2):
            decoded = unquote(name)
            if decoded == name:
                break
            name = decoded

        # Normalize separators and strip null bytes before sanitization
        name = name.replace("\x00", "")
        name = name.replace("∕", "/").replace("／", "/").replace("＼", "\\")

        # Strip leading dot/relative or absolute path markers
        name = name.lstrip(".\\/").strip()

        # Remove parent directory traversal sequences
        while ".." in name:
            name = name.replace("..", "__")

        # Replace any non-alphanumeric characters except hyphens, underscores, and dots
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", name)

        if not sanitized:
            logger.warning(
                f"Prompt name contains no valid characters: {name!r}",
                extra={"security_event": "invalid_name", "input": name},
            )
            raise PromptSecurityError(
                "Prompt name must contain at least one alphanumeric character, hyphen, or underscore"
            )

        # Additional check: ensure the resolved path stays within storage_path
        # This is defense-in-depth even after sanitization
        test_path = (self.storage_path / f"{sanitized}.md").resolve()
        try:
            test_path.relative_to(self.storage_path)
        except ValueError:
            logger.error(
                f"Path traversal detected after sanitization: {name!r} -> {test_path}",
                extra={
                    "security_event": "path_traversal_post_sanitization",
                    "input": name,
                    "resolved_path": str(test_path),
                },
            )
            raise PromptSecurityError("Invalid prompt name: path traversal detected")

        if sanitized != name:
            logger.info(
                f"Prompt name sanitized: {name!r} -> {sanitized!r}",
                extra={"original": name, "sanitized": sanitized},
            )

        return sanitized[:255]

    def list_prompts(self) -> List[str]:
        """List available prompts by name (filename without extension)."""
        if not self.storage_path.exists():
            return []

        prompts = []
        for file in self.storage_path.glob("*.md"):
            prompts.append(file.stem)
        return sorted(prompts)

    def get_prompt(self, name: str) -> Optional[str]:
        """
        Get content of a prompt by name.

        Args:
            name: Prompt name (will be sanitized)

        Returns:
            Prompt content or None if not found

        Raises:
            PromptSecurityError: If name contains invalid characters or path traversal attempts
        """
        sanitized_name = self._sanitize_name(name)
        file_path = self.storage_path / f"{sanitized_name}.md"

        if not file_path.exists():
            return None

        logger.debug(f"Reading prompt: {sanitized_name}")
        return file_path.read_text(encoding="utf-8")

    def save_prompt(self, name: str, content: str) -> Path:
        """
        Save a prompt to storage.

        Args:
            name: Prompt name (will be sanitized)
            content: Prompt content

        Returns:
            Path to the saved file

        Raises:
            PromptSecurityError: If name contains invalid characters or path traversal attempts
        """
        sanitized_name = self._sanitize_name(name)
        file_path = self.storage_path / f"{sanitized_name}.md"

        logger.info(f"Saving prompt: {sanitized_name}")
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def delete_prompt(self, name: str) -> bool:
        """
        Delete a prompt. Returns True if deleted, False if not found.

        Args:
            name: Prompt name (will be sanitized)

        Returns:
            True if deleted, False if not found

        Raises:
            PromptSecurityError: If name contains invalid characters or path traversal attempts
        """
        sanitized_name = self._sanitize_name(name)
        file_path = self.storage_path / f"{sanitized_name}.md"

        if file_path.exists():
            logger.info(f"Deleting prompt: {sanitized_name}")
            file_path.unlink()
            return True

        return False
