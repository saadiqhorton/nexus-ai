"""
Test the base provider interface and models.
"""

from typing import AsyncIterator, List
from unittest.mock import AsyncMock

from nexus.providers.base import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    ModelInfo,
)


def test_model_info_with_all_fields():
    """Test creating ModelInfo with all fields."""
    model = ModelInfo(
        id="gpt-4",
        name="GPT-4",
        provider="openai",
        context_window=8192,
        supports_streaming=True,
        supports_functions=True,
        cost_per_1k_tokens=0.06,
    )

    assert model.id == "gpt-4"
    assert model.name == "GPT-4"
    assert model.provider == "openai"
    assert model.context_window == 8192
    assert model.supports_streaming is True
    assert model.supports_functions is True
    assert model.cost_per_1k_tokens == 0.06


def test_model_info_defaults():
    """Test ModelInfo defaults for optional fields."""
    model = ModelInfo(
        id="gpt-3.5-turbo", name="GPT-3.5 Turbo", provider="openai", context_window=4096
    )

    assert model.id == "gpt-3.5-turbo"
    assert model.name == "GPT-3.5 Turbo"
    assert model.provider == "openai"
    assert model.context_window == 4096
    assert model.supports_streaming is True  # Default
    assert model.supports_functions is False  # Default
    assert model.cost_per_1k_tokens is None  # Default


def test_completion_request_validation():
    """Test CompletionRequest validation with valid inputs."""
    request = CompletionRequest(prompt="Hello, world!", model="gpt-4")

    assert request.prompt == "Hello, world!"
    assert request.model == "gpt-4"
    assert request.temperature == 0.7  # Default
    assert request.max_tokens == 2000  # Default
    assert request.stream is False  # Default (will be set by caller)
    assert request.system_prompt is None
    assert request.messages is None


def test_completion_request_with_messages():
    """Test CompletionRequest with messages list."""
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
    ]

    request = CompletionRequest(prompt="Hello", model="gpt-4", messages=messages)

    assert request.prompt == "Hello"
    assert request.model == "gpt-4"
    assert request.messages == messages


def test_completion_response_validation():
    """Test CompletionResponse validation."""
    response = CompletionResponse(
        content="This is a response",
        model="gpt-4",
        provider="openai",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        finish_reason="stop",
    )

    assert response.content == "This is a response"
    assert response.model == "gpt-4"
    assert response.provider == "openai"
    assert response.usage["prompt_tokens"] == 10
    assert response.usage["completion_tokens"] == 20
    assert response.usage["total_tokens"] == 30
    assert response.finish_reason == "stop"


def test_base_provider_name_extraction():
    """Test BaseProvider extracts name from class name."""

    class TestProvider(BaseProvider):
        def __init__(self, config: dict):
            super().__init__(config)

        async def list_models(self) -> List[ModelInfo]:
            return []

        async def complete(self, request: CompletionRequest) -> CompletionResponse:
            return CompletionResponse(
                content="test",
                model="test",
                provider="test",
                usage={},
                finish_reason="stop",
            )

        async def complete_stream(
            self, request: CompletionRequest
        ) -> AsyncIterator[str]:
            yield "test"

        def validate_config(self) -> bool:
            return True

    provider = TestProvider({"enabled": True})
    assert provider.name == "test"

    class OpenAIProvider(BaseProvider):
        def __init__(self, config: dict):
            super().__init__(config)

        async def list_models(self) -> List[ModelInfo]:
            return []

        async def complete(self, request: CompletionRequest) -> CompletionResponse:
            return CompletionResponse(
                content="test",
                model="test",
                provider="openai",
                usage={},
                finish_reason="stop",
            )

        async def complete_stream(
            self, request: CompletionRequest
        ) -> AsyncIterator[str]:
            yield "test"

        def validate_config(self) -> bool:
            return True

    provider = OpenAIProvider({"enabled": True})
    assert provider.name == "openai"


def test_base_provider_is_available_with_enabled():
    """Test is_available() returns correct value when enabled and configured."""

    class MockProvider(BaseProvider):
        def __init__(self, config: dict):
            super().__init__(config)

        async def list_models(self) -> List[ModelInfo]:
            return []

        async def complete(self, request: CompletionRequest) -> CompletionResponse:
            return CompletionResponse(
                content="test",
                model="test",
                provider="test",
                usage={},
                finish_reason="stop",
            )

        async def complete_stream(
            self, request: CompletionRequest
        ) -> AsyncIterator[str]:
            yield "test"

        def validate_config(self) -> bool:
            return True

    # Provider enabled and valid config
    provider = MockProvider({"enabled": True})
    assert provider.is_available() is True

    # Provider disabled even with valid config
    provider = MockProvider({"enabled": False})
    assert provider.is_available() is False

    # Provider enabled but invalid config
    class InvalidConfigProvider(BaseProvider):
        def __init__(self, config: dict):
            super().__init__(config)

        async def list_models(self) -> List[ModelInfo]:
            return []

        async def complete(self, request: CompletionRequest) -> CompletionResponse:
            return CompletionResponse(
                content="test",
                model="test",
                provider="test",
                usage={},
                finish_reason="stop",
            )

        async def complete_stream(
            self, request: CompletionRequest
        ) -> AsyncIterator[str]:
            yield "test"

        def validate_config(self) -> bool:
            return False

    provider = InvalidConfigProvider({"enabled": True})
    assert provider.is_available() is False


def test_base_provider_is_available_without_client():
    """Test is_available() handles missing client gracefully."""

    class ClientProvider(BaseProvider):
        def __init__(self, config: dict, has_client: bool = True):
            super().__init__(config)
            self.client = AsyncMock() if has_client else None

        async def list_models(self) -> List[ModelInfo]:
            return []

        async def complete(self, request: CompletionRequest) -> CompletionResponse:
            return CompletionResponse(
                content="test",
                model="test",
                provider="test",
                usage={},
                finish_reason="stop",
            )

        async def complete_stream(
            self, request: CompletionRequest
        ) -> AsyncIterator[str]:
            yield "test"

        def validate_config(self) -> bool:
            return self.client is not None

    # Provider with client
    provider = ClientProvider({"enabled": True}, has_client=True)
    assert provider.is_available() is True

    # Provider without client
    provider = ClientProvider({"enabled": True}, has_client=False)
    assert provider.is_available() is False
