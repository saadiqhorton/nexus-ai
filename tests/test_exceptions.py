"""Comprehensive tests for exception hierarchy and behavior.

Tests cover:
1. Exception hierarchy validation
2. Exit code attributes
3. ModelNotFoundError hints and truncation
4. NexusError __init__ with hints (Python 3.8-3.14 compatibility)
5. FileAccessError specifics
"""

import sys

import pytest

from nexus.utils.errors import (
    ConfigError,
    FileAccessError,
    ModelNotFoundError,
    NexusError,
    PromptSecurityError,
    ProviderError,
    ResourceError,
    UsageError,
)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_nexus_error(self):
        """Test that all custom exceptions inherit from NexusError."""
        exceptions = [
            NexusError,
            ResourceError,
            ConfigError,
            ProviderError,
            FileAccessError,
            ModelNotFoundError,
            PromptSecurityError,
            UsageError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, NexusError), (
                f"{exc_class.__name__} should inherit from NexusError"
            )

    def test_resource_error_inherits_from_nexus_error(self):
        """Test ResourceError inheritance chain."""
        assert issubclass(ResourceError, NexusError)
        assert not issubclass(NexusError, ResourceError)

    def test_config_error_inherits_from_nexus_error(self):
        """Test ConfigError inheritance chain."""
        assert issubclass(ConfigError, NexusError)
        assert not issubclass(ConfigError, ResourceError)

    def test_provider_error_inherits_from_resource_error(self):
        """Test ProviderError inherits from ResourceError."""
        assert issubclass(ProviderError, NexusError)
        assert issubclass(ProviderError, ResourceError)
        assert not issubclass(ProviderError, ConfigError)

    def test_file_access_error_inherits_from_resource_error(self):
        """Test FileAccessError inherits from ResourceError."""
        assert issubclass(FileAccessError, NexusError)
        assert issubclass(FileAccessError, ResourceError)
        assert not issubclass(FileAccessError, ConfigError)

    def test_model_not_found_error_inherits_from_config_error(self):
        """Test ModelNotFoundError inherits from ConfigError."""
        assert issubclass(ModelNotFoundError, NexusError)
        assert issubclass(ModelNotFoundError, ConfigError)
        assert not issubclass(ModelNotFoundError, ResourceError)

    def test_prompt_security_error_inherits_from_nexus_error(self):
        """Test PromptSecurityError inheritance chain."""
        assert issubclass(PromptSecurityError, NexusError)
        assert not issubclass(PromptSecurityError, ConfigError)
        assert not issubclass(PromptSecurityError, ResourceError)

    def test_usage_error_inherits_from_nexus_error(self):
        """Test UsageError inheritance chain."""
        assert issubclass(UsageError, NexusError)
        assert not issubclass(UsageError, ConfigError)
        assert not issubclass(UsageError, ResourceError)


