import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from nexus.core.app import NexusApp
from nexus.prompts.manager import PromptManager

console = Console()


@click.group(name="prompts", invoke_without_command=True)
@click.pass_context
def prompts_group(ctx):
    """Manage reusable system prompts (patterns)

    
    Commands:
      nexus prompts list          List available prompts
      nexus prompts show <name>   Show prompt content
      nexus prompts new <name>    Create a new prompt
      nexus prompts edit <name>   Edit an existing prompt
      nexus prompts delete <name> Delete a prompt
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(prompts_list)


@prompts_group.command(name="list")
def prompts_list():
    """List all available prompts"""
    app = NexusApp()
    pm = PromptManager(app.config_manager.config_dir / "prompts")

    prompts = pm.list_prompts()

    if not prompts:
        console.print("[yellow]No prompts found[/yellow]")
        console.print("Create one with: [green]nexus prompts new <name>[/green]")
        return

    table = Table(show_header=True)
    table.add_column("Name", style="cyan")

    for p in prompts:
        table.add_row(p)

    console.print(table)


@prompts_group.command(name="show")
@click.argument("name")
def prompts_show(name):
    """Show prompt content"""
    app = NexusApp()
    pm = PromptManager(app.config_manager.config_dir / "prompts")

    content = pm.get_prompt(name)
    if content is None:
        console.print(f"[red]Prompt '{name}' not found[/red]")
        return

    console.print(f"\n[bold]Prompt: {name}[/bold]\n")
    console.print(Markdown(content))


@prompts_group.command(name="new")
@click.argument("name")
def prompts_new(name):
    """Create a new prompt"""
    app = NexusApp()
    pm = PromptManager(app.config_manager.config_dir / "prompts")

    if pm.get_prompt(name):
        console.print(f"[red]Prompt '{name}' already exists[/red]")
        return

    content = click.edit(text=f"# {name}\n\nEnter your system prompt here.")

    if content:
        pm.save_prompt(name, content)
        console.print(f"[green]✓[/green] Created prompt '{name}'")
    else:
        console.print("[yellow]Aborted[/yellow]")


@prompts_group.command(name="edit")
@click.argument("name")
def prompts_edit(name):
    """Edit an existing prompt"""
    app = NexusApp()
    pm = PromptManager(app.config_manager.config_dir / "prompts")

    current_content = pm.get_prompt(name)
    if current_content is None:
        console.print(f"[red]Prompt '{name}' not found[/red]")
        return

    content = click.edit(text=current_content)

    if content:
        pm.save_prompt(name, content)
        console.print(f"[green]✓[/green] Updated prompt '{name}'")
    else:
        console.print("[yellow]No changes[/yellow]")


@prompts_group.command(name="delete")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def prompts_delete(name, force):
    """Delete a prompt"""
    app = NexusApp()
    pm = PromptManager(app.config_manager.config_dir / "prompts")

    if not force:
        if not click.confirm(f"Delete prompt '{name}'?"):
            return

    if pm.delete_prompt(name):
        console.print(f"[green]✓[/green] Deleted prompt '{name}'")
    else:
        console.print(f"[red]Prompt '{name}' not found[/red]")
