from bson import ObjectId
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
import re

from database import collections_collection, snippets_collection
from models.snippet import SnippetCreate, SnippetUpdate, SnippetResponse
from models.user import UserInDB
from utils.security import get_current_user, get_optional_user
from utils.user_lookup import build_username_map, get_owner_username

router = APIRouter()


def format_snippet(snippet: dict, owner_username: str | None = None) -> dict:
    formatted = {**snippet, "id": str(snippet["_id"])}
    del formatted["_id"]
    if formatted.get("owner_id") is not None:
        formatted["owner_id"] = str(formatted["owner_id"])
    formatted.setdefault("owner_id", None)
    formatted.setdefault("is_public", True)
    formatted["owner_username"] = owner_username
    return formatted


def parse_object_id(value: str, label: str = "snippet id") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail=f"Invalid {label}")
    return ObjectId(value)


def owned_by_user(snippet: dict, user: UserInDB) -> bool:
    return snippet.get("owner_id") == ObjectId(user.id)


def can_change_snippet(snippet: dict, user: UserInDB) -> bool:
    return user.role == "admin" or owned_by_user(snippet, user)


def can_view_snippet(snippet: dict, user: UserInDB | None) -> bool:
    is_public = snippet.get("is_public", True)
    is_owner = user and owned_by_user(snippet, user)
    is_admin = user and user.role == "admin"
    return is_public or bool(is_owner) or bool(is_admin)


async def get_snippet_for_change(snippet_id: str, user: UserInDB) -> dict:
    object_id = parse_object_id(snippet_id)
    snippet = await snippets_collection.find_one({"_id": object_id})
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    if not can_change_snippet(snippet, user):
        raise HTTPException(status_code=403, detail="You can only change your own snippets")
    return snippet


@router.get("/", response_model=list[SnippetResponse])
async def get_snippets(
    search: str | None = None,
    language: str | None = None,
    owner_id: str | None = None,
    current_user: UserInDB | None = Depends(get_optional_user),
):
    filters = []
    if owner_id:
        # Profile page: show only the public snippets of a specific user.
        filters.append({"owner_id": parse_object_id(owner_id, "owner id"), "is_public": True})
    elif current_user and current_user.role == "admin":
        # Admins see everything, no visibility filter applied.
        pass
    elif current_user:
        filters.append({
            "$or": [
                {"is_public": True},
                {"is_public": {"$exists": False}},
                {"owner_id": ObjectId(current_user.id)},
            ]
        })
    else:
        filters.append({
            "$or": [
                {"is_public": True},
                {"is_public": {"$exists": False}},
            ]
        })

    if search:
        escaped_search = re.escape(search)
        filters.append({"$or": [
            {"title": {"$regex": escaped_search, "$options": "i"}},
            {"code": {"$regex": escaped_search, "$options": "i"}},
            {"description": {"$regex": escaped_search, "$options": "i"}},
            {"tags": {"$regex": escaped_search, "$options": "i"}}
        ]})
    if language:
        filters.append({"language": language})

    if not filters:
        query = {}
    elif len(filters) == 1:
        query = filters[0]
    else:
        query = {"$and": filters}
    snippets = await snippets_collection.find(query).sort("created_at", -1).to_list(100)
    username_map = await build_username_map(snippets)
    return [format_snippet(s, username_map.get(s.get("owner_id"))) for s in snippets]


@router.get("/{snippet_id}", response_model=SnippetResponse)
async def get_snippet(
    snippet_id: str,
    current_user: UserInDB | None = Depends(get_optional_user),
):
    object_id = parse_object_id(snippet_id)
    snippet = await snippets_collection.find_one({"_id": object_id})
    if not snippet or not can_view_snippet(snippet, current_user):
        raise HTTPException(status_code=404, detail="Snippet not found")

    username = await get_owner_username(snippet.get("owner_id"))
    return format_snippet(snippet, username)


@router.post("/", response_model=SnippetResponse)
async def create_snippet(
    snippet: SnippetCreate,
    current_user: UserInDB = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    data = snippet.model_dump()
    data["owner_id"] = ObjectId(current_user.id)
    data["is_public"] = False
    data["times_copied"] = 0
    data["created_at"] = now
    data["updated_at"] = now

    result = await snippets_collection.insert_one(data)
    created = await snippets_collection.find_one({"_id": result.inserted_id})
    if not created:
        raise HTTPException(status_code=500, detail="Snippet was not saved")
    return format_snippet(created, current_user.username)


@router.put("/{snippet_id}", response_model=SnippetResponse)
async def update_snippet(
    snippet_id: str,
    snippet: SnippetUpdate,
    current_user: UserInDB = Depends(get_current_user),
):
    existing = await get_snippet_for_change(snippet_id, current_user)
    data = {k: v for k, v in snippet.model_dump().items() if v is not None}
    data["updated_at"] = datetime.now(timezone.utc)

    result = await snippets_collection.find_one_and_update(
        {"_id": existing["_id"]},
        {"$set": data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")
    username = await get_owner_username(result.get("owner_id"))
    return format_snippet(result, username)


@router.delete("/{snippet_id}")
async def delete_snippet(
    snippet_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    existing = await get_snippet_for_change(snippet_id, current_user)
    result = await snippets_collection.find_one_and_delete(
        {"_id": existing["_id"]}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")

    await collections_collection.update_many(
        {"snippet_ids": existing["_id"]},
        {"$pull": {"snippet_ids": existing["_id"]}},
    )
    return {"message": "Snippet deleted"}


@router.patch("/{snippet_id}/copy")
async def increment_copy(snippet_id: str):
    object_id = parse_object_id(snippet_id)
    result = await snippets_collection.update_one(
        {"_id": object_id},
        {"$inc": {"times_copied": 1}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return {"message": "Copy count updated"}


@router.patch("/{snippet_id}/visibility", response_model=SnippetResponse)
async def toggle_visibility(
    snippet_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    existing = await get_snippet_for_change(snippet_id, current_user)
    result = await snippets_collection.find_one_and_update(
        {"_id": existing["_id"]},
        {"$set": {
            "is_public": not existing.get("is_public", True),
            "updated_at": datetime.now(timezone.utc),
        }},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")
    username = await get_owner_username(result.get("owner_id"))
    return format_snippet(result, username)
