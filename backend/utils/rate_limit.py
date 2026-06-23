"""In-memory rate limiting for the AI auto-fill endpoint.

Every call to /snippets/analyze costs real OpenAI credit, so this adds two
guards on top of the OpenAI dashboard's own monthly budget cap:

1. A per-user burst limit, so one account can't loop the endpoint.
2. A global daily cap, so cost can't scale with how many accounts someone
   registers (registration is open with no verification) — closing the
   "just make another account" bypass of #1.

State lives in process memory (no Redis): fine for a single Render instance,
but it resets on every restart/redeploy/idle-spindown. That's an accepted
tradeoff for a portfolio-scale app, not an oversight.

No locks: FastAPI's async event loop runs one coroutine at a time between
await points, and nothing here awaits mid-mutation, so plain dict/list
mutations are safe without extra synchronization.
"""

import os
from datetime import datetime, timezone

from fastapi import HTTPException

PER_USER_LIMIT = int(os.getenv("ANALYZE_PER_USER_LIMIT", "5"))
PER_USER_WINDOW_SECONDS = int(os.getenv("ANALYZE_PER_USER_WINDOW_SECONDS", "60"))
GLOBAL_DAILY_LIMIT = int(os.getenv("ANALYZE_GLOBAL_DAILY_LIMIT", "200"))

_user_calls: dict[str, list[float]] = {}   # user_id -> recent call timestamps (sliding window)
_global_day: str | None = None             # UTC date string, e.g. "2026-06-23"
_global_count = 0


def enforce_analyze_rate_limit(user_id: str) -> None:
    """Raise 429/503 if the user's burst limit or the global daily cap is hit.

    Call this in the /analyze route, after auth, before the OpenAI call.
    Global is checked first: it's cheaper, and a day that's already over
    budget should fail fast for everyone regardless of their own usage.
    """
    _enforce_global_daily_cap()
    _enforce_per_user_burst_limit(user_id)


def _enforce_per_user_burst_limit(user_id: str) -> None:
    window_start = datetime.now(timezone.utc).timestamp() - PER_USER_WINDOW_SECONDS
    calls = [t for t in _user_calls.get(user_id, []) if t > window_start]
    if len(calls) >= PER_USER_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests — please slow down.")
    calls.append(datetime.now(timezone.utc).timestamp())
    _user_calls[user_id] = calls


def _enforce_global_daily_cap() -> None:
    global _global_day, _global_count
    today = datetime.now(timezone.utc).date().isoformat()
    if _global_day != today:
        _global_day, _global_count = today, 0
    if _global_count >= GLOBAL_DAILY_LIMIT:
        raise HTTPException(
            status_code=503,
            detail="AI auto-fill has hit its daily usage limit. Try again tomorrow.",
        )
    _global_count += 1


def _reset_state() -> None:
    """Clear all counters. Used by tests to isolate runs from each other."""
    global _global_day, _global_count
    _user_calls.clear()
    _global_day, _global_count = None, 0
