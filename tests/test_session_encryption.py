"""Tests for encrypted session storage."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from cryptography.fernet import Fernet

from nexus.session.manager import SessionManager
from nexus.session.models import Session


class TestSessionEncryption:
    """Tests for encrypted session load/save."""

    @pytest.fixture
    def mock_encryption(self):
        """Mock EncryptionManager to use a fixed key."""
        key = Fernet.generate_key()
        fernet = Fernet(key)
        
        with patch("nexus.session.manager.EncryptionManager") as MockClass:
            instance = MockClass.return_value
            instance.initialize.return_value = True
            instance.is_available = True
            instance.encrypt.side_effect = lambda x: fernet.encrypt(x.encode()).decode()
            instance.decrypt.side_effect = lambda x: fernet.decrypt(x.encode()).decode()
            yield instance

    @pytest.mark.asyncio
    async def test_save_encrypted_session(self, tmp_path, mock_encryption):
        """Test that session is saved with encryption."""
        manager = SessionManager(tmp_path)
        
        session = Session(name="secret-session", model="gpt-4", provider="openai")
        await manager.save_session(session)
        
        # Verify file exists
        session_path = tmp_path / "secret-session.json"
        assert session_path.exists()
        
        # Verify content is NOT json
        content = session_path.read_text()
        with pytest.raises(json.JSONDecodeError):
            json.loads(content)
            
        # Verify we mocked encryption
        mock_encryption.encrypt.assert_called()

    @pytest.mark.asyncio
    async def test_load_encrypted_session(self, tmp_path, mock_encryption):
        """Test loading an encrypted session."""
        manager = SessionManager(tmp_path)
        
        # Create encrypted file manually (via manager)
        original_session = Session(name="secret", model="gpt-4", provider="openai")
        await manager.save_session(original_session)
        
        # Load it back
        loaded = await manager.load_session("secret")
        
        assert loaded is not None
        assert loaded.name == "secret"
        
        # Verify decryption was called
        mock_encryption.decrypt.assert_called()

    @pytest.mark.asyncio
    async def test_load_plaintext_fallback(self, tmp_path, mock_encryption):
        """Test that loading plaintext session still works (backward compat)."""
        manager = SessionManager(tmp_path)
        
        # Create plaintext file manually
        session = Session(name="plain", model="gpt-4", provider="openai")
        path = tmp_path / "plain.json"
        path.write_text(session.model_dump_json(indent=2))
        
        # Load it
        loaded = await manager.load_session("plain")
        
        assert loaded is not None
        assert loaded.name == "plain"
        
        # Verify decrypt was NOT called
        mock_encryption.decrypt.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_corrupted_encrypted_session(self, tmp_path, mock_encryption):
        """Test handling of corrupted encrypted data."""
        manager = SessionManager(tmp_path)
        
        path = tmp_path / "corrupt.json"
        path.write_text("gibberish-not-encrypted-start")
        
        # Mock decrypt to fail
        mock_encryption.decrypt.side_effect = Exception("Decryption failed")
        
        loaded = await manager.load_session("corrupt")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_encryption_disabled_fallback(self, tmp_path):
        """Test behavior when encryption is unavailable."""
        with patch("nexus.session.manager.EncryptionManager") as MockClass:
            instance = MockClass.return_value
            instance.initialize.return_value = False
            instance.is_available = False
            
            manager = SessionManager(tmp_path)
            
            # Save session
            session = Session(name="no-encrypt", model="gpt-4", provider="openai")
            await manager.save_session(session)
            
            # Verify it is plaintext JSON
            path = tmp_path / "no-encrypt.json"
            content = path.read_text()
            json.loads(content)  # Should verify valid JSON
            
            # Verify encrypt NOT called
            instance.encrypt.assert_not_called()
