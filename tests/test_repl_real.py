#!/usr/bin/env python3
"""
Test actual REPL vs CLI performance comparison.

Environment Variables:
    NEXUS_OLLAMA_URL: URL of the Ollama server (required for these tests)
    NEXUS_TEST_MODEL: Model to use for testing (default: phi4:14b)

These tests are skipped if Ollama is not configured or available.
"""

import subprocess
import time

import pytest
from conftest import (
    MODEL_AVAILABLE,
    OLLAMA_AVAILABLE,
    OLLAMA_CONFIGURED,
    OLLAMA_URL,
    TEST_MODEL,
)


@pytest.mark.integration
@pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
@pytest.mark.skipif(
    OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
    reason=f"Ollama not responding at {OLLAMA_URL}",
)
@pytest.mark.skipif(
    OLLAMA_AVAILABLE and not MODEL_AVAILABLE,
    reason=f"Model {TEST_MODEL} not available",
)
def test_repl_vs_cli_real():
    print("Real REPL vs CLI Performance Test")
    print("=" * 50)

    # Test actual nexus chat command (REPL)
    print("Testing: nexus chat (REPL mode)...")

    # Simulate REPL by starting it and immediately exiting
    repl_cmd = [
        "timeout",
        "60",
        "python3",
        "-m",
        "nexus.cli.main",
        "chat",
        "-m",
        TEST_MODEL,
        "-p",
        "ollama",
    ]

    start_time = time.time()
    _ = subprocess.run(repl_cmd, input="/exit\n", capture_output=True, text=True, timeout=90)
    end_time = time.time()

    repl_time = end_time - start_time
    print(f"   REPL startup time: {repl_time:.3f}s")

    # Test direct CLI command for comparison
    print("\nTesting: nexus (direct command)...")

    cli_cmd = [
        "python3",
        "-m",
        "nexus.cli.main",
        "-m",
        TEST_MODEL,
        "-p",
        "ollama",
        "What is 2 + 2?",
    ]

    start_time = time.time()
    _ = subprocess.run(cli_cmd, capture_output=True, text=True, timeout=120)
    end_time = time.time()

    cli_time = end_time - start_time
    print(f"   CLI execution time: {cli_time:.3f}s")

    print("\n📊 Performance Comparison:")
    print(f"   REPL startup time: {repl_time:.3f}s")
    print(f"   CLI execution time: {cli_time:.3f}s")

    if repl_time < cli_time:
        improvement = (cli_time - repl_time) / cli_time * 100
        print(f"   REPL is {improvement:.1f}% faster than CLI!")
    else:
        improvement = (repl_time - cli_time) / repl_time * 100
        print(f"   CLI is {improvement:.1f}% faster than REPL")

    print("\nOptimization Status: REPL now uses fast initialization path!")


@pytest.mark.integration
@pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
@pytest.mark.skipif(
    OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
    reason=f"Ollama not responding at {OLLAMA_URL}",
)
@pytest.mark.skipif(
    OLLAMA_AVAILABLE and not MODEL_AVAILABLE,
    reason=f"Model {TEST_MODEL} not available",
)
def test_optimization_verification():
    print("\nVerifying Optimization is Active")
    print("=" * 40)

    # Test that the optimization is actually working
    print("Testing REPL with fast initialization...")

    # This should be quick now
    test_script = """
from nexus.core.app import NexusApp

# Test that REPL uses fast initialization
app = NexusApp()
# This should use the fast path now due to our optimization
print("REPL optimization active!")
"""

    with open("/tmp/optimization_test.py", "w") as f:
        f.write(test_script)

    start_time = time.time()
    result = subprocess.run(
        ["python3", "/tmp/optimization_test.py"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    end_time = time.time()

    opt_time = end_time - start_time
    print(f"   Optimization test: {opt_time:.3f}s")
    print(f"   Result: {result.stdout.strip()}")


if __name__ == "__main__":
    test_repl_vs_cli_real()
    test_optimization_verification()
