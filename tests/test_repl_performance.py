#!/usr/bin/env python3
"""
Test REPL vs CLI performance comparison
"""

import subprocess
import sys
import time

sys.path.insert(0, "/home/dezignerdrugz/nexus-ai")


def test_repl_vs_cli():
    print("🔄 Testing REPL vs CLI Performance")
    print("=" * 50)

    # Test command that should trigger the REPL
    repl_cmd = [
        "python3",
        "-c",
        """
import sys
sys.path.insert(0, '/home/dezignerdrugz/nexus-ai')
import asyncio
from nexus.cli.repl import repl_main

async def test():
    await repl_main(
        model="phi4:14b",
        provider="ollama",
        session_name=None,
        temperature=None,
        max_tokens=None,
        system_prompt=None
    )

asyncio.run(test())
""",
    ]

    # Test direct CLI command for comparison
    cli_cmd = [
        "python3",
        "-m",
        "nexus.cli.main",
        "-m",
        "phi4:14b",
        "-p",
        "ollama",
        "What is 2 + 2?",
    ]

    print("⏱️  Testing REPL initialization...")
    start_time = time.time()
    try:
        result = subprocess.run(repl_cmd, capture_output=True, text=True, timeout=10)
        repl_time = time.time() - start_time
        print(f"   REPL init time: {repl_time:.3f}s")
        if result.returncode != 0:
            print(f"   REPL error: {result.stderr[:200]}...")
    except subprocess.TimeoutExpired:
        repl_time = 10.0
        print("   REPL timeout after 10s")

    print("\n⏱️  Testing CLI initialization...")
    start_time = time.time()
    try:
        result = subprocess.run(cli_cmd, capture_output=True, text=True, timeout=10)
        cli_time = time.time() - start_time
        print(f"   CLI time: {cli_time:.3f}s")
        if result.returncode != 0:
            print(f"   CLI error: {result.stderr[:200]}...")
    except subprocess.TimeoutExpired:
        cli_time = 10.0
        print("   CLI timeout after 10s")

    print("\n📊 Performance Comparison:")
    print(f"   REPL initialization: {repl_time:.3f}s")
    print(f"   CLI initialization: {cli_time:.3f}s")
    if repl_time < cli_time:
        improvement = (cli_time - repl_time) / cli_time * 100
        print(f"   REPL is {improvement:.1f}% faster after optimization")
    else:
        improvement = (repl_time - cli_time) / repl_time * 100
        print(f"   CLI is {improvement:.1f}% faster than REPL")


if __name__ == "__main__":
    test_repl_vs_cli()
