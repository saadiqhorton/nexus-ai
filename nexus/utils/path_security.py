"""Path security validation for file operations.

This module provides security validation for file paths to prevent:
- Path traversal attacks (../ sequences, symlinks)
- Accidental exposure of sensitive files (.env, SSH keys, etc.)
- Access to files outside designated base directories

Key functions:
- validate_file_path(): Main validation with canonicalization
- is_sensitive_path(): Pattern matching for sensitive files
"""

import re
import sys
from pathlib import Path
from typing import Optional

import click

from nexus.utils.errors import FileAccessError

# Sensitive file patterns (based on OWASP and industry best practices)
SENSITIVE_PATTERNS = [
    r"\.env.*",  # .env, .env.local, .env.production
    r".*\.pem$",  # SSL certificates
    r".*\.key$",  # Private keys
    r".*\.p12$",  # PKCS#12 certificates
    r".*\.pfx$",  # PKCS#12 certificates (Windows)
    r"id_rsa.*",  # SSH RSA keys
    r"id_dsa",  # SSH DSA keys
    r"id_ecdsa",  # SSH ECDSA keys
    r"id_ed25519",  # SSH Ed25519 keys
    r"\.aws/credentials",  # AWS credentials
    r"\.kube/config",  # Kubernetes config
    r"credentials\.json",  # GCP/Firebase credentials
    r"secrets\.ya?ml",  # Secret files (secrets.yaml, secrets.yml)
    r"\.npmrc",  # npm credentials
    r"\.pypirc",  # PyPI credentials
    r"\.netrc",  # Generic credentials file
    r"\.dockercfg",  # Docker credentials
    r"\.docker/config\.json",  # Docker credentials (new format)
]

# Sensitive directories
SENSITIVE_DIRS = {".ssh", ".aws", ".kube", ".gnupg", ".docker"}


def is_sensitive_path(path: Path) -> bool:
    """Check if path matches sensitive file patterns.

    Args:
        path: Path object to check

    Returns:
        True if path appears to be a sensitive file, False otherwise

    Examples:
        >>> is_sensitive_path(Path(".env"))
        True
        >>> is_sensitive_path(Path("/home/user/.ssh/id_rsa"))
        True
        >>> is_sensitive_path(Path("README.md"))
        False
    """
    # Check directory components
    for part in path.parts:
        if part in SENSITIVE_DIRS:
            return True

    # Check filename against patterns
    filename = path.name
    for pattern in SENSITIVE_PATTERNS:
        if re.match(pattern, filename, re.IGNORECASE):
            return True

    return False


def validate_file_path(
    path_str: str,
    base_dir: Optional[Path] = None,
    allow_sensitive: bool = False,
    interactive: bool = True,
) -> Path:
    """Validate file path with canonicalization and security checks.

    This function implements defense-in-depth file path validation:
    1. Resolves path to canonical absolute form (handles .., symlinks, etc.)
    2. Verifies path exists
    3. Checks path is within base_dir if specified (prevents traversal)
    4. Warns/blocks sensitive files unless explicitly allowed

    Args:
        path_str: User-provided path string
        base_dir: Base directory to restrict access (None = no restriction)
        allow_sensitive: Skip sensitive file warnings/blocking
        interactive: Whether to prompt user for confirmation (vs. deny outright)

    Returns:
        Resolved canonical Path object

    Raises:
        FileAccessError: Path escapes base_dir, is sensitive, or invalid, or doesn't exist

    Examples:
        >>> # Safe file access
        >>> path = validate_file_path("README.md")
        >>> # Blocked traversal
        >>> validate_file_path("../../../etc/passwd", base_dir=Path.cwd())
        FileAccessError: Access denied: '../../../etc/passwd' is outside working directory
        >>> # Sensitive file with warning
        >>> validate_file_path(".env", interactive=False)
        FileAccessError: Sensitive file access blocked: .env
    """
    # 1. Resolve to canonical absolute path (handles .., symlinks, etc.)
    try:
        path = Path(path_str).resolve()
    except (OSError, RuntimeError) as e:
        raise FileAccessError(f"Invalid path: {path_str} ({e})")

    # 2. Verify path exists
    if not path.exists():
        raise FileAccessError(f"Path not found: {path_str}")

    # 3. Check base directory restriction (if specified)
    if base_dir:
        base = base_dir.resolve()
        # Check if path is within base using is_relative_to (Python 3.9+)
        # or fallback to relative_to (Python 3.8)
        try:
            # Python 3.9+ - cleaner API
            if hasattr(path, "is_relative_to"):
                if not path.is_relative_to(base):
                    raise FileAccessError(
                        f"Access denied: '{path_str}' is outside working directory"
                    )
            else:
                # Python 3.8 fallback - use relative_to which raises ValueError
                try:
                    path.relative_to(base)
                except ValueError:
                    raise FileAccessError(
                        f"Access denied: '{path_str}' is outside working directory"
                    )
        except FileAccessError:
            # Re-raise FileAccessError as-is
            raise

    # 4. Sensitive file detection
    if not allow_sensitive and is_sensitive_path(path):
        if interactive and sys.stdin.isatty():
            # Interactive mode: warn and prompt
            click.secho(
                f"⚠️  WARNING: '{path.name}' appears to be a sensitive file",
                fg="yellow",
                err=True,
            )
            if not click.confirm("Include this file?", default=False):
                raise FileAccessError(f"User declined to include sensitive file: {path.name}")
        else:
            # Non-interactive mode: deny
            raise FileAccessError(
                f"Sensitive file access blocked: {path.name}\n"
                f"Use --allow-sensitive flag to override"
            )

    return path
