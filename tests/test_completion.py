"""Tests for shell completion script generation."""

from nexus.cli.completion import get_bash_completion, get_zsh_completion


class TestBashCompletion:
    """Tests for Bash completion script generation."""

    def test_bash_completion_generated(self):
        """Test that Bash completion script is generated."""
        script = get_bash_completion()
        assert "_nexus_completion" in script
        assert "complete -F" in script
        assert "nexus" in script

    def test_bash_completion_has_commands(self):
        """Test that Bash completion includes main commands."""
        script = get_bash_completion()
        assert "chat" in script
        assert "models" in script
        assert "sessions" in script
        assert "config" in script

    def test_bash_completion_has_session_commands(self):
        """Test that Bash completion includes session subcommands."""
        script = get_bash_completion()
        assert "list" in script
        assert "show" in script
        assert "export" in script
        assert "delete" in script
        assert "search" in script
        assert "rename" in script

    def test_bash_completion_has_providers(self):
        """Test that Bash completion includes provider names."""
        script = get_bash_completion()
        assert "openai" in script
        assert "anthropic" in script
        assert "ollama" in script
        assert "openrouter" in script

    def test_bash_completion_has_options(self):
        """Test that Bash completion includes common options."""
        script = get_bash_completion()
        assert "--model" in script or "-m" in script
        assert "--provider" in script or "-p" in script

    def test_bash_completion_has_session_option(self):
        """Test that Bash completion includes --session option."""
        script = get_bash_completion()
        assert "--session" in script

    def test_bash_completion_has_file_option(self):
        """Test that Bash completion includes -f/--file option."""
        script = get_bash_completion()
        assert "-f" in script or "--file" in script

    def test_bash_completion_is_valid_bash(self):
        """Test that the generated script has valid Bash syntax markers."""
        script = get_bash_completion()
        # Should have function definition
        assert "_nexus_completion()" in script or "_nexus_completion ()" in script
        # Should have complete command
        assert "complete" in script

    def test_bash_completion_sessions_dir_handling(self):
        """Test that Bash completion handles sessions directory."""
        script = get_bash_completion()
        assert "sessions_dir" in script or ".nexus/sessions" in script


class TestZshCompletion:
    """Tests for Zsh completion script generation."""

    def test_zsh_completion_generated(self):
        """Test that Zsh completion script is generated."""
        script = get_zsh_completion()
        assert "_nexus" in script
        assert "compdef" in script or "_arguments" in script

    def test_zsh_completion_has_options(self):
        """Test that Zsh completion includes common options."""
        script = get_zsh_completion()
        assert "--model" in script
        assert "--provider" in script
        assert "--session" in script

    def test_zsh_completion_has_commands(self):
        """Test that Zsh completion includes main commands."""
        script = get_zsh_completion()
        assert "chat" in script
        assert "models" in script
        assert "config" in script
        assert "sessions" in script

    def test_zsh_completion_has_providers(self):
        """Test that Zsh completion includes provider options."""
        script = get_zsh_completion()
        assert "openai" in script
        assert "anthropic" in script
        assert "ollama" in script
        assert "openrouter" in script

    def test_zsh_completion_has_session_subcommands(self):
        """Test that Zsh completion includes session subcommands."""
        script = get_zsh_completion()
        assert "list" in script
        assert "show" in script
        assert "export" in script
        assert "delete" in script
        assert "search" in script
        assert "rename" in script

    def test_zsh_completion_has_session_completion_function(self):
        """Test that Zsh has a function for completing session names."""
        script = get_zsh_completion()
        assert "_nexus_sessions" in script

    def test_zsh_completion_sessions_dir_handling(self):
        """Test that Zsh completion handles sessions directory."""
        script = get_zsh_completion()
        assert "sessions_dir" in script or ".nexus/sessions" in script

    def test_zsh_completion_is_valid_zsh(self):
        """Test that the generated script has valid Zsh syntax markers."""
        script = get_zsh_completion()
        # Should have compdef directive
        assert "#compdef" in script
        # Should have function definition
        assert "_nexus()" in script or "_nexus ()" in script

    def test_zsh_completion_has_temperature_option(self):
        """Test that Zsh completion includes temperature option."""
        script = get_zsh_completion()
        assert "--temperature" in script or "-t" in script

    def test_zsh_completion_has_system_option(self):
        """Test that Zsh completion includes system prompt option."""
        script = get_zsh_completion()
        assert "--system" in script or "-s" in script

    def test_zsh_completion_has_file_completion(self):
        """Test that Zsh completion includes file path completion."""
        script = get_zsh_completion()
        assert "_files" in script or "--file" in script


class TestCompletionScriptFormat:
    """Tests for completion script format and structure."""

    def test_bash_script_is_string(self):
        """Test that Bash completion returns a string."""
        script = get_bash_completion()
        assert isinstance(script, str)
        assert len(script) > 0

    def test_zsh_script_is_string(self):
        """Test that Zsh completion returns a string."""
        script = get_zsh_completion()
        assert isinstance(script, str)
        assert len(script) > 0

    def test_bash_script_is_stripped(self):
        """Test that Bash completion script is stripped of extra whitespace."""
        script = get_bash_completion()
        assert not script.startswith("\n")
        assert not script.endswith("\n\n")

    def test_zsh_script_is_stripped(self):
        """Test that Zsh completion script is stripped of extra whitespace."""
        script = get_zsh_completion()
        assert not script.startswith("\n")
        assert not script.endswith("\n\n")

    def test_scripts_are_different(self):
        """Test that Bash and Zsh scripts are different."""
        bash_script = get_bash_completion()
        zsh_script = get_zsh_completion()
        assert bash_script != zsh_script

    def test_bash_has_case_statement(self):
        """Test that Bash completion uses case statement for parsing."""
        script = get_bash_completion()
        assert "case" in script
        assert "esac" in script

    def test_zsh_has_arguments_function(self):
        """Test that Zsh completion uses _arguments."""
        script = get_zsh_completion()
        assert "_arguments" in script
