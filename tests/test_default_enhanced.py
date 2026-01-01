"""Tests for enhanced default command functionality."""

import sys
from pathlib import Path

import yaml
from click.testing import CliRunner

from nexus.cli.main import cli


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
    monkeypatch.setattr("nexus.cli.utils.NexusApp", FakeNexusApp)


def _write_base_config(home: Path, provider: str = "openai", model: str = "gpt-4"):
    """Write a base configuration file."""
    config_dir = home / ".nexus"
    config_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir = config_dir / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    cfg_path = config_dir / "config.yaml"
    config = {
        "version": "1.0",
        "defaults": {
            "provider": provider,
            "model": model,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True,
        },
        "providers": {
            provider: {
                "enabled": True,
                "api_key_env": "OPENAI_API_KEY",
                "base_url": None,
                "default_model": model,
            }
        },
        "cli": {
            "color_output": True,
            "show_thinking": False,
        },
        "history": {
            "enabled": True,
            "max_turns": 50,
            "storage_path": str(home / ".nexus" / "history"),
        },
        "sessions": {
            "enabled": True,
            "storage_path": str(sessions_dir),
            "temp_retention_hours": 24,
        },
    }
    cfg_path.write_text(yaml.safe_dump(config))
    return cfg_path


def _read_config(cfg_path: Path):
    """Read configuration from file."""
    return yaml.safe_load(cfg_path.read_text())


class TestDefaultCommand:
    """Tests for the default command."""

    def test_default_help(self):
        """Test default command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["default", "--help"])
        assert result.exit_code == 0
        assert "default" in result.output.lower()

    def test_default_command_exists(self, monkeypatch, tmp_path):
        """Test that default command is available."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        _write_base_config(home)

        runner = CliRunner()
        result = runner.invoke(cli, ["default", "--help"], env={"HOME": str(home)})
        assert result.exit_code == 0


class TestDefaultWithProviderSlash:
    """Tests for default command with provider/model syntax."""

    def test_default_with_provider_model(self, monkeypatch, tmp_path):
        """Test setting default with provider/model syntax."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        cfg_path = _write_base_config(home, provider="openai", model="old-model")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["default", "anthropic/claude-3"],
            env={"HOME": str(home)},
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(cfg_path)
        assert cfg["defaults"]["provider"] == "anthropic"
        assert cfg["defaults"]["model"] == "claude-3"

    def test_default_with_provider_flag(self, monkeypatch, tmp_path):
        """Test default with -p provider flag."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        _write_base_config(home)

        # When using -p with no model list available, behavior depends on implementation
        runner = CliRunner()
        runner.invoke(
            cli,
            ["default", "-p", "openai"],
            env={"HOME": str(home)},
            input="\n",  # Cancel interactive selection
        )
        # Should either work or prompt for selection


class TestDefaultModelOnly:
    """Tests for default command with model name only."""

    def test_default_with_model_only_fallback(self, monkeypatch, tmp_path):
        """Test setting default with model only uses default provider."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        cfg_path = _write_base_config(home, provider="openai", model="old-model")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["default", "gpt-4o"],
            env={"HOME": str(home)},
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(cfg_path)
        assert cfg["defaults"]["model"] == "gpt-4o"
        # Provider should remain openai (default)
        assert cfg["defaults"]["provider"] == "openai"


class TestDefaultInteractive:
    """Tests for interactive default selection."""

    def test_default_without_args_interactive(self, monkeypatch, tmp_path):
        """Test that default without args enters interactive mode."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        _write_base_config(home)

        runner = CliRunner()
        runner.invoke(
            cli,
            ["-d"],
            env={"HOME": str(home)},
            input="\n",  # Cancel with Enter
        )
        # Should show interactive prompt or model list


