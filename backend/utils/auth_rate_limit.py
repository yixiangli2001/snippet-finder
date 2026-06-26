"""In-memory rate limiting for the auth endpoints most attractive to abuse:
login (credential stuffing), register (mass account creation), and
forgot-password (email-bombing a victim).

State lives in process memory (no Redis), same accepted tradeoff as
utils/rate_limit.py: fine for a single Render instance, resets on
restart/redeploy. Each endpoint gets its own counters so hammering one
can't burn through the allowance of another.
"""

import os
from datetime import datetime, timezone

from fastapi import HTTPException

LOGIN_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "60"))

REGISTER_LIMIT = int(os.getenv("REGISTER_RATE_LIMIT", "3"))
REGISTER_WINDOW_SECONDS = int(os.getenv("REGISTER_RATE_WINDOW_SECONDS", "3600"))

FORGOT_PASSWORD_LIMIT = int(os.getenv("FORGOT_PASSWORD_RATE_LIMIT", "3"))
FORGOT_PASSWORD_WINDOW_SECONDS = int(os.getenv("FORGOT_PASSWORD_RATE_WINDOW_SECONDS", "3600"))

_login_calls: dict[str, list[float]] = {}
_register_calls: dict[str, list[float]] = {}
_forgot_password_calls: dict[str, list[float]] = {}


def _enforce_sliding_window(key: str, limit: int, window_seconds: int, calls_by_key: dict[str, list[float]]) -> None:
    window_start = datetime.now(timezone.utc).timestamp() - window_seconds
    calls = [t for t in calls_by_key.get(key, []) if t > window_start]
    if len(calls) >= limit:
        raise HTTPException(status_code=429, detail="Too many attempts — please slow down.")
    calls.append(datetime.now(timezone.utc).timestamp())
    calls_by_key[key] = calls


def enforce_login_rate_limit(key: str) -> None:
    """key should combine client IP and email, so a brute-force attempt
    against one account doesn't also penalize everyone sharing that IP."""
    _enforce_sliding_window(key, LOGIN_LIMIT, LOGIN_WINDOW_SECONDS, _login_calls)


def enforce_register_rate_limit(key: str) -> None:
    """key is the client IP — limits mass account creation from one source."""
    _enforce_sliding_window(key, REGISTER_LIMIT, REGISTER_WINDOW_SECONDS, _register_calls)


def enforce_forgot_password_rate_limit(key: str) -> None:
    """key should combine client IP and email, so this can't be used to
    flood one victim's inbox with reset emails."""
    _enforce_sliding_window(key, FORGOT_PASSWORD_LIMIT, FORGOT_PASSWORD_WINDOW_SECONDS, _forgot_password_calls)


def _reset_state() -> None:
    """Clear all counters. Used by tests to isolate runs from each other."""
    _login_calls.clear()
    _register_calls.clear()
    _forgot_password_calls.clear()
