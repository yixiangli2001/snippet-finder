import hashlib

import httpx
import pytest

import utils.breach_check as breach_check
from utils.breach_check import is_password_breached


def sha1_prefix_and_suffix(password: str) -> tuple[str, str]:
    """Mirror the k-anonymity split the implementation must perform:
    SHA-1 the password, send only the first 5 hex chars to HIBP."""
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    return digest[:5], digest[5:]


async def test_returns_true_when_hibp_reports_a_match(monkeypatch):
    password = "password123"
    _, suffix = sha1_prefix_and_suffix(password)

    class FakeResponse:
        status_code = 200
        text = f"{suffix}:37810\nAAAA0000000000000000000000000000000:1"

        def raise_for_status(self):
            pass

    async def fake_get(self, url, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await is_password_breached(password) is True


async def test_returns_false_when_hibp_reports_no_match(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = "AAAA0000000000000000000000000000000:1"

        def raise_for_status(self):
            pass

    async def fake_get(self, url, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await is_password_breached("some-unbreached-password") is False


async def test_fails_open_when_hibp_is_unreachable(monkeypatch):
    """A third-party outage must not block registration or password resets."""
    async def fake_get(self, url, timeout=None):
        raise httpx.RequestError("connection failed")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    assert await is_password_breached("anypassword") is False
