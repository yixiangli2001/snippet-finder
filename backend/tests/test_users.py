from fastapi.testclient import TestClient

import routers.auth as auth_router
import routers.users as users_router
import utils.security as security
from main import app
from tests.fakes import FakeCollection


def use_fake_users(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(users_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    return users


def register_and_login(client, email="alice@example.com", username="alice"):
    client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": "securepass"},
    )
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "securepass"},
    )
    return login.json()["access_token"]


def test_get_current_user_returns_logged_in_profile(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)

    token = register_and_login(client)

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


def test_update_username_changes_current_user(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    response = client.put(
        "/users/me/username",
        json={"username": "alice-new"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "alice-new"


def test_update_username_requires_token():
    client = TestClient(app)

    response = client.put("/users/me/username", json={"username": "alice-new"})

    assert response.status_code == 401


def test_update_username_rejects_duplicate(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)
    register_and_login(client, email="bob@example.com", username="bob")

    response = client.put(
        "/users/me/username",
        json={"username": "bob"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_update_email_changes_current_user(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    response = client.put(
        "/users/me/email",
        json={"email": "alice-new@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "alice-new@example.com"


def test_update_email_requires_token():
    client = TestClient(app)

    response = client.put("/users/me/email", json={"email": "alice-new@example.com"})

    assert response.status_code == 401


def test_update_email_rejects_duplicate(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)
    register_and_login(client, email="bob@example.com", username="bob")

    response = client.put(
        "/users/me/email",
        json={"email": "bob@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_update_password_changes_password(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    response = client.put(
        "/users/me/password",
        json={"current_password": "securepass", "new_password": "newsecurepass"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password updated"

    login_with_old_password = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "securepass"},
    )
    login_with_new_password = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "newsecurepass"},
    )
    assert login_with_old_password.status_code == 401
    assert login_with_new_password.status_code == 200


def test_update_password_rejects_wrong_current_password(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    response = client.put(
        "/users/me/password",
        json={"current_password": "wrongpass", "new_password": "newsecurepass"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_update_password_rejects_short_new_password(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    response = client.put(
        "/users/me/password",
        json={"current_password": "securepass", "new_password": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_update_password_rejects_too_long_new_password(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    response = client.put(
        "/users/me/password",
        json={"current_password": "securepass", "new_password": "a" * 73},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
