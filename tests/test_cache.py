from nexus.utils.cache import CacheManager


def test_cache_manager(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = CacheManager(cache_dir)

    # Test set and get
    cache.set("test_key", {"a": 1})
    assert cache.get("test_key") == {"a": 1}

    # Test expiry
    cache.set("expired_key", {"b": 2})
    # Manually check expiry with a very short time if possible,
    # but here we just test that it returns None if we simulate expiry
    assert cache.get("expired_key", expiry_seconds=-1) is None

    # Test non-existent key
    assert cache.get("missing_key") is None
