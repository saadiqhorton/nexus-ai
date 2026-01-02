import asyncio
from typing import AsyncIterator, Dict, List

from openai import AsyncOpenAI

from nexus.utils.logging import get_logger

from .base import BaseProvider, CompletionRequest, CompletionResponse, ModelInfo

logger = get_logger(__name__)


class OllamaProvider(BaseProvider):
    """Ollama local AI provider (OpenAI-compatible API)"""

    def __init__(self, config: Dict):
        super().__init__(config)
        base_url = config.get("base_url", "http://localhost:11434/v1")
        timeout = config.get("timeout", 30.0)
        max_retries = config.get("max_retries", 0)

        # Ollama doesn't require an API key
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",  # Dummy key, Ollama doesn't check it
            timeout=timeout,
            max_retries=max_retries,
        )
        self.timeout = float(timeout)

    def validate_config(self) -> bool:
        """Check if Ollama is running and accessible (always returns true for lazy init)"""
        return self.client is not None

    async def list_models(self) -> List[ModelInfo]:
        """Fetch available Ollama models"""
        if not self.is_available():
            return []

        try:
            models = await asyncio.wait_for(
                self.client.models.list(),
                timeout=self.timeout,
            )
            model_list = []

            for model in models.data:
                model_list.append(
                    ModelInfo(
                        id=model.id,
                        name=model.id,
                        provider="ollama",
                        context_window=self._get_context_window(model.id),
                        supports_streaming=True,
                        supports_functions=False,
                    )
                )

            return sorted(model_list, key=lambda m: m.id)
        except asyncio.TimeoutError:
            logger.error("Timeout while listing Ollama models")
            return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Non-streaming completion"""
        if not self.client:
            raise ValueError("Ollama client not initialized")

        # Use provided messages for multi-turn conversations, otherwise build from prompt
        if request.messages:
            messages = request.messages
        else:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=False,
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout while completing request with model {request.model}")
            raise

        return CompletionResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider="ollama",
            usage={
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0)
                if response.usage
                else 0,
                "completion_tokens": getattr(response.usage, "completion_tokens", 0)
                if response.usage
                else 0,
                "total_tokens": getattr(response.usage, "total_tokens", 0) if response.usage else 0,
            },
            finish_reason=response.choices[0].finish_reason or "stop",
        )

    async def complete_stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Streaming completion"""
        if not self.client:
            raise ValueError("Ollama client not initialized")

        # Use provided messages for multi-turn conversations, otherwise build from prompt
        if request.messages:
            messages = request.messages
        else:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        try:
            stream = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=True,
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout while initiating stream with model {request.model}")
            raise

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @staticmethod
    def _get_context_window(model_id: str) -> int:
        """Return context window size for known Ollama models"""
        # Based on your installed models and common context sizes
        context_windows = {
            "llama3": 8192,
            "mistral": 8192,
            "qwen": 8192,
            "qwen3": 8192,
            "qwen3-vl": 8192,
            "ministral": 32768,
            "codellama": 16384,
            "phi4": 16384,
            "phi": 16384,
            "gemma": 8192,
            "gemma3": 8192,
            "deepseek": 16384,
            "deepseek-r1": 16384,
            "gpt-oss": 8192,
            "nexusraven": 8192,
            "olmo": 8192,
            "esper": 8192,
        }

        model_lower = model_id.lower()
        for key, window in context_windows.items():
            if key in model_lower:
                return window
        return 8192  # Default for most modern models
