"""
Tests for OpenAI provider.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nexus.providers.base import CompletionRequest, CompletionResponse
from nexus.providers.openai_provider import OpenAIProvider


@pytest.fixture
def openai_config():
    """OpenAI provider configuration."""
    return {"api_key_env": "OPENAI_API_KEY", "enabled": True}


@pytest.fixture
def openai_config_with_base_url():
    """OpenAI provider configuration with custom base URL."""
    return {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://custom.openai.com/v1",
        "enabled": True,
    }


class TestOpenAIProviderInit:
    """Tests for OpenAI provider initialization."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    def test_init_with_api_key(self, mock_openai, openai_config):
        """Test provider initializes with valid API key."""
        provider = OpenAIProvider(openai_config)

        assert provider.client is not None
        mock_openai.assert_called_once_with(api_key="test-api-key", base_url=None)

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    def test_init_without_api_key(self, mock_openai, openai_config):
        """Test provider handles missing API key gracefully."""
        provider = OpenAIProvider(openai_config)

        assert provider.client is None
        mock_openai.assert_not_called()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    def test_init_with_custom_base_url(self, mock_openai, openai_config_with_base_url):
        """Test provider initializes with custom base URL."""
        provider = OpenAIProvider(openai_config_with_base_url)

        assert provider.client is not None
        mock_openai.assert_called_once_with(
            api_key="test-api-key", base_url="https://custom.openai.com/v1"
        )


class TestOpenAIProviderValidateConfig:
    """Tests for OpenAI provider configuration validation."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    def test_validate_config_with_client(self, mock_openai, openai_config):
        """Test validate_config returns True when client is initialized."""
        provider = OpenAIProvider(openai_config)
        assert provider.validate_config() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    def test_validate_config_without_client(self, mock_openai, openai_config):
        """Test validate_config returns False when client is None."""
        provider = OpenAIProvider(openai_config)
        assert provider.validate_config() is False


class TestOpenAIProviderListModels:
    """Tests for OpenAI provider list_models."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_list_models_returns_gpt_models(self, mock_openai, openai_config):
        """Test list_models returns only GPT models."""
        # Setup mock response
        mock_model_1 = Mock()
        mock_model_1.id = "gpt-4"
        mock_model_2 = Mock()
        mock_model_2.id = "gpt-3.5-turbo"
        mock_model_3 = Mock()
        mock_model_3.id = "whisper-1"  # Should be filtered out
        mock_model_4 = Mock()
        mock_model_4.id = "text-davinci-003"  # Should be included

        mock_response = Mock()
        mock_response.data = [mock_model_1, mock_model_2, mock_model_3, mock_model_4]

        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        models = await provider.list_models()

        assert len(models) == 3
        model_ids = [m.id for m in models]
        assert "gpt-4" in model_ids
        assert "gpt-3.5-turbo" in model_ids
        assert "text-davinci-003" in model_ids
        assert "whisper-1" not in model_ids

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_list_models_includes_o1_models(self, mock_openai, openai_config):
        """Test list_models includes o1 models."""
        mock_model = Mock()
        mock_model.id = "o1-preview"

        mock_response = Mock()
        mock_response.data = [mock_model]

        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        models = await provider.list_models()

        assert len(models) == 1
        assert models[0].id == "o1-preview"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_list_models_sorted_by_id(self, mock_openai, openai_config):
        """Test list_models returns sorted models."""
        mock_model_1 = Mock()
        mock_model_1.id = "gpt-4"
        mock_model_2 = Mock()
        mock_model_2.id = "gpt-3.5-turbo"

        mock_response = Mock()
        mock_response.data = [mock_model_1, mock_model_2]

        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        models = await provider.list_models()

        assert len(models) == 2
        assert models[0].id == "gpt-3.5-turbo"
        assert models[1].id == "gpt-4"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_list_models_handles_api_error(self, mock_openai, openai_config):
        """Test list_models handles API errors gracefully."""
        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(side_effect=Exception("API error"))
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        models = await provider.list_models()

        assert models == []

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_list_models_returns_empty_without_client(
        self, mock_openai, openai_config
    ):
        """Test list_models returns empty list when client is None."""
        provider = OpenAIProvider(openai_config)
        models = await provider.list_models()

        assert models == []


