"""
Tests for Ollama provider (Live Integration Tests).
"""

import asyncio

import pytest
from conftest import OLLAMA_AVAILABLE, OLLAMA_CONFIGURED, OLLAMA_URL

from nexus.providers.base import CompletionRequest, CompletionResponse, ModelInfo
from nexus.providers.ollama_provider import OllamaProvider


@pytest.fixture
def ollama_config_with_custom_url():
    """Ollama provider configuration with custom base URL."""
    return {
        "base_url": "http://custom.ollama.local:11434/v1",
        "enabled": True,
    }


class TestOllamaProviderInit:
    """Tests for Ollama provider initialization."""

    def test_init_with_default_url(self, ollama_config):
        """Test provider initializes with default URL."""
        provider = OllamaProvider(ollama_config)

        assert provider.client is not None
        assert str(provider.client.base_url) == "http://localhost:11434/v1/"
        assert provider.client.api_key == "ollama"  # Dummy key

    def test_init_with_custom_url(self, ollama_config_with_custom_url):
        """Test provider initializes with custom URL."""
        provider = OllamaProvider(ollama_config_with_custom_url)

        assert provider.client is not None
        assert str(provider.client.base_url) == "http://custom.ollama.local:11434/v1/"
        assert provider.client.api_key == "ollama"


class TestOllamaProviderValidateConfig:
    """Tests for Ollama provider configuration validation."""

    def test_validate_config_with_client(self, ollama_config):
        """Test validate_config returns True when client is initialized."""
        provider = OllamaProvider(ollama_config)
        assert provider.validate_config() is True

    def test_validate_config_returns_true_for_lazy_init(self, ollama_config):
        """Test validate_config returns True (Ollama uses lazy initialization)."""
        provider = OllamaProvider(ollama_config)
        assert provider.validate_config() is True


class TestOllamaProviderListModels:
    """Tests for Ollama provider list_models (LIVE INTEGRATION)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_list_models_live(self, ollama_config):
        """Test list_models works with live Ollama API."""
        provider = OllamaProvider(ollama_config)
        models = await provider.list_models()

        # If Ollama is running, should return models or empty list
        assert isinstance(models, list)
        for model in models:
            assert isinstance(model, ModelInfo)
            assert model.provider == "ollama"
            assert model.supports_streaming is True
            assert model.supports_functions is False  # Ollama doesn't support functions
            assert model.context_window > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_list_models_with_custom_url(self, ollama_config_with_custom_url):
        """Test list_models works with custom URL."""
        provider = OllamaProvider(ollama_config_with_custom_url)
        models = await provider.list_models()

        # Should handle connection errors gracefully
        assert isinstance(models, list)

    @pytest.mark.slow
    async def test_list_models_connection_refused(self, ollama_config):
        """Test list_models handles connection refused gracefully."""
        # Use a non-existent URL to simulate connection refused
        provider = OllamaProvider({"base_url": "http://localhost:9999/v1", "enabled": True})
        models = await provider.list_models()

        # Should return empty list when connection fails
        assert models == []


class TestOllamaProviderComplete:
    """Tests for Ollama provider complete (LIVE INTEGRATION)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_complete_live(self, ollama_config):
        """Test complete works with live Ollama API (requires model)."""
        provider = OllamaProvider(ollama_config)

        # Try with a common model name - this might fail if model not installed
        request = CompletionRequest(prompt="Hello", model="llama3", max_tokens=50)

        try:
            response = await provider.complete(request)
            assert isinstance(response, CompletionResponse)
            assert response.provider == "ollama"
            assert response.model == "llama3"
            assert isinstance(response.content, str)
            assert isinstance(response.usage, dict)
            assert "prompt_tokens" in response.usage
            assert "completion_tokens" in response.usage
            assert "total_tokens" in response.usage
        except Exception as e:
            # If model not found, that's expected - Ollama might not have models installed
            if "model" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"Required model not available: {e}")
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_complete_with_system_prompt(self, ollama_config):
        """Test complete handles system prompt with live Ollama API."""
        provider = OllamaProvider(ollama_config)

        request = CompletionRequest(
            prompt="What is 2 + 2?",
            model="llama3",
            system_prompt="You are a math expert",
            max_tokens=50,
        )

        try:
            response = await provider.complete(request)
            assert isinstance(response, CompletionResponse)
            assert response.provider == "ollama"
            assert response.model == "llama3"
        except Exception as e:
            if "model" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"Required model not available: {e}")
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_complete_with_messages(self, ollama_config):
        """Test complete uses provided messages with live Ollama API."""
        provider = OllamaProvider(ollama_config)

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "What is 2 + 2?"},
        ]

        request = CompletionRequest(
            prompt="Ignored", model="llama3", messages=messages, max_tokens=50
        )

        try:
            response = await provider.complete(request)
            assert isinstance(response, CompletionResponse)
            assert response.provider == "ollama"
        except Exception as e:
            if "model" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"Required model not available: {e}")
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_complete_timeout_handling(self):
        """Test complete handles timeouts gracefully."""
        # Use config-based timeout (proper initialization)
        short_timeout_config = {
            "base_url": "http://localhost:11434/v1",
            "enabled": True,
            "timeout": 0.001,  # Very short timeout to trigger timeout
        }

        provider = OllamaProvider(short_timeout_config)
        request = CompletionRequest(prompt="Count from 1 to 5", model="llama3", max_tokens=50)

        # Should raise asyncio.TimeoutError after Fix 2 changes
        with pytest.raises(asyncio.TimeoutError):
            await provider.complete(request)

    @pytest.mark.asyncio
    async def test_complete_raises_without_client(self, ollama_config):
        """Test complete raises error when client is None."""
        provider = OllamaProvider(ollama_config)
        # Create a new provider with no client to simulate the error
        provider.client = None  # Simulate no client
        request = CompletionRequest(prompt="Test", model="llama3")

        with pytest.raises(ValueError, match="Ollama client not initialized"):
            await provider.complete(request)


