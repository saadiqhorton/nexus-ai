import asyncio
from typing import Dict, List, Optional, Tuple

import click
from rich.console import Console

from nexus.cli.fuzzy_selector import InteractiveFuzzySelector
from nexus.config.config_manager import ConfigManager
from nexus.providers.base import ModelInfo
from nexus.utils.logging import get_logger

logger = get_logger(__name__)
console = Console()

FUZZY_SEARCH_PAGE_SIZE = 10


def _build_model_lookup(all_models: Dict[str, List[ModelInfo]]) -> Tuple[Dict, Dict]:
    """Build lookup maps for provider/model resolution"""
    provider_model_map = {}
    model_name_map = {}

    for provider_name, models in all_models.items():
        for model in models:
            provider_model_map[f"{provider_name}/{model.id}".lower()] = (
                provider_name,
                model.id,
            )
            provider_model_map[f"{provider_name.lower()}/{model.id.lower()}"] = (
                provider_name,
                model.id,
            )

            if model.id.lower() not in model_name_map:
                model_name_map[model.id.lower()] = []
            model_name_map[model.id.lower()].append((provider_name, model.id))

    return provider_model_map, model_name_map


def _resolve_model_selection(
    model_id: str, cfg: ConfigManager, all_models: Dict[str, List[ModelInfo]]
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Resolve provider/model from user input with offline-friendly fallback"""
    provider_model_map, model_name_map = _build_model_lookup(all_models)

    if not model_id:
        return None, None, None, "no_selection"

    model_key = model_id.lower()

    if "/" in model_id:
        if model_key in provider_model_map:
            provider, model = provider_model_map[model_key]
            return provider, model, None, None
        provider, model = model_id.split("/", 1)
        warning = f"Model '{model_id}' not verified against available providers; saving anyway."
        return provider, model, warning, None

    if model_key in model_name_map:
        matches = model_name_map[model_key]
        if len(matches) == 1:
            provider, model = matches[0]
            return provider, model, None, None
        return None, None, matches, "ambiguous"

    default_provider = cfg.get_default_provider()
    warning = f"Using default provider '{default_provider}' without model availability check."
    return default_provider, model_id, warning, None


def display_fuzzy_page(
    console: Console,
    scored: List[Tuple[int, str, str]],
    query: str,
    current_page: int,
    page_size: int = 10,
) -> None:
    """Display a single page of fuzzy search results with pagination info"""
    start_idx = current_page * page_size
    end_idx = start_idx + page_size

    page_results = scored[start_idx:end_idx]
    total_results = len(scored)
    total_pages = (total_results + page_size - 1) // page_size

    console.clear()

    console.print(f"[bold]Fuzzy matches for '{query}':[/bold]\n")

    for local_idx, (score, provider, model_id) in enumerate(page_results, 1):
        console.print(f"  [{local_idx}] {provider}/{model_id}")

    console.print()

    result_start = start_idx + 1
    result_end = min(end_idx, total_results)

    console.print(
        f"Page {current_page + 1} of {total_pages} - "
        f"Showing {result_start}-{result_end} of {total_results} results"
    )

    console.print("[dim](n = next page, p = prev page, Enter = cancel, or select number)[/dim]")


@click.command(name="default")
@click.argument("model_id", required=False)
@click.option("-p", "--provider", "filter_provider", help="Filter by provider")
@click.option("--fuzzy", is_flag=True, help="Fuzzy search model names")
@click.pass_context
def default_command(ctx, model_id, filter_provider, fuzzy):
    """Change default model

    \b
    Examples:
      nexus -d                    Interactive selection
      nexus -d gpt-4o             Set directly
      nexus -d -p openai          Filter by provider
      nexus -d --fuzzy claude     Fuzzy search
    """
    from nexus.cli.utils import init_components

    cfg, prov, comp = init_components()

    all_models = asyncio.run(prov.list_all_models()) or {}

    if filter_provider:
        if filter_provider in all_models:
            all_models = {filter_provider: all_models[filter_provider]}
        else:
            console.print(f"[red]Provider '{filter_provider}' not found[/red]")
            console.print(f"Available: {', '.join(all_models.keys())}")
            return

    flat_models = []
    for prov_name, models_list in all_models.items():
        for model in models_list:
            flat_models.append((prov_name, model.id, model))

    if model_id and not fuzzy:
        selected_provider, selected_model, note, error = _resolve_model_selection(
            model_id, cfg, all_models
        )

        if error == "ambiguous":
            console.print(f"[red]Model '{model_id}' found in multiple providers[/red]")
            console.print("[yellow]Specify as provider/model[/yellow]")
            return

        if error == "no_selection":
            pass
        elif selected_provider and selected_model:
            cfg.config.defaults.provider = selected_provider
            cfg.config.defaults.model = selected_model
            cfg.save()
            console.print(f"[green]✓[/green] Default: {selected_provider}/{selected_model}")
            if note:
                console.print(f"[yellow]{note}[/yellow]")
            return
        elif selected_provider and not selected_model:
            console.print(f"[yellow]Model '{model_id}' found in multiple providers[/yellow]")
            console.print("[yellow]Specify as provider/model[/yellow]")
            return

    if not flat_models:
        console.print("[yellow]No models available[/yellow]")
        return

    if fuzzy:
        if not model_id:
            console.print("[yellow]Usage: nexus -d --fuzzy <search-term>[/yellow]")
            return

        query = model_id.lower()
        scored = []
        for prov_name, model_id_str, model_obj in flat_models:
            full_name = f"{prov_name}/{model_id_str}".lower()
            if query in full_name:
                pos = full_name.find(query)
                score = 100 - pos - (len(full_name) - len(query))
                scored.append((score, prov_name, model_id_str))

        scored.sort(reverse=True)

        if not scored:
            console.print(f"[yellow]No matches for '{model_id}'[/yellow]")
            return

        try:
            selector = InteractiveFuzzySelector(
                scored_results=scored,
                query=model_id,
                page_size=FUZZY_SEARCH_PAGE_SIZE,
            )
            result = selector.run()

            if result.cancelled:
                console.print("[dim]Cancelled[/dim]")
                return

            cfg.config.defaults.provider = result.provider
            cfg.config.defaults.model = result.model
            cfg.save()
            console.print(f"[green]✓[/green] Default: {result.provider}/{result.model}")
            return

        except Exception as e:
            logger.warning(f"Interactive mode failed, falling back to text-based pagination: {e}")

            total_pages = (len(scored) + FUZZY_SEARCH_PAGE_SIZE - 1) // FUZZY_SEARCH_PAGE_SIZE
            current_page = 0

            while True:
                display_fuzzy_page(console, scored, model_id, current_page, FUZZY_SEARCH_PAGE_SIZE)

                console.print()
                try:
                    selection = input("Select number (or n/next/p/prev/Enter): ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[dim]Cancelled[/dim]")
                    return

                if selection in ("n", "next"):
                    current_page = (current_page + 1) % total_pages
                    continue
                elif selection in ("p", "prev"):
                    current_page = (current_page - 1) % total_pages
                    continue
                elif selection == "":
                    console.print("[dim]Cancelled[/dim]")
                    return

                if selection.isdigit():
                    selection_num = int(selection)
                    page_start = current_page * FUZZY_SEARCH_PAGE_SIZE
                    page_end = min(page_start + FUZZY_SEARCH_PAGE_SIZE, len(scored))
                    actual_page_size = page_end - page_start

                    if 1 <= selection_num <= actual_page_size:
                        local_idx = selection_num - 1
                        global_idx = page_start + local_idx
                        _, selected_provider, selected_model = scored[global_idx]
                        cfg.config.defaults.provider = selected_provider
                        cfg.config.defaults.model = selected_model
                        cfg.save()
                        console.print(
                            f"[green]✓[/green] Default: {selected_provider}/{selected_model}"
                        )
                        return
                    else:
                        console.print("[red]Invalid selection[/red]")
                        continue
                else:
                    console.print("[red]Invalid input[/red]")
                    continue

    console.print("\n[bold]Available Models:[/bold]\n")

    idx = 1
    index_map = {}
    for prov_name in sorted(all_models.keys()):
        console.print(f"[cyan][{prov_name.upper()}][/cyan]")
        for model in sorted(all_models[prov_name], key=lambda m: m.id):
            current = (
                prov_name == cfg.config.defaults.provider and model.id == cfg.config.defaults.model
            )
            marker = "*" if current else " "
            suffix = " [dim](current)[/dim]" if current else ""
            console.print(f"  {marker}[{idx}] {model.id}{suffix}")
            index_map[str(idx)] = (prov_name, model.id)
            idx += 1
        print()

    current_default = f"{cfg.config.defaults.provider}/{cfg.config.defaults.model}"
    console.print(f"[bold]Current:[/bold] {current_default}\n")

    try:
        selection = input("Enter number or provider/model (Enter to cancel): ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled[/dim]")
        return

    if not selection:
        console.print("[dim]Cancelled[/dim]")
        return

    if selection in index_map:
        selected_provider, selected_model = index_map[selection]
    else:
        selected_provider, selected_model, note, error = _resolve_model_selection(
            selection, cfg, all_models
        )
        if error or not selected_provider:
            console.print(f"[red]Invalid selection: '{selection}'[/red]")
            return

    cfg.config.defaults.provider = selected_provider
    if selected_model:
        cfg.config.defaults.model = selected_model
        cfg.save()
        console.print(f"[green]✓[/green] Default: {selected_provider}/{selected_model}")
    else:
        console.print(f"[yellow]Model '{selection}' found in multiple providers[/yellow]")
        console.print("[yellow]Specify as provider/model[/yellow]")
