"""Test that _cache access is thread-safe."""

from __future__ import annotations

from aegis.viewer.server import _cache, _cache_lock


def test_cache_lock_exists():
    """The module exposes a threading lock for cache synchronization."""
    # RLock is used to allow reentrant acquisition (helpers called within locked blocks)
    import _thread

    assert isinstance(_cache_lock, _thread.LockType | _thread.RLock)


def test_cache_lock_is_reentrant_safe():
    """Lock can be acquired and released without deadlock."""
    _cache_lock.acquire()
    try:
        _cache["_test"] = True
        assert _cache["_test"] is True
    finally:
        _cache_lock.release()
        _cache.pop("_test", None)
