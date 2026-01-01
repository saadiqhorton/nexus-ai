"""
Tests for Anthropic provider.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nexus.providers.anthropic_provider import AnthropicProvider
from nexus.providers.base import CompletionRequest, CompletionResponse, ModelInfo


@pytest.fixture
def anthropic_config():
    """Anthropic provider configuration."""
    return {"api_key_env": "ANTHROPIC_API_KEY", "enabled": True}


@pytest.fixture
def anthropic_config_with_base_url():
    """Anthropic provider configuration with custom base URL."""
    return {
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://custom.anthropic.com/v1",
        "enabled": True,
    }


class TestAnthropicProviderInit:
    """Tests for Anthropic provider initialization."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    def test_init_with_api_key(self, mock_anthropic, anthropic_config):
        """Test provider initializes with valid API key."""
        provider = AnthropicProvider(anthropic_config)

        assert provider.client is not None
        mock_anthropic.assert_called_once_with(api_key="test-api-key", base_url=None)

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    def test_init_without_api_key(self, mock_anthropic, anthropic_config):
        """Test provider handles missing API key gracefully."""
        provider = AnthropicProvider(anthropic_config)

        assert provider.client is None
        mock_anthropic.assert_not_called()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    def test_init_with_custom_base_url(
        self, mock_anthropic, anthropic_config_with_base_url
    ):
        """Test provider initializes with custom base URL."""
        provider = AnthropicProvider(anthropic_config_with_base_url)

        assert provider.client is not None
        mock_anthropic.assert_called_once_with(
            api_key="test-api-key", base_url="https://custom.anthropic.com/v1"
        )


class TestAnthropicProviderValidateConfig:
    """Tests for Anthropic provider configuration validation."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    def test_validate_config_with_client(self, mock_anthropic, anthropic_config):
        """Test validate_config returns True when client is initialized."""
        provider = AnthropicProvider(anthropic_config)
        assert provider.validate_config() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    def test_validate_config_without_client(self, mock_anthropic, anthropic_config):
        """Test validate_config returns False when client is None."""
        provider = AnthropicProvider(anthropic_config)
        assert provider.validate_config() is False


class TestAnthropicProviderListModels:
    """Tests for Anthropic provider list_models."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_list_models_returns_known_models(
        self, mock_anthropic, anthropic_config
    ):
        """Test list_models returns all known Claude models."""
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        # Check that we have models
        assert len(models) > 0

        # Check that all models are ModelInfo instances
        for model in models:
            assert isinstance(model, ModelInfo)
            assert model.provider == "anthropic"
            assert model.supports_streaming is True
            assert model.supports_functions is True

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_list_models_returns_models(self, mock_anthropic, anthropic_config):
        """Test list_models returns all known models."""
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        # Check that we have models
        assert len(models) > 0

        # Check that we have specific models
        model_ids = [m.id for m in models]
        assert (
            "claude-sonnet-4" in model_ids or "claude-sonnet-4-5-20250929" in model_ids
        )

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_list_models_returns_empty_without_client(
        self, mock_anthropic, anthropic_config
    ):
        """Test list_models returns empty list when client is None."""
        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        assert models == []


