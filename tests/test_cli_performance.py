#!/usr/bin/env python3
"""
Test CLI performance with the optimization
"""

import subprocess
import sys
import time

sys.path.insert(0, "/home/dezignerdrugz/nexus-ai")


def test_cli_performance():
    """Test actual CLI performance"""

    print("💻 Testing Actual CLI Performance")
    print("=" * 50)

    # Test commands
    test_commands = [
        {
            "cmd": ["python3", "-m", "nexus.cli.main", "What is 2 + 2?"],
            "desc": "Basic completion (uses fast path)",
        },
        {
            "cmd": [
                "python3",
                "-m",
                "nexus.cli.main",
                "-m",
                "phi4:14b",
                "What is 2 + 2?",
            ],
            "desc": "Ollama specific model",
        },
        {
            "cmd": [
                "python3",
                "-m",
                "nexus.cli.main",
                "-m",
                "gpt-3.5-turbo",
                "What is 2 + 2?",
            ],
            "desc": "OpenAI specific model",
        },
    ]

    for test in test_commands:
        print(f"\n⏱️  Testing: {test['desc']}")
        print("-" * 40)

        try:
            # Run the command 3 times and measure
            times = []
            for i in range(3):
                print(f"   Run {i + 1}/3...", end=" ")

                start_time = time.time()
                result = subprocess.run(
                    test["cmd"], capture_output=True, text=True, timeout=30
                )
                end_time = time.time()

                duration = end_time - start_time
                times.append(duration)

                if result.returncode == 0:
                    print(f"{duration:.3f}s ✅")
                else:
                    print(f"{duration:.3f}s ❌ (exit code: {result.returncode})")
                    print(f"   Error: {result.stderr[:100]}...")

            if times:
                avg_time = sum(times) / len(times)
                print(f"   📊 Average: {avg_time:.3f}s")

        except subprocess.TimeoutExpired:
            print("   ⏰ Timeout (>30s)")
        except Exception as e:
            print(f"   ❌ Exception: {e}")


def test_model_listing_performance():
    """Test model listing commands (should use full path)"""

    print("\n📋 Testing Model Listing Commands")
    print("=" * 50)

    test_commands = [
        {
            "cmd": ["python3", "-m", "nexus.cli.main", "models"],
            "desc": "List all models (uses full path)",
        },
        {
            "cmd": ["python3", "-m", "nexus.cli.main", "-d", "--fuzzy", "phi"],
            "desc": "Fuzzy search (uses full path)",
        },
    ]

    for test in test_commands:
        print(f"\n⏱️  Testing: {test['desc']}")
        print("-" * 40)

        try:
            start_time = time.time()
            result = subprocess.run(
                test["cmd"], capture_output=True, text=True, timeout=30
            )
            end_time = time.time()

            duration = end_time - start_time

            if result.returncode == 0:
                print(f"   Duration: {duration:.3f}s ✅")
                print(f"   Output preview: {result.stdout[:100]}...")
            else:
                print(
                    f"   Duration: {duration:.3f}s ❌ (exit code: {result.returncode})"
                )
                print(f"   Error: {result.stderr[:100]}...")

        except subprocess.TimeoutExpired:
            print("   ⏰ Timeout (>30s)")
        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    test_cli_performance()
    test_model_listing_performance()
