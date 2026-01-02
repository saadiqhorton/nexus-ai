import os
from typing import Any, AsyncIterator, Dict, List, cast

from openai import AsyncOpenAI

from nexus.utils.logging import get_logger

from .base import BaseProvider, CompletionRequest, CompletionResponse, ModelInfo

logger = get_logger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider"""

    def __init__(self, config: Dict):
        super().__init__(config)
        api_key = os.getenv(config.get("api_key_env", "OPENAI_API_KEY"))
        base_url = config.get("base_url")

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url) if api_key else None

    def validate_config(self) -> bool:
        """Check if OpenAI API key is set"""
        return self.client is not None

    async def list_models(self) -> List[ModelInfo]:
        """Fetch available OpenAI models"""
        if not self.is_available():
            return []

        try:
            # We need to check if client is initialized because is_available()
            # might have been called before __init__ finished or similar (though not here)
            if not self.client:
                return []

            models = await self.client.models.list()
            model_list = []

            for model in models.data:
                # Only include GPT models for now
                if any(prefix in model.id for prefix in ["gpt-", "text-", "o1-"]):
                    model_list.append(
                        ModelInfo(
                            id=model.id,
                            name=model.id,
                            provider="openai",
                            context_window=self._get_context_window(model.id),
                            supports_streaming=True,
                            supports_functions=True,
                        )
                    )

            return sorted(model_list, key=lambda m: m.id)
        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            return []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Non-streaming completion"""
        if not self.client:
            raise ValueError("OpenAI client not initialized")

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
            provider="openai",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            finish_reason=response.choices[0].finish_reason,
        )

    async def complete_stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Streaming completion"""
        if not self.client:
            raise ValueError("OpenAI client not initialized")

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
        """Return context window size for known models"""
        context_windows = {
            "gpt-4o": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
            "o1-": 128000,
        }

        for key, window in context_windows.items():
            if key in model_id:
                return window
        return 4096  # Default
