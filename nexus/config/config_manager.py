from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from nexus.config.models import (
    NexusConfig,
)
from nexus.utils.logging import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Manages configuration from YAML and environment variables"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_dir = Path.home() / ".nexus"
        self.config_dir.mkdir(exist_ok=True)

        # Load environment variables
        load_dotenv()

        # Determine config file location
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = self.config_dir / "config.yaml"

        # Create default config if doesn't exist
        if not self.config_path.exists():
            self._create_default_config()

        # Load configuration
        self._config_data = self._load_config_file()
        self.config = NexusConfig(**self._config_data)
        logger.debug(f"Config loaded from {self.config_path}")

    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
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
                    "base_url": None,
                    "default_model": "gpt-4",
                },
                "anthropic": {
                    "enabled": True,
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "base_url": None,
                    "default_model": "claude-sonnet-4",
                },
                "ollama": {
                    "enabled": True,
                    "base_url": "http://localhost:11434",
                    "default_model": "llama2",
                },
                "openrouter": {
                    "enabled": False,
                    "api_key_env": "OPENROUTER_API_KEY",
                    "base_url": "https://openrouter.ai/api/v1",
                    "default_model": "anthropic/claude-3.5-sonnet",
                },
            },
            "cli": {
                "color_output": True,
                "show_thinking": False,
                "enhanced_reasoning": True,
            },
            "history": {
                "enabled": True,
                "max_turns": 50,
                "storage_path": str(self.config_dir / "history"),
            },
            "sessions": {
                "enabled": True,
                "storage_path": str(self.config_dir / "sessions"),
                "temp_retention_hours": 24,
            },
        }

        with open(self.config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        logger.info(f"Created default config at {self.config_path}")

    def _load_config_file(self) -> Dict:
        """Load configuration from YAML file"""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def get(self, key: str, default=None) -> Any:
        """Get configuration value using dot notation"""
        return self.config.get_dot_notation(key, default)

    def get_provider_config(self, provider: str) -> Dict:
        """Get configuration for specific provider"""
        p_config = self.config.providers.get(provider)
        return p_config.model_dump() if p_config else {}

    def get_default_provider(self) -> str:
        """Get default provider name"""
        return self.config.defaults.provider

    def get_default_model(self, provider: Optional[str] = None) -> str:
        """Get default model for provider"""
        if provider and provider in self.config.providers:
            return self.config.providers[provider].default_model
        return self.config.defaults.model

    def save(self):
        """Save current configuration to file"""
        with open(self.config_path, "w") as f:
            yaml.dump(self.config.model_dump(), f, default_flow_style=False)
        logger.info(f"Config saved to {self.config_path}")
