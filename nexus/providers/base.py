from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Standardized model information"""

    id: str
    name: str
    provider: str
    context_window: int
    supports_streaming: bool = True
    supports_functions: bool = False
    cost_per_1k_tokens: Optional[float] = None


class CompletionRequest(BaseModel):
    """Standardized completion request"""

    prompt: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = False
    system_prompt: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None  # For multi-turn conversations


class CompletionResponse(BaseModel):
    """Standardized completion response"""

    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    finish_reason: str


class BaseProvider(ABC):
    """Abstract base for all AI providers"""

    def __init__(self, config: Dict):
        self.config = config
        self.name = self.__class__.__name__.replace("Provider", "").lower()

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """Return all available models from this provider"""
        pass

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send completion request (non-streaming)"""
        pass

    @abstractmethod
    def complete_stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Send streaming completion request"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Check if provider is properly configured"""
        pass

    def is_available(self) -> bool:
        """Check if provider is enabled and configured"""
        return self.config.get("enabled", False) and self.validate_config()
