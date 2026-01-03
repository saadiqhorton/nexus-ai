import sys
from pathlib import Path
from typing import Optional

from nexus.core.app import NexusApp
from nexus.prompts.manager import PromptManager
from nexus.utils.errors import FileAccessError
from nexus.utils.path_security import validate_file_path

# Maximum input size from stdin (10MB)
MAX_INPUT_SIZE = 10 * 1024 * 1024


def is_binary_file(filepath: str) -> bool:
    """Check if a file is binary by attempting to read it as text"""
    try:
        with open(filepath, encoding="utf-8") as f:
            f.read(1024)
        return False
    except UnicodeDecodeError:
        return True
    except Exception:
        return True


def read_file_with_metadata(filepath: str, console=None, allow_sensitive: bool = False) -> str:
    """Read file and format with metadata header

    Args:
        filepath: Path to file to read
        console: Optional Rich console for error output
        allow_sensitive: If True, skip sensitive file warnings/blocking

    Returns:
        Formatted file content with metadata header, or empty string on error
    """
    try:
        # Validate path security (handles path traversal, sensitive files, etc.)
        path_obj = validate_file_path(
            filepath, base_dir=None, allow_sensitive=allow_sensitive, interactive=True
        )

        if is_binary_file(str(path_obj)):
            return ""

        content = path_obj.read_text(encoding="utf-8")

        formatted = f"File: {path_obj}\n---\n{content}\n---\n"
        return formatted

    except FileNotFoundError as e:
        raise FileAccessError(str(e)) from e
    except PermissionError as e:
        raise FileAccessError(str(e)) from e
    except Exception as e:
        if console:
            console.print(f"[red]Error reading file {filepath}: {e}[/red]")
        return ""


def process_files_and_stdin(files: tuple, prompt: str, allow_sensitive: bool = False) -> str:
    """Process file/directory inputs and stdin, combine with prompt

    Args:
        files: Tuple of file/directory paths to process
        prompt: User prompt text
        allow_sensitive: If True, skip sensitive file warnings/blocking

    Returns:
        Combined content from files, stdin, and prompt
    """
    parts = []

    if files:
        for path_str in files:
            # Validate path exists before checking type
            # validate_file_path will raise FileNotFoundError if path doesn't exist
            try:
                validated_path = validate_file_path(
                    path_str,
                    base_dir=None,
                    allow_sensitive=allow_sensitive,
                    interactive=True,
                )
            except (FileNotFoundError, PermissionError) as e:
                raise FileAccessError(str(e)) from e

            if validated_path.is_file():
                content = read_file_with_metadata(
                    str(validated_path), allow_sensitive=allow_sensitive
                )
                if content:
                    parts.append(content)
            elif validated_path.is_dir():
                for file_path in validated_path.rglob("*"):
                    # Filter hidden files
                    if file_path.is_file() and not any(p.startswith(".") for p in file_path.parts):
                        # Validate each file in directory traversal
                        try:
                            validate_file_path(
                                str(file_path),
                                base_dir=None,
                                allow_sensitive=allow_sensitive,
                                interactive=True,
                            )
                            content = read_file_with_metadata(
                                str(file_path), allow_sensitive=allow_sensitive
                            )
                            if content:
                                parts.append(content)
                        except (FileNotFoundError, PermissionError) as e:
                            raise FileAccessError(str(e)) from e

    if not sys.stdin.isatty():
        # Read with size limit to prevent OOM attacks
        stdin_content = sys.stdin.read(MAX_INPUT_SIZE + 1)
        if len(stdin_content) > MAX_INPUT_SIZE:
            raise ValueError(
                f"Input exceeds maximum size of {MAX_INPUT_SIZE // (1024*1024)}MB. "
                f"Use --file for large inputs."
            )
        if stdin_content.strip():
            parts.append(stdin_content)

    if prompt:
        parts.append(prompt)

    return "\n".join(parts) if parts else prompt


def resolve_system_prompt(
    system_arg: Optional[str], use_arg: Optional[str], config_dir: Path
) -> Optional[str]:
    """Resolve system prompt from -s arg or -u (library) arg"""
    if system_arg:
        return system_arg

    if use_arg:
        pm = PromptManager(config_dir / "prompts")
        content = pm.get_prompt(use_arg)
        if content:
            return content
        from rich.console import Console

        console = Console()
        console.print(f"[yellow]Warning: Prompt '{use_arg}' not found in library[/yellow]")
        return None

    return None


def init_components():
    """Initialize NexusApp, ProviderManager, and CompletionHandler with full model listing"""
    app = NexusApp()
    return app.config_manager, app.provider_manager, app.completion_handler


def init_components_fast():
    """Initialize components optimized for direct completions (skip model listing)"""
    app = NexusApp()
    app.provider_manager.list_all_models = app.provider_manager.list_all_models_fast
    return app.config_manager, app.provider_manager, app.completion_handler
