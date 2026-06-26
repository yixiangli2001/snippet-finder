from datetime import timedelta

import pytest

import utils.auth_rate_limit as auth_rate_limit
from utils.auth_rate_limit import (
    enforce_forgot_password_rate_limit,
    enforce_login_rate_limit,
    enforce_register_rate_limit,
)

# Counters are reset between tests by the autouse fixture in tests/conftest.py.


def test_login_limit_blocks_after_n_attempts(monkeypatch):
    monkeypatch.setattr(auth_rate_limit, "LOGIN_LIMIT", 2)

    enforce_login_rate_limit("1.2.3.4:alice@example.com")
    enforce_login_rate_limit("1.2.3.4:alice@example.com")
    with pytest.raises(Exception) as exc_info:
        enforce_login_rate_limit("1.2.3.4:alice@example.com")

    assert exc_info.value.status_code == 429


def test_login_limit_is_independent_per_key(monkeypatch):
    monkeypatch.setattr(auth_rate_limit, "LOGIN_LIMIT", 1)

    enforce_login_rate_limit("1.2.3.4:alice@example.com")
    # A different IP+email combination has its own untouched allowance.
    enforce_login_rate_limit("5.6.7.8:alice@example.com")
    enforce_login_rate_limit("1.2.3.4:bob@example.com")


def test_login_limit_resets_after_window(monkeypatch):
    monkeypatch.setattr(auth_rate_limit, "LOGIN_LIMIT", 1)
    monkeypatch.setattr(auth_rate_limit, "LOGIN_WINDOW_SECONDS", 60)

    enforce_login_rate_limit("1.2.3.4:alice@example.com")

    real_datetime = auth_rate_limit.datetime

    class FrozenDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime.now(tz) + timedelta(seconds=61)

    monkeypatch.setattr(auth_rate_limit, "datetime", FrozenDatetime)

    enforce_login_rate_limit("1.2.3.4:alice@example.com")


def test_register_limit_blocks_after_n_attempts(monkeypatch):
    monkeypatch.setattr(auth_rate_limit, "REGISTER_LIMIT", 2)

    enforce_register_rate_limit("1.2.3.4")
    enforce_register_rate_limit("1.2.3.4")
    with pytest.raises(Exception) as exc_info:
        enforce_register_rate_limit("1.2.3.4")

    assert exc_info.value.status_code == 429


def test_forgot_password_limit_blocks_after_n_attempts(monkeypatch):
    monkeypatch.setattr(auth_rate_limit, "FORGOT_PASSWORD_LIMIT", 2)

    enforce_forgot_password_rate_limit("1.2.3.4:alice@example.com")
    enforce_forgot_password_rate_limit("1.2.3.4:alice@example.com")
    with pytest.raises(Exception) as exc_info:
        enforce_forgot_password_rate_limit("1.2.3.4:alice@example.com")

    assert exc_info.value.status_code == 429


def test_each_endpoint_has_an_independent_limit(monkeypatch):
    """Hammering /login shouldn't use up the /register allowance — they're
    different abuse surfaces and must not share state."""
    monkeypatch.setattr(auth_rate_limit, "LOGIN_LIMIT", 1)

    enforce_login_rate_limit("1.2.3.4:alice@example.com")
    enforce_register_rate_limit("1.2.3.4")
    enforce_forgot_password_rate_limit("1.2.3.4:alice@example.com")