class TestAnthropicProviderComplete:
    """Tests for Anthropic provider complete (non-streaming)."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_success(self, mock_anthropic, anthropic_config):
        """Test complete returns a successful response."""
        # Setup mock response
        mock_text_block = Mock()
        mock_text_block.text = "This is a test response"

        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_response.model = "claude-sonnet-4"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        request = CompletionRequest(prompt="Test prompt", model="claude-sonnet-4")
        response = await provider.complete(request)

        assert isinstance(response, CompletionResponse)
        assert response.content == "This is a test response"
        assert response.model == "claude-sonnet-4"
        assert response.provider == "anthropic"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 20
        assert response.usage["total_tokens"] == 30
        assert response.finish_reason == "end_turn"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_with_system_prompt(self, mock_anthropic, anthropic_config):
        """Test complete handles system prompt correctly."""
        mock_text_block = Mock()
        mock_text_block.text = "Response with system prompt"

        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_response.model = "claude-sonnet-4"
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 25
        mock_response.stop_reason = "max_tokens"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        request = CompletionRequest(
            prompt="Test prompt",
            model="claude-sonnet-4",
            system_prompt="You are helpful",
        )
        await provider.complete(request)

        # Verify system prompt was included in the call
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["system"] == "You are helpful"
        assert call_args[1]["messages"] == [{"role": "user", "content": "Test prompt"}]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_with_messages(self, mock_anthropic, anthropic_config):
        """Test complete uses provided messages list."""
        mock_text_block = Mock()
        mock_text_block.text = "Response from messages"

        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_response.model = "claude-sonnet-4"
        mock_response.usage.input_tokens = 20
        mock_response.usage.output_tokens = 30
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        messages = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
        ]
        request = CompletionRequest(
            prompt="Ignored", model="claude-sonnet-4", messages=messages
        )
        await provider.complete(request)

        # Verify provided messages were used (system messages filtered out)
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["messages"] == messages

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_with_system_in_messages(
        self, mock_anthropic, anthropic_config
    ):
        """Test complete extracts system prompt from messages."""
        mock_text_block = Mock()
        mock_text_block.text = "Response with system from messages"

        mock_response = Mock()
        mock_response.content = [mock_text_block]
        mock_response.model = "claude-sonnet-4"
        mock_response.usage.input_tokens = 18
        mock_response.usage.output_tokens = 22
        mock_response.stop_reason = "end_turn"

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        messages = [
            {"role": "system", "content": "System instructions"},
            {"role": "user", "content": "User message"},
        ]
        request = CompletionRequest(
            prompt="Ignored", model="claude-sonnet-4", messages=messages
        )
        await provider.complete(request)

        # Verify system prompt was extracted and user message kept
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["system"] == "System instructions"
        assert call_args[1]["messages"] == [{"role": "user", "content": "User message"}]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_raises_without_client(
        self, mock_anthropic, anthropic_config
    ):
        """Test complete raises error when client is None."""
        provider = AnthropicProvider(anthropic_config)
        request = CompletionRequest(prompt="Test", model="claude-sonnet-4")

        with pytest.raises(ValueError, match="Anthropic client not initialized"):
            await provider.complete(request)


class TestAnthropicProviderCompleteStream:
    """Tests for Anthropic provider complete_stream."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_stream_yields_chunks(
        self, mock_anthropic, anthropic_config
    ):
        """Test complete_stream yields content chunks."""

        # Create mock chunks
        async def mock_text_stream():
            chunks = ["This ", "is ", "a ", "test"]
            for chunk in chunks:
                yield chunk

        # Create proper async context manager mock
        class MockStreamContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            @property
            def text_stream(self):
                return mock_text_stream()

        mock_client = AsyncMock()
        mock_client.messages.stream = AsyncMock(return_value=MockStreamContext())
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        request = CompletionRequest(
            prompt="Test prompt", model="claude-sonnet-4", stream=True
        )

        chunks = []
        async for chunk in provider.complete_stream(request):
            chunks.append(chunk)

        assert chunks == ["This ", "is ", "a ", "test"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_stream_with_system_prompt(
        self, mock_anthropic, anthropic_config
    ):
        """Test complete_stream handles system prompt correctly."""

        async def mock_text_stream():
            yield "Hello"
            yield " World"

        class MockStreamContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            @property
            def text_stream(self):
                return mock_text_stream()

        mock_client = AsyncMock()
        mock_client.messages.stream = AsyncMock(return_value=MockStreamContext())
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_config)
        request = CompletionRequest(
            prompt="Test",
            model="claude-sonnet-4",
            stream=True,
            system_prompt="Be helpful",
        )

        chunks = []
        async for chunk in provider.complete_stream(request):
            chunks.append(chunk)

        assert chunks == ["Hello", " World"]

        # Verify system prompt was included in the call
        call_args = mock_client.messages.stream.call_args
        assert call_args[1]["system"] == "Be helpful"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_complete_stream_raises_without_client(
        self, mock_anthropic, anthropic_config
    ):
        """Test complete_stream raises error when client is None."""
        provider = AnthropicProvider(anthropic_config)
        request = CompletionRequest(prompt="Test", model="claude-sonnet-4", stream=True)

        with pytest.raises(ValueError, match="Anthropic client not initialized"):
            async for _ in provider.complete_stream(request):
                pass


class TestAnthropicProviderKnownModels:
    """Tests for Anthropic provider known models."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_known_models_contains_opus_models(
        self, mock_anthropic, anthropic_config
    ):
        """Test known models includes Opus models."""
        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        model_ids = [m.id for m in models]

        # Check for Opus models
        opus_models = [m for m in model_ids if "opus" in m]
        assert len(opus_models) > 0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_known_models_contains_sonnet_models(
        self, mock_anthropic, anthropic_config
    ):
        """Test known models includes Sonnet models."""
        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        model_ids = [m.id for m in models]

        # Check for Sonnet models
        sonnet_models = [m for m in model_ids if "sonnet" in m]
        assert len(sonnet_models) > 0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_known_models_contains_haiku_models(
        self, mock_anthropic, anthropic_config
    ):
        """Test known models includes Haiku models."""
        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        model_ids = [m.id for m in models]

        # Check for Haiku models
        haiku_models = [m for m in model_ids if "haiku" in m]
        assert len(haiku_models) > 0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_known_models_context_window(self, mock_anthropic, anthropic_config):
        """Test known models have correct context windows."""
        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        for model in models:
            assert model.context_window == 200000  # All Claude models have 200k context

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("nexus.providers.anthropic_provider.AsyncAnthropic")
    async def test_known_models_support_streaming_and_functions(
        self, mock_anthropic, anthropic_config
    ):
        """Test known models support streaming and functions."""
        provider = AnthropicProvider(anthropic_config)
        models = await provider.list_models()

        for model in models:
            assert model.supports_streaming is True
            assert model.supports_functions is True
