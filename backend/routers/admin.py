from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import snippets_collection, users_collection
from models.user import UserInDB, UserResponse
from routers.auth import format_user
from routers.snippets import format_snippet
from utils.security import require_admin

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(_: UserInDB = Depends(require_admin)):
    users = await users_collection.find({}).to_list(1000)
    return [format_user(u) for u in users]


@router.get("/snippets")
async def list_snippets(_: UserInDB = Depends(require_admin)):
    snippets = await snippets_collection.find({}).sort("created_at", -1).to_list(1000)
    return [format_snippet(s) for s in snippets]


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
    await users_collection.find_one_and_delete({"_id": object_id})

    return {"message": "User deleted"}


@router.delete("/snippets/{snippet_id}")
async def delete_snippet(snippet_id: str, _: UserInDB = Depends(require_admin)):
    try:
        object_id = ObjectId(snippet_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid snippet id")

    result = await snippets_collection.find_one_and_delete({"_id": object_id})
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")

    return {"message": "Snippet deleted"}