class TestExitCodes:
    """Test exit code attributes on exceptions."""

    def test_nexus_error_default_exit_code(self):
        """Test NexusError has default exit_code."""
        assert NexusError.exit_code == 1

    def test_resource_error_exit_code(self):
        """Test ResourceError has correct exit_code (75 - EX_TEMPFAIL)."""
        assert ResourceError.exit_code == 75

    def test_config_error_exit_code(self):
        """Test ConfigError has correct exit_code (78 - EX_CONFIG)."""
        assert ConfigError.exit_code == 78

    def test_provider_error_inherits_exit_code(self):
        """Test ProviderError inherits exit_code from ResourceError."""
        exc = ProviderError("Test error")
        assert exc.exit_code == 75

    def test_file_access_error_exit_code(self):
        """Test FileAccessError has correct exit_code (66 - EX_NOINPUT)."""
        assert FileAccessError.exit_code == 66
        exc = FileAccessError("Test error")
        assert exc.exit_code == 66

    def test_model_not_found_error_exit_code(self):
        """Test ModelNotFoundError inherits exit_code from ConfigError."""
        assert ModelNotFoundError.exit_code == 78
        exc = ModelNotFoundError("test-model")
        assert exc.exit_code == 78

    def test_prompt_security_error_exit_code(self):
        """Test PromptSecurityError has correct exit_code (77 - EX_NOPERM)."""
        assert PromptSecurityError.exit_code == 77
        exc = PromptSecurityError("Test error")
        assert exc.exit_code == 77

    def test_usage_error_exit_code(self):
        """Test UsageError has correct exit_code (64 - EX_USAGE)."""
        assert UsageError.exit_code == 64
        exc = UsageError("Test error")
        assert exc.exit_code == 64

    def test_exit_code_override_in_init(self):
        """Test that exit_code can be overridden in __init__."""
        exc = NexusError("Test", exit_code=42)
        assert exc.exit_code == 42

    def test_exit_code_override_with_none_uses_default(self):
        """Test that exit_code=None uses default value."""
        exc = NexusError("Test", exit_code=None)
        assert exc.exit_code == 1

    def test_all_exceptions_have_exit_code_class_attribute(self):
        """Test all exception classes have exit_code defined."""
        exceptions = [
            NexusError,
            ResourceError,
            ConfigError,
            ProviderError,
            FileAccessError,
            ModelNotFoundError,
            PromptSecurityError,
            UsageError,
        ]

        for exc_class in exceptions:
            assert hasattr(exc_class, "exit_code"), (
                f"{exc_class.__name__} should have exit_code class attribute"
            )
            assert isinstance(exc_class.exit_code, int), (
                f"{exc_class.__name__}.exit_code should be an integer"
            )
            assert 1 <= exc_class.exit_code <= 78, (
                f"{exc_class.__name__}.exit_code should be in valid range 1-78"
            )


class TestModelNotFoundErrorHints:
    """Test ModelNotFoundError hint generation."""

    def test_hint_with_available_models(self):
        """Test hint includes available models list."""
        available = ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]
        exc = ModelNotFoundError("fake-model", available=available)

        assert str(exc) == "Model 'fake-model' not found"

        if sys.version_info >= (3, 11):
            assert hasattr(exc, "__notes__")
            assert len(exc.__notes__) == 1
            assert "Available models:" in exc.__notes__[0]
            assert "gpt-4" in exc.__notes__[0]
            assert "gpt-3.5-turbo" in exc.__notes__[0]
            assert "claude-3-opus" in exc.__notes__[0]

    def test_hint_shows_first_five_models(self):
        """Test hint truncates to first 5 models when more available."""
        available = [f"model-{i}" for i in range(10)]
        exc = ModelNotFoundError("fake-model", available=available)

        if sys.version_info >= (3, 11):
            assert hasattr(exc, "__notes__")
            notes = exc.__notes__[0]
            assert "model-0" in notes
            assert "model-1" in notes
            assert "model-2" in notes
            assert "model-3" in notes
            assert "model-4" in notes
            assert "model-5" not in notes
            assert "and 5 more" in notes

    def test_hint_exactly_five_models_no_truncation(self):
        """Test hint shows all models when exactly 5 available."""
        available = [f"model-{i}" for i in range(5)]
        exc = ModelNotFoundError("fake-model", available=available)

        if sys.version_info >= (3, 11):
            assert hasattr(exc, "__notes__")
            notes = exc.__notes__[0]
            assert "model-0" in notes
            assert "model-4" in notes
            assert "more" not in notes

    def test_hint_with_single_available_model(self):
        """Test hint with only one available model."""
        exc = ModelNotFoundError("fake-model", available=["gpt-4"])

        if sys.version_info >= (3, 11):
            assert hasattr(exc, "__notes__")
            notes = exc.__notes__[0]
            assert "Available models: gpt-4" in notes

    def test_no_hint_without_available_models(self):
        """Test no hint when available models list is None."""
        exc = ModelNotFoundError("fake-model", available=None)

        if sys.version_info >= (3, 11):
            assert not hasattr(exc, "__notes__") or len(exc.__notes__) == 0

    def test_no_hint_with_empty_available_models_list(self):
        """Test no hint when available models list is empty."""
        exc = ModelNotFoundError("fake-model", available=[])

        if sys.version_info >= (3, 11):
            assert not hasattr(exc, "__notes__") or len(exc.__notes__) == 0

    def test_hint_message_format(self):
        """Test hint message follows expected format."""
        available = ["model-a", "model-b"]
        exc = ModelNotFoundError("missing", available=available)

        if sys.version_info >= (3, 11):
            expected_hint = "Available models: model-a, model-b"
            assert exc.__notes__[0] == expected_hint

    def test_hint_truncation_message_format(self):
        """Test truncation message format when >5 models."""
        available = [f"model-{i}" for i in range(7)]
        exc = ModelNotFoundError("missing", available=available)

        if sys.version_info >= (3, 11):
            expected_hint = (
                "Available models: model-0, model-1, model-2, model-3, model-4 (and 2 more)"
            )
            assert exc.__notes__[0] == expected_hint


