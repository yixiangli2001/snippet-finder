from fastapi.testclient import TestClient

import routers.auth as auth_router
import utils.security as security
from main import app
from tests.fakes import FakeCollection


def use_fake_users(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    return users


def test_register_creates_user_without_returning_password(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "username": "alice", "password": "securepass"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert body["role"] == "user"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    payload = {"email": "alice@example.com", "username": "alice", "password": "securepass"}

    assert client.post("/auth/register", json=payload).status_code == 200
    response = client.post(
        "/auth/register",
        json={**payload, "username": "alice2"},
    )

    assert response.status_code == 400


def test_login_returns_access_token(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={"email": "alice@example.com", "username": "alice", "password": "securepass"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "securepass"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"].split(".")) == 3


def test_login_rejects_wrong_password(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={"email": "alice@example.com", "username": "alice", "password": "securepass"},
    )

    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrongpass"},
    )

    assert response.status_code == 401
