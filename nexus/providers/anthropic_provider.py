import inspect
import os
from typing import AsyncIterator, Dict, List

from anthropic import AsyncAnthropic, APIError, APITimeoutError, RateLimitError

from nexus.utils.logging import get_logger
from nexus.utils.errors import ProviderError

from .base import BaseProvider, CompletionRequest, CompletionResponse, ModelInfo

logger = get_logger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic (Claude) API provider"""

    def __init__(self, config: Dict):
        super().__init__(config)
        api_key = os.getenv(config.get("api_key_env", "ANTHROPIC_API_KEY"))
        base_url = config.get("base_url")

        self.client = AsyncAnthropic(api_key=api_key, base_url=base_url) if api_key else None

        # Claude model catalog (from Anthropic Models API)
        self.known_models = [
            # ... (omitted for brevity, keeping existing list)
            ModelInfo(
                id="claude-opus-4-5-20251101",
                name="Claude Opus 4.5",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            ModelInfo(
                id="claude-sonnet-4-5-20250929",
                name="Claude Sonnet 4.5",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            ModelInfo(
                id="claude-haiku-4-5-20251001",
                name="Claude Haiku 4.5",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            # Claude 4 models
            ModelInfo(
                id="claude-opus-4-1-20250805",
                name="Claude Opus 4.1",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            ModelInfo(
                id="claude-opus-4-20250514",
                name="Claude Opus 4",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            ModelInfo(
                id="claude-sonnet-4-20250514",
                name="Claude Sonnet 4",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            # Claude 3 models
            ModelInfo(
                id="claude-3-7-sonnet-20250219",
                name="Claude Sonnet 3.7",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            ModelInfo(
                id="claude-3-5-haiku-20241022",
                name="Claude Haiku 3.5",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
            ModelInfo(
                id="claude-3-haiku-20240307",
                name="Claude Haiku 3",
                provider="anthropic",
                context_window=200000,
                supports_streaming=True,
                supports_functions=True,
            ),
        ]

    def validate_config(self) -> bool:
        """Check if Anthropic API key is set"""
        return self.client is not None

    async def list_models(self) -> List[ModelInfo]:
        """Return known Claude models"""
        if not self.is_available():
            return []
        return self.known_models

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Non-streaming completion"""
        if not self.client:
            raise ValueError("Anthropic client not initialized")

        # Use provided messages for multi-turn conversations, otherwise build from prompt
        # Anthropic API separates system from messages, so we need to extract it
        if request.messages:
            messages = [m for m in request.messages if m.get("role") != "system"]
            system_msg = next(
                (m["content"] for m in request.messages if m.get("role") == "system"),
                "",
            )
        else:
            messages = [{"role": "user", "content": request.prompt}]
            system_msg = request.system_prompt or ""

        try:
            response = await self.client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=system_msg,
                messages=messages,  # type: ignore[arg-type]
            )

            return CompletionResponse(
                content=response.content[0].text if response.content else "",
                model=response.model,
                provider="anthropic",
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason or "unknown",
            )
        except (APIError, APITimeoutError, RateLimitError) as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.exception("Unexpected error in Anthropic completion")
            raise ProviderError(f"Anthropic completion failed: {e}") from e

    async def complete_stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Streaming completion"""
        if not self.client:
            raise ValueError("Anthropic client not initialized")

        # Use provided messages for multi-turn conversations, otherwise build from prompt
        # Anthropic API separates system from messages, so we need to extract it
        if request.messages:
            messages = [m for m in request.messages if m.get("role") != "system"]
            system_msg = next(
                (m["content"] for m in request.messages if m.get("role") == "system"),
                "",
            )
        else:
            messages = [{"role": "user", "content": request.prompt}]
            system_msg = request.system_prompt or ""

        try:
            stream = self.client.messages.stream(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=system_msg,
                messages=messages,  # type: ignore[arg-type]
            )
            if inspect.isawaitable(stream):
                stream = await stream

            async with stream as stream_ctx:
                async for text in stream_ctx.text_stream:
                    yield text
        except (APIError, APITimeoutError, RateLimitError) as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
        except Exception as e:
            logger.exception("Unexpected error in Anthropic streaming")
            raise ProviderError(f"Anthropic streaming failed: {e}") from e
