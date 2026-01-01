"""Session manager for handling session persistence and operations."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from nexus.session.models import SearchResult, Session, Turn
from nexus.utils.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages session persistence and operations."""

    def __init__(self, sessions_dir: Path):
        """Initialize session manager.

        Args:
            sessions_dir: Directory to store session files.
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"SessionManager initialized with dir: {self.sessions_dir}")

        # Auto-cleanup temp sessions on init
        self.cleanup_temp_sessions()

    def _get_session_path(self, name: str) -> Path:
        """Get the file path for a session."""
        return self.sessions_dir / f"{name}.json"

    def _sanitize_name(self, name: str) -> str:
        """Sanitize session name for filesystem safety."""
        # Replace problematic characters with underscores
        invalid_chars = '<>:"/\\|?*'
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")
        return sanitized.strip()

    def get_or_create_session(self, name: str, model: str, provider: str) -> Session:
        """Get existing session or create a new one.

        Args:
            name: Session name.
            model: Model identifier.
            provider: Provider name.

        Returns:
            Session object.
        """
        session = self.load_session(name)
        if session is not None:
            return session
        return self.create_session(name, model, provider)

    def create_session(self, name: str, model: str, provider: str) -> Session:
        """Create a new session.

        Args:
            name: Session name.
            model: Model identifier.
            provider: Provider name.

        Returns:
            New Session object.
        """
        sanitized_name = self._sanitize_name(name)
        session = Session(
            name=sanitized_name,
            model=model,
            provider=provider,
        )
        self.save_session(session)
        logger.info(f"Created new session: {sanitized_name}")
        return session

    def load_session(self, name: str) -> Optional[Session]:
        """Load a session from disk.

        Args:
            name: Session name.

        Returns:
            Session object if found, None otherwise.
        """
        sanitized_name = self._sanitize_name(name)
        session_path = self._get_session_path(sanitized_name)

        if not session_path.exists():
            return None

        try:
            with open(session_path, encoding="utf-8") as f:
                data = f.read()
            session = Session.model_validate_json(data)
            logger.debug(f"Loaded session: {sanitized_name}")
            return session
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted session file {session_path}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load session {sanitized_name}: {e}")
            return None

    def save_session(self, session: Session) -> None:
        """Save a session to disk with atomic write.

        Args:
            session: Session object to save.
        """
        session.updated_at = datetime.now()
        session_path = self._get_session_path(session.name)
        tmp_path = session_path.with_suffix(".tmp")

        try:
            # Write to temp file first
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(session.model_dump_json(indent=2))

            # Atomic rename
            tmp_path.replace(session_path)
            logger.debug(f"Saved session: {session.name}")
        except Exception as e:
            logger.error(f"Failed to save session {session.name}: {e}")
            # Clean up temp file if it exists
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def add_turn(self, session: Session, turn: Turn, save: bool = False) -> None:
        """Add a turn to a session.

        Args:
            session: Session to add turn to.
            turn: Turn to add.
            save: Whether to save immediately (default False).
        """
        session.turns.append(turn)
        session.total_tokens += turn.tokens.get("total", 0)
        if save:
            self.save_session(session)
        logger.debug(f"Added turn to session {session.name}")

    def list_sessions(self) -> List[Session]:
        """List all sessions.

        Returns:
            List of Session objects (excluding temp sessions).
        """
        sessions = []
        for path in self.sessions_dir.glob("*.json"):
            # Skip temp sessions
            if path.stem.startswith(".temp-"):
                continue

            session = self.load_session(path.stem)
            if session is not None:
                sessions.append(session)

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def delete_session(self, name: str) -> bool:
        """Delete a session.

        Args:
            name: Session name to delete.

        Returns:
            True if deleted, False if not found.
        """
        sanitized_name = self._sanitize_name(name)
        session_path = self._get_session_path(sanitized_name)

        if not session_path.exists():
            logger.warning(f"Session not found: {sanitized_name}")
            return False

        try:
            session_path.unlink()
            logger.info(f"Deleted session: {sanitized_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {sanitized_name}: {e}")
            return False

    def rename_session(self, old_name: str, new_name: str) -> bool:
        """Rename a session.

        Args:
            old_name: Current session name.
            new_name: New session name.

        Returns:
            True if renamed, False otherwise.
        """
        old_sanitized = self._sanitize_name(old_name)
        new_sanitized = self._sanitize_name(new_name)

        old_path = self._get_session_path(old_sanitized)
        new_path = self._get_session_path(new_sanitized)

        if not old_path.exists():
            logger.warning(f"Session not found: {old_sanitized}")
            return False

        if new_path.exists():
            logger.warning(f"Session already exists: {new_sanitized}")
            return False

        try:
            session = self.load_session(old_sanitized)
            if session is None:
                return False

            session.name = new_sanitized
            self.save_session(session)
            old_path.unlink()
            logger.info(f"Renamed session: {old_sanitized} -> {new_sanitized}")
            return True
        except Exception as e:
            logger.error(f"Failed to rename session: {e}")
            return False

    def search_sessions(self, query: str) -> List[SearchResult]:
        """Search sessions by name or content.

        Args:
            query: Search query string.

        Returns:
            List of SearchResult objects.
        """
        results = []
        query_lower = query.lower()

        for path in self.sessions_dir.glob("*.json"):
            # Skip temp sessions
            if path.stem.startswith(".temp-"):
                continue

            session = self.load_session(path.stem)
            if session is None:
                continue

            # Check name match
            if query_lower in session.name.lower():
                results.append(
                    SearchResult(
                        session_name=session.name,
                        match_type="name",
                        matched_text=session.name,
                        turn_count=len(session.turns),
                        updated_at=session.updated_at,
                    )
                )
                continue

            # Check content match in turns
            for turn in session.turns:
                if query_lower in turn.content.lower():
                    results.append(
                        SearchResult(
                            session_name=session.name,
                            match_type="content",
                            matched_text=turn.content,
                            turn_count=len(session.turns),
                            updated_at=session.updated_at,
                        )
                    )
                    break  # Only one result per session

        # Sort by updated_at descending
        results.sort(key=lambda r: r.updated_at, reverse=True)
        return results

    def get_temp_session(self, model: str, provider: str) -> Session:
        """Create a temporary session.

        Args:
            model: Model identifier.
            provider: Provider name.

        Returns:
            New temporary Session object.
        """
        timestamp = int(time.time() * 1000)
        temp_name = f".temp-{timestamp}"
        return self.create_session(temp_name, model, provider)

    def cleanup_temp_sessions(self, max_age_hours: int = 24) -> None:
        """Clean up old temporary sessions.

        Args:
            max_age_hours: Maximum age in hours before cleanup.
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        for path in self.sessions_dir.glob(".temp-*.json"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff_time:
                    path.unlink()
                    cleaned_count += 1
                    logger.debug(f"Cleaned up temp session: {path.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp session {path.name}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} temp session(s)")

    def export_session(self, name: str, format: str) -> str:
        """Export a session to a string format.

        Args:
            name: Session name to export.
            format: Export format ('json', 'markdown', 'text').

        Returns:
            Exported session as string.

        Raises:
            ValueError: If session not found or invalid format.
        """
        session = self.load_session(name)
        if session is None:
            raise ValueError(f"Session not found: {name}")

        if format == "json":
            return session.model_dump_json(indent=2)

        elif format == "markdown":
            lines = [
                f"# Session: {session.name}",
                "",
                f"**Created:** {session.created_at.isoformat()}",
                f"**Updated:** {session.updated_at.isoformat()}",
                f"**Model:** {session.model}",
                f"**Provider:** {session.provider}",
                f"**Total Tokens:** {session.total_tokens}",
                "",
                "---",
                "",
            ]
            for turn in session.turns:
                role_label = "User" if turn.role == "user" else "Assistant"
                lines.append(f"## {role_label}")
                lines.append("")
                lines.append(turn.content)
                lines.append("")
            return "\n".join(lines)

        elif format == "text":
            lines = [
                f"Session: {session.name}",
                f"Created: {session.created_at.isoformat()}",
                f"Model: {session.model} ({session.provider})",
                "",
                "-" * 40,
                "",
            ]
            for turn in session.turns:
                role_label = "User" if turn.role == "user" else "Assistant"
                lines.append(f"[{role_label}]")
                lines.append(turn.content)
                lines.append("")
            return "\n".join(lines)

        else:
            raise ValueError(f"Invalid export format: {format}")