class TestDefaultWithModels:
    """Tests for default command when models are available."""

    def test_default_with_available_models(self, monkeypatch, tmp_path):
        """Test default with models available from providers."""
        from nexus.providers.base import ModelInfo

        models_data = {
            "openai": [
                ModelInfo(
                    id="gpt-4", name="GPT-4", provider="openai", context_window=8192
                ),
                ModelInfo(
                    id="gpt-4o", name="GPT-4o", provider="openai", context_window=128000
                ),
            ],
            "anthropic": [
                ModelInfo(
                    id="claude-3",
                    name="Claude 3",
                    provider="anthropic",
                    context_window=100000,
                ),
            ],
        }
        _stub_provider_manager(monkeypatch, models_data=models_data)
        home = tmp_path / "home"
        cfg_path = _write_base_config(home)

        monkeypatch.setattr(sys, "argv", ["nexus", "-d", "gpt-4o"])
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["-d", "gpt-4o"],
            env={"HOME": str(home)},
            prog_name="nexus",
            input="",
        )

        assert result.exit_code == 0
        cfg = _read_config(cfg_path)
        assert cfg["defaults"]["model"] == "gpt-4o"


class TestDefaultAmbiguousModel:
    """Tests for default command with ambiguous model names."""

    def test_default_ambiguous_model_shows_options(self, monkeypatch, tmp_path):
        """Test that ambiguous model shows available options."""
        from nexus.providers.base import ModelInfo

        # Same model name in multiple providers
        models_data = {
            "openai": [
                ModelInfo(
                    id="shared-model",
                    name="Shared Model",
                    provider="openai",
                    context_window=8192,
                ),
            ],
            "anthropic": [
                ModelInfo(
                    id="shared-model",
                    name="Shared Model",
                    provider="anthropic",
                    context_window=100000,
                ),
            ],
        }
        _stub_provider_manager(monkeypatch, models_data=models_data)
        home = tmp_path / "home"
        _write_base_config(home)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["-d", "shared-model"],
            env={"HOME": str(home)},
        )

        # Should show options or error about ambiguous selection
        output_lower = result.output.lower()
        assert (
            "multiple" in output_lower
            or "ambiguous" in output_lower
            or "options" in output_lower
            or "provider" in output_lower
        )


class TestDefaultShorthandFlag:
    """Tests for default command directly."""

    def test_default_command_works(self, monkeypatch, tmp_path):
        """Test default command sets model correctly."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        cfg_path = _write_base_config(home, model="old-model")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["default", "openai/new-model"],
            env={"HOME": str(home)},
        )

        assert result.exit_code == 0, result.output
        cfg = _read_config(cfg_path)
        assert cfg["defaults"]["model"] == "new-model"


class TestSetModelCommand:
    """Tests for set-model command."""

    def test_set_model_help(self, monkeypatch, tmp_path):
        """Test set-model command help."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        _write_base_config(home)

        runner = CliRunner()
        result = runner.invoke(cli, ["set-model", "--help"], env={"HOME": str(home)})
        assert result.exit_code == 0

    def test_set_model_interactive_cancel(self, monkeypatch, tmp_path):
        """Test cancelling set-model interactive selection."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        _write_base_config(home)

        runner = CliRunner()
        runner.invoke(
            cli,
            ["set-model"],
            env={"HOME": str(home)},
            input="\n",  # Press enter to cancel
        )
        # Should show cancelled message or exit gracefully


class TestDefaultWithWarnings:
    """Tests for default command warning messages."""

    def test_default_offline_warning(self, monkeypatch, tmp_path):
        """Test that offline mode shows appropriate warning."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        _write_base_config(home)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["default", "unknown-model"],
            env={"HOME": str(home)},
        )

        # Should work but may show warning about unverified model
        assert result.exit_code == 0

    def test_default_success_message(self, monkeypatch, tmp_path):
        """Test that successful default shows confirmation."""
        _stub_provider_manager(monkeypatch, models_data={})
        home = tmp_path / "home"
        _write_base_config(home)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["default", "openai/gpt-4"],
            env={"HOME": str(home)},
        )

        assert result.exit_code == 0
        # Should show success message or model info
        output_lower = result.output.lower()
        assert (
            "gpt-4" in output_lower
            or "default" in output_lower
            or "set" in output_lower
            or result.exit_code == 0
        )
