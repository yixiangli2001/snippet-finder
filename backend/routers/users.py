import re
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import collections_collection, snippets_collection, users_collection
from models.user import UpdateEmail, UpdatePassword, UpdateUsername, UserInDB, PublicUserResponse, UserResponse
from routers.auth import format_user
from utils.security import get_current_user, hash_password, verify_password

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    return format_user(current_user.model_dump(by_alias=True))


@router.put("/me/username", response_model=UserResponse)
async def update_username(
    update: UpdateUsername,
    current_user: UserInDB = Depends(get_current_user),
):
    existing = await users_collection.find_one(
        {"username": {"$regex": f"^{re.escape(update.username)}$", "$options": "i"}}
    )
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


@router.get("/{username}", response_model=PublicUserResponse)
async def get_user_profile(username: str):
    """Return the public profile for a user. No auth required."""
    user = await users_collection.find_one(
        {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": str(user["_id"]), "username": user["username"]}


@router.delete("/me")
async def delete_account(current_user: UserInDB = Depends(get_current_user)):
    user_id = ObjectId(current_user.id)

    await snippets_collection.delete_many({
        "owner_id": user_id,
        "is_public": False,
    })
    await snippets_collection.update_many(
        {
            "owner_id": user_id,
            "is_public": True,
        },
        {"$set": {
            "owner_id": None,
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    await collections_collection.delete_many({
        "owner_id": user_id,
        "is_public": False,
    })
    await collections_collection.update_many(
        {
            "owner_id": user_id,
            "is_public": True,
        },
        {"$set": {
            "owner_id": None,
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    await users_collection.find_one_and_delete({"_id": user_id})

    return {"message": "Account deleted"}
