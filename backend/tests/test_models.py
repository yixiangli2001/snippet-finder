from datetime import datetime, timezone

from bson import ObjectId
import pytest
from pydantic import ValidationError

from models.collection import CollectionCreate, CollectionResponse, CollectionUpdate
from models.snippet import SnippetResponse
from models.user import UserCreate, UserResponse, UserInDB


# --- UserCreate ---

def test_user_create_accepts_valid_input():
    user = UserCreate(username="alice", email="alice@example.com", password="securepass")
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.password == "securepass"


def test_user_create_rejects_missing_username():
    with pytest.raises(ValidationError):
        UserCreate(email="alice@example.com", password="securepass")


def test_user_create_rejects_missing_email():
    with pytest.raises(ValidationError):
        UserCreate(username="alice", password="securepass")


def test_user_create_rejects_missing_password():
    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="alice@example.com")


def test_user_create_rejects_empty_username():
    with pytest.raises(ValidationError):
        UserCreate(username="", email="alice@example.com", password="securepass")


def test_user_create_rejects_whitespace_only_username():
    with pytest.raises(ValidationError):
        UserCreate(username="   ", email="alice@example.com", password="securepass")


def test_user_create_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="not-an-email", password="securepass")


def test_user_create_rejects_short_password():
    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="alice@example.com", password="short")


def test_user_create_rejects_whitespace_only_password():
    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="alice@example.com", password="        ")


def test_user_create_rejects_password_too_long_for_bcrypt():
    with pytest.raises(ValidationError):
        UserCreate(username="alice", email="alice@example.com", password="a" * 73)


# --- UserResponse ---

def test_user_response_contains_only_safe_public_fields():
    now = datetime.now(timezone.utc)
    user = UserResponse(
        id="507f1f77bcf86cd799439011",
        email="alice@example.com",
        username="alice",
        created_at=now,
        updated_at=now,
    )

    assert user.model_dump() == {
        "id": "507f1f77bcf86cd799439011",
        "email": "alice@example.com",
        "username": "alice",
        "role": "user",
        "created_at": now,
        "updated_at": now,
    }


# --- UserInDB ---

def test_user_in_db_accepts_mongo_record_shape():
    now = datetime.now(timezone.utc)
    user_id = ObjectId()
    user = UserInDB(
        _id=user_id,
        email="alice@example.com",
        username="alice",
        password_hash="hashed-password",
        created_at=now,
        updated_at=now,
    )

    assert user.id == str(user_id)
    assert user.password_hash == "hashed-password"
    assert user.role == "user"


# --- CollectionCreate ---

def test_collection_create_accepts_valid_input():
    col = CollectionCreate(name="My snippets")
    assert col.name == "My snippets"
    assert col.description is None


def test_collection_create_accepts_optional_description():
    col = CollectionCreate(name="My snippets", description="A handy collection")
    assert col.description == "A handy collection"


def test_collection_create_strips_whitespace_from_name():
    col = CollectionCreate(name="  My snippets  ")
    assert col.name == "My snippets"


def test_collection_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        CollectionCreate(name="")


def test_collection_create_rejects_whitespace_only_name():
    with pytest.raises(ValidationError):
        CollectionCreate(name="   ")


# --- CollectionUpdate ---

def test_collection_update_allows_all_fields_optional():
    update = CollectionUpdate()
    assert update.name is None
    assert update.description is None
    assert update.is_public is None


def test_collection_update_rejects_empty_name():
    with pytest.raises(ValidationError):
        CollectionUpdate(name="")


# --- CollectionResponse ---

def test_collection_response_contains_expected_fields():
    now = datetime.now(timezone.utc)
    col = CollectionResponse(
        id="507f1f77bcf86cd799439011",
        owner_id="507f1f77bcf86cd799439012",
        name="My snippets",
        snippet_ids=[],
        is_public=False,
        created_at=now,
        updated_at=now,
    )
    assert col.id == "507f1f77bcf86cd799439011"
    assert col.is_public is False
    assert col.snippet_ids == []
    assert col.description is None


# --- SnippetResponse ---

def test_snippet_response_defaults_to_public_legacy_snippet():
    now = datetime.now(timezone.utc)
    snippet = SnippetResponse(
        id="507f1f77bcf86cd799439011",
        title="hello",
        language="python",
        code="print('hi')",
        created_at=now,
        updated_at=now,
    )

    assert snippet.owner_id is None
    assert snippet.is_public is True
