from bson import ObjectId
from fastapi.testclient import TestClient

import routers.admin as admin_router
import routers.auth as auth_router
import routers.snippets as snippets_router
import utils.auth_tokens as auth_tokens
import utils.security as security
import utils.user_lookup as user_lookup
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


async def _not_breached(password):
    return False


def setup(monkeypatch, extra_users=None, snippets=None):
    admin = make_user(email="admin@example.com", username="admin", role="admin")
    users = FakeCollection([admin] + (extra_users or []))
    snippet_col = FakeCollection(snippets or [])

    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(admin_router, "users_collection", users)
    monkeypatch.setattr(admin_router, "snippets_collection", snippet_col)
    monkeypatch.setattr(snippets_router, "snippets_collection", snippet_col)
    monkeypatch.setattr(auth_tokens, "auth_tokens_collection", FakeCollection())
    monkeypatch.setattr(auth_router, "is_password_breached", _not_breached)

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
    # Registration leaves the account unverified; these tests are about other
    # behavior, so mark it verified directly rather than going through email.
    for user in auth_router.users_collection.documents:
        if user["email"] == email:
            user["is_verified"] = True
    login = client.post("/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


def setup_with_registered_admin(monkeypatch, extra_users=None, snippets=None, collections=None):
    users = FakeCollection(extra_users or [])
    snippet_col = FakeCollection(snippets or [])
    col_col = FakeCollection(collections or [])

    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(admin_router, "users_collection", users)
    monkeypatch.setattr(admin_router, "snippets_collection", snippet_col)
    monkeypatch.setattr(admin_router, "collections_collection", col_col)
    monkeypatch.setattr(snippets_router, "snippets_collection", snippet_col)
    monkeypatch.setattr(user_lookup, "users_collection", users)
    monkeypatch.setattr(auth_tokens, "auth_tokens_collection", FakeCollection())
    monkeypatch.setattr(auth_router, "is_password_breached", _not_breached)

    client = TestClient(app)
    register_and_login(client, "admin@example.com", username="admin")

    # Promote to admin directly in the fake collection
    users.documents[0]["role"] = "admin"

    admin_token = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "securepass"}
    ).json()["access_token"]

    return users, snippet_col, col_col, client, admin_token


# ── List users ────────────────────────────────────────────────


def test_list_users_returns_all_accounts(monkeypatch):
    users, _, _, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")

    response = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert emails == {"admin@example.com", "bob@example.com"}


def test_list_users_requires_admin(monkeypatch):
    users, _, _, client, _ = setup_with_registered_admin(monkeypatch)
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
    users, snippet_col, _, client, token = setup_with_registered_admin(monkeypatch)
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
    _, _, _, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")

    response = client.get("/admin/snippets", headers={"Authorization": f"Bearer {user_token}"})

    assert response.status_code == 403


# ── Delete user ───────────────────────────────────────────────


