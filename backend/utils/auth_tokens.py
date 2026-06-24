"""Single-use tokens for email verification and password reset.

Stored in Mongo rather than encoded as stateless JWTs so they can be
invalidated after one use — important for password reset, where a stale
link must stop working the instant it's used.
"""

import secrets
from datetime import datetime, timedelta, timezone

from database import auth_tokens_collection

VERIFY_EMAIL_TTL = timedelta(hours=24)
RESET_PASSWORD_TTL = timedelta(hours=1)


async def create_auth_token(user_id: str, purpose: str, ttl: timedelta) -> str:
    """Create and store a new token, returning the raw value to send by email."""
    token = secrets.token_urlsafe(32)
    await auth_tokens_collection.insert_one({
        "token": token,
        "user_id": user_id,
        "purpose": purpose,
        "expires_at": datetime.now(timezone.utc) + ttl,
    })
    return token


async def consume_auth_token(token: str, purpose: str) -> str | None:
    """Return the user_id for a valid token of the given purpose, deleting it.

    Deleting unconditionally on match (before checking expiry) means an
    expired token is consumed too, so it can never be retried.
    """
    record = await auth_tokens_collection.find_one_and_delete({"token": token, "purpose": purpose})
    if not record:
        return None
    if record["expires_at"] < datetime.now(timezone.utc):
        return None
    return record["user_id"]
