"""
Shared pytest fixtures and helpers for Nexus AI tests.

This module provides common fixtures and helper functions for testing,
particularly for Ollama integration tests that require environment-based
configuration.

Environment Variables:
    NEXUS_OLLAMA_URL: Base URL for Ollama server (e.g., "http://localhost:11434")
    NEXUS_TEST_MODEL: Model to use for integration tests (default: "phi4:14b")
"""

import os
from typing import Optional

import pytest
import requests

# =============================================================================
# Helper Functions
# =============================================================================


def get_ollama_url() -> Optional[str]:
    """Get Ollama URL from environment variable.

    Returns:
        The Ollama base URL from NEXUS_OLLAMA_URL env var, or None if not set.
    """
    return os.environ.get("NEXUS_OLLAMA_URL")


def get_test_model() -> str:
    """Get test model name from environment variable.

    Returns:
        The model name from NEXUS_TEST_MODEL env var, or "phi4:14b" as default.
    """
    return os.environ.get("NEXUS_TEST_MODEL", "phi4:14b")


def check_ollama_available(url: str) -> bool:
    """Check if Ollama server is responding at the given URL.

    Args:
        url: The base URL of the Ollama server (e.g., "http://localhost:11434")

    Returns:
        True if Ollama server responds with HTTP 200, False otherwise.
    """
    try:
        response = requests.get(f"{url}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def check_model_available(url: str, model: str) -> bool:
    """Check if a specific model is available in Ollama.

    Args:
        url: The base URL of the Ollama server
        model: The model name to check for (e.g., "phi4:14b")

    Returns:
        True if the model is available, False otherwise.
    """
    try:
        response = requests.get(f"{url}/api/tags", timeout=5)
        if response.status_code != 200:
            return False

        data = response.json()
        models = data.get("models", [])

        # Check if model name matches (handle both "model" and "model:tag" formats)
        model_base = model.split(":")[0] if ":" in model else model

        for m in models:
            model_name = m.get("name", "")
            # Match exact name or base name
            if model_name == model or model_name.startswith(f"{model_base}:"):
                return True
            # Also check if our model matches the installed model's base name
            installed_base = model_name.split(":")[0] if ":" in model_name else model_name
            if installed_base == model_base:
                return True

        return False
    except (requests.exceptions.RequestException, ValueError, KeyError):
        return False


# =============================================================================
# Module-level Constants (evaluated once at collection time)
# =============================================================================

OLLAMA_URL: Optional[str] = get_ollama_url()
OLLAMA_CONFIGURED: bool = OLLAMA_URL is not None
OLLAMA_AVAILABLE: bool = OLLAMA_CONFIGURED and check_ollama_available(OLLAMA_URL)
TEST_MODEL: str = get_test_model()
MODEL_AVAILABLE: bool = OLLAMA_AVAILABLE and check_model_available(OLLAMA_URL, TEST_MODEL)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ollama_url() -> Optional[str]:
    """Fixture that provides the Ollama URL from environment.

    Returns:
        The Ollama base URL from NEXUS_OLLAMA_URL, or None if not configured.
    """
    return OLLAMA_URL


@pytest.fixture
def test_model() -> str:
    """Fixture that provides the test model name.

    Returns:
        The model name from NEXUS_TEST_MODEL, or "phi4:14b" as default.
    """
    return TEST_MODEL


@pytest.fixture
def ollama_config() -> dict:
    """Fixture that provides Ollama provider configuration.

    Uses NEXUS_OLLAMA_URL if set, otherwise falls back to localhost:11434.

    Returns:
        Dictionary with base_url and enabled keys for OllamaProvider.
    """
    url = OLLAMA_URL if OLLAMA_URL else "http://localhost:11434"
    return {
        "base_url": f"{url}/v1",
        "enabled": True,
    }


@pytest.fixture
def ollama_config_custom() -> dict:
    """Fixture that provides hardcoded custom URL config for testing.

    This fixture provides a custom URL configuration for testing
    config handling, independent of environment variables.

    Returns:
        Dictionary with custom base_url and enabled keys.
    """
    return {
        "base_url": "http://custom.ollama.local:11434/v1",
        "enabled": True,
    }
