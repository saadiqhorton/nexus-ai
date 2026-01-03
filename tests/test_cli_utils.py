"""Tests for CLI utilities including input validation"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from nexus.cli.utils import MAX_INPUT_SIZE, process_files_and_stdin


class TestInputSizeValidation:
    """Test input size validation to prevent OOM attacks"""

    def test_stdin_within_limit(self, monkeypatch):
        """Test that stdin within size limit is processed normally"""
        # Create content within limit (1MB)
        test_content = "x" * (1024 * 1024)
        monkeypatch.setattr("sys.stdin", StringIO(test_content))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        result = process_files_and_stdin((), "test prompt")
        assert test_content in result
        assert "test prompt" in result

    def test_stdin_exceeds_limit(self, monkeypatch):
        """Test that oversized stdin raises ValueError"""
        # Create content exceeding 10MB limit
        oversized_content = "x" * (MAX_INPUT_SIZE + 1000)
        monkeypatch.setattr("sys.stdin", StringIO(oversized_content))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        with pytest.raises(ValueError) as exc_info:
            process_files_and_stdin((), "test prompt")

        assert "exceeds maximum size" in str(exc_info.value)
        assert "10MB" in str(exc_info.value)
        assert "--file" in str(exc_info.value)

    def test_stdin_exactly_at_limit(self, monkeypatch):
       """Test that stdin exactly at limit is accepted"""
        test_content = "x" * MAX_INPUT_SIZE
        monkeypatch.setattr("sys.stdin", StringIO(test_content))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        result = process_files_and_stdin((), "test prompt")
        assert test_content in result

    def test_no_stdin_no_size_check(self, monkeypatch):
        """Test that TTY stdin doesn't trigger size validation"""
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        
        result = process_files_and_stdin((), "test prompt")
        assert result == "test prompt"

    def test_empty_stdin(self, monkeypatch):
        """Test that empty stdin is handled correctly"""
        monkeypatch.setattr("sys.stdin", StringIO(""))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        result = process_files_and_stdin((), "test prompt")
        assert result == "test prompt"


class TestFilesAndStdinCombined:
    """Test combined file and stdin processing"""

    def test_file_and_stdin_combined(self, tmp_path, monkeypatch):
        """Test that files and stdin are combined correctly"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("file content")

        # Mock stdin
        stdin_content = "stdin content"
        monkeypatch.setattr("sys.stdin", StringIO(stdin_content))
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)

        result = process_files_and_stdin((str(test_file),), "prompt")
        assert "file content" in result
        assert "stdin content" in result
        assert "prompt" in result
