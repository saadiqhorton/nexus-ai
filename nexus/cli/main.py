import sys

import click
from rich.console import Console
from rich.panel import Panel

from nexus.cli.commands import (
    chat_command,
    completion_command,
    config_command,
    default_command,
    models_command,
    providers_command,
    sessions_group,
    version_command,
)
from nexus.cli.core import NexusGroup, handle_prompt
from nexus.cli.prompts import prompts_group
from nexus.cli.utils import resolve_system_prompt
from nexus.core.app import NexusApp
from nexus.utils.errors import NexusError
from nexus.utils.logging import get_logger

console = Console()
logger = get_logger(__name__)

_debug_mode = False


def handle_exception(e: Exception, debug_mode: bool = False) -> None:
    """Handle exceptions with clean output."""
    exit_code = 1

    if isinstance(e, NexusError):
        exit_code = getattr(e, "exit_code", 1)
        notes = getattr(e, "__notes__", [])
        hint_text = "\n".join([f"[dim]💡 {note}[/dim]" for note in notes])
        error_msg = str(e)

        if hint_text:
            console.print(
                Panel(
                    f"[red]Error[/red]: {error_msg}\n\n{hint_text}",
                    title="[bold]Nexus Error[/bold]",
                    border_style="red",
                )
            )
        else:
            console.print(
                Panel(
                    f"[red]Error[/red]: {error_msg}",
                    title="[bold]Nexus Error[/bold]",
                    border_style="red",
                )
            )
    elif isinstance(e, KeyboardInterrupt):
        console.print("[yellow]Interrupted[/yellow]")
        exit_code = 130
    else:
        console.print(
            Panel(
                f"[red]Unexpected Error[/red]: {str(e)}\n\n"
                f"[dim]This is a bug. Please report it at:[/dim]\n"
                f"[cyan]https://github.com/saadiqhorton/nexus-ai/issues/new[/cyan]",
                title="[bold]Nexus Error[/bold]",
                border_style="red",
            )
        )

    if debug_mode:
        logger.exception(f"Unhandled exception: {e}")
        console.print_exception(show_locals=True)

    sys.exit(exit_code)


def excepthook(exc_type, exc_value, exc_traceback) -> None:
    """Global exception handler."""
    if exc_type is KeyboardInterrupt:
        console.print("[yellow]Interrupted[/yellow]")
        sys.exit(130)
    handle_exception(exc_value, debug_mode=_debug_mode)


@click.group(
    cls=NexusGroup,
    invoke_without_command=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
)
@click.option("-m", "--model", default=None, help="Model to use (e.g., gpt-4o, claude-sonnet-4)")
@click.option(
    "-p",
    "--provider",
    default=None,
    help="Provider (openai, anthropic, ollama, openrouter)",
)
@click.option("-t", "--temperature", type=float, default=None, help="Temperature (0.0-2.0)")
@click.option("--max-tokens", type=int, default=None, help="Maximum tokens to generate")
@click.option("--no-stream", is_flag=True, default=False, help="Disable streaming output")
@click.option("-s", "--system", default=None, help="System prompt")
@click.option("-u", "--use", default=None, help="Use a prompt from library")
@click.option(
    "-f",
    "--file",
    "files",
    multiple=True,
    type=click.Path(),
    help="Include file/directory content",
)
@click.option(
    "-d",
    "--default",
    "set_default_flag",
    is_flag=True,
    default=False,
    help="Change default model (interactive or specify model after)",
)
@click.option("--fuzzy", is_flag=True, help="Fuzzy search model names")
@click.option(
    "--session",
    default=None,
    help="Session name (creates if missing, appends if exists)",
)
@click.option(
    "--allow-sensitive",
    is_flag=True,
    default=False,
    help="Allow reading sensitive files (e.g., .env, config files with secrets)",
)
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.pass_context
def cli(
    ctx,
    model,
    provider,
    temperature,
    max_tokens,
    no_stream,
    system,
    use,
    files,
    set_default_flag,
    fuzzy,
    session,
    allow_sensitive,
    debug,
):
    """Nexus - Ultra-minimal AI framework

    \b
    Examples:
      nexus "your prompt"                       # Use default model
      nexus -m gpt-4o "your prompt"             # Specify model
      nexus -p anthropic "your prompt"          # Specify provider
      nexus -f file.txt "explain this"          # Include file
      nexus -f .env --allow-sensitive "check"   # Include sensitive file
      cat file.txt | nexus "explain"            # Pipe content
      nexus --session myproject "your prompt"   # Save to session
      nexus -u summarize "content"              # Use system prompt from library

    \b
    Default Model:
      nexus -d                    Interactive selection
      nexus -d gpt-4o             Set directly
      nexus -d -p anthropic       Filter by provider
      nexus -d --fuzzy gpt        Fuzzy search
    """
    global _debug_mode
    _debug_mode = debug
    sys.excepthook = excepthook

    app = NexusApp()

    final_system_prompt = resolve_system_prompt(system, use, app.config_manager.config_dir)

    ctx.obj = {
        "app": app,
        "model": model,
        "provider": provider,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "no_stream": no_stream,
        "system": final_system_prompt,
        "files": files,
        "fuzzy": fuzzy,
        "session_name": session,
        "allow_sensitive": allow_sensitive,
        "debug": debug,
    }

    default_model_value = None
    if set_default_flag:
        for i, arg in enumerate(sys.argv):
            if arg in ["-d", "--default"]:
                j = i + 1
                while j < len(sys.argv) and sys.argv[j].startswith("-"):
                    j += 1
                if j < len(sys.argv):
                    default_model_value = sys.argv[j]
                break

    if set_default_flag:
        if default_model_value:
            ctx.invoke(default_command, model_id=default_model_value, fuzzy=fuzzy)
        else:
            ctx.invoke(default_command, fuzzy=fuzzy)
        sys.exit(0)

    if ctx.invoked_subcommand is not None:
        return

    if len(sys.argv) == 1:
        click.echo(ctx.get_help())
        return

    pass


@cli.result_callback()
@click.pass_context
def handle_result(ctx, result, **kwargs):
    handle_prompt(ctx, result, **kwargs)


cli.add_command(chat_command, "chat")
cli.add_command(models_command, "models")
cli.add_command(providers_command, "providers")
cli.add_command(config_command, "config")
cli.add_command(version_command, "version")
cli.add_command(default_command, "default")
cli.add_command(sessions_group, "sessions")
cli.add_command(prompts_group, "prompts")
cli.add_command(completion_command, "completion")


if __name__ == "__main__":
    cli()
