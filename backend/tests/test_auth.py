from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

import routers.auth as auth_router
import utils.auth_rate_limit as auth_rate_limit
import utils.auth_tokens as auth_tokens
import utils.security as security
from main import app
from tests.fakes import FakeCollection
from utils.security import hash_password


async def _not_breached(password: str) -> bool:
    return False


async def _turnstile_passes(token: str, remote_ip: str | None = None) -> bool:
    return True


def use_fake_users(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(auth_tokens, "auth_tokens_collection", FakeCollection())
    # Default to "not breached" / "captcha passed" so tests don't depend on
    # network access; tests exercising these checks override them explicitly.
    monkeypatch.setattr(auth_router, "is_password_breached", _not_breached)
    monkeypatch.setattr(auth_router, "verify_turnstile_token", _turnstile_passes)
    return users


def spy_on_emails(monkeypatch):
    """Replace the email senders with spies so tests can assert on calls
    instead of actually sending (or printing) anything."""
    sent = {"verification": [], "reset": []}
    monkeypatch.setattr(
        auth_router, "send_verification_email",
        lambda to, link: sent["verification"].append({"to": to, "link": link}),
    )
    monkeypatch.setattr(
        auth_router, "send_reset_email",
        lambda to, link: sent["reset"].append({"to": to, "link": link}),
    )
    return sent


def register(client, email="alice@example.com", username="alice", password="securepass"):
    return client.post("/auth/register", json={"email": email, "username": username, "password": password})


def verify_user(monkeypatch, users, email):
    """Mark a registered user as verified directly, bypassing the email flow."""
    for user in users.documents:
        if user["email"] == email:
            user["is_verified"] = True


# ── POST /auth/register ─────────────────────────────────────────


def test_register_creates_unverified_user_without_returning_password(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)

    response = register(client)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert body["is_verified"] is False
    assert "password" not in body
    assert "password_hash" not in body


def test_register_sends_a_verification_email(monkeypatch):
    use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)

    register(client)

    assert len(sent["verification"]) == 1
    assert sent["verification"][0]["to"] == "alice@example.com"
    assert "token=" in sent["verification"][0]["link"]


def test_register_rejects_duplicate_email(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)
    payload = {"email": "alice@example.com", "username": "alice", "password": "securepass"}

    assert client.post("/auth/register", json=payload).status_code == 200
    response = client.post("/auth/register", json={**payload, "username": "alice2"})

    assert response.status_code == 400


# ── POST /auth/login ─────────────────────────────────────────────


def test_login_blocks_unverified_user(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)

    response = client.post("/auth/login", json={"email": "alice@example.com", "password": "securepass"})

    assert response.status_code == 403


