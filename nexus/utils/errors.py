"""Exception hierarchy for Nexus AI."""


class NexusError(Exception):
    """Base exception for all Nexus errors."""

    exit_code = 1

    def __init__(self, message: str, exit_code: int | None = None, hint: str | None = None):
        """
        Initialize exception with optional exit code and hint.

        Args:
            message: Error message
            exit_code: Override default exit code
            hint: Helpful hint for resolving the error (uses Python 3.11+ __notes__)
        """
        super().__init__(message)
        if exit_code:
            self.exit_code = exit_code
        if hint:
            if hasattr(self, "add_note"):
                self.add_note(hint)


class ResourceError(NexusError):
    """External resources unavailable (API, network, files)."""

    exit_code = 75


class ConfigError(NexusError):
    """Configuration-related errors (.env, config.yaml, missing keys)."""

    exit_code = 78


class ProviderError(ResourceError):
    """Provider API errors (network, auth, rate limit)."""

    pass


class FileAccessError(ResourceError):
    """File system access errors."""

    exit_code = 66


class ModelNotFoundError(ConfigError):
    """Requested model not available."""

    def __init__(self, model_name: str, available: list[str] | None = None):
        message = f"Model '{model_name}' not found"
        hint = None
        if available:
            hint = f"Available models: {', '.join(available[:5])}"
            if len(available) > 5:
                hint += f" (and {len(available) - 5} more)"
        super().__init__(message, hint=hint)


class PromptSecurityError(NexusError):
    """Prompt contains dangerous content (path traversal, injection)."""

    exit_code = 77


class UsageError(NexusError):
    """Invalid CLI arguments or options."""

    exit_code = 64
