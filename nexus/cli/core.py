import asyncio
import sys

import click

from nexus.cli.utils import (
    init_components_fast,
    process_files_and_stdin,
)
from nexus.session.manager import SessionManager
from nexus.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


class PassthroughCommand(click.Command):
    """Dummy command that does nothing - used for unknown commands"""

    def __init__(self):
        super().__init__("_passthrough")

    def invoke(self, ctx):
        pass


class NexusGroup(click.Group):
    """Custom Click Group that doesn't error on unknown commands"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._passthrough = PassthroughCommand()

    def get_command(self, ctx, cmd_name):
        """Override to return passthrough for unknown commands"""
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        return self._passthrough

    def resolve_command(self, ctx, args):
        """Override to not error on unknown commands"""
        try:
            cmd_name, cmd, args = click.Group.resolve_command(self, ctx, args)
            return cmd_name, cmd, args
        except click.exceptions.UsageError as e:
            error_msg = str(e).lower()
            if "no such command" in error_msg and "no such option" not in error_msg:
                return "_passthrough", self._passthrough, args
            raise


def handle_prompt(ctx, result, **kwargs):
    """Handle direct prompts after command processing"""

    real_commands = [
        "chat",
        "models",
        "providers",
        "config",
        "default",
        "sessions",
        "completion",
        "version",
        "prompts",
    ]

    if ctx.invoked_subcommand in real_commands:
        return

    model = ctx.obj.get("model")
    provider = ctx.obj.get("provider")
    temperature = ctx.obj.get("temperature")
    max_tokens = ctx.obj.get("max_tokens")
    no_stream = ctx.obj.get("no_stream")
    system = ctx.obj.get("system")
    files = ctx.obj.get("files")
    session_name = ctx.obj.get("session_name")
    allow_sensitive = ctx.obj.get("allow_sensitive", False)

    args = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in [
            "-m",
            "--model",
            "-p",
            "--provider",
            "-t",
            "--temperature",
            "--max-tokens",
            "-s",
            "--system",
            "-u",
            "--use",
            "--session",
        ]:
            i += 2
        elif arg in ["-f", "--file"]:
            i += 2
        elif arg in ["--no-stream", "--allow-sensitive"]:
            i += 1
        elif arg in ["-d", "--default"]:
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("-"):
                i += 2
            else:
                i += 1
        elif not arg.startswith("-"):
            args.append(arg)
            i += 1
        else:
            i += 1

    if args:
        prompt = " ".join(args)
        cfg, prov, comp = init_components_fast()

        final_prompt = process_files_and_stdin(
            files, prompt, allow_sensitive=allow_sensitive
        )

        session_manager = None
        if session_name:
            from pathlib import Path

            sessions_dir = Path.home() / ".nexus" / "sessions"
            session_manager = SessionManager(sessions_dir)
            resolved_provider = provider or cfg.get_default_provider()
            resolved_model = model or cfg.get_default_model(resolved_provider)
            session_manager.get_or_create_session(
                session_name, resolved_model, resolved_provider
            )

        asyncio.run(
            comp.complete(
                prompt=final_prompt,
                model=model,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=not no_stream,
                system_prompt=system,
                session_name=session_name,
                session_manager=session_manager,
            )
        )
