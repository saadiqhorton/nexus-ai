from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from nexus.cli.utils import init_components
from nexus.session.manager import SessionManager

console = Console()


@click.group(name="sessions", invoke_without_command=True)
@click.pass_context
def sessions_group(ctx):
    """Manage conversation sessions

    \b
    Commands:
      nexus sessions              List all sessions
      nexus sessions show <name>  Display conversation
      nexus sessions search <q>   Search sessions
      nexus sessions export       Export session
      nexus sessions rename       Rename a session
      nexus sessions delete       Delete a session
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(sessions_list)


@sessions_group.command(name="list")
@click.option("--recent", "-r", type=int, help="Show N most recent sessions")
def sessions_list(recent: int):
    """List all sessions"""
    cfg, prov, comp = init_components()

    sessions_dir = Path(cfg.config.sessions.storage_path)
    sm = SessionManager(sessions_dir)

    sessions = sm.list_sessions()

    if not sessions:
        console.print("[yellow]No sessions found[/yellow]")
        return

    if recent:
        sessions = sessions[:recent]

    table = Table(show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Model")
    table.add_column("Turns", justify="right")
    table.add_column("Updated", style="dim")

    for s in sessions:
        if s.name.startswith(".temp-"):
            continue
        table.add_row(
            s.name,
            f"{s.provider}/{s.model}",
            str(len(s.turns)),
            s.updated_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@sessions_group.command(name="show")
@click.argument("name")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["pretty", "json", "raw"]),
    default="pretty",
    help="Output format",
)
def sessions_show(name: str, fmt: str):
    """Display session conversation"""
    cfg, prov, comp = init_components()

    sessions_dir = Path(cfg.config.sessions.storage_path)
    sm = SessionManager(sessions_dir)
    session = sm.load_session(name)

    if not session:
        console.print(f"[red]Session '{name}' not found[/red]")
        return

    if fmt == "json":
        print(session.model_dump_json(indent=2))
        return

    if fmt == "raw":
        for turn in session.turns:
            print(f"[{turn.role}] {turn.content}")
        return

    console.print(f"\n[bold]Session: {name}[/bold]")
    console.print(
        f"[dim]Model: {session.provider}/{session.model} | Turns: {len(session.turns)}[/dim]\n"
    )

    for turn in session.turns:
        if turn.role == "user":
            console.print("[bold cyan]You:[/bold cyan]")
        else:
            console.print("[bold green]Assistant:[/bold green]")
        console.print(Markdown(turn.content))
        print()


@sessions_group.command(name="export")
@click.argument("name")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["json", "markdown"]),
    default="markdown",
    help="Export format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def sessions_export(name: str, fmt: str, output: str):
    """Export session as JSON or Markdown"""
    cfg, prov, comp = init_components()

    sessions_dir = Path(cfg.config.sessions.storage_path)
    sm = SessionManager(sessions_dir)

    try:
        content = sm.export_session(name, fmt)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return

    if output:
        Path(output).write_text(content)
        console.print(f"[green]✓[/green] Exported to {output}")
    else:
        print(content)


@sessions_group.command(name="delete")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def sessions_delete(name: str, force: bool):
    """Delete a session"""
    cfg, prov, comp = init_components()

    sessions_dir = Path(cfg.config.sessions.storage_path)
    sm = SessionManager(sessions_dir)

    if not force:
        if not click.confirm(f"Delete session '{name}'?"):
            return

    if sm.delete_session(name):
        console.print(f"[green]✓[/green] Session '{name}' deleted")
    else:
        console.print(f"[red]Session '{name}' not found[/red]")


@sessions_group.command(name="search")
@click.argument("query")
@click.option("--limit", "-l", type=int, default=10, help="Maximum results to show")
def sessions_search(query: str, limit: int):
    """Search sessions by name or content"""
    cfg, prov, comp = init_components()

    sessions_dir = Path(cfg.config.sessions.storage_path)
    sm = SessionManager(sessions_dir)

    results = sm.search_sessions(query)

    if not results:
        console.print("[yellow]No matches found[/yellow]")
        return

    console.print(f"\n[bold]Found {len(results)} results:[/bold]\n")

    for result in results[:limit]:
        console.print(f"[cyan]{result.session_name}[/cyan] ({result.turn_count} turns)")
        if result.match_type == "name":
            console.print("  [dim]Match in name[/dim]")
        else:
            console.print(f"  [dim]Match: {result.matched_text}[/dim]")
        print()


@sessions_group.command(name="rename")
@click.argument("old_name")
@click.argument("new_name")
def sessions_rename(old_name: str, new_name: str):
    """Rename a session"""
    cfg, prov, comp = init_components()

    sessions_dir = Path(cfg.config.sessions.storage_path)
    sm = SessionManager(sessions_dir)

    if sm.rename_session(old_name, new_name):
        console.print(f"[green]✓[/green] Renamed '{old_name}' to '{new_name}'")
    else:
        console.print(
            f"[red]Failed: '{old_name}' not found or '{new_name}' already exists[/red]"
        )
