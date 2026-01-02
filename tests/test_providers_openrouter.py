"""
Tests for OpenRouter provider.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nexus.providers.base import CompletionRequest, CompletionResponse
from nexus.providers.openrouter_provider import OpenRouterProvider


@pytest.fixture
def openrouter_config():
    """OpenRouter provider configuration."""
    return {"api_key_env": "OPENROUTER_API_KEY", "enabled": True}


@pytest.fixture
def openrouter_config_with_custom_url():
    """OpenRouter provider configuration with custom base URL."""
    return {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://custom.openrouter.ai/api/v1",
        "enabled": True,
    }


class TestOpenRouterProviderInit:
    """Tests for OpenRouter provider initialization."""

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    def test_init_with_api_key(self, mock_openai, openrouter_config):
        """Test provider initializes with valid API key."""
        provider = OpenRouterProvider(openrouter_config)

        assert provider.client is not None
        mock_openai.assert_called_once_with(
            base_url="https://openrouter.ai/api/v1", api_key="test-api-key"
        )

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    def test_init_without_api_key(self, mock_openai, openrouter_config):
        """Test provider handles missing API key gracefully."""
        provider = OpenRouterProvider(openrouter_config)

        assert provider.client is None
        mock_openai.assert_not_called()

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    def test_init_with_custom_base_url(self, mock_openai, openrouter_config_with_custom_url):
        """Test provider initializes with custom base URL."""
        provider = OpenRouterProvider(openrouter_config_with_custom_url)

        assert provider.client is not None
        mock_openai.assert_called_once_with(
            base_url="https://custom.openrouter.ai/api/v1", api_key="test-api-key"
        )


class TestOpenRouterProviderValidateConfig:
    """Tests for OpenRouter provider configuration validation."""

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    def test_validate_config_with_client(self, mock_openai, openrouter_config):
        """Test validate_config returns True when client is initialized."""
        provider = OpenRouterProvider(openrouter_config)
        assert provider.validate_config() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    def test_validate_config_without_client(self, mock_openai, openrouter_config):
        """Test validate_config returns False when client is None."""
        provider = OpenRouterProvider(openrouter_config)
        assert provider.validate_config() is False


class TestOpenRouterProviderListModels:
    """Tests for OpenRouter provider list_models."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_list_models_returns_openrouter_models(self, mock_openai, openrouter_config):
        """Test list_models returns OpenRouter models."""
        # Setup mock response
        mock_model_1 = Mock()
        mock_model_1.id = "openai/gpt-4"
        mock_model_2 = Mock()
        mock_model_2.id = "anthropic/claude-3-sonnet"
        mock_model_3 = Mock()
        mock_model_3.id = "google/gemini-pro"

        mock_response = Mock()
        mock_response.data = [mock_model_1, mock_model_2, mock_model_3]

        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        models = await provider.list_models()

        assert len(models) == 3
        model_ids = [m.id for m in models]
        assert "openai/gpt-4" in model_ids
        assert "anthropic/claude-3-sonnet" in model_ids
        assert "google/gemini-pro" in model_ids

        # Check provider is set to openrouter
        for model in models:
            assert model.provider == "openrouter"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_list_models_sorted_by_id(self, mock_openai, openrouter_config):
        """Test list_models returns sorted models."""
        mock_model_1 = Mock()
        mock_model_1.id = "openai/gpt-4"
        mock_model_2 = Mock()
        mock_model_2.id = "anthropic/claude-3-sonnet"

        mock_response = Mock()
        mock_response.data = [mock_model_1, mock_model_2]

        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        models = await provider.list_models()

        assert len(models) == 2
        assert models[0].id == "anthropic/claude-3-sonnet"
        assert models[1].id == "openai/gpt-4"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_list_models_handles_api_error(self, mock_openai, openrouter_config):
        """Test list_models handles API errors gracefully."""
        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(side_effect=Exception("API error"))
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        models = await provider.list_models()

        assert models == []

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_list_models_returns_empty_without_client(self, mock_openai, openrouter_config):
        """Test list_models returns empty list when client is None."""
        provider = OpenRouterProvider(openrouter_config)
        models = await provider.list_models()

        assert models == []


