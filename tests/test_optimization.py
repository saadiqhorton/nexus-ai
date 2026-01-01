#!/usr/bin/env python3
"""
Test script to verify Ollama performance optimization.

To run these tests, set NEXUS_OLLAMA_URL to point to your Ollama server:
    NEXUS_OLLAMA_URL=http://localhost:11434 pytest tests/test_optimization.py -v
"""

import time

import pytest
from conftest import OLLAMA_AVAILABLE, OLLAMA_CONFIGURED, OLLAMA_URL

from nexus.cli.utils import init_components, init_components_fast


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(not OLLAMA_CONFIGURED, reason="NEXUS_OLLAMA_URL not set")
@pytest.mark.skipif(
    OLLAMA_CONFIGURED and not OLLAMA_AVAILABLE,
    reason=f"Ollama not responding at {OLLAMA_URL}",
)
@pytest.mark.asyncio
async def test_performance():
    """Test the performance improvement from the optimization"""
    print("🧪 Testing Ollama Performance Optimization")
    print("=" * 50)

    # Test 1: Regular initialization (with full model listing)
    print("\n📊 Test 1: Regular initialization (list_all_models)")
    start_time = time.time()
    cfg1, prov1, comp1 = init_components()
    models1 = await prov1.list_all_models(use_cache=False)
    regular_time = time.time() - start_time

    print(f"   Time: {regular_time:.3f}s")
    print("   Models found:")
    for provider, model_list in models1.items():
        print(f"     {provider}: {len(model_list)} models")

    # Test 2: Fast initialization (optimized)
    print("\n⚡ Test 2: Fast initialization (list_all_models_fast)")
    start_time = time.time()
    cfg2, prov2, comp2 = init_components_fast()
    models2 = await prov2.list_all_models_fast(use_cache=False)
    fast_time = time.time() - start_time

    print(f"   Time: {fast_time:.3f}s")
    print("   Models found:")
    for provider, model_list in models2.items():
        print(f"     {provider}: {len(model_list)} models")

    # Test 3: Ollama-specific performance
    print("\n🦙 Test 3: Ollama provider performance")

    # Test direct Ollama provider
    ollama_config = cfg2.get_provider_config("ollama")
    from nexus.providers.ollama_provider import OllamaProvider

    ollama_provider = OllamaProvider(ollama_config)

    start_time = time.time()
    ollama_models = await ollama_provider.list_models()
    ollama_time = time.time() - start_time

    print(f"   Ollama direct: {ollama_time:.3f}s")
    print(f"   Ollama models: {[m.id for m in ollama_models[:5]]}...")

    # Results
    print("\n📈 Results")
    print("=" * 50)
    print(f"Regular initialization: {regular_time:.3f}s")
    print(f"Fast initialization: {fast_time:.3f}s")
    print(f"Speed improvement: {regular_time / fast_time:.1f}x faster")
    print(f"Time saved per CLI call: {regular_time - fast_time:.3f}s")

    if "ollama" in models2 and len(models2["ollama"]) > 0:
        print(f"✅ Ollama integration working: {len(models2['ollama'])} models found")
    else:
        print("❌ Ollama integration issue")

    print("\n🎯 Expected impact:")
    print("- Direct completions (nexus 'prompt'): ~1.0s faster")
    print("- Model selection commands: No change (still need full listing)")
    print("- Chat REPL: No change (may need interactive selection)")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_performance())
