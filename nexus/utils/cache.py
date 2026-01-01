import json
import time
from pathlib import Path
from typing import Any, Optional

from nexus.utils.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Manages simple file-based caching"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, expiry_seconds: int = 3600) -> Optional[Any]:
        """Get value from cache if not expired"""
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            logger.debug(f"Cache miss: {key} (file does not exist)")
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)

            if time.time() - data["timestamp"] > expiry_seconds:
                logger.debug(f"Cache expired: {key}")
                return None

            logger.debug(f"Cache hit: {key}")
            return data["value"]
        except json.JSONDecodeError as e:
            logger.warning(f"Cache read failed for {key}: Invalid JSON - {e}")
            return None
        except OSError as e:
            logger.warning(f"Cache read failed for {key}: File error - {e}")
            return None
        except KeyError as e:
            logger.warning(f"Cache read failed for {key}: Missing field {e}")
            return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp"""
        cache_file = self.cache_dir / f"{key}.json"
        data = {"timestamp": time.time(), "value": value}
        try:
            with open(cache_file, "w") as f:
                json.dump(data, f)
            logger.debug(f"Cache write successful: {key}")
        except OSError as e:
            logger.warning(f"Cache write failed for {key}: {e}")
        except (TypeError, ValueError) as e:
            logger.warning(
                f"Cache write failed for {key}: Value not JSON serializable - {e}"
            )
