#!/usr/bin/env python3
"""
Test actual REPL performance with optimization
"""

import subprocess
import sys
import time

sys.path.insert(0, "/home/dezignerdrugz/nexus-ai")


def test_actual_repl():
    print("🧪 Testing Actual REPL Performance")
    print("=" * 50)

    # Create a simple test script that mimics REPL usage
    test_script = """
import sys
sys.path.insert(0, '/home/dezignerdrugz/nexus-ai')
import asyncio

from nexus.core.app import NexusApp

async def test():
    # Test REPL initialization speed
    import time
    start = time.time()

    # Initialize REPL components
    app = NexusApp()

    # This should now use fast initialization
    print("REPL initialized successfully")

    end = time.time()
    print(f"REPL initialization time: {end - start:.3f}s")

asyncio.run(test())
"""

    # Write test script
    with open("/tmp/repl_test.py", "w") as f:
        f.write(test_script)

    print("⏱️  Testing REPL with optimization...")
    start_time = time.time()
    result = subprocess.run(
        ["python3", "/tmp/repl_test.py"], capture_output=True, text=True, timeout=10
    )
    end_time = time.time()

    duration = end_time - start_time
    print(f"   Total execution time: {duration:.3f}s")
    print(f"   Output: {result.stdout.strip()}")

    if result.returncode != 0:
        print(f"   Error: {result.stderr}")

    # Compare with direct CLI
    print("\n⏱️  Testing direct CLI for comparison...")
    start_time = time.time()
    result = subprocess.run(
        ["python3", "-m", "nexus.cli.main", "version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    end_time = time.time()

    cli_duration = end_time - start_time
    print(f"   CLI execution time: {cli_duration:.3f}s")

    print("\n📊 Final Comparison:")
    print(f"   REPL initialization: ~{duration:.3f}s")
    print(f"   CLI execution: ~{cli_duration:.3f}s")
    print("   REPL should now be faster due to optimization!")


if __name__ == "__main__":
    test_actual_repl()
