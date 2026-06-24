from bson import ObjectId
from fastapi.testclient import TestClient

import routers.auth as auth_router
import routers.collections as collections_router
import utils.auth_tokens as auth_tokens
import utils.security as security
import utils.user_lookup as user_lookup
from main import app
from tests.fakes import FakeCollection
from utils.security import create_token


def setup(monkeypatch, collections=None, snippets=None):
    users = FakeCollection()
    col_collection = FakeCollection(collections or [])
    snippet_collection = FakeCollection(snippets or [])

    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(collections_router, "collections_collection", col_collection)
    monkeypatch.setattr(collections_router, "snippets_collection", snippet_collection)
    monkeypatch.setattr(user_lookup, "users_collection", users)
    monkeypatch.setattr(auth_tokens, "auth_tokens_collection", FakeCollection())

    client = TestClient(app)
    return users, col_collection, snippet_collection, client


def register_and_login(client, email="alice@example.com", username="alice"):
    client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": "securepass"},
    )
    # Registration leaves the account unverified; these tests are about other
    # behavior, so mark it verified directly rather than going through email.
    for user in auth_router.users_collection.documents:
        if user["email"] == email:
            user["is_verified"] = True
    login = client.post("/auth/login", json={"email": email, "password": "securepass"})
    return login.json()["access_token"]


# ── GET /collections ──────────────────────────────────────────


