from fastapi.testclient import TestClient

import routers.auth as auth_router
import utils.security as security
from main import app
from tests.fakes import FakeCollection


def test_get_current_user_returns_logged_in_profile(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    client = TestClient(app)

    client.post(
        "/auth/register",
        json={"email": "alice@example.com", "username": "alice", "password": "securepass"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "securepass"},
    )
    token = login.json()["access_token"]

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert "password_hash" not in body


def test_get_current_user_requires_token():
    client = TestClient(app)

    response = client.get("/users/me")

    assert response.status_code == 401
