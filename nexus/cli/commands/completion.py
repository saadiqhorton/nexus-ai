from pathlib import Path

import click
from rich.console import Console

from nexus.cli.completion import get_bash_completion, get_zsh_completion

console = Console()


@click.command(name="completion")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh"]),
    default="bash",
    help="Shell type",
)
@click.option("--output", "-o", type=click.Path(), help="Output file")
@click.option("--remove", is_flag=True, help="Remove completions from shell rc file")
def completion_command(shell: str, output: str, remove: bool):
    """Generate or remove shell completion scripts

    \b
    Usage:
      nexus completion                    Generate bash completion (default)
      nexus completion --shell=bash       Generate bash completion
      nexus completion --shell=zsh        Generate zsh completion
      nexus completion --output <file>    Write to specific file
      nexus completion --remove           Uninstall
    """
    if remove:
        rc_file = Path.home() / f".{shell}rc"
        if not rc_file.exists():
            console.print(f"[yellow]No {rc_file} found to clean up.[/yellow]")
            return

        content = rc_file.read_text()
        start_marker = "# >>> NEXUS COMPLETION START >>>"
        end_marker = "# <<< NEXUS COMPLETION END <<<"

        if start_marker in content and end_marker in content:
            import re

            pattern = re.compile(
                f"{re.escape(start_marker)}.*?{re.escape(end_marker)}\n*", re.DOTALL
            )
            new_content = pattern.sub("", content)

            if new_content != content:
                rc_file.write_text(new_content)
                console.print(f"[green]✓[/green] Removed Nexus completions from {rc_file}")
                console.print("[dim]Restart your shell for changes to take effect.[/dim]")
            else:
                console.print(f"[yellow]Could not remove block from {rc_file}[/yellow]")
        else:
            console.print(f"[yellow]Completion markers not found in {rc_file}[/yellow]")
            console.print("[dim]You may need to remove them manually.[/dim]")
        return

    if shell == "bash":
        script = get_bash_completion()
    else:
        script = get_zsh_completion()

    if output:
        Path(output).write_text(script)
        console.print(f"[green]✓[/green] Wrote completion to {output}")
        console.print(f"[dim]Source it in your ~/.{shell}rc[/dim]")
    else:
        print(script)
