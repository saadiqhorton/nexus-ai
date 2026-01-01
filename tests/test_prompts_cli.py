import pytest
from click.testing import CliRunner

from nexus.cli.main import cli
from nexus.prompts.manager import PromptManager


@pytest.fixture
def temp_nexus_dir(tmp_path):
    """Setup temp nexus dir"""
    nexus_dir = tmp_path / ".nexus"
    nexus_dir.mkdir()
    prompts_dir = nexus_dir / "prompts"
    prompts_dir.mkdir()

    # Mock ConfigManager to use this path
    with pytest.MonkeyPatch.context() as m:
        m.setenv("HOME", str(tmp_path))
        yield nexus_dir


def test_prompts_crud(temp_nexus_dir):
    runner = CliRunner()

    # 1. List - empty
    result = runner.invoke(cli, ["prompts", "list"])
    assert result.exit_code == 0
    assert "No prompts found" in result.output

    # 2. New (we can't easily interact with click.edit in tests, so we skip 'new' command test
    # and test manager directly for creation, then list/show via CLI)
    pm = PromptManager(temp_nexus_dir / "prompts")
    pm.save_prompt("test_prompt", "This is a test prompt.")

    # 3. List - populated
    result = runner.invoke(cli, ["prompts", "list"])
    assert result.exit_code == 0
    assert "test_prompt" in result.output

    # 4. Show
    result = runner.invoke(cli, ["prompts", "show", "test_prompt"])
    assert result.exit_code == 0
    assert "This is a test prompt" in result.output

    # 5. Delete
    result = runner.invoke(cli, ["prompts", "delete", "test_prompt", "--force"])
    assert result.exit_code == 0
    assert "Deleted prompt 'test_prompt'" in result.output

    result = runner.invoke(cli, ["prompts", "list"])
    assert "No prompts found" in result.output


def test_recursive_file_processing(temp_nexus_dir):
    """Test -f with directory"""
    # Create structure
    # data/
    #   file1.txt
    #   subdir/
    #     file2.txt

    data_dir = temp_nexus_dir.parent / "data"
    data_dir.mkdir()
    (data_dir / "file1.txt").write_text("content1")
    (data_dir / "subdir").mkdir()
    (data_dir / "subdir" / "file2.txt").write_text("content2")

    # We need to mock the actual completion to verify input content
    # We can inspect the prompt passed to completion logic
    # But for CLI integration test, we can just check if it runs without error
    # and maybe verify via mocking `process_files_and_stdin`?
    # Or better, we can invoke `process_files_and_stdin` directly as unit test.

    # Mock stdin.isatty to return True so we skip stdin reading
    import sys

    from nexus.cli.utils import process_files_and_stdin

    with pytest.MonkeyPatch.context() as m:
        m.setattr(sys.stdin, "isatty", lambda: True)
        combined = process_files_and_stdin([str(data_dir)], "prompt")

    assert "file1.txt" in combined
    assert "content1" in combined
    assert "file2.txt" in combined
    assert "content2" in combined
    assert "prompt" in combined


def test_use_flag_resolution(temp_nexus_dir):
    """Test resolution of -u flag"""
    pm = PromptManager(temp_nexus_dir / "prompts")
    pm.save_prompt("summarize", "You are a summarizer.")

    from nexus.cli.main import resolve_system_prompt

    # Test valid lookup
    prompt = resolve_system_prompt(None, "summarize", temp_nexus_dir)
    assert prompt == "You are a summarizer."

    # Test invalid lookup
    prompt = resolve_system_prompt(None, "missing", temp_nexus_dir)
    assert prompt is None

    # Test priority (system arg overrides use)
    prompt = resolve_system_prompt("Manual system", "summarize", temp_nexus_dir)
    assert prompt == "Manual system"
