import os
from typing import Any, AsyncIterator, Dict, List, cast

from openai import AsyncOpenAI

from nexus.utils.logging import get_logger

from .base import BaseProvider, CompletionRequest, CompletionResponse, ModelInfo

logger = get_logger(__name__)


class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider (OpenAI-compatible API with multi-model access)"""

    def __init__(self, config: Dict):
        super().__init__(config)
        api_key = os.getenv(config.get("api_key_env", "OPENROUTER_API_KEY"))
        base_url = config.get("base_url", "https://openrouter.ai/api/v1")

        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key) if api_key else None

    def validate_config(self) -> bool:
        """Check if OpenRouter API key is set"""
        return self.client is not None

    async def list_models(self) -> List[ModelInfo]:
        """Fetch available OpenRouter models"""
        if not self.is_available():
            return []

        try:
            if not self.client:
                return []

            models = await self.client.models.list()
            model_list = []

            for model in models.data:
                model_list.append(
                    ModelInfo(
                        id=model.id,
                        name=model.id,
                        provider="openrouter",
                        context_window=self._get_context_window(model.id),
                        supports_streaming=True,
                        supports_functions=True,
                    )
                )

            return sorted(model_list, key=lambda m: m.id)
        except Exception as e:
            logger.error(f"Error listing OpenRouter models: {e}")
            return []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Non-streaming completion"""
        if not self.client:
            raise ValueError("OpenRouter client not initialized")

        # Use provided messages for multi-turn conversations, otherwise build from prompt
        if request.messages:
            messages = request.messages
        else:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        response = await self.client.chat.completions.create(
            model=request.model,
            messages=cast(Any, messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )

        return CompletionResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider="openrouter",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            finish_reason=response.choices[0].finish_reason or "stop",
        )

    async def complete_stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Streaming completion"""
        if not self.client:
            raise ValueError("OpenRouter client not initialized")

        # Use provided messages for multi-turn conversations, otherwise build from prompt
        if request.messages:
            messages = request.messages
        else:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        stream = await self.client.chat.completions.create(
            model=request.model,
            messages=cast(Any, messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @staticmethod
    def _get_context_window(model_id: str) -> int:
        """Return context window size for known OpenRouter models"""
        # OpenRouter supports many providers, map common ones
        context_windows = {
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-3.5": 16385,
            "claude-3": 200000,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,
            "claude-opus-4": 200000,
            "claude-sonnet-4": 200000,
            "gemini": 32768,
            "llama-3": 8192,
            "mistral": 32768,
            "mixtral": 32768,
        }

        model_lower = model_id.lower()
        for key, window in context_windows.items():
            if key in model_lower:
                return window
        return 8192  # Default
