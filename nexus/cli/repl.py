"""Interactive REPL chat mode for Nexus AI."""

import asyncio
import os
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.console import Console

from nexus.core.app import NexusApp
from nexus.session.manager import SessionManager
from nexus.session.models import Session, Turn
from nexus.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

REPL_COMMANDS = {
    "/exit",
    "/quit",
    "/help",
    "/clear",
    "/save",
    "/history",
    "/model",
    "/export",
}

# Create completer for REPL commands
repl_completer = WordCompleter(
    list(REPL_COMMANDS),
    ignore_case=True,
    sentence=True,
)


async def _async_save_session(
    session_manager: SessionManager, session: Session
) -> None:
    """Save session asynchronously without blocking the REPL.

    Args:
        session_manager: SessionManager instance.
        session: Session to save.
    """
    try:
        # Run the synchronous save_session in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, session_manager.save_session, session)
        logger.debug(f"Async saved session: {session.name}")
    except Exception as e:
        logger.error(f"Failed to async save session: {e}")


async def repl_main(
    model: Optional[str],
    provider: Optional[str],
    session_name: Optional[str],
    temperature: Optional[float],
    max_tokens: Optional[int],
    system_prompt: Optional[str],
) -> None:
    """Interactive chat REPL.

    Args:
        model: Model to use.
        provider: Provider to use.
        session_name: Session name (creates if missing).
        temperature: Temperature for generation.
        max_tokens: Maximum tokens to generate.
        system_prompt: System prompt to use.
    """
    # Initialize
    # Use fast initialization for REPL to avoid model listing overhead
    app = NexusApp()
    # Override the provider manager to use fast model listing
    app.provider_manager.list_all_models = app.provider_manager.list_all_models_fast
    sessions_dir = Path(app.config_manager.config.sessions.storage_path)
    session_manager = SessionManager(sessions_dir)

    # Get or create session (temp if no name provided)
    if session_name:
        session = session_manager.get_or_create_session(
            session_name,
            model or app.config_manager.get_default_model(),
            provider or app.config_manager.get_default_provider(),
        )
    else:
        session = session_manager.get_temp_session(
            model or app.config_manager.get_default_model(),
            provider or app.config_manager.get_default_provider(),
        )

    # Resolve model/provider
    model = model or session.model
    provider = provider or session.provider

    # Header
    console.print("[bold cyan]Nexus Chat[/bold cyan]")
    console.print(f"[dim]Session: {session.name}[/dim]")
    console.print(f"[dim]Model: {provider}/{model}[/dim]")
    console.print("[dim]Type /help for commands, Ctrl+D or /exit to quit[/dim]")
    print()

    # Create prompt session with tab completion for REPL commands
    prompt_session = PromptSession(completer=repl_completer)

    # REPL Loop
    while True:
        try:
            # Get input with tab completion
            print()
            user_input = (await prompt_session.prompt_async("You: ")).strip()

            if not user_input:
                continue

            # Handle REPL commands
            if user_input.startswith("/"):
                should_continue = await handle_repl_command(
                    user_input, session, session_manager, model
                )
                if not should_continue:
                    break
                continue

            # Execute completion using shared CompletionHandler
            print()
            console.print("[bold green]Assistant:[/bold green]")

            # Build completion request with conversation history for better GPU utilization
            from nexus.providers.base import CompletionRequest

            # Build messages array from session history for multi-turn context
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add all previous turns from session for KV cache optimization
            for turn in session.turns:
                messages.append({"role": turn.role, "content": turn.content})

            # Add current user message
            messages.append({"role": "user", "content": user_input})

            request = CompletionRequest(
                prompt=user_input,  # Keep for backwards compatibility
                model=model,
                temperature=temperature
                or app.config_manager.get("defaults.temperature", 0.7),
                max_tokens=max_tokens
                or app.config_manager.get("defaults.max_tokens", 2000),
                stream=True,
                system_prompt=system_prompt,
                messages=messages,  # Pass full conversation history
            )

            # Use the completion handler's streaming method
            provider_instance = app.provider_manager.get_provider(provider)
            if not provider_instance:
                raise ValueError(f"Provider '{provider}' not available")

            (
                response_content,
                tokens,
                duration_ms,
            ) = await app.completion_handler._handle_streaming(
                provider_instance, request
            )

            # Save turns to session
            user_turn = Turn(
                role="user",
                content=user_input,
                model=model,
                metadata={"system_prompt": system_prompt} if system_prompt else {},
            )
            session.turns.append(user_turn)

            assistant_turn = Turn(
                role="assistant",
                content=response_content,
                model=model,
                tokens=tokens,
                duration_ms=duration_ms,
            )
            session.turns.append(assistant_turn)

            # Save session asynchronously without blocking
            asyncio.create_task(_async_save_session(session_manager, session))

        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            console.print("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            logger.exception(f"REPL error: {e}")
            console.print(f"[red]Error: {e}[/red]")

    # Final save on exit (synchronous to ensure it completes)
    try:
        session_manager.save_session(session)
        logger.debug("Final session save on exit")
    except Exception as e:
        logger.error(f"Failed to save session on exit: {e}")


async def handle_repl_command(
    cmd: str, session: Session, sm: SessionManager, model: str
) -> bool:
    """Handle REPL commands.

    Args:
        cmd: Command string.
        session: Current session.
        sm: SessionManager instance.
        model: Current model.

    Returns:
        False if should exit, True otherwise.
    """
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command in ("/exit", "/quit"):
        console.print("[dim]Goodbye![/dim]")
        return False

    elif command == "/help":
        show_help()

    elif command == "/clear":
        os.system("clear" if os.name != "nt" else "cls")
        session.turns = []
        console.print("[dim]Conversation cleared[/dim]")

    elif command == "/save":
        if args:
            old_name = session.name
            session.name = args
            sm.save_session(session)
            # Delete old temp file if it was temp
            if old_name.startswith(".temp-"):
                sm.delete_session(old_name)
            console.print(f"[green]✓[/green] Saved as '{args}'")
        else:
            console.print("[yellow]Usage: /save <session-name>[/yellow]")

    elif command == "/history":
        limit = int(args) if args.isdigit() else 10
        show_history(session, limit)

    elif command == "/model":
        if args:
            session.model = args
            console.print(f"[green]✓[/green] Switched to model: {args}")
        else:
            console.print(f"[dim]Current model: {session.model}[/dim]")

    elif command == "/export":
        export_format = args if args in ("json", "markdown") else "markdown"
        try:
            content = sm.export_session(session.name, export_format)
            print(content)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")

    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print("[dim]Type /help for available commands[/dim]")

    return True


def show_help() -> None:
    """Display help text for REPL commands."""
    help_text = """
[bold]REPL Commands:[/bold]

  [cyan]/help[/cyan]           Show this help
  [cyan]/exit, /quit[/cyan]   Exit REPL (also Ctrl+D)
  [cyan]/clear[/cyan]          Clear conversation
  [cyan]/model <name>[/cyan]   Switch model
  [cyan]/save <name>[/cyan]    Save session with name
  [cyan]/history [n][/cyan]    Show last N turns
  [cyan]/export[/cyan]          Export session
"""
    console.print(help_text)


def show_history(session: Session, limit: int) -> None:
    """Display conversation history.

    Args:
        session: Session to display history from.
        limit: Maximum number of turns to show.
    """
    turns = session.turns[-limit:]
    console.print(f"[dim]Last {len(turns)} turns:[/dim]\n")
    for turn in turns:
        role_color = "cyan" if turn.role == "user" else "green"
        label = "You" if turn.role == "user" else "Assistant"
        # Truncate for display
        content = (
            turn.content[:200] + "..." if len(turn.content) > 200 else turn.content
        )
        console.print(f"[{role_color}]{label}:[/{role_color}] {content}\n")
