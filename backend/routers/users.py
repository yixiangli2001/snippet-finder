from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from database import users_collection
from models.user import UserInDB, UserResponse
from routers.auth import format_user
from utils.password_rules import MAX_BCRYPT_PASSWORD_BYTES, MIN_PASSWORD_CHARACTERS
from utils.security import get_current_user, hash_password, verify_password

router = APIRouter()


class UpdateUsername(BaseModel):
    username: str

    @field_validator("username")
    @classmethod
    def username_must_not_be_empty(cls, username: str) -> str:
        stripped_username = username.strip()
        if not stripped_username:
            raise ValueError("username must not be empty")
        return stripped_username


class UpdateEmail(BaseModel):
    email: EmailStr


class UpdatePassword(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_must_be_useful(cls, password: str) -> str:
        stripped_password = password.strip()
        if not stripped_password:
            raise ValueError("password must not be empty")
        if len(stripped_password) < MIN_PASSWORD_CHARACTERS:
            raise ValueError(f"password must be at least {MIN_PASSWORD_CHARACTERS} characters")
        if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError(f"password must be at most {MAX_BCRYPT_PASSWORD_BYTES} bytes")
        return password


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    return format_user(current_user.model_dump(by_alias=True))


@router.put("/me/username", response_model=UserResponse)
async def update_username(
    update: UpdateUsername,
    current_user: UserInDB = Depends(get_current_user),
):
    existing = await users_collection.find_one({"username": update.username})
    if existing and str(existing["_id"]) != current_user.id:
        raise HTTPException(status_code=409, detail="Username already exists")

    updated = await users_collection.find_one_and_update(
        {"_id": ObjectId(current_user.id)},
        {"$set": {
            "username": update.username,
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True,
    )
    return format_user(updated)


@router.put("/me/password")
async def update_password(
    update: UpdatePassword,
    current_user: UserInDB = Depends(get_current_user),
):
    if not verify_password(update.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    await users_collection.find_one_and_update(
        {"_id": ObjectId(current_user.id)},
        {"$set": {
            "password_hash": hash_password(update.new_password),
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True,
    )
    return {"message": "Password updated"}


@router.put("/me/email", response_model=UserResponse)
async def update_email(
    update: UpdateEmail,
    current_user: UserInDB = Depends(get_current_user),
):
    existing = await users_collection.find_one({"email": update.email})
    if existing and str(existing["_id"]) != current_user.id:
        raise HTTPException(status_code=409, detail="Email already exists")

    updated = await users_collection.find_one_and_update(
        {"_id": ObjectId(current_user.id)},
        {"$set": {
            "email": update.email,
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True,
    )
    return format_user(updated)
