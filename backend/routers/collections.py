from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from database import collections_collection, snippets_collection
from models.collection import AddSnippet, CollectionCreate, CollectionResponse, CollectionUpdate
from models.user import UserInDB
from utils.security import get_current_user, get_optional_user
from utils.user_lookup import build_username_map, get_owner_username

router = APIRouter()


def format_collection(col: dict, owner_username: str | None = None) -> dict:
    """Convert a MongoDB document to a client-safe dict (ObjectIds → strings)."""
    formatted = {**col, "id": str(col["_id"])}
    del formatted["_id"]
    if formatted.get("owner_id") is not None:
        formatted["owner_id"] = str(formatted["owner_id"])
    formatted.setdefault("owner_id", None)
    formatted["snippet_ids"] = [str(sid) for sid in formatted.get("snippet_ids", [])]
    formatted["owner_username"] = owner_username
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
    owner_id: str | None = None,
    current_user: UserInDB | None = Depends(get_optional_user),
):
    """Return public collections, plus the user's own private ones if logged in."""
    if owner_id:
        # Profile page: show only the public collections of a specific user.
        query = {"owner_id": parse_object_id(owner_id, "owner id"), "is_public": True}
    elif current_user:
        query = {"$or": [{"is_public": True}, {"owner_id": ObjectId(current_user.id)}]}
    else:
        query = {"is_public": True}
    cols = await collections_collection.find(query).sort("created_at", -1).to_list(100)
    username_map = await build_username_map(cols)
    return [format_collection(c, username_map.get(c.get("owner_id"))) for c in cols]


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
    if not created:
        raise HTTPException(status_code=500, detail="Collection was not saved")
    return format_collection(created, current_user.username)


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

    username = await get_owner_username(col.get("owner_id"))
    return format_collection(col, username)


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
        username = await get_owner_username(col.get("owner_id"))
        return format_collection(col, username)

    updates["updated_at"] = datetime.now(timezone.utc)
    result = await collections_collection.find_one_and_update(
        {"_id": col["_id"]},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found")
    username = await get_owner_username(result.get("owner_id"))
    return format_collection(result, username)


@router.post("/{collection_id}/snippets", response_model=CollectionResponse)
async def add_snippet_to_collection(
    collection_id: str,
    body: AddSnippet,
    current_user: UserInDB = Depends(get_current_user),
):
    """Add a snippet to a collection. The snippet must be visible to the user."""
    col = await get_collection_for_change(collection_id, current_user)

    snippet_object_id = parse_object_id(body.snippet_id, "snippet id")
    snippet = await snippets_collection.find_one({"_id": snippet_object_id})
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    # Users can only add snippets they are allowed to view.
    is_public = snippet.get("is_public", True)
    is_snippet_owner = snippet.get("owner_id") == ObjectId(current_user.id)
    if not is_public and not is_snippet_owner and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You cannot add a snippet you cannot view")

    # Public collections may only contain public snippets.
    if col.get("is_public") and not is_public:
        raise HTTPException(status_code=400, detail="Cannot add a private snippet to a public collection")

    if snippet_object_id in col.get("snippet_ids", []):
        raise HTTPException(status_code=409, detail="Snippet is already in this collection")

    result = await collections_collection.find_one_and_update(
        {"_id": col["_id"]},
        {"$push": {"snippet_ids": snippet_object_id}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found")
    username = await get_owner_username(result.get("owner_id"))
    return format_collection(result, username)


@router.delete("/{collection_id}/snippets/{snippet_id}", response_model=CollectionResponse)
async def remove_snippet_from_collection(
    collection_id: str,
    snippet_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """Remove a snippet from a collection."""
    col = await get_collection_for_change(collection_id, current_user)
    snippet_object_id = parse_object_id(snippet_id, "snippet id")

    result = await collections_collection.find_one_and_update(
        {"_id": col["_id"]},
        {"$pull": {"snippet_ids": snippet_object_id}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found")
    username = await get_owner_username(result.get("owner_id"))
    return format_collection(result, username)


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: str,
    current_user: UserInDB = Depends(get_current_user),
):
    """Delete a collection. Does not delete the snippets inside it."""
    col = await get_collection_for_change(collection_id, current_user)
    await collections_collection.find_one_and_delete({"_id": col["_id"]})
    return {"message": "Collection deleted"}
