from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
        if len(stripped_password) < 8:
            raise ValueError("password must be at least 8 characters")
        return password


class UserResponse(BaseModel):
    """API response model. Safe to send to clients — contains no password data."""

    id: str
    email: str
    username: str
    role: str = "user"
    created_at: datetime
    updated_at: datetime


class UserInDB(BaseModel):
    """Internal model representing a full DB record. Never serialised directly into a response."""

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: str | ObjectId = Field(alias="_id")
    email: str
    username: str
    password_hash: str
    role: str = "user"
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_mongo_id_to_string(cls, mongo_id: object) -> str:
        return str(mongo_id)
