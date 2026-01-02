import logging
import sys
from typing import Optional


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None):
    """
    Setup logging for the application.
    """
    logger = logging.getLogger("nexus")
    logger.setLevel(level)

    # Prevent adding handlers if they already exist
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler if log_file is provided
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


def get_logger(name: str):
    """
    Get a logger with the given name under the 'nexus' namespace.
    """
    if name.startswith("nexus."):
        return logging.getLogger(name)
    return logging.getLogger(f"nexus.{name}")
