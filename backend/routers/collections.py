from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import collections_collection, snippets_collection
from models.collection import CollectionCreate, CollectionResponse, CollectionUpdate
from models.user import UserInDB
from utils.security import get_current_user, get_optional_user

router = APIRouter()


def format_collection(col: dict) -> dict:
    """Convert a MongoDB document to a client-safe dict (ObjectIds → strings)."""
    formatted = {**col, "id": str(col["_id"])}
    del formatted["_id"]
    formatted["owner_id"] = str(formatted["owner_id"])
    formatted["snippet_ids"] = [str(sid) for sid in formatted.get("snippet_ids", [])]
    return formatted


def parse_object_id(value: str, label: str = "id") -> ObjectId:
    """Convert a string to ObjectId, raising 400 if the format is invalid."""
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=400, detail=f"Invalid {label}")
    return ObjectId(value)


async def get_collection_for_change(collection_id: str, user: UserInDB) -> dict:
    """Fetch a collection and verify the user is the owner or an admin."""
    object_id = parse_object_id(collection_id, "collection id")
    col = await collections_collection.find_one({"_id": object_id})
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    is_owner = str(col["owner_id"]) == user.id
    if not is_owner and user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only change your own collections")
    return col


@router.get("/", response_model=list[CollectionResponse])
async def get_collections(
    current_user: UserInDB | None = Depends(get_optional_user),
):
    """Return public collections, plus the user's own private ones if logged in."""
    if current_user:
        query = {"$or": [{"is_public": True}, {"owner_id": ObjectId(current_user.id)}]}
    else:
        query = {"is_public": True}
    cols = await collections_collection.find(query).sort("created_at", -1).to_list(100)
    return [format_collection(c) for c in cols]


@router.post("/", response_model=CollectionResponse)
async def create_collection(
    body: CollectionCreate,
    current_user: UserInDB = Depends(get_current_user),
):
    """Create a collection owned by the current user. Private by default."""
    now = datetime.now(timezone.utc)
    data = {
        "owner_id": ObjectId(current_user.id),
        "name": body.name,
        "description": body.description,
        "snippet_ids": [],
        "is_public": False,
        "created_at": now,
        "updated_at": now,
    }
    result = await collections_collection.insert_one(data)
    created = await collections_collection.find_one({"_id": result.inserted_id})
    return format_collection(created)


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str,
    current_user: UserInDB | None = Depends(get_optional_user),
):
    """Return a collection. Private ones return 404 to non-owners (avoids leaking existence)."""
    object_id = parse_object_id(collection_id, "collection id")
    col = await collections_collection.find_one({"_id": object_id})
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    is_owner = current_user and str(col["owner_id"]) == current_user.id
    is_admin = current_user and current_user.role == "admin"
    if not col.get("is_public") and not is_owner and not is_admin:
        raise HTTPException(status_code=404, detail="Collection not found")

    return format_collection(col)


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    body: CollectionUpdate,
    current_user: UserInDB = Depends(get_current_user),
):
    """Update name, description, or visibility. Only provided fields are changed."""
    col = await get_collection_for_change(collection_id, current_user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return format_collection(col)

    updates["updated_at"] = datetime.now(timezone.utc)
    result = await collections_collection.find_one_and_update(
        {"_id": col["_id"]},
        {"$set": updates},
        return_document=True,
    )
    return format_collection(result)


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """Delete a collection. Does not delete the snippets inside it."""
    col = await get_collection_for_change(collection_id, current_user)
    await collections_collection.find_one_and_delete({"_id": col["_id"]})
    return {"message": "Collection deleted"}
