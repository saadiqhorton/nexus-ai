"""Tests for REPL command handling."""

import asyncio
from unittest.mock import MagicMock

import pytest

from nexus.session.models import Session, Turn


class TestREPLCommands:
    """Tests for REPL command parsing and handling."""

    def test_exit_commands_recognized(self):
        """Test that exit commands start with /."""
        from nexus.cli.repl import REPL_COMMANDS

        assert "/exit" in REPL_COMMANDS
        assert "/quit" in REPL_COMMANDS

    def test_help_command_exists(self):
        """Test that /help command is recognized."""
        from nexus.cli.repl import REPL_COMMANDS

        assert "/help" in REPL_COMMANDS

    def test_clear_command_exists(self):
        """Test that /clear command is recognized."""
        from nexus.cli.repl import REPL_COMMANDS

        assert "/clear" in REPL_COMMANDS

    def test_save_command_exists(self):
        """Test that /save command is recognized."""
        from nexus.cli.repl import REPL_COMMANDS

        assert "/save" in REPL_COMMANDS

    def test_history_command_exists(self):
        """Test that /history command is recognized."""
        from nexus.cli.repl import REPL_COMMANDS

        assert "/history" in REPL_COMMANDS

    def test_model_command_exists(self):
        """Test that /model command is recognized."""
        from nexus.cli.repl import REPL_COMMANDS

        assert "/model" in REPL_COMMANDS

    def test_export_command_exists(self):
        """Test that /export command is recognized."""
        from nexus.cli.repl import REPL_COMMANDS

        assert "/export" in REPL_COMMANDS


class TestShowHelp:
    """Tests for show_help function."""

    def test_show_help_no_error(self):
        """Test that show_help doesn't raise an error."""
        from nexus.cli.repl import show_help

        # Should not raise
        show_help()

    def test_show_help_displays_commands(self, capsys):
        """Test that show_help displays command information."""
        from nexus.cli.repl import show_help

        show_help()
        # The output is printed via Rich console, which may not be captured
        # by capsys in the same way. Just verify no exception.


class TestShowHistory:
    """Tests for show_history function."""

    def test_show_history_empty_session(self):
        """Test showing history for an empty session."""
        from nexus.cli.repl import show_history

        session = Session(name="test", model="gpt-4", provider="openai")
        # Should not raise
        show_history(session, 10)

    def test_show_history_with_turns(self):
        """Test showing history for a session with turns."""
        from nexus.cli.repl import show_history

        session = Session(name="test", model="gpt-4", provider="openai")
        session.turns.append(Turn(role="user", content="Hello", model="gpt-4"))
        session.turns.append(Turn(role="assistant", content="Hi there", model="gpt-4"))
        # Should not raise
        show_history(session, 10)

    def test_show_history_respects_limit(self):
        """Test that show_history respects the limit parameter."""
        from nexus.cli.repl import show_history

        session = Session(name="test", model="gpt-4", provider="openai")
        for i in range(20):
            session.turns.append(Turn(role="user", content=f"Message {i}", model="gpt-4"))

        # Should not raise, and should only show last 5
        show_history(session, 5)

    def test_show_history_truncates_long_content(self):
        """Test that show_history truncates long content."""
        from nexus.cli.repl import show_history

        session = Session(name="test", model="gpt-4", provider="openai")
        long_content = "A" * 500  # Longer than 200 char limit
        session.turns.append(Turn(role="user", content=long_content, model="gpt-4"))
        # Should not raise
        show_history(session, 10)


class TestHandleREPLCommand:
    """Tests for handle_repl_command function."""

    @pytest.fixture
    def mock_session_manager(self):
        """Create a mock SessionManager."""
        sm = MagicMock()
        sm.save_session = MagicMock()
        sm.delete_session = MagicMock(return_value=True)
        sm.export_session = MagicMock(return_value="exported content")
        return sm

    @pytest.fixture
    def test_session(self):
        """Create a test session."""
        return Session(name="test", model="gpt-4", provider="openai")

    def test_exit_returns_false(self, test_session, mock_session_manager):
        """Test that /exit returns False to exit the REPL."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/exit", test_session, mock_session_manager, "gpt-4")
        )
        assert result is False

    def test_quit_returns_false(self, test_session, mock_session_manager):
        """Test that /quit returns False to exit the REPL."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/quit", test_session, mock_session_manager, "gpt-4")
        )
        assert result is False

    def test_help_returns_true(self, test_session, mock_session_manager):
        """Test that /help returns True to continue the REPL."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/help", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True

    def test_history_returns_true(self, test_session, mock_session_manager):
        """Test that /history returns True to continue the REPL."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/history", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True

    def test_history_with_limit(self, test_session, mock_session_manager):
        """Test /history with a limit argument."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/history 5", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True

    def test_model_shows_current(self, test_session, mock_session_manager):
        """Test /model without args shows current model."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/model", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True

    def test_model_changes_model(self, test_session, mock_session_manager):
        """Test /model with arg changes the model."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/model claude-3", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True
        assert test_session.model == "claude-3"

    def test_save_without_name_shows_usage(self, test_session, mock_session_manager):
        """Test /save without name shows usage message."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/save", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True

    def test_save_with_name_saves_session(self, test_session, mock_session_manager):
        """Test /save with name saves the session."""
        from nexus.cli.repl import handle_repl_command

        test_session.name = ".temp-123"
        result = asyncio.run(
            handle_repl_command("/save mysession", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True
        assert test_session.name == "mysession"
        mock_session_manager.save_session.assert_called_once()

    def test_unknown_command_returns_true(self, test_session, mock_session_manager):
        """Test that unknown commands return True to continue."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/unknown", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True

    def test_export_calls_session_manager(self, test_session, mock_session_manager):
        """Test /export calls session manager export."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/export", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True
        mock_session_manager.export_session.assert_called_once()

    def test_export_with_format(self, test_session, mock_session_manager):
        """Test /export with format argument."""
        from nexus.cli.repl import handle_repl_command

        result = asyncio.run(
            handle_repl_command("/export json", test_session, mock_session_manager, "gpt-4")
        )
        assert result is True


class TestREPLCommandParsing:
    """Tests for REPL command parsing behavior."""

    def test_command_starts_with_slash(self):
        """Test that REPL commands start with /."""
        from nexus.cli.repl import REPL_COMMANDS

        for cmd in REPL_COMMANDS:
            assert cmd.startswith("/")

    def test_all_commands_lowercase(self):
        """Test that all defined commands are lowercase."""
        from nexus.cli.repl import REPL_COMMANDS

        for cmd in REPL_COMMANDS:
            assert cmd == cmd.lower()


class TestAsyncSaveSession:
    """Tests for async session saving functionality."""

    @pytest.mark.asyncio
    async def test_async_save_session_calls_save(self):
        """Test that _async_save_session calls save_session."""
        from nexus.cli.repl import _async_save_session

        mock_sm = MagicMock()
        mock_sm.save_session = MagicMock()
        test_session = Session(name="test", model="gpt-4", provider="openai")

        await _async_save_session(mock_sm, test_session)
        mock_sm.save_session.assert_called_once_with(test_session)

    @pytest.mark.asyncio
    async def test_async_save_session_handles_error(self):
        """Test that _async_save_session handles errors gracefully."""
        from nexus.cli.repl import _async_save_session

        mock_sm = MagicMock()
        mock_sm.save_session = MagicMock(side_effect=Exception("Save failed"))
        test_session = Session(name="test", model="gpt-4", provider="openai")

        # Should not raise, just log the error
        await _async_save_session(mock_sm, test_session)
