"""Tests for SessionManager operations."""

import time

import pytest

from nexus.session.manager import SessionManager
from nexus.session.models import Turn


@pytest.fixture
def session_manager(tmp_path):
    """Create a SessionManager with a temporary directory."""
    return SessionManager(tmp_path / "sessions")


class TestSessionManagerInit:
    """Tests for SessionManager initialization."""

    def test_creates_sessions_directory(self, tmp_path):
        """Test that SessionManager creates the sessions directory."""
        sessions_dir = tmp_path / "sessions"
        assert not sessions_dir.exists()
        SessionManager(sessions_dir)
        assert sessions_dir.exists()

    def test_uses_existing_directory(self, tmp_path):
        """Test that SessionManager uses an existing directory."""
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        sm = SessionManager(sessions_dir)
        assert sm.sessions_dir == sessions_dir


class TestCreateSession:
    """Tests for creating sessions."""

    def test_create_session(self, session_manager):
        """Test creating a new session."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        assert session.name == "test"
        assert session.model == "gpt-4"
        assert session.provider == "openai"

        # Verify file exists
        session_file = session_manager.sessions_dir / "test.json"
        assert session_file.exists()

    def test_create_session_sanitizes_name(self, session_manager):
        """Test that session names are sanitized."""
        session = session_manager.create_session("test/name:with*chars", "gpt-4", "openai")
        # Invalid characters should be replaced with underscores
        assert "/" not in session.name
        assert ":" not in session.name
        assert "*" not in session.name

    def test_create_multiple_sessions(self, session_manager):
        """Test creating multiple sessions."""
        session1 = session_manager.create_session("session1", "gpt-4", "openai")
        session2 = session_manager.create_session("session2", "claude-3", "anthropic")

        assert session1.name == "session1"
        assert session2.name == "session2"
        assert session1.id != session2.id


class TestLoadSession:
    """Tests for loading sessions."""

    def test_load_session(self, session_manager):
        """Test loading an existing session."""
        session_manager.create_session("test", "gpt-4", "openai")
        loaded = session_manager.load_session("test")
        assert loaded is not None
        assert loaded.name == "test"
        assert loaded.model == "gpt-4"

    def test_load_nonexistent_session(self, session_manager):
        """Test loading a session that doesn't exist."""
        loaded = session_manager.load_session("nonexistent")
        assert loaded is None

    def test_load_session_with_turns(self, session_manager):
        """Test loading a session with conversation turns."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn = Turn(role="user", content="Hello", model="gpt-4", tokens={"total": 10})
        session_manager.add_turn(session, turn)
        session_manager.save_session(session)

        loaded = session_manager.load_session("test")
        assert len(loaded.turns) == 1
        assert loaded.turns[0].content == "Hello"


class TestGetOrCreateSession:
    """Tests for get_or_create_session."""

    def test_get_or_create_new(self, session_manager):
        """Test creating a new session via get_or_create."""
        session = session_manager.get_or_create_session("new", "gpt-4", "openai")
        assert session.name == "new"
        assert session.model == "gpt-4"

    def test_get_or_create_existing(self, session_manager):
        """Test loading an existing session via get_or_create."""
        session_manager.create_session("existing", "gpt-4", "openai")
        session = session_manager.get_or_create_session("existing", "claude", "anthropic")
        # Should load existing, not create with new model
        assert session.model == "gpt-4"
        assert session.provider == "openai"


class TestAddTurn:
    """Tests for adding turns to sessions."""

    def test_add_turn(self, session_manager):
        """Test adding a turn to a session."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn = Turn(role="user", content="Hello", model="gpt-4")
        session_manager.add_turn(session, turn)
        assert len(session.turns) == 1
        assert session.turns[0].content == "Hello"

    def test_add_turn_with_tokens(self, session_manager):
        """Test that adding turns updates total_tokens."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn = Turn(role="user", content="Hello", model="gpt-4", tokens={"total": 10})
        session_manager.add_turn(session, turn)
        assert session.total_tokens == 10

    def test_add_multiple_turns(self, session_manager):
        """Test adding multiple turns."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn1 = Turn(role="user", content="Hello", model="gpt-4", tokens={"total": 5})
        turn2 = Turn(role="assistant", content="Hi!", model="gpt-4", tokens={"total": 3})
        session_manager.add_turn(session, turn1)
        session_manager.add_turn(session, turn2)
        assert len(session.turns) == 2
        assert session.total_tokens == 8


