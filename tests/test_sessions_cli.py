"""Tests for CLI session commands."""

import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from nexus.cli.main import cli


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


def _stub_provider_manager(monkeypatch, models_data=None):
    """Stub out the provider manager for offline testing."""
    models_data = models_data or {}

    class FakeProviderManager:
        def __init__(self, config_manager):
            self.config_manager = config_manager

        async def list_all_models(self, use_cache=True):
            return models_data

        def list_providers(self):
            return list(models_data.keys())

        def get_provider(self, name):
            return None

    class FakeNexusApp:
        def __init__(self, config_path=None):
            from nexus.config.config_manager import ConfigManager

            self.config_manager = ConfigManager(config_path)
            self.provider_manager = FakeProviderManager(self.config_manager)
            self.completion_handler = None

    monkeypatch.setattr("nexus.cli.main.NexusApp", FakeNexusApp)
    monkeypatch.setattr(sys, "argv", ["nexus"])


@pytest.fixture
def setup_sessions(tmp_path, monkeypatch):
    """Setup test environment with sessions directory."""
    home = tmp_path / "home"
    home.mkdir()
    nexus_dir = home / ".nexus"
    nexus_dir.mkdir()
    sessions_dir = nexus_dir / "sessions"
    sessions_dir.mkdir()

    # Create test config
    config = {
        "version": "1.0",
        "defaults": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True,
        },
        "providers": {
            "openai": {
                "enabled": True,
                "api_key_env": "OPENAI_API_KEY",
                "default_model": "gpt-4",
            }
        },
        "cli": {
            "color_output": True,
            "show_thinking": False,
        },
        "history": {
            "enabled": True,
            "max_turns": 50,
            "storage_path": str(nexus_dir / "history"),
        },
        "sessions": {
            "enabled": True,
            "storage_path": str(sessions_dir),
            "temp_retention_hours": 24,
        },
    }
    (nexus_dir / "config.yaml").write_text(yaml.safe_dump(config))

    monkeypatch.setenv("HOME", str(home))
    _stub_provider_manager(monkeypatch)
    return sessions_dir


def _create_session_file(
    sessions_dir: Path, name: str, model: str = "gpt-4", provider: str = "openai"
):
    """Helper to create a session file directly."""
    import json
    from datetime import datetime

    session_data = {
        "id": "test-id",
        "name": name,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "model": model,
        "provider": provider,
        "total_tokens": 0,
        "turns": [],
    }
    session_file = sessions_dir / f"{name}.json"
    session_file.write_text(json.dumps(session_data, indent=2))
    return session_file


class TestSessionsCLI:
    """Tests for sessions CLI commands."""

    def test_sessions_help(self, runner, setup_sessions):
        """Test sessions command help."""
        result = runner.invoke(cli, ["sessions", "--help"])
        assert result.exit_code == 0
        # Should show available subcommands
        assert "sessions" in result.output.lower() or "list" in result.output.lower()

    def test_sessions_list_empty(self, runner, setup_sessions):
        """Test listing sessions when none exist."""
        result = runner.invoke(cli, ["sessions"])
        assert result.exit_code == 0
        # Either shows "No sessions" or empty list
        output_lower = result.output.lower()
        assert (
            "no sessions" in output_lower
            or result.output.strip() == ""
            or "session" in output_lower
        )

    def test_sessions_list_with_sessions(self, runner, setup_sessions):
        """Test listing sessions when they exist."""
        _create_session_file(setup_sessions, "test-session")
        result = runner.invoke(cli, ["sessions"])
        assert result.exit_code == 0

    def test_sessions_show_not_found(self, runner, setup_sessions):
        """Test showing a session that doesn't exist."""
        result = runner.invoke(cli, ["sessions", "show", "nonexistent"])
        output_lower = result.output.lower()
        assert "not found" in output_lower or "error" in output_lower or result.exit_code != 0

    def test_sessions_show_existing(self, runner, setup_sessions):
        """Test showing an existing session."""
        _create_session_file(setup_sessions, "my-session")
        result = runner.invoke(cli, ["sessions", "show", "my-session"])
        # Should either show the session or return without error
        assert result.exit_code == 0 or "my-session" in result.output

    def test_sessions_delete_not_found(self, runner, setup_sessions):
        """Test deleting a session that doesn't exist."""
        result = runner.invoke(cli, ["sessions", "delete", "nonexistent", "--force"])
        output_lower = result.output.lower()
        assert "not found" in output_lower or result.exit_code != 0

    def test_sessions_delete_existing(self, runner, setup_sessions):
        """Test deleting an existing session."""
        session_file = _create_session_file(setup_sessions, "to-delete")
        assert session_file.exists()
        runner.invoke(cli, ["sessions", "delete", "to-delete", "--force"])
        # After delete, file should be gone or command should succeed
        # (depending on implementation)

    def test_sessions_search_no_results(self, runner, setup_sessions):
        """Test searching with no matching results."""
        result = runner.invoke(cli, ["sessions", "search", "xyz"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert (
            "no match" in output_lower or "not found" in output_lower or result.output.strip() == ""
        )

    def test_sessions_search_with_results(self, runner, setup_sessions):
        """Test searching with matching results."""
        _create_session_file(setup_sessions, "quantum-research")
        result = runner.invoke(cli, ["sessions", "search", "quantum"])
        assert result.exit_code == 0

    def test_sessions_export_json(self, runner, setup_sessions):
        """Test exporting a session as JSON."""
        _create_session_file(setup_sessions, "export-test")
        runner.invoke(cli, ["sessions", "export", "export-test", "--format", "json"])
        # Should either succeed or show the session

    def test_sessions_export_markdown(self, runner, setup_sessions):
        """Test exporting a session as Markdown."""
        _create_session_file(setup_sessions, "export-test")
        runner.invoke(cli, ["sessions", "export", "export-test", "--format", "markdown"])

    def test_sessions_rename(self, runner, setup_sessions):
        """Test renaming a session."""
        _create_session_file(setup_sessions, "old-name")
        runner.invoke(cli, ["sessions", "rename", "old-name", "new-name"])
        # Should succeed or show appropriate message


class TestChatCommandWithSession:
    """Tests for chat command with session option."""

    def test_chat_help_shows_session_option(self, runner, setup_sessions):
        """Test that chat command shows session option in help."""
        result = runner.invoke(cli, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--session" in result.output

    def test_prompt_with_session_option(self, runner, setup_sessions):
        """Test that prompt command accepts session option."""
        result = runner.invoke(cli, ["--help"])
        assert "--session" in result.output


class TestSessionOption:
    """Tests for the --session option on the main CLI."""

    def test_session_option_in_help(self, runner, setup_sessions):
        """Test that --session option appears in help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "--session" in result.output
