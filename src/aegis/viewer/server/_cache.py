"""Shared module-level cache and session-scoped helpers for the viewer server."""

from __future__ import annotations

import threading
import uuid

from flask import session

# Module-level cache shared across route modules.
_cache: dict = {}
_cache_lock = threading.RLock()


def _sid() -> str:
    """Return the current request's session ID, creating one if absent."""
    sid = session.get("session_id")
    if sid is None:
        sid = uuid.uuid4().hex
        session["session_id"] = sid
        session.permanent = True
    return sid


def _skey(key: str) -> str:
    """Build a session-scoped cache key: ``'{sid}:{key}'``."""
    return f"{_sid()}:{key}"


def scoped_cache_get(cache: dict, key: str, default=None):
    """Read a session-scoped value from the cache."""
    return cache.get(_skey(key), default)


def scoped_cache_set(cache: dict, key: str, value) -> None:
    """Write a session-scoped value into the cache."""
    cache[_skey(key)] = value


def scoped_cache_pop(cache: dict, key: str, default=None):
    """Remove and return a session-scoped value from the cache."""
    return cache.pop(_skey(key), default)


def scoped_cache_clear_session(cache: dict) -> None:
    """Remove all session-scoped entries for the current session."""
    prefix = f"{_sid()}:"
    keys_to_remove = [k for k in cache if isinstance(k, str) and k.startswith(prefix)]
    for k in keys_to_remove:
        cache.pop(k, None)