class TestSaveSession:
    """Tests for saving sessions."""

    def test_save_session(self, session_manager):
        """Test saving a session to disk."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn = Turn(role="user", content="Hello", model="gpt-4", tokens={"total": 10})
        session_manager.add_turn(session, turn)
        session_manager.save_session(session)

        loaded = session_manager.load_session("test")
        assert len(loaded.turns) == 1
        assert loaded.total_tokens == 10

    def test_save_updates_updated_at(self, session_manager):
        """Test that saving updates the updated_at timestamp."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        original_updated = session.updated_at

        # Small delay to ensure different timestamp
        time.sleep(0.01)
        session_manager.save_session(session)

        loaded = session_manager.load_session("test")
        assert loaded.updated_at > original_updated


class TestDeleteSession:
    """Tests for deleting sessions."""

    def test_delete_session(self, session_manager):
        """Test deleting an existing session."""
        session_manager.create_session("test", "gpt-4", "openai")
        assert session_manager.delete_session("test") is True
        assert session_manager.load_session("test") is None

    def test_delete_nonexistent(self, session_manager):
        """Test deleting a session that doesn't exist."""
        assert session_manager.delete_session("nonexistent") is False


class TestRenameSession:
    """Tests for renaming sessions."""

    def test_rename_session(self, session_manager):
        """Test renaming a session."""
        session_manager.create_session("old", "gpt-4", "openai")
        assert session_manager.rename_session("old", "new") is True
        assert session_manager.load_session("old") is None
        assert session_manager.load_session("new") is not None

    def test_rename_to_existing(self, session_manager):
        """Test renaming to an existing session name fails."""
        session_manager.create_session("a", "gpt-4", "openai")
        session_manager.create_session("b", "gpt-4", "openai")
        assert session_manager.rename_session("a", "b") is False
        # Original should still exist
        assert session_manager.load_session("a") is not None

    def test_rename_nonexistent(self, session_manager):
        """Test renaming a session that doesn't exist fails."""
        assert session_manager.rename_session("nonexistent", "new") is False

    def test_rename_preserves_content(self, session_manager):
        """Test that rename preserves session content."""
        session = session_manager.create_session("old", "gpt-4", "openai")
        turn = Turn(role="user", content="Hello", model="gpt-4")
        session_manager.add_turn(session, turn)
        session_manager.save_session(session)

        session_manager.rename_session("old", "new")
        loaded = session_manager.load_session("new")
        assert len(loaded.turns) == 1
        assert loaded.turns[0].content == "Hello"


class TestListSessions:
    """Tests for listing sessions."""

    def test_list_sessions_empty(self, session_manager):
        """Test listing when no sessions exist."""
        sessions = session_manager.list_sessions()
        assert len(sessions) == 0

    def test_list_sessions(self, session_manager):
        """Test listing multiple sessions."""
        session_manager.create_session("a", "gpt-4", "openai")
        session_manager.create_session("b", "claude", "anthropic")
        sessions = session_manager.list_sessions()
        assert len(sessions) == 2

    def test_list_sessions_excludes_temp(self, session_manager):
        """Test that temp sessions are excluded from list."""
        session_manager.create_session("regular", "gpt-4", "openai")
        session_manager.get_temp_session("gpt-4", "openai")
        sessions = session_manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].name == "regular"

    def test_list_sessions_sorted_by_updated(self, session_manager):
        """Test that sessions are sorted by updated_at descending."""
        session_manager.create_session("first", "gpt-4", "openai")
        time.sleep(0.01)
        session_manager.create_session("second", "gpt-4", "openai")

        sessions = session_manager.list_sessions()
        assert sessions[0].name == "second"  # Most recently updated first
        assert sessions[1].name == "first"


