from datetime import datetime, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

import routers.snippets as snippets_router
import utils.security as security
import utils.user_lookup as user_lookup
from main import app
from tests.fakes import FakeCollection
from utils.security import create_token, hash_password


def make_user(email: str, username: str):
    return {
        "_id": ObjectId(),
        "email": email,
        "username": username,
        "password_hash": hash_password("securepass"),
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


def auth_header(user):
    token = create_token(str(user["_id"]), user["role"])
    return {"Authorization": f"Bearer {token}"}


def use_fake_data(monkeypatch, snippets=None, user_documents=None):
    if user_documents is None:
        user_documents = [
            make_user("alice@example.com", "alice"),
            make_user("bob@example.com", "bob"),
        ]
    users = FakeCollection(user_documents)
    snippet_collection = FakeCollection(snippets or [])
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(snippets_router, "snippets_collection", snippet_collection)
    monkeypatch.setattr(user_lookup, "users_collection", users)
    return user_documents[0], user_documents[1], snippet_collection


def snippet(title, owner_id=None, is_public=False):
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
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


def test_logged_out_users_see_public_and_legacy_snippets(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    public = snippet("public", owner_id=alice["_id"], is_public=True)
    private = snippet("private", owner_id=alice["_id"], is_public=False)
    legacy = snippet("legacy")
    del legacy["owner_id"]
    del legacy["is_public"]
    use_fake_data(monkeypatch, [public, private, legacy], [alice, make_user("bob@example.com", "bob")])
    client = TestClient(app)

    response = client.get("/snippets/")

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"public", "legacy"}


def test_logged_in_user_sees_own_private_snippets(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    own_private = snippet("own private", owner_id=alice["_id"], is_public=False)
    other_private = snippet("other private", owner_id=bob["_id"], is_public=False)
    use_fake_data(monkeypatch, [own_private, other_private], [alice, bob])
    client = TestClient(app)

    response = client.get("/snippets/", headers=auth_header(alice))

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["own private"]


def test_create_snippet_requires_login(monkeypatch):
    use_fake_data(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/snippets/",
        json={"title": "secret", "language": "python", "code": "print('hi')", "tags": []},
    )

    assert response.status_code == 401


def test_create_snippet_sets_owner_and_private_visibility(monkeypatch):
    alice, _, _ = use_fake_data(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/snippets/",
        json={"title": "secret", "language": "python", "code": "print('hi')", "tags": []},
        headers=auth_header(alice),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["owner_id"] == str(alice["_id"])
    assert body["is_public"] is False


def test_non_owner_cannot_update_snippet(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    private = snippet("secret", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [private], [alice, bob])
    client = TestClient(app)

    response = client.put(
        f"/snippets/{private['_id']}",
        json={"title": "stolen"},
        headers=auth_header(bob),
    )

    assert response.status_code == 403


def test_owner_can_update_snippet(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    private = snippet("secret", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [private], [alice, make_user("bob@example.com", "bob")])
    client = TestClient(app)

    response = client.put(
        f"/snippets/{private['_id']}",
        json={"title": "updated"},
        headers=auth_header(alice),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "updated"


def test_owner_can_toggle_visibility(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    private = snippet("secret", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [private], [alice, make_user("bob@example.com", "bob")])
    client = TestClient(app)

    response = client.patch(
        f"/snippets/{private['_id']}/visibility",
        headers=auth_header(alice),
    )

    assert response.status_code == 200
    assert response.json()["is_public"] is True
