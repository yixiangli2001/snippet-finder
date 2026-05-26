import re
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import collections_collection, snippets_collection, users_collection
from models.user import UserInDB, UserResponse
from routers.auth import format_user
from routers.collections import format_collection
from routers.snippets import format_snippet
from utils.security import require_admin


class AdminUserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(_: UserInDB = Depends(require_admin)):
    users = await users_collection.find({}).to_list(1000)
    return [format_user(u) for u in users]


@router.get("/snippets")
async def list_snippets(_: UserInDB = Depends(require_admin)):
    snippets = await snippets_collection.find({}).sort("created_at", -1).to_list(1000)
    return [format_snippet(s) for s in snippets]


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    _: UserInDB = Depends(require_admin),
):
    """Update a user's username or email. Rejects duplicates."""
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    user = await users_collection.find_one({"_id": object_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates: dict = {}

    if body.username is not None:
        existing = await users_collection.find_one({
            "username": {"$regex": f"^{re.escape(body.username)}$", "$options": "i"}
        })
        if existing and str(existing["_id"]) != user_id:
            raise HTTPException(status_code=409, detail="Username already exists")
        updates["username"] = body.username

    if body.email is not None:
        existing = await users_collection.find_one({"email": body.email})
        if existing and str(existing["_id"]) != user_id:
            raise HTTPException(status_code=409, detail="Email already exists")
        updates["email"] = body.email

    if not updates:
        return format_user(user)

    updates["updated_at"] = datetime.now(timezone.utc)
    updated = await users_collection.find_one_and_update(
        {"_id": object_id},
        {"$set": updates},
        return_document=True,
    )
    return format_user(updated)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, _: UserInDB = Depends(require_admin)):
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    user = await users_collection.find_one({"_id": object_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await snippets_collection.delete_many({"owner_id": object_id, "is_public": False})
    await snippets_collection.update_many(
        {"owner_id": object_id, "is_public": True},
        {"$set": {"owner_id": None, "updated_at": datetime.now(timezone.utc)}},
    )
    await collections_collection.delete_many({"owner_id": object_id, "is_public": False})
    await collections_collection.update_many(
        {"owner_id": object_id, "is_public": True},
        {"$set": {"owner_id": None, "updated_at": datetime.now(timezone.utc)}},
    )
    await users_collection.find_one_and_delete({"_id": object_id})

    return {"message": "User deleted"}


@router.get("/collections")
async def list_collections(_: UserInDB = Depends(require_admin)):
    cols = await collections_collection.find({}).sort("created_at", -1).to_list(1000)
    return [format_collection(c) for c in cols]


@router.delete("/collections/{collection_id}")
async def delete_collection(collection_id: str, _: UserInDB = Depends(require_admin)):
    try:
        object_id = ObjectId(collection_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid collection id")

    result = await collections_collection.find_one_and_delete({"_id": object_id})
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {"message": "Collection deleted"}


@router.delete("/snippets/{snippet_id}")
async def delete_snippet(snippet_id: str, _: UserInDB = Depends(require_admin)):
    try:
        object_id = ObjectId(snippet_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid snippet id")

    result = await snippets_collection.find_one_and_delete({"_id": object_id})
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")

    await collections_collection.update_many(
        {"snippet_ids": object_id},
        {"$pull": {"snippet_ids": object_id}},
    )

    return {"message": "Snippet deleted"}
