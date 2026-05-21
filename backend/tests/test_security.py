from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from utils.security import (
    ALGORITHM,
    SECRET_KEY,
    create_token,
    decode_token,
    get_required_secret_key,
    hash_password,
    verify_password,
)


# --- Password hashing ---

def test_hash_password_output_is_not_plain_text():
    assert hash_password("hunter2") != "hunter2"


def test_hash_password_produces_different_hashes_for_same_input():
    # bcrypt generates a fresh random salt each time, so two hashes of the
    # same password must never be identical
    assert hash_password("hunter2") != hash_password("hunter2")


def test_verify_password_returns_true_for_correct_password():
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True


def test_verify_password_returns_false_for_wrong_password():
    hashed = hash_password("hunter2")
    assert verify_password("wrongpassword", hashed) is False


# --- Token creation ---

def test_create_token_returns_three_part_string():
    # A valid JWT is always header.payload.signature
    token = create_token("user123", "user")
    assert len(token.split(".")) == 3


def test_create_token_embeds_user_id_and_role():
    token = create_token("user123", "admin")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user123"
    assert payload["role"] == "admin"


def test_create_token_includes_expiry_claim():
    token = create_token("user123", "user")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


# --- Token decoding ---

def test_decode_token_returns_correct_sub_and_role():
    token = create_token("user456", "user")
    payload = decode_token(token)
    assert payload["sub"] == "user456"
    assert payload["role"] == "user"


def test_decode_token_raises_401_for_expired_token():
    expired_payload = {
        "sub": "user123",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(HTTPException) as exc:
        decode_token(expired_token)
    assert exc.value.status_code == 401


def test_decode_token_raises_401_for_tampered_payload():
    token = create_token("user123", "user")
    header, _, signature = token.split(".")
    # Swap in a different payload — signature will no longer match
    tampered = f"{header}.dGFtcGVyZWRwYXlsb2Fk.{signature}"

    with pytest.raises(HTTPException) as exc:
        decode_token(tampered)
    assert exc.value.status_code == 401


def test_decode_token_raises_401_for_completely_invalid_token():
    with pytest.raises(HTTPException) as exc:
        decode_token("this.is.garbage")
    assert exc.value.status_code == 401


# --- Configuration ---

def test_get_required_secret_key_rejects_missing_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        get_required_secret_key()


def test_get_required_secret_key_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "short")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        get_required_secret_key()
