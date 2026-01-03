"""Encryption utilities for secure session storage."""

import getpass
import json
import os
import secrets
import sys
from typing import Optional, Tuple

import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from nexus.utils.logging import get_logger

logger = get_logger(__name__)

SERVICE_NAME = "nexus-ai-cli"
KEY_USERNAME = f"session_key_{getpass.getuser()}"


class EncryptionManager:
    """Manages encryption keys and operations."""

    def __init__(self, key_service: str = SERVICE_NAME, key_username: str = KEY_USERNAME):
        self.service = key_service
        self.username = key_username
        self._fernet: Optional[Fernet] = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize encryption manager, loading or generating key."""
        try:
            key = self._get_or_create_key()
            if key:
                self._fernet = Fernet(key)
                self._initialized = True
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize encryption: {e}")
            return False

    @property
    def is_available(self) -> bool:
        """Check if encryption is available."""
        return self._initialized

    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        return self._fernet.encrypt(data.encode("utf-8")).decode("utf-8")

    def decrypt(self, data: str) -> str:
        """Decrypt string data."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        return self._fernet.decrypt(data.encode("utf-8")).decode("utf-8")

    def _get_or_create_key(self) -> Optional[bytes]:
        """Get existing key from keyring or generate a new one."""
        try:
            # Try to get existing key
            key = keyring.get_password(self.service, self.username)
            
            if key:
                # Provide debug info about key source without leaking key
                logger.debug(f"Loaded encryption key from keyring service: {self.service}")
                return key.encode("utf-8")

            # Generate new key
            logger.info("Generating new encryption key...")
            new_key = Fernet.generate_key()
            key_str = new_key.decode("utf-8")
            
            # Store in keyring
            keyring.set_password(self.service, self.username, key_str)
            logger.info(f"Stored new encryption key in keyring service: {self.service}")
            
            return new_key

        except Exception as e:
            # If keyring fails (e.g. headless environment), fallback or fail
            logger.error(f"Keyring access failed: {e}")
            
            # Allow fallback to env var for CI/headless
            env_key = os.environ.get("NEXUS_ENCRYPTION_KEY")
            if env_key:
                logger.warning("Using encryption key from environment variable")
                return env_key.encode("utf-8")
                
            logger.warning("Encryption unavailable: Could not access keyring and no env key provided")
            return None
