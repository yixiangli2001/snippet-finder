import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as bcrypt_lib
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from database import users_collection
from models.user import UserInDB
from utils.password_rules import MAX_BCRYPT_PASSWORD_BYTES

# --- Configuration ---

load_dotenv()

MIN_SECRET_KEY_LENGTH = 32
def get_required_secret_key() -> str:
    """Return the JWT secret key, or fail fast if it is unsafe."""
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key or len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(
            f"SECRET_KEY must be set and at least {MIN_SECRET_KEY_LENGTH} characters long"
        )
    return secret_key


SECRET_KEY = get_required_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# --- Password hashing ---


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plain-text password.

    bcrypt.gensalt() generates a fresh random salt on every call, which means
    two hashes of the same password are always different — defeating rainbow tables.
    """
    if len(plain.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_BCRYPT_PASSWORD_BYTES} bytes")

    salt = bcrypt_lib.gensalt()
    return bcrypt_lib.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash, False otherwise.

    bcrypt.checkpw re-hashes the plain password using the salt embedded in
    the stored hash, then compares — the original plain text is never stored.
    """
    return bcrypt_lib.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# --- JWT utilities ---

# oauth2_scheme extracts the Bearer token from the Authorization header.
# auto_error=True (default) raises 401 automatically if the header is missing.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Same extractor but auto_error=False returns None instead of raising 401,
# allowing routes that work both with and without authentication.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def create_token(user_id: str, role: str) -> str:
    """Create a signed JWT containing the user's id, role, and expiry."""
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises 401 if the token is invalid or expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# --- FastAPI dependencies ---

async def _fetch_user_from_token(token: str) -> UserInDB:
    """Decode a token and load the matching user from the database.

    Shared by get_current_user and get_optional_user to avoid duplication.
    Raises 401 if the token is invalid, the payload is malformed, or the
    user no longer exists in the database.
    """
    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    raw = await users_collection.find_one({"_id": object_id})
    if raw is None:
        # User was deleted after the token was issued
        raise HTTPException(status_code=401, detail="User no longer exists")

    return UserInDB(**raw)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Dependency for routes that require authentication.

    Raises 401 if no token is provided or the token is invalid.
    """
    return await _fetch_user_from_token(token)


async def get_optional_user(
    token: Optional[str] = Depends(optional_oauth2_scheme),
) -> Optional[UserInDB]:
    """Dependency for routes that work with or without authentication.

    Returns None for unauthenticated requests instead of raising 401.
    """
    if token is None:
        return None
    return await _fetch_user_from_token(token)


def require_admin(user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Dependency for admin-only routes.

    Raises 403 if the authenticated user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
