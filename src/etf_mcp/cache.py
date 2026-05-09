from __future__ import annotations

import datetime
import functools
import hashlib
import json
import sqlite3
import time
from typing import Any, Callable

from etf_mcp.config import config

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        config.cache_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(config.cache_path), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at REAL NOT NULL)"
        )
        _conn.commit()
    return _conn


def _make_key(fn_name: str, args: tuple, kwargs: dict) -> str:
    payload = json.dumps(
        {"fn": fn_name, "args": list(args), "kwargs": dict(sorted(kwargs.items()))},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _ttl(ttl_key: str) -> int:
    return {
        "quote": config.ttl_quote,
        "profile": config.ttl_profile,
        "history": config.ttl_history,
    }[ttl_key]


class _Encoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)


def cached(ttl_key: str) -> Callable:
    """SQLite TTL cache for source functions returning JSON-serialisable dicts."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _make_key(fn.__name__, args, kwargs)
            now = time.time()
            conn = _get_conn()

            row = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if row and row[1] > now:
                return json.loads(row[0])

            result = await fn(*args, **kwargs)
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                (key, json.dumps(result, cls=_Encoder), now + _ttl(ttl_key)),
            )
            conn.commit()
            return result

        return wrapper

    return decorator