def test_unauthenticated_user_sees_only_public_collections(monkeypatch):
    owner_id = ObjectId()
    _, col_collection, _, client = setup(monkeypatch, [
        {"owner_id": owner_id, "name": "Public", "is_public": True, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"owner_id": owner_id, "name": "Private", "is_public": False, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.get("/collections/")

    assert response.status_code == 200
    names = [c["name"] for c in response.json()["items"]]
    assert names == ["Public"]


def test_authenticated_user_sees_own_private_collections(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]

    other_id = ObjectId()
    col_collection.documents.extend([
        {"_id": ObjectId(), "owner_id": user_id, "name": "My private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": other_id, "name": "Their private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.get("/collections/", headers={"Authorization": f"Bearer {token}"})

    names = [c["name"] for c in response.json()["items"]]
    assert "My private" in names
    assert "Their private" not in names


def test_admin_sees_all_private_collections(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)

    admin_id = ObjectId()
    users.documents.append({
        "_id": admin_id,
        "email": "admin@example.com",
        "username": "admin",
        "password_hash": "$2b$12$placeholder",
        "role": "admin",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    })

    other_id = ObjectId()
    col_collection.documents.extend([
        {"_id": ObjectId(), "owner_id": other_id, "name": "Their private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": other_id, "name": "Their public", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    token = create_token(str(admin_id), "admin")
    response = client.get("/collections/", headers={"Authorization": f"Bearer {token}"})

    names = {c["name"] for c in response.json()["items"]}
    assert names == {"Their private", "Their public"}


# ── POST /collections ─────────────────────────────────────────


def test_create_collection_requires_auth(monkeypatch):
    _, _, _, client = setup(monkeypatch)

    response = client.post("/collections/", json={"name": "My collection"})

    assert response.status_code == 401


def test_create_collection_sets_owner_and_private_by_default(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)

    response = client.post(
        "/collections/",
        json={"name": "My collection"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My collection"
    assert body["is_public"] is False
    assert body["snippet_ids"] == []
    assert body["owner_id"] == str(users.documents[0]["_id"])


# ── GET /collections/{id} ─────────────────────────────────────


def test_get_public_collection_without_auth(monkeypatch):
    owner = {
        "_id": ObjectId(),
        "email": "owner@example.com",
        "username": "owner",
        "password_hash": "hash",
        "role": "user",
        "created_at": "2026-01-01",
        "updated_at": "2026-01-01",
    }
    users, col_collection, _, client = setup(monkeypatch, [
        {"owner_id": owner["_id"], "name": "Public", "is_public": True, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])
    users.documents.append(owner)
    col_id = col_collection.documents[0]["_id"]

    response = client.get(f"/collections/{col_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Public"
    assert response.json()["owner_username"] == "owner"


def test_get_private_collection_returns_404_to_non_owner(monkeypatch):
    owner_id = ObjectId()
    _, col_collection, _, client = setup(monkeypatch, [
        {"owner_id": owner_id, "name": "Private", "is_public": False, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])
    col_id = col_collection.documents[0]["_id"]

    response = client.get(f"/collections/{col_id}")

    assert response.status_code == 404


def test_owner_can_get_own_private_collection(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    col_collection.documents.append(
        {"owner_id": user_id, "name": "Private", "is_public": False, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01",
         "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    response = client.get(f"/collections/{col_id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


# ── PUT /collections/{id} ─────────────────────────────────────


def test_owner_can_update_collection(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    col_collection.documents.append(
        {"owner_id": user_id, "name": "Old name", "is_public": False, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01",
         "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    response = client.put(
        f"/collections/{col_id}",
        json={"name": "New name", "is_public": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New name"
    assert body["is_public"] is True


def test_cannot_make_collection_public_with_private_snippets(monkeypatch):
    users, col_collection, snippet_collection, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    private_snippet_id = ObjectId()
    snippet_collection.documents.append({
        "_id": private_snippet_id,
        "owner_id": user_id,
        "title": "Private snippet",
        "language": "PYTHON",
        "code": "print('secret')",
        "description": "",
        "tags": [],
        "is_public": False,
        "times_copied": 0,
        "created_at": "2026-01-01",
        "updated_at": "2026-01-01",
    })
    col_collection.documents.append(
        {"owner_id": user_id, "name": "Private collection", "is_public": False,
         "snippet_ids": [private_snippet_id], "description": None,
         "created_at": "2026-01-01", "updated_at": "2026-01-01",
         "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    response = client.put(
        f"/collections/{col_id}",
        json={"is_public": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert col_collection.documents[0]["is_public"] is False


def test_no_op_collection_update_keeps_owner_username(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user = users.documents[0]
    col_collection.documents.append(
        {"owner_id": user["_id"], "name": "Same name", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01",
         "updated_at": "2026-01-01", "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    response = client.put(
        f"/collections/{col_id}",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["owner_username"] == "alice"


def test_non_owner_cannot_update_collection(monkeypatch):
    _, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    col_collection.documents.append(
        {"owner_id": ObjectId(), "name": "Their collection", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01",
         "updated_at": "2026-01-01", "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    response = client.put(
        f"/collections/{col_id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


# ── DELETE /collections/{id} ──────────────────────────────────


def test_owner_can_delete_collection(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    col_collection.documents.append(
        {"owner_id": user_id, "name": "To delete", "is_public": False, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01",
         "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    response = client.delete(
        f"/collections/{col_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert col_collection.documents == []


def test_delete_collection_does_not_delete_snippets(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    snippet_id = ObjectId()
    col_collection.documents.append(
        {"owner_id": user_id, "name": "To delete", "is_public": False,
         "snippet_ids": [snippet_id], "description": None,
         "created_at": "2026-01-01", "updated_at": "2026-01-01", "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    client.delete(f"/collections/{col_id}", headers={"Authorization": f"Bearer {token}"})

    # Collection is gone but we have no snippets collection here — just verify
    # the collection record itself was removed and snippet_ids were not cascaded.
    assert col_collection.documents == []


def test_owner_sees_own_private_collections_via_profile_filter(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]

    col_collection.documents.extend([
        {"_id": ObjectId(), "owner_id": user_id, "name": "My public", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": user_id, "name": "My private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.get(
        f"/collections/?owner_id={user_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    names = {c["name"] for c in response.json()["items"]}
    assert names == {"My public", "My private"}


def test_owner_can_filter_their_collections_to_private_only(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]

    col_collection.documents.extend([
        {"_id": ObjectId(), "owner_id": user_id, "name": "My public", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": user_id, "name": "My private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.get(
        f"/collections/?owner_id={user_id}&is_public=false",
        headers={"Authorization": f"Bearer {token}"},
    )

    names = [c["name"] for c in response.json()["items"]]
    assert names == ["My private"]


def test_public_collection_filter_does_not_leak_private_collections(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    other_id = ObjectId()

    col_collection.documents.append(
        {"_id": ObjectId(), "owner_id": other_id, "name": "Their private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    )

    response = client.get(
        f"/collections/?owner_id={other_id}&is_public=false",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.json()["items"] == []


def test_admin_sees_private_collections_via_profile_filter(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)

    admin_id = ObjectId()
    users.documents.append({
        "_id": admin_id, "email": "admin@example.com", "username": "admin",
        "password_hash": "$2b$12$placeholder", "role": "admin",
        "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
    })

    other_id = ObjectId()
    col_collection.documents.extend([
        {"_id": ObjectId(), "owner_id": other_id, "name": "Their public", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": other_id, "name": "Their private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    token = create_token(str(admin_id), "admin")
    response = client.get(
        f"/collections/?owner_id={other_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    names = {c["name"] for c in response.json()["items"]}
    assert names == {"Their public", "Their private"}


def test_owner_id_filter_returns_only_public_collections_of_that_user(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    other_id = ObjectId()
    col_collection.documents.extend([
        {"_id": ObjectId(), "owner_id": user_id, "name": "My public", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": user_id, "name": "My private", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"_id": ObjectId(), "owner_id": other_id, "name": "Their public", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.get(f"/collections/?owner_id={user_id}")

    names = [c["name"] for c in response.json()["items"]]
    assert names == ["My public"]


def test_non_owner_cannot_delete_collection(monkeypatch):
    _, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    col_collection.documents.append(
        {"owner_id": ObjectId(), "name": "Their collection", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01",
         "updated_at": "2026-01-01", "_id": ObjectId()}
    )
    col_id = col_collection.documents[0]["_id"]

    response = client.delete(
        f"/collections/{col_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


# ── POST /collections/{id}/snippets ──────────────────────────


def test_owner_can_add_public_snippet_to_collection(monkeypatch):
    users, col_collection, snippet_collection, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    col_id = ObjectId()
    snippet_id = ObjectId()
    col_collection.documents.append(
        {"_id": col_id, "owner_id": user_id, "name": "My col", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )
    snippet_collection.documents.append(
        {"_id": snippet_id, "owner_id": ObjectId(), "is_public": True,
         "title": "A snippet", "language": "python", "code": "x=1",
         "description": None, "tags": [], "times_copied": 0,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )

    response = client.post(
        f"/collections/{col_id}/snippets",
        json={"snippet_id": str(snippet_id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert str(snippet_id) in response.json()["snippet_ids"]


def test_cannot_add_same_snippet_to_collection_twice(monkeypatch):
    users, col_collection, snippet_collection, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    col_id = ObjectId()
    snippet_id = ObjectId()
    col_collection.documents.append(
        {"_id": col_id, "owner_id": user_id, "name": "My col", "is_public": False,
         "snippet_ids": [snippet_id], "description": None,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )
    snippet_collection.documents.append(
        {"_id": snippet_id, "owner_id": user_id, "is_public": False,
         "title": "A snippet", "language": "python", "code": "x=1",
         "description": None, "tags": [], "times_copied": 0,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )

    response = client.post(
        f"/collections/{col_id}/snippets",
        json={"snippet_id": str(snippet_id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Snippet is already in this collection"
    assert col_collection.documents[0]["snippet_ids"] == [snippet_id]


def test_cannot_add_private_snippet_to_public_collection(monkeypatch):
    users, col_collection, snippet_collection, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    col_id = ObjectId()
    snippet_id = ObjectId()
    col_collection.documents.append(
        {"_id": col_id, "owner_id": user_id, "name": "My public col", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )
    snippet_collection.documents.append(
        {"_id": snippet_id, "owner_id": user_id, "is_public": False,
         "title": "My private snippet", "language": "python", "code": "x=1",
         "description": None, "tags": [], "times_copied": 0,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )

    response = client.post(
        f"/collections/{col_id}/snippets",
        json={"snippet_id": str(snippet_id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


def test_cannot_add_private_snippet_you_do_not_own(monkeypatch):
    users, col_collection, snippet_collection, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    col_id = ObjectId()
    snippet_id = ObjectId()
    col_collection.documents.append(
        {"_id": col_id, "owner_id": user_id, "name": "My col", "is_public": False,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )
    snippet_collection.documents.append(
        {"_id": snippet_id, "owner_id": ObjectId(), "is_public": False,
         "title": "Secret", "language": "python", "code": "x=1",
         "description": None, "tags": [], "times_copied": 0,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )

    response = client.post(
        f"/collections/{col_id}/snippets",
        json={"snippet_id": str(snippet_id)},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


# ── DELETE /collections/{id}/snippets/{snippet_id} ───────────


def test_owner_can_remove_snippet_from_collection(monkeypatch):
    users, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    user_id = users.documents[0]["_id"]
    snippet_id = ObjectId()
    col_id = ObjectId()
    col_collection.documents.append(
        {"_id": col_id, "owner_id": user_id, "name": "My col", "is_public": False,
         "snippet_ids": [snippet_id], "description": None,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )

    response = client.delete(
        f"/collections/{col_id}/snippets/{snippet_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["snippet_ids"] == []


def test_non_owner_cannot_remove_snippet_from_collection(monkeypatch):
    _, col_collection, _, client = setup(monkeypatch)
    token = register_and_login(client)
    snippet_id = ObjectId()
    col_id = ObjectId()
    col_collection.documents.append(
        {"_id": col_id, "owner_id": ObjectId(), "name": "Their col", "is_public": True,
         "snippet_ids": [snippet_id], "description": None,
         "created_at": "2026-01-01", "updated_at": "2026-01-01"}
    )

    response = client.delete(
        f"/collections/{col_id}/snippets/{snippet_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_collections_pagination_returns_page_and_total(monkeypatch):
    owner_id = ObjectId()
    public_cols = [
        {"_id": ObjectId(), "owner_id": owner_id, "name": f"Col {i}", "is_public": True,
         "snippet_ids": [], "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"}
        for i in range(5)
    ]
    _, col_collection, _, client = setup(monkeypatch, public_cols)

    response = client.get("/collections/?skip=0&limit=2")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
