"""Verifies Cloudflare Turnstile tokens for bot protection on register and
forgot-password.

Defaults to Cloudflare's official "always passes" test secret key, so the
app works end-to-end on a fresh checkout with no Cloudflare account —
swap in real site/secret keys via env vars to get real bot filtering.

Unlike the breach check, this fails closed: if Cloudflare's verify
endpoint is unreachable, the token is treated as unverified rather than
let through, otherwise an outage would silently turn bot protection off.
"""

import os

import httpx

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA")
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data={"secret": TURNSTILE_SECRET_KEY, "response": token, "remoteip": remote_ip},
                timeout=5,
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return False

    return bool(response.json().get("success"))
