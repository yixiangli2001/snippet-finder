import httpx

import utils.turnstile as turnstile
from utils.turnstile import verify_turnstile_token


class FakeResponse:
    def __init__(self, success: bool):
        self._success = success

    def raise_for_status(self):
        pass

    def json(self):
        return {"success": self._success}


async def test_returns_true_when_cloudflare_reports_success(monkeypatch):
    async def fake_post(self, url, data=None, timeout=None):
        return FakeResponse(success=True)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    assert await verify_turnstile_token("good-token", "1.2.3.4") is True


async def test_returns_false_when_cloudflare_reports_failure(monkeypatch):
    async def fake_post(self, url, data=None, timeout=None):
        return FakeResponse(success=False)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    assert await verify_turnstile_token("bad-token", "1.2.3.4") is False


async def test_fails_closed_when_cloudflare_is_unreachable(monkeypatch):
    """Unlike the breach check, a CAPTCHA must fail closed — if we can't
    verify the token, treat the request as unverified rather than letting
    it through, otherwise bot protection silently disables itself."""
    async def fake_post(self, url, data=None, timeout=None):
        raise httpx.RequestError("connection failed")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    assert await verify_turnstile_token("any-token", "1.2.3.4") is False


async def test_sends_token_and_remote_ip_to_cloudflare(monkeypatch):
    captured = {}

    async def fake_post(self, url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return FakeResponse(success=True)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    await verify_turnstile_token("the-token", "9.8.7.6")

    assert captured["data"]["response"] == "the-token"
    assert captured["data"]["remoteip"] == "9.8.7.6"
    assert captured["data"]["secret"] == turnstile.TURNSTILE_SECRET_KEY