class TestOllamaProviderCompleteStream:
    """Tests for Ollama provider complete_stream (LIVE INTEGRATION)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_complete_stream_live(self, ollama_config):
        """Test complete_stream works with live Ollama API."""
        provider = OllamaProvider(ollama_config)

        request = CompletionRequest(
            prompt="Say 'Hello World'", model="llama3", stream=True, max_tokens=50
        )

        try:
            chunks = []
            async for chunk in provider.complete_stream(request):
                chunks.append(chunk)
                # Stop early to avoid long responses
                if len(chunks) >= 5:
                    break

            assert len(chunks) > 0
            for chunk in chunks:
                assert isinstance(chunk, str)
        except Exception as e:
            if "model" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"Required model not available: {e}")
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
    @pytest.mark.skipif(
        OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
        reason=f"Ollama not responding at {OLLAMA_URL}",
    )
    async def test_complete_stream_with_system_prompt(self, ollama_config):
        """Test complete_stream handles system prompt with live Ollama API."""
        provider = OllamaProvider(ollama_config)

        request = CompletionRequest(
            prompt="Count from 1 to 5",
            model="llama3",
            stream=True,
            system_prompt="You are a counting expert",
            max_tokens=50,
        )

        try:
            chunks = []
            async for chunk in provider.complete_stream(request):
                chunks.append(chunk)
                if len(chunks) >= 5:
                    break

            assert len(chunks) > 0
        except Exception as e:
            if "model" in str(e).lower() or "not found" in str(e).lower():
                pytest.skip(f"Required model not available: {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_complete_stream_raises_without_client(self, ollama_config):
        """Test complete_stream raises error when client is None."""
        provider = OllamaProvider(ollama_config)
        provider.client = None  # Simulate no client
        request = CompletionRequest(prompt="Test", model="llama3", stream=True)

        with pytest.raises(ValueError, match="Ollama client not initialized"):
            async for _ in provider.complete_stream(request):
                pass


class TestOllamaProviderContextWindow:
    """Tests for Ollama provider _get_context_window."""

    def test_get_context_window_llama3(self):
        """Test context window for LLaMA 3."""
        assert OllamaProvider._get_context_window("llama3") == 8192
        assert OllamaProvider._get_context_window("llama3.1") == 8192

    def test_get_context_window_mistral(self):
        """Test context window for Mistral."""
        assert OllamaProvider._get_context_window("mistral") == 8192
        assert OllamaProvider._get_context_window("mistral-large") == 8192

    def test_get_context_window_qwen(self):
        """Test context window for Qwen."""
        assert OllamaProvider._get_context_window("qwen") == 8192
        assert OllamaProvider._get_context_window("qwen3") == 8192
        assert OllamaProvider._get_context_window("qwen3-vl") == 8192

    def test_get_context_window_ministral(self):
        """Test context window for Ministral."""
        assert OllamaProvider._get_context_window("ministral") == 32768

    def test_get_context_window_codellama(self):
        """Test context window for CodeLlama."""
        assert OllamaProvider._get_context_window("codellama") == 16384

    def test_get_context_window_phi(self):
        """Test context window for Phi."""
        assert OllamaProvider._get_context_window("phi4") == 16384
        assert OllamaProvider._get_context_window("phi") == 16384

    def test_get_context_window_gemma(self):
        """Test context window for Gemma."""
        assert OllamaProvider._get_context_window("gemma") == 8192
        assert OllamaProvider._get_context_window("gemma3") == 8192

    def test_get_context_window_deepseek(self):
        """Test context window for DeepSeek."""
        assert OllamaProvider._get_context_window("deepseek") == 16384
        assert OllamaProvider._get_context_window("deepseek-r1") == 16384

    def test_get_context_window_unknown_model(self):
        """Test context window for unknown models defaults to 8192."""
        assert OllamaProvider._get_context_window("unknown-model") == 8192
        assert OllamaProvider._get_context_window("custom/model") == 8192
        assert OllamaProvider._get_context_window("my-custom-model") == 8192
