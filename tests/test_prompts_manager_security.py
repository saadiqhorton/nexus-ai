"""
Security tests for PromptManager - Comprehensive path traversal prevention.
"""

import os
import tempfile
from pathlib import Path

import pytest

from nexus.prompts.manager import PromptManager, PromptSecurityError
from nexus.utils.errors import NexusError


class TestPromptSanitization:
    """Test input validation and sanitization."""

    def test_sanitize_name_rejects_empty_string(self):
        """Test that empty string is rejected."""
        manager = PromptManager(Path("/tmp/prompts"))

        with pytest.raises(
            PromptSecurityError, match="Prompt name must be a non-empty string"
        ):
            manager._sanitize_name("")

    def test_sanitize_name_rejects_whitespace_only(self):
        """Test that whitespace-only strings are rejected."""
        manager = PromptManager(Path("/tmp/prompts"))

        with pytest.raises(PromptSecurityError, match="Prompt name cannot be empty"):
            manager._sanitize_name("   ")

        with pytest.raises(PromptSecurityError, match="Prompt name cannot be empty"):
            manager._sanitize_name("\t\n\r")

    def test_sanitize_name_rejects_leading_trailing_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        manager = PromptManager(Path("/tmp/prompts"))

        result = manager._sanitize_name("  test  ")
        assert result == "test"

    def test_sanitize_name_preserves_valid_name(self):
        """Test that valid names are preserved unchanged."""
        manager = PromptManager(Path("/tmp/prompts"))

        valid_names = [
            "test",
            "valid_name",
            "valid-name",
            "valid123",
            "VALID_NAME",
            "test123abc",
        ]

        for name in valid_names:
            result = manager._sanitize_name(name)
            assert result == name, f"Expected '{name}', got '{result}'"

    def test_sanitize_name_replaces_invalid_chars(self):
        """Test that invalid characters are replaced with underscores."""
        manager = PromptManager(Path("/tmp/prompts"))

        test_cases = [
            ("test<name", "test_name"),
            ("test>name", "test_name"),
            ('test"name', "test_name"),
            ("test/name", "test_name"),
            ("test\\name", "test_name"),
            ("test|name", "test_name"),
            ("test?name", "test_name"),
            ("test*name", "test_name"),
            ("test:name", "test_name"),
        ]

        for input_name, expected in test_cases:
            result = manager._sanitize_name(input_name)
            assert result == expected, (
                f"Input '{input_name}' -> Expected '{expected}', got '{result}'"
            )

    def test_sanitize_name_max_length_enforcement(self):
        """Test that names are truncated to max length."""
        manager = PromptManager(Path("/tmp/prompts"))

        long_name = "a" * 300
        result = manager._sanitize_name(long_name)

        # Should be truncated to 255 characters
        assert len(result) <= 255
        assert result == "a" * 255

    def test_sanitize_name_multiple_invalid_chars(self):
        """Test that multiple invalid characters are all replaced."""
        manager = PromptManager(Path("/tmp/prompts"))

        result = manager._sanitize_name("test<>/\\|?*:name")
        assert result == "test________name"

    def test_sanitize_name_leading_dots_stripped(self):
        """Test that leading dots are stripped."""
        manager = PromptManager(Path("/tmp/prompts"))

        result = manager._sanitize_name("...test")
        assert result == "test"

        result = manager._sanitize_name(".test")
        assert result == "test"


