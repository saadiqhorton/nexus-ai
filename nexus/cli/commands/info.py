import asyncio

import click
from rich.console import Console
from rich.table import Table

from nexus.cli.utils import init_components

console = Console()


@click.command()
@click.option("-p", "--provider", help="Filter by provider")
def models(provider):
    """List all available models"""
    cfg, prov, comp = init_components()

    all_models = asyncio.run(prov.list_all_models())

    if not all_models:
        console.print("[yellow]No models available. Check your API keys.[/yellow]")
        return

    if provider:
        all_models = {k: v for k, v in all_models.items() if k == provider}

    for provider_name, models_list in all_models.items():
        table = Table(title=f"{provider_name.upper()} Models", show_header=True)
        table.add_column("Model ID", style="cyan")
        table.add_column("Context", justify="right", style="green")
        table.add_column("Streaming", justify="center")

        for model in models_list:
            table.add_row(
                model.id,
                f"{model.context_window:,}",
                "✓" if model.supports_streaming else "✗",
            )

        console.print(table)
        console.print()


@click.command()
def providers():
    """List all configured providers"""
    cfg, prov, comp = init_components()

    available = prov.list_providers()

    table = Table(title="Available Providers", show_header=True)
    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Default Model", style="green")

    all_providers = ["openai", "anthropic", "ollama", "openrouter"]

    for provider_name in all_providers:
        is_available = provider_name in available
        status = "✓" if is_available else "✗"
        status_color = "green" if is_available else "red"

        default_model = cfg.get_default_model(provider_name) if is_available else "N/A"

        table.add_row(
            provider_name, f"[{status_color}]{status}[/{status_color}]", default_model
        )

    console.print(table)


@click.command()
def config():
    """Show current configuration"""
    cfg, prov, comp = init_components()

    console.print("\n[bold cyan]Configuration[/bold cyan]")
    console.print(f"  Config file: [yellow]{cfg.config_path}[/yellow]")
    console.print("\n[bold cyan]Defaults[/bold cyan]")
    console.print(f"  Provider: [green]{cfg.get_default_provider()}[/green]")
    console.print(f"  Model: [green]{cfg.get_default_model()}[/green]")
    console.print(f"  Temperature: [green]{cfg.get('defaults.temperature')}[/green]")
    console.print(f"  Max tokens: [green]{cfg.get('defaults.max_tokens')}[/green]")
    console.print(f"  Streaming: [green]{cfg.get('defaults.stream')}[/green]")
    console.print()


@click.command()
def version():
    """Show version information"""
    console.print("[cyan]Nexus AI Framework[/cyan] v0.1.0")
    console.print("Ultra-minimal multi-provider AI CLI")


# Export individual commands for top-level CLI registration
models_command = models
providers_command = providers
config_command = config
version_command = version

__all__ = [
    "models_command",
    "providers_command",
    "config_command",
    "version_command",
]
