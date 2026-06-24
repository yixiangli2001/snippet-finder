from datetime import datetime, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

import routers.snippets as snippets_router
import utils.security as security
import utils.user_lookup as user_lookup
from main import app
from tests.fakes import FakeCollection
from utils.security import create_token, hash_password


def make_user(email: str, username: str, role: str = "user"):
    return {
        "_id": ObjectId(),
        "email": email,
        "username": username,
        "password_hash": hash_password("securepass"),
        "role": role,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


def auth_header(user):
    token = create_token(str(user["_id"]), user["role"])
    return {"Authorization": f"Bearer {token}"}


def use_fake_data(monkeypatch, snippets=None, user_documents=None, collections=None):
    if user_documents is None:
        user_documents = [
            make_user("alice@example.com", "alice"),
            make_user("bob@example.com", "bob"),
        ]
    users = FakeCollection(user_documents)
    snippet_collection = FakeCollection(snippets or [])
    collection_collection = FakeCollection(collections or [])
    monkeypatch.setattr(security, "users_collection", users)
    monkeypatch.setattr(snippets_router, "snippets_collection", snippet_collection)
    monkeypatch.setattr(snippets_router, "collections_collection", collection_collection)
    monkeypatch.setattr(user_lookup, "users_collection", users)
    return user_documents[0], user_documents[1], snippet_collection, collection_collection


def snippet(title, owner_id=None, is_public=False, language="python"):
    return {
        "_id": ObjectId(),
        "owner_id": owner_id,
        "title": title,
        "language": language,
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
    titles = {item["title"] for item in response.json()["items"]}
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
    assert [item["title"] for item in response.json()["items"]] == ["own private"]


def test_admin_sees_all_private_snippets(monkeypatch):
    admin = make_user("admin@example.com", "admin", role="admin")
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    alice_private = snippet("alice private", owner_id=alice["_id"], is_public=False)
    bob_private = snippet("bob private", owner_id=bob["_id"], is_public=False)
    public = snippet("public", owner_id=alice["_id"], is_public=True)
    use_fake_data(monkeypatch, [alice_private, bob_private, public], [admin, alice, bob])
    client = TestClient(app)

    response = client.get("/snippets/", headers=auth_header(admin))

    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {"alice private", "bob private", "public"}


def test_get_public_snippet_by_id_without_login(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    public = snippet("public", owner_id=alice["_id"], is_public=True)
    use_fake_data(monkeypatch, [public], [alice, make_user("bob@example.com", "bob")])
    client = TestClient(app)

    response = client.get(f"/snippets/{public['_id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "public"


def test_owner_can_get_private_snippet_by_id(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    private = snippet("private", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [private], [alice, make_user("bob@example.com", "bob")])
    client = TestClient(app)

    response = client.get(f"/snippets/{private['_id']}", headers=auth_header(alice))

    assert response.status_code == 200
    assert response.json()["title"] == "private"


def test_non_owner_cannot_get_private_snippet_by_id(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    private = snippet("private", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [private], [alice, bob])
    client = TestClient(app)

    response = client.get(f"/snippets/{private['_id']}", headers=auth_header(bob))

    assert response.status_code == 404


def test_create_snippet_requires_login(monkeypatch):
    use_fake_data(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/snippets/",
        json={"title": "secret", "language": "python", "code": "print('hi')", "tags": []},
    )

    assert response.status_code == 401


def test_create_snippet_sets_owner_and_private_visibility(monkeypatch):
    alice, _, _, _ = use_fake_data(monkeypatch)
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


def test_owner_delete_snippet_removes_it_from_collections(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    snippet_to_delete = snippet("delete me", owner_id=alice["_id"], is_public=False)
    collection = {
        "_id": ObjectId(),
        "owner_id": alice["_id"],
        "name": "My collection",
        "description": None,
        "snippet_ids": [snippet_to_delete["_id"], ObjectId()],
        "is_public": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    _, _, _, collections = use_fake_data(
        monkeypatch,
        [snippet_to_delete],
        [alice, make_user("bob@example.com", "bob")],
        [collection],
    )
    client = TestClient(app)

    response = client.delete(
        f"/snippets/{snippet_to_delete['_id']}",
        headers=auth_header(alice),
    )

    assert response.status_code == 200
    assert snippet_to_delete["_id"] not in collections.documents[0]["snippet_ids"]


def test_owner_id_filter_returns_only_public_snippets_of_that_user(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    alice_public = snippet("alice public", owner_id=alice["_id"], is_public=True)
    alice_private = snippet("alice private", owner_id=alice["_id"], is_public=False)
    bob_public = snippet("bob public", owner_id=bob["_id"], is_public=True)
    use_fake_data(monkeypatch, [alice_public, alice_private, bob_public], [alice, bob])
    client = TestClient(app)

    response = client.get(f"/snippets/?owner_id={alice['_id']}")

    assert response.status_code == 200
    titles = [s["title"] for s in response.json()["items"]]
    assert titles == ["alice public"]


def test_owner_sees_own_private_snippets_via_profile_filter(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    alice_public = snippet("alice public", owner_id=alice["_id"], is_public=True)
    alice_private = snippet("alice private", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [alice_public, alice_private], [alice, bob])
    client = TestClient(app)

    response = client.get(f"/snippets/?owner_id={alice['_id']}", headers=auth_header(alice))

    assert response.status_code == 200
    titles = {s["title"] for s in response.json()["items"]}
    assert titles == {"alice public", "alice private"}


def test_admin_sees_private_snippets_via_profile_filter(monkeypatch):
    admin = make_user("admin@example.com", "admin", role="admin")
    alice = make_user("alice@example.com", "alice")
    alice_public = snippet("alice public", owner_id=alice["_id"], is_public=True)
    alice_private = snippet("alice private", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [alice_public, alice_private], [admin, alice])
    client = TestClient(app)

    response = client.get(f"/snippets/?owner_id={alice['_id']}", headers=auth_header(admin))

    assert response.status_code == 200
    titles = {s["title"] for s in response.json()["items"]}
    assert titles == {"alice public", "alice private"}


def test_owner_can_filter_their_list_to_private_only(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    alice_public = snippet("alice public", owner_id=alice["_id"], is_public=True)
    alice_private = snippet("alice private", owner_id=alice["_id"], is_public=False)
    use_fake_data(monkeypatch, [alice_public, alice_private], [alice, bob])
    client = TestClient(app)

    response = client.get(
        f"/snippets/?owner_id={alice['_id']}&is_public=false",
        headers=auth_header(alice),
    )

    assert response.status_code == 200
    titles = [s["title"] for s in response.json()["items"]]
    assert titles == ["alice private"]


def test_public_filter_excludes_own_private_snippets(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    alice_private = snippet("alice private", owner_id=alice["_id"], is_public=False)
    alice_public = snippet("alice public", owner_id=alice["_id"], is_public=True)
    bob_public = snippet("bob public", owner_id=bob["_id"], is_public=True)
    use_fake_data(monkeypatch, [alice_private, alice_public, bob_public], [alice, bob])
    client = TestClient(app)

    response = client.get("/snippets/?is_public=true", headers=auth_header(alice))

    assert response.status_code == 200
    titles = {s["title"] for s in response.json()["items"]}
    assert titles == {"alice public", "bob public"}


def test_private_filter_does_not_leak_other_users_private_snippets(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    bob_private = snippet("bob private", owner_id=bob["_id"], is_public=False)
    use_fake_data(monkeypatch, [bob_private], [alice, bob])
    client = TestClient(app)

    response = client.get(
        f"/snippets/?owner_id={bob['_id']}&is_public=false",
        headers=auth_header(alice),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_owner_id_filter_rejects_invalid_owner_id(monkeypatch):
    use_fake_data(monkeypatch)
    client = TestClient(app)

    response = client.get("/snippets/?owner_id=not-an-id")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid owner id"


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


def test_languages_returns_distinct_languages_for_visible_snippets(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    bob = make_user("bob@example.com", "bob")
    use_fake_data(monkeypatch, [
        snippet("pub py",   owner_id=alice["_id"], is_public=True,  language="python"),
        snippet("priv js",  owner_id=alice["_id"], is_public=False, language="javascript"),
        snippet("pub sql",  owner_id=bob["_id"],   is_public=True,  language="sql"),
        snippet("priv go",  owner_id=bob["_id"],   is_public=False, language="go"),
    ], [alice, bob])
    client = TestClient(app)

    # Unauthenticated: only public snippet languages
    response = client.get("/snippets/languages")
    assert response.status_code == 200
    assert response.json() == ["python", "sql"]

    # Alice: adds her own private snippet's language
    response = client.get("/snippets/languages", headers=auth_header(alice))
    assert response.json() == ["javascript", "python", "sql"]


def test_languages_admin_sees_all(monkeypatch):
    admin = make_user("admin@example.com", "admin", role="admin")
    alice = make_user("alice@example.com", "alice")
    use_fake_data(monkeypatch, [
        snippet("pub",  owner_id=alice["_id"], is_public=True,  language="python"),
        snippet("priv", owner_id=alice["_id"], is_public=False, language="rust"),
    ], [admin, alice])
    client = TestClient(app)

    response = client.get("/snippets/languages", headers=auth_header(admin))
    assert response.json() == ["python", "rust"]


def test_snippets_pagination_returns_page_and_total(monkeypatch):
    alice = make_user("alice@example.com", "alice")
    public_snippets = [snippet(f"s{i}", owner_id=alice["_id"], is_public=True) for i in range(7)]
    use_fake_data(monkeypatch, public_snippets, [alice, make_user("bob@example.com", "bob")])
    client = TestClient(app)

    response = client.get("/snippets/?skip=0&limit=3")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 7
    assert len(body["items"]) == 3

    response2 = client.get("/snippets/?skip=3&limit=3")
    body2 = response2.json()
    assert body2["total"] == 7
    assert len(body2["items"]) == 3