class TestOpenRouterProviderComplete:
    """Tests for OpenRouter provider complete (non-streaming)."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_complete_success(self, mock_openai, openrouter_config):
        """Test complete returns a successful response."""
        # Setup mock response
        mock_message = Mock()
        mock_message.content = "This is a test response from OpenRouter"

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "openai/gpt-4"
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        request = CompletionRequest(prompt="Test prompt", model="openai/gpt-4")
        response = await provider.complete(request)

        assert isinstance(response, CompletionResponse)
        assert response.content == "This is a test response from OpenRouter"
        assert response.model == "openai/gpt-4"
        assert response.provider == "openrouter"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 20
        assert response.usage["total_tokens"] == 30
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_complete_with_system_prompt(self, mock_openai, openrouter_config):
        """Test complete includes system prompt in messages."""
        mock_message = Mock()
        mock_message.content = "Response with system prompt"

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "anthropic/claude-3-sonnet"
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        request = CompletionRequest(
            prompt="Test prompt",
            model="anthropic/claude-3-sonnet",
            system_prompt="You are helpful",
        )
        await provider.complete(request)

        # Verify system prompt was included in the call
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Test prompt"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_complete_with_messages(self, mock_openai, openrouter_config):
        """Test complete uses provided messages list."""
        mock_message = Mock()
        mock_message.content = "Response from messages"

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "google/gemini-pro"
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "User message"},
        ]
        request = CompletionRequest(prompt="Ignored", model="google/gemini-pro", messages=messages)
        await provider.complete(request)

        # Verify provided messages were used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["messages"] == messages

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_complete_raises_without_client(self, mock_openai, openrouter_config):
        """Test complete raises error when client is None."""
        provider = OpenRouterProvider(openrouter_config)
        request = CompletionRequest(prompt="Test", model="openai/gpt-4")

        with pytest.raises(ValueError, match="OpenRouter client not initialized"):
            await provider.complete(request)


class TestOpenRouterProviderCompleteStream:
    """Tests for OpenRouter provider complete_stream."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_complete_stream_yields_chunks(self, mock_openai, openrouter_config):
        """Test complete_stream yields content chunks."""

        # Create mock chunks
        async def mock_stream():
            chunks = [
                {"content": "This "},
                {"content": "is "},
                {"content": "a "},
                {"content": "test"},
            ]
            for chunk_data in chunks:
                mock_delta = Mock()
                mock_delta.content = chunk_data["content"]

                mock_choice = Mock()
                mock_choice.delta = mock_delta

                mock_chunk = Mock()
                mock_chunk.choices = [mock_choice]

                yield mock_chunk

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        request = CompletionRequest(prompt="Test prompt", model="openai/gpt-4", stream=True)

        chunks = []
        async for chunk in provider.complete_stream(request):
            chunks.append(chunk)

        assert chunks == ["This ", "is ", "a ", "test"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-api-key"})
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_complete_stream_with_custom_headers(self, mock_openai, openrouter_config):
        """Test complete_stream with custom OpenRouter headers."""

        async def mock_stream():
            mock_delta = Mock()
            mock_delta.content = "Hello"
            mock_choice = Mock()
            mock_choice.delta = mock_delta
            mock_chunk = Mock()
            mock_chunk.choices = [mock_choice]
            yield mock_chunk

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_openai.return_value = mock_client

        provider = OpenRouterProvider(openrouter_config)
        request = CompletionRequest(prompt="Test", model="anthropic/claude-3-sonnet", stream=True)

        chunks = []
        async for chunk in provider.complete_stream(request):
            chunks.append(chunk)

        assert chunks == ["Hello"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openrouter_provider.AsyncOpenAI")
    async def test_complete_stream_raises_without_client(self, mock_openai, openrouter_config):
        """Test complete_stream raises error when client is None."""
        provider = OpenRouterProvider(openrouter_config)
        request = CompletionRequest(prompt="Test", model="openai/gpt-4", stream=True)

        with pytest.raises(ValueError, match="OpenRouter client not initialized"):
            async for _ in provider.complete_stream(request):
                pass


class TestOpenRouterProviderContextWindow:
    """Tests for OpenRouter provider _get_context_window."""

    def test_get_context_window_gpt4(self):
        """Test context window for GPT-4."""
        assert OpenRouterProvider._get_context_window("openai/gpt-4") == 8192
        assert OpenRouterProvider._get_context_window("anthropic/claude-3-opus") == 200000

    def test_get_context_window_claude(self):
        """Test context window for Claude models."""
        assert OpenRouterProvider._get_context_window("anthropic/claude-3-sonnet") == 200000
        assert OpenRouterProvider._get_context_window("anthropic/claude-3-haiku") == 200000

    def test_get_context_window_gemini(self):
        """Test context window for Gemini models."""
        assert OpenRouterProvider._get_context_window("google/gemini-pro") == 32768
        assert OpenRouterProvider._get_context_window("google/gemini-ultra") == 32768

    def test_get_context_window_llama(self):
        """Test context window for LLaMA models."""
        assert OpenRouterProvider._get_context_window("meta/llama-3") == 8192
        assert OpenRouterProvider._get_context_window("meta/llama-3-70b") == 8192

    def test_get_context_window_mistral(self):
        """Test context window for Mistral models."""
        assert OpenRouterProvider._get_context_window("mistralai/mistral-large") == 32768
        assert OpenRouterProvider._get_context_window("mistralai/mixtral-8x7b") == 32768

    def test_get_context_window_unknown_model(self):
        """Test context window for unknown models defaults to 8192."""
        assert OpenRouterProvider._get_context_window("unknown/model") == 8192
        assert OpenRouterProvider._get_context_window("custom/model-name") == 8192
