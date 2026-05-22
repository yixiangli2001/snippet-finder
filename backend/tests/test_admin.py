from bson import ObjectId
from fastapi.testclient import TestClient

import routers.admin as admin_router
import routers.auth as auth_router
import routers.snippets as snippets_router
import utils.security as security
from main import app
from tests.fakes import FakeCollection


def make_user(email="alice@example.com", username="alice", role="user"):
    return {
        "_id": ObjectId(),
        "email": email,
        "username": username,
        "password_hash": "$2b$12$placeholder",
        "role": role,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


def make_snippet(owner_id, title="My snippet", is_public=True):
    return {
        "_id": ObjectId(),
        "owner_id": owner_id,
        "title": title,
        "language": "python",
        "code": "print('hi')",
        "description": None,
        "tags": [],
        "is_public": is_public,
        "times_copied": 0,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


def setup(monkeypatch, extra_users=None, snippets=None):
    admin = make_user(email="admin@example.com", username="admin", role="admin")
    users = FakeCollection([admin] + (extra_users or []))
    snippet_col = FakeCollection(snippets or [])

    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(admin_router, "users_collection", users)
    monkeypatch.setattr(admin_router, "snippets_collection", snippet_col)
    monkeypatch.setattr(snippets_router, "snippets_collection", snippet_col)

    client = TestClient(app)
    login = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "securepass"},
    )
    # Admin exists in FakeCollection directly — login will fail password check.
    # Register admin instead so the hash is correct.
    return users, snippet_col, client


def register_and_login(client, email, password="securepass", username=None):
    client.post(
        "/auth/register",
        json={"email": email, "username": username or email.split("@")[0], "password": password},
    )
    login = client.post("/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


def setup_with_registered_admin(monkeypatch, extra_users=None, snippets=None):
    users = FakeCollection(extra_users or [])
    snippet_col = FakeCollection(snippets or [])

    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(admin_router, "users_collection", users)
    monkeypatch.setattr(admin_router, "snippets_collection", snippet_col)
    monkeypatch.setattr(snippets_router, "snippets_collection", snippet_col)

    client = TestClient(app)
    register_and_login(client, "admin@example.com", username="admin")

    # Promote to admin directly in the fake collection
    users.documents[0]["role"] = "admin"

    admin_token = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "securepass"}
    ).json()["access_token"]

    return users, snippet_col, client, admin_token


# ── List users ────────────────────────────────────────────────


def test_list_users_returns_all_accounts(monkeypatch):
    users, _, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")

    response = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert emails == {"admin@example.com", "bob@example.com"}


def test_list_users_requires_admin(monkeypatch):
    users, _, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")

    response = client.get("/admin/users", headers={"Authorization": f"Bearer {user_token}"})

    assert response.status_code == 403


def test_list_users_requires_token(monkeypatch):
    setup_with_registered_admin(monkeypatch)
    client = TestClient(app)

    response = client.get("/admin/users")

    assert response.status_code == 401


# ── List snippets ─────────────────────────────────────────────


def test_list_snippets_returns_all_including_private(monkeypatch):
    users, snippet_col, client, token = setup_with_registered_admin(monkeypatch)
    owner_id = users.documents[0]["_id"]
    snippet_col.documents.extend([
        make_snippet(owner_id, "public snippet", is_public=True),
        make_snippet(owner_id, "private snippet", is_public=False),
    ])

    response = client.get("/admin/snippets", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    titles = {s["title"] for s in response.json()}
    assert titles == {"public snippet", "private snippet"}


def test_list_snippets_requires_admin(monkeypatch):
    _, _, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")

    response = client.get("/admin/snippets", headers={"Authorization": f"Bearer {user_token}"})

    assert response.status_code == 403


# ── Delete user ───────────────────────────────────────────────


def test_delete_user_removes_account(monkeypatch):
    users, _, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")

    response = client.delete(
        f"/admin/users/{bob['_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert not any(u["email"] == "bob@example.com" for u in users.documents)


def test_delete_user_removes_private_snippets_and_orphans_public(monkeypatch):
    users, snippet_col, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")
    snippet_col.documents.extend([
        make_snippet(bob["_id"], "bob public", is_public=True),
        make_snippet(bob["_id"], "bob private", is_public=False),
    ])

    client.delete(f"/admin/users/{bob['_id']}", headers={"Authorization": f"Bearer {token}"})

    titles = {s["title"] for s in snippet_col.documents}
    assert titles == {"bob public"}
    assert snippet_col.documents[0]["owner_id"] is None


def test_delete_user_returns_404_for_unknown_id(monkeypatch):
    _, _, client, token = setup_with_registered_admin(monkeypatch)

    response = client.delete(
        f"/admin/users/{ObjectId()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_delete_user_requires_admin(monkeypatch):
    users, _, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")

    response = client.delete(
        f"/admin/users/{bob['_id']}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


# ── Delete snippet ────────────────────────────────────────────


def test_delete_snippet_removes_any_snippet(monkeypatch):
    users, snippet_col, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")
    snippet_col.documents.append(make_snippet(bob["_id"], "bob snippet"))
    snippet_id = snippet_col.documents[0]["_id"]

    response = client.delete(
        f"/admin/snippets/{snippet_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert snippet_col.documents == []


def test_delete_snippet_returns_404_for_unknown_id(monkeypatch):
    _, _, client, token = setup_with_registered_admin(monkeypatch)

    response = client.delete(
        f"/admin/snippets/{ObjectId()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_delete_snippet_requires_admin(monkeypatch):
    users, snippet_col, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")
    snippet_col.documents.append(make_snippet(bob["_id"], "bob snippet"))
    snippet_id = snippet_col.documents[0]["_id"]

    response = client.delete(
        f"/admin/snippets/{snippet_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403