class TestSearchSessions:
    """Tests for searching sessions."""

    def test_search_by_name(self, session_manager):
        """Test searching sessions by name."""
        session_manager.create_session("quantum-research", "gpt-4", "openai")
        session_manager.create_session("other", "gpt-4", "openai")
        results = session_manager.search_sessions("quantum")
        assert len(results) == 1
        assert results[0].match_type == "name"
        assert results[0].session_name == "quantum-research"

    def test_search_by_content(self, session_manager):
        """Test searching sessions by content."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn = Turn(role="user", content="explain quantum computing", model="gpt-4")
        session_manager.add_turn(session, turn)
        session_manager.save_session(session)

        results = session_manager.search_sessions("quantum")
        assert len(results) == 1
        assert results[0].match_type == "content"
        assert "quantum" in results[0].matched_text.lower()

    def test_search_case_insensitive(self, session_manager):
        """Test that search is case insensitive."""
        session_manager.create_session("QUANTUM", "gpt-4", "openai")
        results = session_manager.search_sessions("quantum")
        assert len(results) == 1

    def test_search_no_results(self, session_manager):
        """Test search with no matches."""
        session_manager.create_session("test", "gpt-4", "openai")
        results = session_manager.search_sessions("xyz")
        assert len(results) == 0

    def test_search_excludes_temp_sessions(self, session_manager):
        """Test that temp sessions are excluded from search."""
        temp = session_manager.get_temp_session("gpt-4", "openai")
        turn = Turn(role="user", content="quantum test", model="gpt-4")
        session_manager.add_turn(temp, turn)
        session_manager.save_session(temp)

        results = session_manager.search_sessions("quantum")
        assert len(results) == 0

    def test_search_name_takes_priority(self, session_manager):
        """Test that name match takes priority over content match."""
        session = session_manager.create_session("quantum", "gpt-4", "openai")
        turn = Turn(role="user", content="explain quantum physics", model="gpt-4")
        session_manager.add_turn(session, turn)
        session_manager.save_session(session)

        results = session_manager.search_sessions("quantum")
        assert len(results) == 1
        assert results[0].match_type == "name"


class TestTempSession:
    """Tests for temporary sessions."""

    def test_temp_session(self, session_manager):
        """Test creating a temporary session."""
        temp = session_manager.get_temp_session("gpt-4", "openai")
        assert temp.name.startswith(".temp-")

    def test_temp_session_unique(self, session_manager):
        """Test that temp sessions have unique names."""
        temp1 = session_manager.get_temp_session("gpt-4", "openai")
        time.sleep(0.002)  # Ensure different timestamp
        temp2 = session_manager.get_temp_session("gpt-4", "openai")
        assert temp1.name != temp2.name


class TestCleanupTempSessions:
    """Tests for cleanup of temp sessions."""

    def test_cleanup_old_temp_sessions(self, session_manager, tmp_path):
        """Test that old temp sessions are cleaned up."""
        # Create temp session file manually with old timestamp
        sessions_dir = session_manager.sessions_dir
        old_temp_file = sessions_dir / ".temp-old.json"
        old_temp_file.write_text(
            '{"name": ".temp-old", "model": "gpt-4", "provider": "openai", "id": "x", "created_at": "2020-01-01T00:00:00", "updated_at": "2020-01-01T00:00:00", "total_tokens": 0, "turns": []}'
        )

        # Set modification time to 2 days ago
        import os

        old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago
        os.utime(old_temp_file, (old_time, old_time))

        # Run cleanup (should remove files older than 24 hours by default)
        session_manager.cleanup_temp_sessions(max_age_hours=24)

        assert not old_temp_file.exists()

    def test_cleanup_keeps_recent_temp_sessions(self, session_manager):
        """Test that recent temp sessions are kept."""
        temp = session_manager.get_temp_session("gpt-4", "openai")
        temp_file = session_manager.sessions_dir / f"{temp.name}.json"
        assert temp_file.exists()

        session_manager.cleanup_temp_sessions(max_age_hours=24)
        assert temp_file.exists()


class TestExportSession:
    """Tests for exporting sessions."""

    def test_export_json(self, session_manager):
        """Test exporting session as JSON."""
        session_manager.create_session("test", "gpt-4", "openai")
        content = session_manager.export_session("test", "json")
        assert '"name": "test"' in content
        assert '"model": "gpt-4"' in content

    def test_export_markdown(self, session_manager):
        """Test exporting session as Markdown."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn = Turn(role="user", content="Hello", model="gpt-4")
        session_manager.add_turn(session, turn)
        session_manager.save_session(session)

        content = session_manager.export_session("test", "markdown")
        assert "# Session: test" in content
        assert "Hello" in content
        assert "**Model:** gpt-4" in content

    def test_export_text(self, session_manager):
        """Test exporting session as plain text."""
        session = session_manager.create_session("test", "gpt-4", "openai")
        turn = Turn(role="user", content="Hello", model="gpt-4")
        session_manager.add_turn(session, turn)
        session_manager.save_session(session)

        content = session_manager.export_session("test", "text")
        assert "Session: test" in content
        assert "Hello" in content
        assert "[User]" in content

    def test_export_nonexistent_session(self, session_manager):
        """Test exporting a session that doesn't exist."""
        with pytest.raises(ValueError) as excinfo:
            session_manager.export_session("nonexistent", "json")
        assert "not found" in str(excinfo.value).lower()

    def test_export_invalid_format(self, session_manager):
        """Test exporting with invalid format."""
        session_manager.create_session("test", "gpt-4", "openai")
        with pytest.raises(ValueError) as excinfo:
            session_manager.export_session("test", "invalid")
        assert "Invalid export format" in str(excinfo.value)
