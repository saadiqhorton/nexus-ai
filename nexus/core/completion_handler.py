import time
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from nexus.core.provider_manager import ProviderManager
from nexus.providers.base import CompletionRequest
from nexus.session.models import Turn
from nexus.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


class CompletionHandler:
    """Handles completion requests with smart routing"""

    def __init__(self, provider_manager: ProviderManager, config_manager):
        self.provider_manager = provider_manager
        self.config_manager = config_manager

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None,
        system_prompt: Optional[str] = None,
        session_name: Optional[str] = None,
        session_manager: Any = None,
    ):
        """
        Execute completion with smart defaults and optional session tracking.

        Args:
            prompt: The user prompt.
            model: Model to use (defaults to config).
            provider: Provider to use (defaults to config).
            temperature: Temperature setting.
            max_tokens: Maximum tokens to generate.
            stream: Whether to stream the response.
            system_prompt: System prompt to include.
            session_name: Optional session name for persistence.
            session_manager: Optional SessionManager instance.
        """
        # Determine provider and model
        provider = provider or self.config_manager.get_default_provider()
        model = model or self.config_manager.get_default_model(provider)

        if not provider or not model:
            error_msg = "Provider and model must be specified or set as defaults"
            console.print(f"[red]Error: {error_msg}[/red]")
            logger.error(error_msg)
            return

        logger.debug(
            f"Completion request: provider={provider}, model={model}, stream={stream}"
        )

        # Get provider instance
        provider_instance = self.provider_manager.get_provider(provider)
        if not provider_instance:
            error_msg = f"Provider '{provider}' not available"
            console.print(f"[red]Error: {error_msg}[/red]")
            console.print(
                f"Available providers: {', '.join(self.provider_manager.list_providers())}"
            )
            logger.error(error_msg)
            return

        # Build request with defaults
        request = CompletionRequest(
            prompt=prompt,
            model=model,
            temperature=temperature
            if temperature is not None
            else self.config_manager.get("defaults.temperature", 0.7),
            max_tokens=max_tokens
            if max_tokens is not None
            else self.config_manager.get("defaults.max_tokens", 2000),
            stream=stream
            if stream is not None
            else self.config_manager.get("defaults.stream", True),
            system_prompt=system_prompt,
        )

        # Execute request
        try:
            if request.stream:
                response_content, tokens, duration_ms = await self._handle_streaming(
                    provider_instance, request
                )
            else:
                (
                    response_content,
                    tokens,
                    duration_ms,
                ) = await self._handle_non_streaming(provider_instance, request)

            # Save to session if session provided
            if session_name and session_manager and response_content:
                self._save_to_session(
                    session_name=session_name,
                    session_manager=session_manager,
                    prompt=prompt,
                    response_content=response_content,
                    model=model,
                    system_prompt=system_prompt,
                    tokens=tokens,
                    duration_ms=duration_ms,
                )

        except Exception as e:
            logger.exception(f"Error during completion: {e}")
            console.print(f"[red]Error during completion: {e}[/red]")

    async def _handle_streaming(
        self, provider, request: CompletionRequest
    ) -> Tuple[str, Dict[str, int], int]:
        """Handle streaming response - output the text and return collected data.

        Returns:
            Tuple of (response_content, tokens_dict, duration_ms)
        """
        start_time = time.time()
        response_buffer = []
        tokens: Dict[str, int] = {}

        try:
            async for chunk in provider.complete_stream(request):
                print(chunk, end="", flush=True)
                response_buffer.append(chunk)
            print("\n")  # Extra line break at end

            duration_ms = int((time.time() - start_time) * 1000)
            response_content = "".join(response_buffer)

            # Estimate tokens for streaming (providers may not return usage for streams)
            # This is a rough estimate; actual token counts may differ
            if not tokens:
                tokens = {
                    "prompt": 0,
                    "completion": 0,
                    "total": 0,
                }

            return response_content, tokens, duration_ms

        except KeyboardInterrupt:
            logger.info("Streaming interrupted by user")
            print("\n[Interrupted]")
            duration_ms = int((time.time() - start_time) * 1000)
            return "".join(response_buffer), tokens, duration_ms
        except Exception as e:
            logger.exception(f"Stream error: {e}")
            console.print(f"\n[red]Stream error: {e}[/red]")
            duration_ms = int((time.time() - start_time) * 1000)
            return "".join(response_buffer), tokens, duration_ms

    async def _handle_non_streaming(
        self, provider, request: CompletionRequest
    ) -> Tuple[str, Dict[str, int], int]:
        """Handle non-streaming response.

        Returns:
            Tuple of (response_content, tokens_dict, duration_ms)
        """
        try:
            start_time = time.time()
            response = await provider.complete(request)
            duration_ms = int((time.time() - start_time) * 1000)

            print(response.content)
            print()  # Extra line break

            # Extract token usage from response
            tokens: Dict[str, int] = {}
            if response.usage:
                tokens = {
                    "prompt": response.usage.get("prompt_tokens", 0),
                    "completion": response.usage.get("completion_tokens", 0),
                    "total": response.usage.get("total_tokens", 0),
                }

            logger.info(
                f"Completion finished in {duration_ms}ms. Usage: {response.usage}"
            )

            return response.content, tokens, duration_ms

        except Exception as e:
            logger.exception(f"Non-streaming error: {e}")
            console.print(f"[red]Error: {e}[/red]")
            return "", {}, 0

    def _save_to_session(
        self,
        session_name: str,
        session_manager: Any,
        prompt: str,
        response_content: str,
        model: Optional[str],
        system_prompt: Optional[str],
        tokens: Dict[str, int],
        duration_ms: int,
    ) -> None:
        """Save user and assistant turns to session with spinner.

        Args:
            session_name: Name of the session.
            session_manager: SessionManager instance.
            prompt: The user's prompt.
            response_content: The assistant's response.
            model: Model used.
            system_prompt: System prompt if any.
            tokens: Token usage dictionary.
            duration_ms: Response duration in milliseconds.
        """
        try:
            session = session_manager.load_session(session_name)
            if session is None:
                logger.warning(f"Session '{session_name}' not found for saving")
                return

            # Resolve model name
            resolved_model = model or self.config_manager.get_default_model()

            # Create user turn
            user_metadata: Dict[str, Any] = {}
            if system_prompt:
                user_metadata["system_prompt"] = system_prompt

            user_turn = Turn(
                role="user",
                content=prompt,
                model=resolved_model,
                metadata=user_metadata,
            )
            session_manager.add_turn(session, user_turn, save=False)

            # Create assistant turn
            assistant_turn = Turn(
                role="assistant",
                content=response_content,
                model=resolved_model,
                tokens=tokens,
                duration_ms=duration_ms,
            )
            session_manager.add_turn(session, assistant_turn, save=False)

            # Save with spinner (transient - disappears after completion)
            with Live(
                Spinner("dots", text="Saving session..."),
                refresh_per_second=10,
                transient=True,
            ):
                session_manager.save_session(session)

            logger.debug(f"Saved turns to session '{session_name}'")

        except Exception as e:
            logger.error(f"Failed to save to session '{session_name}': {e}")
            console.print(f"[yellow]Warning: Failed to save session: {e}[/yellow]")