class TestOpenAIProviderComplete:
    """Tests for OpenAI provider complete (non-streaming)."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_complete_success(self, mock_openai, openai_config):
        """Test complete returns a successful response."""
        # Setup mock response
        mock_message = Mock()
        mock_message.content = "This is a test response"

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        request = CompletionRequest(prompt="Test prompt", model="gpt-4")
        response = await provider.complete(request)

        assert isinstance(response, CompletionResponse)
        assert response.content == "This is a test response"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 20
        assert response.usage["total_tokens"] == 30
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_complete_with_system_prompt(self, mock_openai, openai_config):
        """Test complete includes system prompt in messages."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        request = CompletionRequest(
            prompt="Test prompt", model="gpt-4", system_prompt="You are helpful"
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
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_complete_with_messages(self, mock_openai, openai_config):
        """Test complete uses provided messages list."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "User message"},
        ]
        request = CompletionRequest(prompt="Ignored", model="gpt-4", messages=messages)
        await provider.complete(request)

        # Verify provided messages were used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["messages"] == messages

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_complete_raises_without_client(self, mock_openai, openai_config):
        """Test complete raises error when client is None."""
        provider = OpenAIProvider(openai_config)
        request = CompletionRequest(prompt="Test", model="gpt-4")

        with pytest.raises(ValueError, match="OpenAI client not initialized"):
            await provider.complete(request)


class TestOpenAIProviderCompleteStream:
    """Tests for OpenAI provider complete_stream."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_complete_stream_yields_chunks(self, mock_openai, openai_config):
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

        provider = OpenAIProvider(openai_config)
        request = CompletionRequest(prompt="Test prompt", model="gpt-4", stream=True)

        chunks = []
        async for chunk in provider.complete_stream(request):
            chunks.append(chunk)

        assert chunks == ["This ", "is ", "a ", "test"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-api-key"})
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_complete_stream_handles_empty_delta(
        self, mock_openai, openai_config
    ):
        """Test complete_stream handles chunks with no content."""

        async def mock_stream():
            # Chunk with content
            mock_delta_1 = Mock()
            mock_delta_1.content = "Hello"
            mock_choice_1 = Mock()
            mock_choice_1.delta = mock_delta_1
            mock_chunk_1 = Mock()
            mock_chunk_1.choices = [mock_choice_1]
            yield mock_chunk_1

            # Chunk with None content (should be skipped)
            mock_delta_2 = Mock()
            mock_delta_2.content = None
            mock_choice_2 = Mock()
            mock_choice_2.delta = mock_delta_2
            mock_chunk_2 = Mock()
            mock_chunk_2.choices = [mock_choice_2]
            yield mock_chunk_2

            # Another chunk with content
            mock_delta_3 = Mock()
            mock_delta_3.content = "World"
            mock_choice_3 = Mock()
            mock_choice_3.delta = mock_delta_3
            mock_chunk_3 = Mock()
            mock_chunk_3.choices = [mock_choice_3]
            yield mock_chunk_3

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(openai_config)
        request = CompletionRequest(prompt="Test", model="gpt-4", stream=True)

        chunks = []
        async for chunk in provider.complete_stream(request):
            chunks.append(chunk)

        assert chunks == ["Hello", "World"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    @patch("nexus.providers.openai_provider.AsyncOpenAI")
    async def test_complete_stream_raises_without_client(
        self, mock_openai, openai_config
    ):
        """Test complete_stream raises error when client is None."""
        provider = OpenAIProvider(openai_config)
        request = CompletionRequest(prompt="Test", model="gpt-4", stream=True)

        with pytest.raises(ValueError, match="OpenAI client not initialized"):
            async for _ in provider.complete_stream(request):
                pass


class TestOpenAIProviderContextWindow:
    """Tests for OpenAI provider _get_context_window."""

    def test_get_context_window_gpt4o(self):
        """Test context window for gpt-4o."""
        assert OpenAIProvider._get_context_window("gpt-4o") == 128000
        assert OpenAIProvider._get_context_window("gpt-4o-2024-08-06") == 128000

    def test_get_context_window_gpt4_turbo(self):
        """Test context window for gpt-4-turbo."""
        assert OpenAIProvider._get_context_window("gpt-4-turbo") == 128000
        assert OpenAIProvider._get_context_window("gpt-4-turbo-preview") == 128000

    def test_get_context_window_gpt4(self):
        """Test context window for gpt-4."""
        assert OpenAIProvider._get_context_window("gpt-4") == 8192
        assert OpenAIProvider._get_context_window("gpt-4-0613") == 8192

    def test_get_context_window_gpt35_turbo(self):
        """Test context window for gpt-3.5-turbo."""
        assert OpenAIProvider._get_context_window("gpt-3.5-turbo") == 16385
        assert OpenAIProvider._get_context_window("gpt-3.5-turbo-16k") == 16385

    def test_get_context_window_o1(self):
        """Test context window for o1 models."""
        assert OpenAIProvider._get_context_window("o1-preview") == 128000
        assert OpenAIProvider._get_context_window("o1-mini") == 128000

    def test_get_context_window_unknown_model(self):
        """Test context window for unknown models defaults to 4096."""
        assert OpenAIProvider._get_context_window("unknown-model") == 4096
        assert OpenAIProvider._get_context_window("gpt-5") == 4096
