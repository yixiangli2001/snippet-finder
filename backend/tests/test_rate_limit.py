from datetime import datetime, timedelta, timezone

import pytest

import utils.rate_limit as rate_limit
from utils.rate_limit import enforce_analyze_rate_limit


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    """Each test gets a clean slate — module-level counters would otherwise
    bleed between tests since they're shared global state."""
    rate_limit._reset_state()
    yield
    rate_limit._reset_state()


def test_per_user_limit_blocks_after_n_calls(monkeypatch):
    monkeypatch.setattr(rate_limit, "PER_USER_LIMIT", 2)

    enforce_analyze_rate_limit("user-1")
    enforce_analyze_rate_limit("user-1")
    with pytest.raises(Exception) as exc_info:
        enforce_analyze_rate_limit("user-1")

    assert exc_info.value.status_code == 429


def test_per_user_limit_is_independent_per_user(monkeypatch):
    monkeypatch.setattr(rate_limit, "PER_USER_LIMIT", 1)

    enforce_analyze_rate_limit("user-1")
    # A different user has their own untouched allowance.
    enforce_analyze_rate_limit("user-2")


def test_per_user_limit_resets_after_window(monkeypatch):
    monkeypatch.setattr(rate_limit, "PER_USER_LIMIT", 1)
    monkeypatch.setattr(rate_limit, "PER_USER_WINDOW_SECONDS", 60)

    enforce_analyze_rate_limit("user-1")

    real_datetime = rate_limit.datetime

    class FrozenDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.now(tz) + timedelta(seconds=61)

    monkeypatch.setattr(rate_limit, "datetime", FrozenDatetime)

    # The earlier call has fallen out of the window, so this should succeed.
    enforce_analyze_rate_limit("user-1")


def test_global_daily_cap_blocks_across_different_users(monkeypatch):
    monkeypatch.setattr(rate_limit, "GLOBAL_DAILY_LIMIT", 2)
    monkeypatch.setattr(rate_limit, "PER_USER_LIMIT", 100)

    enforce_analyze_rate_limit("user-1")
    enforce_analyze_rate_limit("user-2")
    with pytest.raises(Exception) as exc_info:
        # A third, never-seen-before user — proves the cap is global, not per-user.
        enforce_analyze_rate_limit("user-3")

    assert exc_info.value.status_code == 503


def test_global_cap_resets_on_new_day(monkeypatch):
    monkeypatch.setattr(rate_limit, "GLOBAL_DAILY_LIMIT", 1)
    monkeypatch.setattr(rate_limit, "PER_USER_LIMIT", 100)

    enforce_analyze_rate_limit("user-1")

    real_datetime = rate_limit.datetime

    class NextDayDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.now(tz) + timedelta(days=1)

    monkeypatch.setattr(rate_limit, "datetime", NextDayDatetime)

    # New UTC day, counter should have reset.
    enforce_analyze_rate_limit("user-2")
