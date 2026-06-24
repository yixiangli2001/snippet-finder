from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from utils.password_rules import MAX_BCRYPT_PASSWORD_BYTES, MIN_PASSWORD_CHARACTERS


class UserCreate(BaseModel):
    """Input model for registration. Contains raw password — never stored or returned."""

    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_must_not_be_empty(cls, username: str) -> str:
        stripped_username = username.strip()
        if not stripped_username:
            raise ValueError("username must not be empty")
        return stripped_username

    @field_validator("password")
    @classmethod
    def password_must_be_useful(cls, password: str) -> str:
        stripped_password = password.strip()
        if not stripped_password:
            raise ValueError("password must not be empty")
        if len(stripped_password) < MIN_PASSWORD_CHARACTERS:
            raise ValueError(f"password must be at least {MIN_PASSWORD_CHARACTERS} characters")
        if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError(f"password must be at most {MAX_BCRYPT_PASSWORD_BYTES} bytes")
        return password


class UpdateUsername(BaseModel):
    """Input model for changing the current user's username."""

    username: str

    @field_validator("username")
    @classmethod
    def username_must_not_be_empty(cls, username: str) -> str:
        stripped_username = username.strip()
        if not stripped_username:
            raise ValueError("username must not be empty")
        return stripped_username


class UpdateEmail(BaseModel):
    """Input model for changing the current user's email address."""

    email: EmailStr


def _validate_new_password(password: str) -> str:
    stripped_password = password.strip()
    if not stripped_password:
        raise ValueError("password must not be empty")
    if len(stripped_password) < MIN_PASSWORD_CHARACTERS:
        raise ValueError(f"password must be at least {MIN_PASSWORD_CHARACTERS} characters")
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_BCRYPT_PASSWORD_BYTES} bytes")
    return password


class UpdatePassword(BaseModel):
    """Input model for changing the current user's password."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_must_be_useful(cls, password: str) -> str:
        return _validate_new_password(password)


class ResetPasswordRequest(BaseModel):
    """Input model for completing a password reset via emailed token."""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_must_be_useful(cls, password: str) -> str:
        return _validate_new_password(password)


class UserResponse(BaseModel):
    """API response model. Safe to send to clients — contains no password data."""

    id: str
    email: str
    username: str
    role: str = "user"
    # Default True covers legacy accounts created before email verification
    # shipped — they never had a chance to verify, so they aren't punished.
    is_verified: bool = True
    created_at: datetime
    updated_at: datetime


class PublicUserResponse(BaseModel):
    """Minimal public profile returned on GET /users/{username}. No email."""

    id: str
    username: str


class UserInDB(BaseModel):
    """Internal model representing a full DB record. Never serialised directly into a response."""

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: str | ObjectId = Field(alias="_id")
    email: str
    username: str
    password_hash: str
    role: str = "user"
    is_verified: bool = True
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_mongo_id_to_string(cls, mongo_id: object) -> str:
        return str(mongo_id)
