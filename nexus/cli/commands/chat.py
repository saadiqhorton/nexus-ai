import asyncio

import click

from nexus.cli.repl import repl_main
from nexus.cli.utils import process_files_and_stdin, resolve_system_prompt


@click.command(name="chat")
@click.option("-m", "--model", help="Model to use (e.g., gpt-4, claude-sonnet-4)")
@click.option("-p", "--provider", help="Provider to use (openai, anthropic, ollama)")
@click.option("-t", "--temperature", type=float, help="Temperature (0.0-2.0)")
@click.option("--max-tokens", type=int, help="Maximum tokens to generate")
@click.option("-s", "--system", help="System prompt")
@click.option("-u", "--use", help="Use a prompt from library")
@click.option(
    "-f",
    "--file",
    "files",
    multiple=True,
    type=click.Path(),
    help="Include file/directory content",
)
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
def chat_command(
    model,
    provider,
    temperature,
    max_tokens,
    system,
    use,
    files,
    session,
    allow_sensitive,
):
    """Start interactive chat REPL

    \b
    Examples:
      nexus chat                                    # Start REPL with temp session
      nexus chat --session myproject                # Start REPL with named session
      nexus chat -m gpt-4o -p openai                # REPL with specific model
      nexus chat -u personality                     # REPL with system prompt from library
    """
    from nexus.core.app import NexusApp

    app = NexusApp()
    final_system_prompt = resolve_system_prompt(system, use, app.config_manager.config_dir)

    if files:
        process_files_and_stdin(files, "", allow_sensitive=allow_sensitive)

    asyncio.run(
        repl_main(
            model=model,
            provider=provider,
            session_name=session,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=final_system_prompt,
        )
    )
