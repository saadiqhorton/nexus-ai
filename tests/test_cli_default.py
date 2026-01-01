import sys
from pathlib import Path

import yaml
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nexus.cli.main import cli


def _stub_provider_manager(monkeypatch, models_data=None):
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


def _write_base_config(home: Path, provider: str = "openai", model: str = "old-model"):
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
            "temperature": 0.5,
            "max_tokens": 100,
            "stream": True,
        },
        "providers": {
            provider: {
                "enabled": True,
                "api_key_env": "OPENAI_API_KEY",
                "base_url": None,
                "default_model": "fallback-model",
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
    return yaml.safe_load(cfg_path.read_text())


def test_default_accepts_provider_model_offline(monkeypatch, tmp_path):
    """Test `nexus default openai/gpt-4` sets both provider and model."""
    _stub_provider_manager(monkeypatch, models_data={})
    home = tmp_path / "home1"
    cfg_path = _write_base_config(home, provider="openai", model="old-model")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["default", "openai/gpt-4"],
        env={"HOME": str(home)},
    )

    assert result.exit_code == 0, result.output
    cfg = _read_config(cfg_path)
    assert cfg["defaults"]["provider"] == "openai"
    assert cfg["defaults"]["model"] == "gpt-4"


def test_default_accepts_model_only_with_default_provider(monkeypatch, tmp_path):
    """Test `nexus default gpt-4` uses existing provider."""
    _stub_provider_manager(monkeypatch, models_data={})
    home = tmp_path / "home2"
    cfg_path = _write_base_config(home, provider="openai", model="another-model")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["default", "gpt-4"],
        env={"HOME": str(home)},
    )

    assert result.exit_code == 0, result.output
    cfg = _read_config(cfg_path)
    assert cfg["defaults"]["provider"] == "openai"
    assert cfg["defaults"]["model"] == "gpt-4"


def test_default_accepts_different_provider_model(monkeypatch, tmp_path):
    """Test `nexus default anthropic/claude-3` sets different provider."""
    _stub_provider_manager(monkeypatch, models_data={})
    home = tmp_path / "home3"
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
