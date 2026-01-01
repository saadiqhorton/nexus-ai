from typing import Any, Dict, Optional

from pydantic import BaseModel


class ProviderConfig(BaseModel):
    enabled: bool = True
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    default_model: str


class DefaultsConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = True


class CliConfig(BaseModel):
    color_output: bool = True
    show_thinking: bool = False
    enhanced_reasoning: bool = True


class HistoryConfig(BaseModel):
    enabled: bool = True
    max_turns: int = 50
    storage_path: str


class SessionConfig(BaseModel):
    enabled: bool = True
    storage_path: str
    temp_retention_hours: int = 24


class NexusConfig(BaseModel):
    version: str = "1.0"
    defaults: DefaultsConfig
    providers: Dict[str, ProviderConfig]
    cli: CliConfig
    history: HistoryConfig
    sessions: SessionConfig

    def get_dot_notation(self, key: str, default: Any = None) -> Any:
        """Get value using dot notation from the config model"""
        parts = key.split(".")
        current = self
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current