def test_delete_user_removes_account(monkeypatch):
    users, _, _, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")

    response = client.delete(
        f"/admin/users/{bob['_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert not any(u["email"] == "bob@example.com" for u in users.documents)


def test_delete_user_removes_private_snippets_and_orphans_public(monkeypatch):
    users, snippet_col, _, client, token = setup_with_registered_admin(monkeypatch)
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


def test_delete_user_removes_private_collections_and_orphans_public(monkeypatch):
    users, _, col_col, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")
    col_col.documents.extend([
        {"_id": ObjectId(), "owner_id": bob["_id"], "name": "bob public", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": bob["_id"], "name": "bob private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.delete(f"/admin/users/{bob['_id']}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    names = {collection["name"] for collection in col_col.documents}
    assert names == {"bob public"}
    assert col_col.documents[0]["owner_id"] is None


def test_delete_user_returns_404_for_unknown_id(monkeypatch):
    _, _, _, client, token = setup_with_registered_admin(monkeypatch)

    response = client.delete(
        f"/admin/users/{ObjectId()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_delete_user_requires_admin(monkeypatch):
    users, _, _, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")

    response = client.delete(
        f"/admin/users/{bob['_id']}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


# ── Delete snippet ────────────────────────────────────────────


def test_delete_snippet_removes_any_snippet(monkeypatch):
    users, snippet_col, _, client, token = setup_with_registered_admin(monkeypatch)
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


def test_delete_snippet_removes_it_from_collections(monkeypatch):
    users, snippet_col, col_col, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")
    snippet_col.documents.append(make_snippet(bob["_id"], "bob snippet"))
    snippet_id = snippet_col.documents[0]["_id"]
    other_snippet_id = ObjectId()
    col_col.documents.append(
        {"_id": ObjectId(), "owner_id": bob["_id"], "name": "Bob collection", "is_public": False,
         "snippet_ids": [snippet_id, other_snippet_id], "description": None,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )

    response = client.delete(
        f"/admin/snippets/{snippet_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert col_col.documents[0]["snippet_ids"] == [other_snippet_id]


def test_delete_snippet_returns_404_for_unknown_id(monkeypatch):
    _, _, _, client, token = setup_with_registered_admin(monkeypatch)

    response = client.delete(
        f"/admin/snippets/{ObjectId()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_delete_snippet_requires_admin(monkeypatch):
    users, snippet_col, _, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")
    bob = next(u for u in users.documents if u["email"] == "bob@example.com")
    snippet_col.documents.append(make_snippet(bob["_id"], "bob snippet"))
    snippet_id = snippet_col.documents[0]["_id"]

    response = client.delete(
        f"/admin/snippets/{snippet_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403


# ── Admin collections ─────────────────────────────────────────


def test_admin_list_collections_returns_all_including_private(monkeypatch):
    users, _, col_col, client, token = setup_with_registered_admin(monkeypatch)
    owner_id = users.documents[0]["_id"]
    col_col.documents.extend([
        {"_id": ObjectId(), "owner_id": owner_id, "name": "Public col", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": owner_id, "name": "Private col", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.get("/admin/collections", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert names == {"Public col", "Private col"}


def test_admin_delete_collection_removes_it(monkeypatch):
    users, _, col_col, client, token = setup_with_registered_admin(monkeypatch)
    owner_id = users.documents[0]["_id"]
    col_col.documents.append(
        {"_id": ObjectId(), "owner_id": owner_id, "name": "To delete", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )
    col_id = col_col.documents[0]["_id"]

    response = client.delete(f"/admin/collections/{col_id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert col_col.documents == []


def test_admin_collections_requires_admin(monkeypatch):
    _, _, _, client, _ = setup_with_registered_admin(monkeypatch)
    user_token = register_and_login(client, "bob@example.com")

    response = client.get("/admin/collections", headers={"Authorization": f"Bearer {user_token}"})

    assert response.status_code == 403


# ── PUT /admin/users/{id} ──────────────────────────────────────


def test_admin_can_update_user_username(monkeypatch):
    users, _, _, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com", username="bob")
    bob = next(u for u in users.documents if u["username"] == "bob")

    response = client.put(
        f"/admin/users/{bob['_id']}",
        json={"username": "bobby"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "bobby"


def test_admin_can_update_user_email(monkeypatch):
    users, _, _, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com", username="bob")
    bob = next(u for u in users.documents if u["username"] == "bob")

    response = client.put(
        f"/admin/users/{bob['_id']}",
        json={"email": "bobby@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "bobby@example.com"


def test_admin_update_user_rejects_duplicate_username(monkeypatch):
    users, _, _, client, token = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "alice@example.com", username="alice")
    register_and_login(client, "bob@example.com", username="bob")
    bob = next(u for u in users.documents if u["username"] == "bob")

    response = client.put(
        f"/admin/users/{bob['_id']}",
        json={"username": "alice"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_admin_update_user_requires_admin(monkeypatch):
    users, _, _, client, _ = setup_with_registered_admin(monkeypatch)
    register_and_login(client, "bob@example.com", username="bob")
    bob = next(u for u in users.documents if u["username"] == "bob")
    user_token = register_and_login(client, "charlie@example.com")

    response = client.put(
        f"/admin/users/{bob['_id']}",
        json={"username": "hacked"},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403
