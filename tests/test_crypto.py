"""Tests for encryption utilities."""

import os
from unittest.mock import Mock, patch

import pytest
from cryptography.fernet import Fernet

from nexus.utils.crypto import EncryptionManager


class TestEncryptionManager:
    """Tests for EncryptionManager."""

    def test_initialization_generates_key(self):
        """Test that initialization generates and stores a key."""
        with patch("keyring.get_password", return_value=None) as mock_get:
            with patch("keyring.set_password") as mock_set:
                manager = EncryptionManager(key_service="test-service", key_username="test-user")
                success = manager.initialize()
                
                assert success
                assert manager.is_available
                mock_get.assert_called_once()
                mock_set.assert_called_once()
                
                # Verify key format
                args = mock_set.call_args[0]
                key_str = args[2]
                Fernet(key_str.encode("utf-8"))  # Should not raise

    def test_initialization_loads_key(self):
        """Test that initialization loads existing key."""
        existing_key = Fernet.generate_key().decode("utf-8")
        
        with patch("keyring.get_password", return_value=existing_key) as mock_get:
            with patch("keyring.set_password") as mock_set:
                manager = EncryptionManager(key_service="test-service", key_username="test-user")
                success = manager.initialize()
                
                assert success
                assert manager.is_available
                mock_get.assert_called_once()
                mock_set.assert_not_called()

    def test_encryption_roundtrip(self):
        """Test encrypt and decrypt roundtrip."""
        # Use real key for this test, but mock keyring to avoid system calls
        key = Fernet.generate_key().decode("utf-8")
        
        with patch("keyring.get_password", return_value=key):
            manager = EncryptionManager()
            manager.initialize()
            
            original_text = "Secret Data 123"
            encrypted = manager.encrypt(original_text)
            decrypted = manager.decrypt(encrypted)
            
            assert original_text != encrypted
            assert original_text == decrypted

    def test_fallback_to_env_var(self):
        """Test fallback to environment variable if keyring fails."""
        key = Fernet.generate_key().decode("utf-8")
        
        with patch("keyring.get_password", side_effect=Exception("Keyring failed")):
            with patch.dict(os.environ, {"NEXUS_ENCRYPTION_KEY": key}):
                manager = EncryptionManager()
                success = manager.initialize()
                
                assert success
                assert manager.is_available
                
                # verify it works
                encrypted = manager.encrypt("test")
                assert manager.decrypt(encrypted) == "test"

    def test_initialization_failure(self):
        """Test graceful failure when no key available."""
        with patch("keyring.get_password", side_effect=Exception("Keyring failed")):
            with patch.dict(os.environ, {}, clear=True):
                manager = EncryptionManager()
                success = manager.initialize()
                
                assert not success
                assert not manager.is_available
