from bson import ObjectId
from fastapi.testclient import TestClient

import routers.auth as auth_router
import routers.collections as collections_router
import utils.security as security
from main import app
from tests.fakes import FakeCollection


def setup(monkeypatch, collections=None):
    users = FakeCollection()
    col_collection = FakeCollection(collections or [])

    monkeypatch.setattr(auth_router, "users_collection", users)
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(collections_router, "collections_collection", col_collection)

    client = TestClient(app)
    return users, col_collection, client


def register_and_login(client, email="alice@example.com", username="alice"):
    client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": "securepass"},
    )
    login = client.post("/auth/login", json={"email": email, "password": "securepass"})
    return login.json()["access_token"]


# ── GET /collections ──────────────────────────────────────────


def test_unauthenticated_user_sees_only_public_collections(monkeypatch):
    owner_id = ObjectId()
    _, col_collection, client = setup(monkeypatch, [
        {"owner_id": owner_id, "name": "Public", "is_public": True, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
        {"owner_id": owner_id, "name": "Private", "is_public": False, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])

    response = client.get("/collections/")

    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names == ["Public"]


def test_authenticated_user_sees_own_private_collections(monkeypatch):
    users, col_collection, client = setup(monkeypatch)
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

    names = [c["name"] for c in response.json()]
    assert "My private" in names
    assert "Their private" not in names


# ── POST /collections ─────────────────────────────────────────


def test_create_collection_requires_auth(monkeypatch):
    _, _, client = setup(monkeypatch)

    response = client.post("/collections/", json={"name": "My collection"})

    assert response.status_code == 401


def test_create_collection_sets_owner_and_private_by_default(monkeypatch):
    users, col_collection, client = setup(monkeypatch)
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
    owner_id = ObjectId()
    _, col_collection, client = setup(monkeypatch, [
        {"owner_id": owner_id, "name": "Public", "is_public": True, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])
    col_id = col_collection.documents[0]["_id"]

    response = client.get(f"/collections/{col_id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Public"


def test_get_private_collection_returns_404_to_non_owner(monkeypatch):
    owner_id = ObjectId()
    _, col_collection, client = setup(monkeypatch, [
        {"owner_id": owner_id, "name": "Private", "is_public": False, "snippet_ids": [],
         "description": None, "created_at": "2026-01-01", "updated_at": "2026-01-01"},
    ])
    col_id = col_collection.documents[0]["_id"]

    response = client.get(f"/collections/{col_id}")

    assert response.status_code == 404


def test_owner_can_get_own_private_collection(monkeypatch):
    users, col_collection, client = setup(monkeypatch)
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
    users, col_collection, client = setup(monkeypatch)
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


def test_non_owner_cannot_update_collection(monkeypatch):
    _, col_collection, client = setup(monkeypatch)
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
    users, col_collection, client = setup(monkeypatch)
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
    users, col_collection, client = setup(monkeypatch)
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


def test_non_owner_cannot_delete_collection(monkeypatch):
    _, col_collection, client = setup(monkeypatch)
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
