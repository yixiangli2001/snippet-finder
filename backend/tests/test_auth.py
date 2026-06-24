from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

import routers.auth as auth_router
import utils.auth_tokens as auth_tokens
import utils.security as security
from main import app
from tests.fakes import FakeCollection
from utils.security import hash_password


def use_fake_users(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(auth_tokens, "auth_tokens_collection", FakeCollection())
    return users


def spy_on_emails(monkeypatch):
    """Replace the email senders with spies so tests can assert on calls
    instead of actually sending (or printing) anything."""
    sent = {"verification": [], "reset": []}
    monkeypatch.setattr(
        auth_router, "send_verification_email",
        lambda to, link: sent["verification"].append({"to": to, "link": link}),
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
