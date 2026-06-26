"""Checks a password against HaveIBeenPwned's breached-password list.

Uses the k-anonymity range API: only the first 5 characters of the
password's SHA-1 hash are sent, so the real password (and its full hash)
never leaves the server. If HIBP is slow or unreachable, the check fails
open — a third-party outage must not block registration or password resets.
"""

import hashlib

import httpx

HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/{prefix}"


async def is_password_breached(password: str) -> bool:
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(HIBP_RANGE_URL.format(prefix=prefix), timeout=5)
            response.raise_for_status()
    except httpx.HTTPError:
        return False

    returned_suffixes = (line.split(":")[0] for line in response.text.splitlines())
    return suffix in returned_suffixes
