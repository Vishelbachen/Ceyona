"""
memory/supabase_client.py

Resilient Supabase client factory.

Root cause: supabase-py uses httpx with HTTP/2. On HF Spaces free tier,
Supabase's load balancer silently closes idle TCP connections after ~5
minutes. The next call on the same client raises ConnectionTerminated
(h2) or RemoteProtocolError. The existing try/except in supabase_store.py
and conversation_history.py catch it and return [] / False — but the
NEXT call on the same dead client fails too, until the Space restarts.

Fix: proactively recreate the client every 4 minutes (below the ~5-min
idle timeout). On any connection error, reconnect immediately and retry
the operation once.

Drop-in usage in bootstrap.py:

    from memory.supabase_client import ResilientSupabase
    supabase = ResilientSupabase(settings.supabase_url,
                                  settings.supabase_service_role_key)

Everywhere else (supabase_store.py, conversation_history.py, etc.) the
type hint says `Client` but ResilientSupabase forwards all attribute
access to the real client, so nothing else needs to change.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from supabase import Client, create_client

logger = logging.getLogger(__name__)

_RECONNECT_PHRASES = (
    "ConnectionTerminated",
    "RemoteProtocolError",
    "ConnectionResetError",
    "BrokenPipeError",
    "EOF occurred",
    "peer closed connection",
    "Server disconnected",
    "ConnectionAbortedError",
)

# Proactively recycle client before Supabase's idle timeout (~5 min).
_MAX_AGE_SECONDS = 240  # 4 minutes


def _is_dead_connection(exc: Exception) -> bool:
    msg = str(exc)
    return any(p in msg for p in _RECONNECT_PHRASES)


class ResilientSupabase:
    """
    Wraps supabase.Client with automatic reconnection.

    All attribute access is forwarded to the inner client, so this is a
    transparent drop-in wherever Client is used.
    """

    def __init__(self, url: str, key: str) -> None:
        self._url = url
        self._key = key
        self._born = time.monotonic()
        self._client: Client = create_client(url, key)
        logger.info("Supabase client initialised")

    # ── Internal ──────────────────────────────────────────────────────────

    def _reconnect(self) -> None:
        logger.info("Supabase: reconnecting")
        self._client = create_client(self._url, self._key)
        self._born = time.monotonic()

    def _ensure_fresh(self) -> None:
        if time.monotonic() - self._born > _MAX_AGE_SECONDS:
            logger.info("Supabase: proactive client recycle (age > %ds)", _MAX_AGE_SECONDS)
            self._reconnect()

    # ── Public query entry points ─────────────────────────────────────────

    def table(self, name: str) -> "_RetryingBuilder":
        self._ensure_fresh()
        return _RetryingBuilder(self, name)

    def rpc(self, fn: str, params: dict | None = None) -> "_RetryingRpc":
        self._ensure_fresh()
        return _RetryingRpc(self, fn, params or {})

    # Forward everything else (auth, storage, postgrest_client, …)
    def __getattr__(self, item: str) -> Any:
        return getattr(self._client, item)


# ── Query builder proxy ───────────────────────────────────────────────────────

class _RetryingBuilder:
    """
    Proxies a PostgREST QueryBuilder and retries execute() once after
    reconnecting on a dead-connection error.

    The builder chain (select / insert / eq / order / limit / …) is
    accumulated as a list of (method, args, kwargs) calls and replayed
    on a fresh builder if the first execute() raises a connection error.
    """

    def __init__(self, owner: ResilientSupabase, table_name: str) -> None:
        self._owner = owner
        self._table_name = table_name
        self._calls: list[tuple[str, tuple, dict]] = []
        self._builder = owner._client.table(table_name)

    def _replay(self) -> Any:
        """Replay recorded chain on a brand-new builder (after reconnect)."""
        b = self._owner._client.table(self._table_name)
        for method, args, kwargs in self._calls:
            b = getattr(b, method)(*args, **kwargs)
        return b

    def __getattr__(self, item: str) -> Any:
        if item.startswith("_"):
            raise AttributeError(item)

        def _method(*args, **kwargs):
            self._calls.append((item, args, kwargs))
            result = getattr(self._builder, item)(*args, **kwargs)
            self._builder = result
            return self  # allow further chaining

        return _method

    def execute(self) -> Any:
        try:
            return self._builder.execute()
        except Exception as exc:
            if not _is_dead_connection(exc):
                raise
            logger.warning(
                "Supabase table '%s': dead connection, reconnecting and retrying",
                self._table_name,
                extra={"error": str(exc)},
            )
            self._owner._reconnect()
            fresh = self._replay()
            return fresh.execute()  # let the second failure propagate normally


# ── RPC proxy ─────────────────────────────────────────────────────────────────

class _RetryingRpc:
    def __init__(self, owner: ResilientSupabase, fn: str, params: dict) -> None:
        self._owner = owner
        self._fn = fn
        self._params = params

    def execute(self) -> Any:
        try:
            return self._owner._client.rpc(self._fn, self._params).execute()
        except Exception as exc:
            if not _is_dead_connection(exc):
                raise
            logger.warning(
                "Supabase rpc '%s': dead connection, reconnecting and retrying",
                self._fn,
                extra={"error": str(exc)},
            )
            self._owner._reconnect()
            return self._owner._client.rpc(self._fn, self._params).execute()