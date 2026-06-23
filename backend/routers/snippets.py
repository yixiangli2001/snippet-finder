from bson import ObjectId
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAIError
import re

from database import collections_collection, snippets_collection
from models.ai import SnippetAnalyzeRequest, SnippetMetadata
from models.snippet import SnippetCreate, SnippetUpdate, SnippetResponse, SnippetListResponse
from models.user import UserInDB
from utils.ai import analyze_snippet
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


@router.get("/", response_model=SnippetListResponse)
async def get_snippets(
    search: str | None = None,
    language: str | None = None,
    owner_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
    current_user: UserInDB | None = Depends(get_optional_user),
):
    filters = []
    if owner_id:
        owner_obj_id = parse_object_id(owner_id, "owner id")
        is_own_profile = current_user and owner_obj_id == ObjectId(current_user.id)
        is_admin = current_user and current_user.role == "admin"
        if is_own_profile or is_admin:
            # Owner viewing their own profile, or admin: include private snippets.
            filters.append({"owner_id": owner_obj_id})
        else:
            # Anyone else: public snippets of that user only.
            filters.append({"owner_id": owner_obj_id, "is_public": True})
    elif current_user and current_user.role == "admin":
        # Admins see everything, no visibility filter applied.
        pass
    elif current_user:
        # Logged in users see all public snippets, plus their own private ones.
        filters.append({
            "$or": [
                {"is_public": True},
                {"is_public": {"$exists": False}},
                {"owner_id": ObjectId(current_user.id)},
            ]
        })
    else:
        # Not logged in: show only public snippets.
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
    total = await snippets_collection.count_documents(query)
    snippets = await snippets_collection.find(query).sort("created_at", -1).skip(skip).to_list(limit)
    username_map = await build_username_map(snippets)
    items = [format_snippet(s, username_map.get(s.get("owner_id"))) for s in snippets]
    return {"items": items, "total": total}


@router.get("/languages", response_model=list[str])
async def get_languages(
    current_user: UserInDB | None = Depends(get_optional_user),
):
    """Return sorted distinct languages across all snippets visible to the requester."""
    if current_user and current_user.role == "admin":
        query = {}
    elif current_user:
        query = {
            "$or": [
                {"is_public": True},
                {"is_public": {"$exists": False}},
                {"owner_id": ObjectId(current_user.id)},
            ]
        }
    else:
        query = {
            "$or": [
                {"is_public": True},
                {"is_public": {"$exists": False}},
            ]
        }
    languages = await snippets_collection.distinct("language", query)
    return sorted(languages)


@router.post("/analyze", response_model=SnippetMetadata)
async def analyze(
    payload: SnippetAnalyzeRequest,
    current_user: UserInDB = Depends(get_current_user),
):
    """Use the LLM to extract title/language/description/tags from pasted code.

    Auth is required because each call costs money — only logged-in users can
    spend it. The result is returned for the user to review and edit before
    saving; it is never persisted here.
    """
    try:
        return await analyze_snippet(payload.code)
    except RuntimeError as exc:
        # No API key configured, or the model returned nothing usable.
        raise HTTPException(status_code=503, detail=str(exc))
    except OpenAIError:
        # Network/quota/provider errors — let the user fall back to manual entry.
        raise HTTPException(status_code=502, detail="AI service is temporarily unavailable")


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