def test_login_succeeds_once_verified(monkeypatch):
    users = use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")

    response = client.post("/auth/login", json={"email": "alice@example.com", "password": "securepass"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"].split(".")) == 3


def test_login_rejects_wrong_password_even_when_unverified(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)

    response = client.post("/auth/login", json={"email": "alice@example.com", "password": "wrongpass"})

    assert response.status_code == 401


def test_legacy_user_without_is_verified_field_can_log_in(monkeypatch):
    """Accounts created before this feature shipped have no is_verified field
    at all — they must default to verified rather than being locked out."""
    users = use_fake_users(monkeypatch)
    client = TestClient(app)
    users.documents.append({
        "_id": ObjectId(),
        "email": "legacy@example.com",
        "username": "legacy",
        "password_hash": hash_password("securepass"),
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    response = client.post("/auth/login", json={"email": "legacy@example.com", "password": "securepass"})

    assert response.status_code == 200


# ── POST /auth/verify-email ──────────────────────────────────────


def test_verify_email_with_valid_token_marks_user_verified(monkeypatch):
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    token = sent["verification"][0]["link"].split("token=")[1]

    response = client.post("/auth/verify-email", json={"token": token})

    assert response.status_code == 200
    assert users.documents[0]["is_verified"] is True


def test_verify_email_allows_subsequent_login(monkeypatch):
    use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    token = sent["verification"][0]["link"].split("token=")[1]
    client.post("/auth/verify-email", json={"token": token})

    response = client.post("/auth/login", json={"email": "alice@example.com", "password": "securepass"})

    assert response.status_code == 200


def test_verify_email_token_is_single_use(monkeypatch):
    use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    token = sent["verification"][0]["link"].split("token=")[1]
    client.post("/auth/verify-email", json={"token": token})

    second_attempt = client.post("/auth/verify-email", json={"token": token})

    assert second_attempt.status_code == 400


def test_verify_email_rejects_unknown_token(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)

    response = client.post("/auth/verify-email", json={"token": "not-a-real-token"})

    assert response.status_code == 400


# ── POST /auth/resend-verification ───────────────────────────────


def test_resend_verification_sends_new_link_for_unverified_user(monkeypatch):
    use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    sent["verification"].clear()

    response = client.post("/auth/resend-verification", json={"email": "alice@example.com"})

    assert response.status_code == 200
    assert len(sent["verification"]) == 1
    assert sent["verification"][0]["to"] == "alice@example.com"


def test_resend_verification_is_generic_for_unknown_email(monkeypatch):
    """Same response whether or not the email exists, so the endpoint can't
    be used to discover which addresses are registered."""
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)

    known = client.post("/auth/resend-verification", json={"email": "alice@example.com"})
    unknown = client.post("/auth/resend-verification", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_resend_verification_does_not_email_an_already_verified_user(monkeypatch):
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")
    sent["verification"].clear()

    response = client.post("/auth/resend-verification", json={"email": "alice@example.com"})

    assert response.status_code == 200
    assert len(sent["verification"]) == 0


# ── POST /auth/forgot-password ───────────────────────────────────


def test_forgot_password_sends_reset_link_for_existing_user(monkeypatch):
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")

    response = client.post("/auth/forgot-password", json={"email": "alice@example.com"})

    assert response.status_code == 200
    assert len(sent["reset"]) == 1
    assert sent["reset"][0]["to"] == "alice@example.com"
    assert "token=" in sent["reset"][0]["link"]


def test_forgot_password_is_generic_for_unknown_email(monkeypatch):
    """Same response whether or not the email exists, so the endpoint can't
    be used to discover which addresses are registered."""
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")

    known = client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(sent["reset"]) == 1  # only the real account got an email


# ── POST /auth/reset-password ─────────────────────────────────────


def test_reset_password_with_valid_token_changes_password(monkeypatch):
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")
    client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    token = sent["reset"][0]["link"].split("token=")[1]

    response = client.post("/auth/reset-password", json={"token": token, "new_password": "newsecurepass"})

    assert response.status_code == 200
    old_login = client.post("/auth/login", json={"email": "alice@example.com", "password": "securepass"})
    new_login = client.post("/auth/login", json={"email": "alice@example.com", "password": "newsecurepass"})
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_reset_password_verifies_an_unverified_account(monkeypatch):
    """Clicking the emailed reset link proves email ownership, so an unverified
    user who completes a reset should be able to log in straight away rather
    than still being blocked by the verification check."""
    use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)  # leaves the account unverified
    client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    token = sent["reset"][0]["link"].split("token=")[1]

    client.post("/auth/reset-password", json={"token": token, "new_password": "newsecurepass"})

    login = client.post("/auth/login", json={"email": "alice@example.com", "password": "newsecurepass"})
    assert login.status_code == 200


def test_reset_password_token_is_single_use(monkeypatch):
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")
    client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    token = sent["reset"][0]["link"].split("token=")[1]
    client.post("/auth/reset-password", json={"token": token, "new_password": "newsecurepass"})

    second_attempt = client.post("/auth/reset-password", json={"token": token, "new_password": "anotherpass"})

    assert second_attempt.status_code == 400


def test_reset_password_rejects_unknown_token(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)

    response = client.post("/auth/reset-password", json={"token": "not-a-real-token", "new_password": "newsecurepass"})

    assert response.status_code == 400


def test_reset_password_rejects_too_short_new_password(monkeypatch):
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")
    client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    token = sent["reset"][0]["link"].split("token=")[1]

    response = client.post("/auth/reset-password", json={"token": token, "new_password": "short"})

    assert response.status_code == 422


# ── Rate limiting ──────────────────────────────────────────────


def test_login_is_rate_limited_after_repeated_attempts(monkeypatch):
    use_fake_users(monkeypatch)
    monkeypatch.setattr(auth_rate_limit, "LOGIN_LIMIT", 3)
    client = TestClient(app)

    for _ in range(3):
        client.post("/auth/login", json={"email": "alice@example.com", "password": "wrongpass"})
    response = client.post("/auth/login", json={"email": "alice@example.com", "password": "wrongpass"})

    assert response.status_code == 429


def test_register_is_rate_limited_after_repeated_attempts(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    monkeypatch.setattr(auth_rate_limit, "REGISTER_LIMIT", 2)
    client = TestClient(app)

    register(client, email="one@example.com", username="one")
    register(client, email="two@example.com", username="two")
    response = register(client, email="three@example.com", username="three")

    assert response.status_code == 429


def test_forgot_password_is_rate_limited_after_repeated_attempts(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    monkeypatch.setattr(auth_rate_limit, "FORGOT_PASSWORD_LIMIT", 2)
    client = TestClient(app)

    client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    response = client.post("/auth/forgot-password", json={"email": "alice@example.com"})

    assert response.status_code == 429


# ── Breached-password check ───────────────────────────────────────


def test_register_rejects_a_breached_password(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    monkeypatch.setattr(auth_router, "is_password_breached", lambda password: _async_true())
    client = TestClient(app)

    response = register(client, password="whateveryouwant")

    assert response.status_code == 400


def test_register_allows_a_password_that_is_not_breached(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)

    response = register(client, password="securepass")

    assert response.status_code == 200


def test_reset_password_rejects_a_breached_new_password(monkeypatch):
    users = use_fake_users(monkeypatch)
    sent = spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")
    client.post("/auth/forgot-password", json={"email": "alice@example.com"})
    token = sent["reset"][0]["link"].split("token=")[1]
    monkeypatch.setattr(auth_router, "is_password_breached", lambda password: _async_true())

    response = client.post("/auth/reset-password", json={"token": token, "new_password": "whateveryouwant"})

    assert response.status_code == 400


async def _async_true() -> bool:
    return True


async def _async_false() -> bool:
    return False


# ── Turnstile bot protection ──────────────────────────────────────


def test_register_rejects_failed_turnstile_check(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)
    monkeypatch.setattr(auth_router, "verify_turnstile_token", lambda token, remote_ip=None: _async_false())

    response = register(client, password="securepass2")

    assert response.status_code == 400


def test_register_allows_a_passed_turnstile_check(monkeypatch):
    use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)

    response = register(client, password="securepass2")

    assert response.status_code == 200


def test_forgot_password_rejects_failed_turnstile_check(monkeypatch):
    users = use_fake_users(monkeypatch)
    spy_on_emails(monkeypatch)
    client = TestClient(app)
    register(client)
    verify_user(monkeypatch, users, "alice@example.com")
    monkeypatch.setattr(auth_router, "verify_turnstile_token", lambda token, remote_ip=None: _async_false())

    response = client.post("/auth/forgot-password", json={"email": "alice@example.com"})

    assert response.status_code == 400
