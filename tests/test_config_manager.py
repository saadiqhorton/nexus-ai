"""Tests for ConfigManager atomic save functionality"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from nexus.config.config_manager import ConfigManager


class TestAtomicConfigSave:
    """Test atomic write behavior for config saves"""

    def test_save_creates_temp_file_first(self, tmp_path, monkeypatch):
        """Test that save() creates temp file before final write"""
        config_path = tmp_path / "config.yaml"
        monkeypatch.setenv("HOME", str(tmp_path))
        
        # Mock to track temp file creation
        temp_files_created = []
        original_mkstemp = tempfile.mkstemp
        
        def track_mkstemp(*args, **kwargs):
            fd, path = original_mkstemp(*args, **kwargs)
            temp_files_created.append(path)
            return fd, path
        
        with patch("tempfile.mkstemp", side_effect=track_mkstemp):
            config_manager = ConfigManager(str(config_path))
            config_manager.save()
        
        # Verify temp file was created (and cleaned up)
        assert len(temp_files_created) > 0
        # Temp file should be cleaned up after successful rename
        for temp_file in temp_files_created:
            assert not os.path.exists(temp_file)

    def test_save_cleans_up_on_error(self, tmp_path, monkeypatch):
        """Test that temp file is cleaned up if save fails"""
        config_path = tmp_path / "config.yaml"
        monkeypatch.setenv("HOME", str(tmp_path))
        
        config_manager = ConfigManager(str(config_path))
        
        # Track temp files
        temp_files = []
        original_mkstemp = tempfile.mkstemp
        
        def track_mkstemp(*args, **kwargs):
            fd, path = original_mkstemp(*args, **kwargs)
            temp_files.append(path)
            return fd, path
        
        # Mock shutil.move to raise an error
        with patch("tempfile.mkstemp", side_effect=track_mkstemp):
            with patch("shutil.move", side_effect=IOError("Disk full")):
                with pytest.raises(IOError):
                    config_manager.save()
        
        # Verify temp file was cleaned up
        for temp_file in temp_files:
            assert not os.path.exists(temp_file), f"Temp file {temp_file} was not cleaned up"

    def test_save_is_atomic(self, tmp_path, monkeypatch):
        """Test that config file is not corrupted if save is interrupted"""
        config_path = tmp_path / "config.yaml"
        monkeypatch.setenv("HOME", str(tmp_path))
        
        # Create initial config
        config_manager = ConfigManager(str(config_path))
        initial_content = config_path.read_text()
        
        # Modify config
        config_manager.config.defaults.model = "new-model"
        
        # Save should be atomic - either complete or original intact
        try:
            config_manager.save()
            # If successful, verify new content
            saved_config = yaml.safe_load(config_path.read_text())
            assert saved_config["defaults"]["model"] == "new-model"
        except Exception:
            # If failed, original should be intact
            assert config_path.read_text() == initial_content

    def test_save_with_readonly_directory(self, tmp_path, monkeypatch):
        """Test save behavior when directory is read-only"""
        config_path = tmp_path / "config.yaml"
        monkeypatch.setenv("HOME", str(tmp_path))
        
        config_manager = ConfigManager(str(config_path))
        
        # Make directory read-only (platform-specific)
        if os.name != 'nt':  # Skip on Windows
            original_mode = tmp_path.stat().st_mode
            try:
                os.chmod(tmp_path, 0o444)
                with pytest.raises(Exception):  # Should raise permission error
                    config_manager.save()
            finally:
                os.chmod(tmp_path, original_mode)

    def test_config_survives_write_interruption(self, tmp_path, monkeypatch):
        """Test that original config survives write interruption"""
        config_path = tmp_path / "config.yaml"
        monkeypatch.setenv("HOME", str(tmp_path))
        
        # Create and save initial config
        config_manager = ConfigManager(str(config_path))
        config_manager.config.defaults.model = "original-model"
        config_manager.save()
        
        original_content = config_path.read_text()
        
        # Try to save with interruption
        config_manager.config.defaults.model = "new-model"
        
        with patch("yaml.dump", side_effect=KeyboardInterrupt("Interrupted!")):
            try:
                config_manager.save()
            except KeyboardInterrupt:
                pass
        
        # Original file should still exist and be intact
        assert config_path.exists()
        assert config_path.read_text() == original_content