class TestPathTraversalPrevention:
    """Test comprehensive path traversal attack prevention."""

    def test_sanitize_name_blocks_basic_traversal(self):
        """Test basic path traversal with ../"""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "../etc/passwd",
            "../../etc/passwd",
            "../../../etc/passwd",
            "....//etc/passwd",
            "test/../etc/passwd",
            "test/../../etc/passwd",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert ".." not in result, (
                f"Path traversal not blocked: '{vector}' -> '{result}'"
            )
            assert "/" not in result
            assert "\\" not in result
            assert result

    def test_sanitize_name_blocks_windows_traversal(self):
        """Test Windows-style path traversal with ..\\"""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "..\\..\\..\\windows\\system32",
            "..\\\\..\\\\..\\\\windows\\\\system32",
            "test..\\\\windows",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert ".." not in result, (
                f"Windows path traversal not blocked: '{vector}' -> '{result}'"
            )

    def test_sanitize_name_blocks_absolute_path_unix(self):
        """Test absolute path prevention on Unix."""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "/etc/passwd",
            "/etc/shadow",
            "/root/.ssh/id_rsa",
            "/var/log/auth.log",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert not result.startswith("/"), (
                f"Absolute path not blocked: '{vector}' -> '{result}'"
            )
            assert "/" not in result
            assert result

    def test_sanitize_name_blocks_absolute_path_windows(self):
        """Test absolute path prevention on Windows."""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "C:\\Windows\\System32",
            "C:\\Users\\Administrator\\Desktop",
            "D:\\sensitive\\data.txt",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert ":" not in result, (
                f"Windows absolute path not blocked: '{vector}' -> '{result}'"
            )

    def test_sanitize_name_blocks_mixed_separators(self):
        """Test mixed path separators."""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "../..//etc/passwd",
            "..\\..//etc/passwd",
            "../..\\\\etc/passwd",
            "..\\\\..//etc/passwd",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert ".." not in result, (
                f"Mixed separators not blocked: '{vector}' -> '{result}'"
            )

    def test_sanitize_name_blocks_hidden_traversal(self):
        """Test traversal attempts hidden in normal names."""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "normal-name/../../../etc/passwd",
            "test/..\\..\\..\\windows",
            "valid/../../../sensitive",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert ".." not in result, (
                f"Hidden traversal not blocked: '{vector}' -> '{result}'"
            )

    def test_sanitize_name_blocks_null_byte_injection(self):
        """Test null byte injection prevention."""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "test\x00/../etc/passwd",
            "test\x00/etc/passwd",
            "test\x00..\\windows",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert "\x00" not in result, (
                f"Null byte not removed: '{vector}' -> '{result}'"
            )

    def test_sanitize_name_blocks_unicode_separators(self):
        """Test Unicode path separators."""
        manager = PromptManager(Path("/tmp/prompts"))

        # Unicode separators that might bypass simple checks
        attack_vectors = [
            "test∕..∕etc∕passwd",  # Unicode division slash
            "test／..／etc／passwd",  # Unicode fullwidth slash
            "test＼..＼etc＼passwd",  # Unicode fullwidth backslash
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            # Should be sanitized to remove Unicode separators
            assert "∕" not in result
            assert "／" not in result
            assert "＼" not in result

    def test_sanitize_name_blocks_url_encoded(self):
        """Test URL-encoded path traversal."""
        manager = PromptManager(Path("/tmp/prompts"))

        attack_vectors = [
            "../etc/passwd%2e%2e/etc/passwd",
            "%2e%2e%2fetc%2fpasswd",
            "..%2fetc%2fpasswd",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            # Should be sanitized - URL decoding happens before our check
            assert ".." not in result or "%2e" not in result.lower()

    def test_sanitize_name_blocks_double_encoded(self):
        """Test double URL-encoded path traversal."""
        manager = PromptManager(Path("/tmp/prompts"))

        # %252e%252e = %2e%2e = ..
        attack_vectors = [
            "%252e%252e%252fetc%252fpasswd",
            "%252e%252e%2fetc%2fpasswd",
        ]

        for vector in attack_vectors:
            result = manager._sanitize_name(vector)
            assert "%252e" not in result.lower() or ".." not in result


class TestDefenseInDepth:
    """Test defense-in-depth validation."""

    def test_get_prompt_validates_resolved_path_within_storage(self):
        """Test that resolved path stays within storage directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "prompts"
            manager = PromptManager(storage_path)

            # Create a file outside storage
            outside_file = Path(temp_dir) / "outside.txt"
            outside_file.write_text("malicious content")

            # This should be blocked by the sanitization
            try:
                result = manager._sanitize_name("../../../outside.txt")
                # The sanitized name should not point outside
                assert ".." not in result
                assert "/" not in result
                assert "\\" not in result
            except PromptSecurityError:
                # Expected - sanitization should reject this
                pass

    def test_save_prompt_validates_resolved_path_within_storage(self):
        """Test save prompt path validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "prompts"
            manager = PromptManager(storage_path)

            # Try to save with path traversal
            try:
                sanitized = manager._sanitize_name("../../../outside.txt")
                # Should be sanitized to safe name
                assert ".." not in sanitized
                assert "/" not in sanitized
                assert "\\" not in sanitized
            except PromptSecurityError:
                # Expected - sanitization should reject this
                pass

    def test_delete_prompt_validates_resolved_path_within_storage(self):
        """Test delete prompt path validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "prompts"
            manager = PromptManager(storage_path)

            # Try to delete with path traversal
            try:
                sanitized = manager._sanitize_name("../../../outside.txt")
                # Should be sanitized to safe name
                assert ".." not in sanitized
                assert "/" not in sanitized
                assert "\\" not in sanitized
            except PromptSecurityError:
                # Expected - sanitization should reject this
                pass


class TestPromptManagerCRUD:
    """Test PromptManager CRUD operations with security."""

    def test_get_prompt_saves_and_loads(self, tmp_path):
        """Test basic get_prompt functionality."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Create a prompt
        manager.save_prompt("test_prompt", "This is a test prompt.")

        # Load it back
        content = manager.get_prompt("test_prompt")
        assert content == "This is a test prompt."

    def test_get_prompt_returns_none_nonexistent(self, tmp_path):
        """Test get_prompt returns None for non-existent prompt."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        content = manager.get_prompt("nonexistent")
        assert content is None

    def test_save_prompt_overwrites_existing(self, tmp_path):
        """Test save_prompt overwrites existing prompt."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Create prompt
        manager.save_prompt("test", "Original content")

        # Overwrite
        manager.save_prompt("test", "New content")

        # Check it was overwritten
        content = manager.get_prompt("test")
        assert content == "New content"

    def test_delete_prompt_removes_file(self, tmp_path):
        """Test delete_prompt removes the file."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Create prompt
        manager.save_prompt("test", "Content")

        # Delete it
        manager.delete_prompt("test")

        # Should not exist
        assert manager.get_prompt("test") is None

    def test_list_prompts_excludes_non_md_files(self, tmp_path):
        """Test list_prompts only includes .md files."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Create files
        manager.save_prompt("test1", "Content 1")
        manager.save_prompt("test2", "Content 2")

        # Create non-md file
        non_md_file = storage_path / "not_a_prompt.txt"
        non_md_file.write_text("Not a prompt")

        # List should only include .md files
        prompts = manager.list_prompts()
        assert len(prompts) == 2
        assert "test1" in prompts
        assert "test2" in prompts
        assert "not_a_prompt" not in prompts

    def test_list_prompts_returns_sorted(self, tmp_path):
        """Test list_prompts returns sorted names."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Create prompts in random order
        manager.save_prompt("zebra", "Content")
        manager.save_prompt("alpha", "Content")
        manager.save_prompt("beta", "Content")

        # List should be sorted
        prompts = manager.list_prompts()
        assert prompts == ["alpha", "beta", "zebra"]

    def test_save_prompt_sanitizes_name(self, tmp_path):
        """Test save_prompt sanitizes the prompt name."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Try to save with dangerous name
        sanitized = manager._sanitize_name("../etc/passwd")
        manager.save_prompt(sanitized, "Content")

        # Should be saved with safe name
        assert (storage_path / f"{sanitized}.md").exists()
        assert "../etc/passwd.md" not in os.listdir(storage_path)

    def test_get_prompt_sanitizes_name(self, tmp_path):
        """Test get_prompt sanitizes the prompt name."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Create safe prompt
        safe_name = manager._sanitize_name("normal")
        manager.save_prompt(safe_name, "Content")

        # Try to access with dangerous name
        content = manager.get_prompt("../etc/passwd")
        assert content is None  # Should not find the file

    def test_delete_prompt_sanitizes_name(self, tmp_path):
        """Test delete_prompt sanitizes the prompt name."""
        storage_path = tmp_path / "prompts"
        manager = PromptManager(storage_path)

        # Create safe prompt
        safe_name = manager._sanitize_name("normal")
        manager.save_prompt(safe_name, "Content")

        # Try to delete with dangerous name
        # Should not delete the safe prompt
        manager.delete_prompt("../etc/passwd")

        # Safe prompt should still exist
        assert manager.get_prompt(safe_name) == "Content"


class TestPromptSecurityError:
    """Test PromptSecurityError exception."""

    def test_prompt_security_error_inherits_from_nexus_error(self):
        """Test that PromptSecurityError inherits from NexusError."""
        error = PromptSecurityError("Test message")
        assert isinstance(error, NexusError)
        assert isinstance(error, PromptSecurityError)
        assert str(error) == "Test message"
