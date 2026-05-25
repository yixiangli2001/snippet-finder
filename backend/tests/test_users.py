from fastapi.testclient import TestClient

import routers.auth as auth_router
import routers.snippets as snippets_router
import routers.users as users_router
import utils.security as security
from main import app
from tests.fakes import FakeCollection


def fake_snippet(owner_id, title, is_public):
    return {
        "owner_id": owner_id,
        "title": title,
        "language": "python",
        "code": "print('hi')",
        "description": None,
        "tags": [],
        "is_public": is_public,
        "times_copied": 0,
    }


def use_fake_users(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(users_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    return users


def use_fake_users_and_snippets(monkeypatch, snippets=None):
    users = use_fake_users(monkeypatch)
    snippet_collection = FakeCollection(snippets or [])
    monkeypatch.setattr(users_router, "snippets_collection", snippet_collection)
    monkeypatch.setattr(snippets_router, "snippets_collection", snippet_collection)
    return users, snippet_collection


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


def test_delete_account_removes_private_snippets_and_orphans_public_snippets(monkeypatch):
    users, snippets = use_fake_users_and_snippets(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)
    user = users.documents[0]
    snippets.documents.extend([
        fake_snippet(user["_id"], "private", False),
        fake_snippet(user["_id"], "public", True),
    ])

    response = client.delete("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["message"] == "Account deleted"
    remaining_titles = {snippet["title"] for snippet in snippets.documents}
    assert remaining_titles == {"public"}
    assert snippets.documents[0]["owner_id"] is None


def test_delete_account_removes_user_record(monkeypatch):
    users, _ = use_fake_users_and_snippets(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    response = client.delete("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert users.documents == []


def test_deleted_user_token_no_longer_valid(monkeypatch):
    users, _ = use_fake_users_and_snippets(monkeypatch)
    client = TestClient(app)
    token = register_and_login(client)

    client.delete("/users/me", headers={"Authorization": f"Bearer {token}"})
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


# ── GET /users/{username} ─────────────────────────────────────


def test_get_user_profile_returns_id_and_username(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)
    register_and_login(client)

    response = client.get("/users/alice")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert "id" in body
    assert "email" not in body


def test_get_user_profile_returns_404_for_unknown_username(monkeypatch):
    use_fake_users(monkeypatch)
    client = TestClient(app)

    response = client.get("/users/nobody")

    assert response.status_code == 404
