from typing import Optional

from nexus.config.config_manager import ConfigManager
from nexus.core.completion_handler import CompletionHandler
from nexus.core.provider_manager import ProviderManager
from nexus.utils.logging import get_logger

logger = get_logger(__name__)


class NexusApp:
    """
    Main application class that manages all components and their lifecycles.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_manager = ConfigManager(config_path) if config_path else ConfigManager()
        self.provider_manager = ProviderManager(self.config_manager)
        self.completion_handler = CompletionHandler(self.provider_manager, self.config_manager)
        logger.debug("NexusApp initialized")

    @classmethod
    def create(cls, config_path: Optional[str] = None) -> "NexusApp":
        """
        Factory method to create a NexusApp instance.
        """
        return cls(config_path)
