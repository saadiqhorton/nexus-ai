from pathlib import Path
from typing import Dict, List, Optional

from nexus.providers.anthropic_provider import AnthropicProvider
from nexus.providers.base import BaseProvider, ModelInfo
from nexus.providers.ollama_provider import OllamaProvider
from nexus.providers.openai_provider import OpenAIProvider
from nexus.providers.openrouter_provider import OpenRouterProvider
from nexus.utils.cache import CacheManager
from nexus.utils.logging import get_logger

logger = get_logger(__name__)


class ProviderManager:
    """Manages all AI providers"""

    # Registry of available provider classes
    PROVIDER_CLASSES = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "openrouter": OpenRouterProvider,
    }

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.providers: Dict[str, BaseProvider] = {}

        # Initialize cache
        self.config_dir = Path(config_manager.config_dir)
        cache_dir = self.config_dir / "cache"
        self.cache = CacheManager(cache_dir)

    def _initialize_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """Initialize a specific provider"""
        if provider_name in self.providers:
            return self.providers[provider_name]

        provider_class = self.PROVIDER_CLASSES.get(provider_name)
        if not provider_class:
            return None

        provider_config = self.config_manager.get_provider_config(provider_name)

        if provider_config.get("enabled", False):
            try:
                provider = provider_class(provider_config)
                if provider.is_available():
                    self.providers[provider_name] = provider
                    logger.debug(f"Initialized provider: {provider_name}")
                    return provider
                else:
                    logger.warning(
                        f"Provider {provider_name} is enabled but not available (check configuration/API keys)"
                    )
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name}: {e}")
        return None

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get provider by name"""
        return self._initialize_provider(name)

    def list_providers(self) -> List[str]:
        """List all available provider names (enabled in config)"""
        enabled = []
        for name in self.PROVIDER_CLASSES.keys():
            if self.config_manager.get_provider_config(name).get("enabled", False):
                enabled.append(name)
        return enabled

    async def list_all_models(self, use_cache: bool = True) -> Dict[str, List[ModelInfo]]:
        """Get models from all providers"""
        if use_cache:
            cached_models = self.cache.get("all_models", expiry_seconds=3600)
            if cached_models:
                logger.debug("Returning cached models")
                # Convert back to ModelInfo objects
                result = {}
                for p_name, models in cached_models.items():
                    result[p_name] = [ModelInfo(**m) for m in models]
                return result

        all_models = {}
        # We need to initialize all enabled providers to list their models
        enabled_providers = self.list_providers()
        for provider_name in enabled_providers:
            provider = self._initialize_provider(provider_name)
            if provider:
                try:
                    models = await provider.list_models()
                    if models:
                        all_models[provider_name] = models
                except Exception as e:
                    logger.error(f"Error listing models from {provider_name}: {e}")

        if all_models:
            # Cache the models (converting ModelInfo to dict for JSON serialization)
            cache_data = {
                p_name: [m.model_dump() for m in models] for p_name, models in all_models.items()
            }
            self.cache.set("all_models", cache_data)

        return all_models

    async def list_all_models_fast(self, use_cache: bool = True) -> Dict[str, List[ModelInfo]]:
        """Fast version that only lists models for enabled providers, skipping slow ones when possible"""
        if use_cache:
            cached_models = self.cache.get("all_models", expiry_seconds=3600)
            if cached_models:
                logger.debug("Returning cached models")
                # Convert back to ModelInfo objects
                result = {}
                for p_name, models in cached_models.items():
                    result[p_name] = [ModelInfo(**m) for m in models]
                return result

        all_models = {}
        enabled_providers = self.list_providers()

        # For direct completions, we don't need to list ALL models
        # Only initialize providers that might be used
        for provider_name in enabled_providers:
            provider = self._initialize_provider(provider_name)
            if provider:
                try:
                    # For Ollama (local), always try to list models
                    if provider_name == "ollama":
                        models = await provider.list_models()
                        if models:
                            all_models[provider_name] = models
                    else:
                        # For remote providers, just check if they're available
                        # Don't actually fetch the full model list unless needed
                        if provider.is_available():
                            all_models[provider_name] = []
                except Exception as e:
                    logger.error(f"Error checking {provider_name}: {e}")

        if all_models:
            # Cache the models (converting ModelInfo to dict for JSON serialization)
            cache_data = {
                p_name: [m.model_dump() for m in models] for p_name, models in all_models.items()
            }
            self.cache.set("all_models", cache_data)

        return all_models

    async def find_model(
        self, model_id: str, provider_name: Optional[str] = None
    ) -> Optional[tuple]:
        """
        Find a model across providers
        Returns: (provider_name, ModelInfo) or None
        """
        if provider_name:
            # Search specific provider
            provider = self.get_provider(provider_name)
            if provider:
                try:
                    models = await provider.list_models()
                    for model in models:
                        if model.id == model_id or model.name == model_id:
                            return (provider_name, model)
                except Exception as e:
                    logger.error(f"Error searching models in {provider_name}: {e}")
        else:
            # Search all providers
            enabled_providers = self.list_providers()
            for prov_name in enabled_providers:
                provider = self._initialize_provider(prov_name)
                if provider:
                    try:
                        models = await provider.list_models()
                        for model in models:
                            if model.id == model_id or model.name == model_id:
                                return (prov_name, model)
                    except Exception as e:
                        logger.error(f"Error searching models in {prov_name}: {e}")

        return None