class TestNexusErrorInitWithHints:
    """Test NexusError __init__ with hint parameter."""

    def test_hint_creates_notes_on_python_311_plus(self):
        """Test that hint parameter creates __notes__ on Python 3.11+."""
        if sys.version_info >= (3, 11):
            exc = NexusError("Error message", hint="This is a helpful hint")

            assert hasattr(exc, "__notes__")
            assert len(exc.__notes__) == 1
            assert exc.__notes__[0] == "This is a helpful hint"

    def test_hint_no_error_on_python_38_to_310(self):
        """Test graceful degradation on Python 3.8-3.10 (no add_note)."""
        exc = NexusError("Error message", hint="This is a helpful hint")

        assert str(exc) == "Error message"
        assert exc.exit_code == 1

        if sys.version_info < (3, 11):
            assert not hasattr(exc, "__notes__")

    def test_hint_with_none_value(self):
        """Test that hint=None does not create notes."""
        exc = NexusError("Error message", hint=None)

        if sys.version_info >= (3, 11):
            assert not hasattr(exc, "__notes__") or len(exc.__notes__) == 0

    def test_hint_with_custom_exit_code(self):
        """Test hint parameter works with custom exit_code."""
        exc = NexusError("Error", exit_code=42, hint="Hint text")

        assert exc.exit_code == 42
        if sys.version_info >= (3, 11):
            assert hasattr(exc, "__notes__")
            assert exc.__notes__[0] == "Hint text"

    def test_message_preserved_with_hint(self):
        """Test that error message is preserved when hint is provided."""
        msg = "Something went wrong"
        exc = NexusError(msg, hint="Try again")

        assert str(exc) == msg

    def test_add_note_not_called_when_unavailable(self):
        """Test that missing add_note method doesn't cause errors."""
        if sys.version_info >= (3, 11):
            exc = NexusError("Test", hint="Hint")
            assert hasattr(exc, "add_note")

        if sys.version_info < (3, 11):
            exc = NexusError("Test", hint="Hint")
            assert not hasattr(exc, "__notes__")

    def test_multiple_notes_from_multiple_exceptions(self):
        """Test that each exception gets its own notes."""
        if sys.version_info >= (3, 11):
            exc1 = NexusError("Error 1", hint="Hint 1")
            exc2 = NexusError("Error 2", hint="Hint 2")

            assert exc1.__notes__[0] == "Hint 1"
            assert exc2.__notes__[0] == "Hint 2"
            assert exc1.__notes__ != exc2.__notes__


class TestFileAccessError:
    """Test FileAccessError specific behavior."""

    def test_file_access_error_exit_code_is_66(self):
        """Test FileAccessError uses exit code 66 (EX_NOINPUT)."""
        exc = FileAccessError("Cannot read file")
        assert exc.exit_code == 66

    def test_file_access_error_message_format(self):
        """Test FileAccessError message format."""
        message = "Unable to open configuration file"
        exc = FileAccessError(message)

        assert str(exc) == message

    def test_file_access_error_inherits_from_resource_error(self):
        """Test FileAccessError is a ResourceError."""
        exc = FileAccessError("Test")
        assert isinstance(exc, ResourceError)
        assert isinstance(exc, NexusError)

    def test_file_access_error_with_hint(self):
        """Test FileAccessError with hint parameter."""
        if sys.version_info >= (3, 11):
            exc = FileAccessError("File error", hint="Check file permissions")

            assert hasattr(exc, "__notes__")
            assert exc.__notes__[0] == "Check file permissions"

    def test_file_access_error_exit_code_override(self):
        """Test FileAccessError exit_code can be overridden."""
        exc = FileAccessError("File error", exit_code=1)
        assert exc.exit_code == 1

    def test_file_access_error_class_attribute(self):
        """Test FileAccessError class has correct exit_code."""
        assert FileAccessError.exit_code == 66

    def test_file_access_error_custom_message(self):
        """Test FileAccessError accepts custom error messages."""
        messages = [
            "File not found",
            "Permission denied",
            "Path is a directory",
            "Invalid file format",
        ]

        for msg in messages:
            exc = FileAccessError(msg)
            assert str(exc) == msg


class TestExceptionBehavior:
    """Test general exception behavior and attributes."""

    def test_exception_can_be_raised_and_caught(self):
        """Test exceptions can be raised and caught normally."""
        with pytest.raises(NexusError):
            raise NexusError("Test error")

    def test_exception_can_be_caught_by_base_class(self):
        """Test all exceptions can be caught as NexusError."""
        exceptions_to_test = [
            ResourceError,
            ConfigError,
            ProviderError,
            FileAccessError,
            ModelNotFoundError,
            PromptSecurityError,
            UsageError,
        ]

        for exc_class in exceptions_to_test:
            with pytest.raises(NexusError):
                raise exc_class("Test error")

    def test_exception_message_string_conversion(self):
        """Test exception message can be converted to string."""
        exc = NexusError("Test message with unicode: 你好世界")
        assert "Test message" in str(exc)
        assert "你好世界" in str(exc)

    def test_exception_repr(self):
        """Test exception repr contains useful information."""
        exc = NexusError("Test error")
        repr_str = repr(exc)
        assert "NexusError" in repr_str
        assert "Test error" in repr_str

    def test_exception_args_tuple(self):
        """Test exception args tuple contains message."""
        exc = NexusError("Test message")
        assert exc.args == ("Test message",)

    def test_exception_without_message(self):
        """Test exception can be raised with empty message."""
        exc = NexusError("")
        assert str(exc) == ""

    def test_exception_with_multiline_message(self):
        """Test exception handles multiline messages."""
        msg = "Line 1\nLine 2\nLine 3"
        exc = NexusError(msg)
        assert str(exc) == msg
        assert "Line 1" in str(exc)
        assert "Line 2" in str(exc)
        assert "Line 3" in str(exc)

    def test_exit_code_persists_after_raise_catch(self):
        """Test exit_code persists after exception is raised and caught."""
        exc = ConfigError("Config error", exit_code=78)
        original_exit_code = exc.exit_code

        try:
            raise exc
        except ConfigError as e:
            assert e.exit_code == original_exit_code
            assert e.exit_code == 78


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_nexus_error_with_hint_none_python_311(self):
        """Test NexusError with hint=None on Python 3.11+."""
        if sys.version_info >= (3, 11):
            exc = NexusError("Test", hint=None)
            assert not hasattr(exc, "__notes__") or len(exc.__notes__) == 0

    def test_model_not_found_error_with_special_characters_in_names(self):
        """Test ModelNotFoundError handles special characters in model names."""
        model_name = "model-with_special.chars@123"
        exc = ModelNotFoundError(model_name, available=["model-1", "model-2"])
        assert model_name in str(exc)

    def test_model_not_found_error_with_unicode_model_names(self):
        """Test ModelNotFoundError handles unicode in model names."""
        model_name = "模型-名称"
        exc = ModelNotFoundError(model_name, available=["gpt-4"])
        assert model_name in str(exc)

    def test_empty_string_available_models_list(self):
        """Test ModelNotFoundError with empty string in available list."""
        exc = ModelNotFoundError("test", available=[""])
        if sys.version_info >= (3, 11):
            assert hasattr(exc, "__notes__")

    def test_exception_with_very_long_message(self):
        """Test exception with very long error message."""
        long_msg = "Error: " + "x" * 10000
        exc = NexusError(long_msg)
        assert len(str(exc)) > 10000

    def test_exit_code_zero_not_overridden(self):
        """Test exit_code=0 does not override default (0 is falsy)."""
        exc = NexusError("Test", exit_code=0)
        assert exc.exit_code == 1

    def test_exit_code_negative_value_overrides(self):
        """Test negative exit_code overrides (negative is truthy)."""
        exc = NexusError("Test", exit_code=-1)
        assert exc.exit_code == -1
