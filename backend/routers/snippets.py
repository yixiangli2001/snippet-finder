from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime, timezone
import re
from database import snippets_collection
from models.snippet import SnippetCreate, SnippetUpdate, SnippetResponse

router = APIRouter()


def format_snippet(snippet: dict) -> dict:
    formatted = {**snippet, "id": str(snippet["_id"])}
    del formatted["_id"]
    return formatted


def parse_object_id(snippet_id: str) -> ObjectId:
    if not ObjectId.is_valid(snippet_id):
        raise HTTPException(status_code=400, detail="Invalid snippet id")
    return ObjectId(snippet_id)


@router.get("/", response_model=list[SnippetResponse])
async def get_snippets(search: str = None, language: str = None):
    query = {}
    if search:
        escaped_search = re.escape(search)
        query["$or"] = [
            {"title": {"$regex": escaped_search, "$options": "i"}},
            {"code": {"$regex": escaped_search, "$options": "i"}},
            {"description": {"$regex": escaped_search, "$options": "i"}},
            {"tags": {"$regex": escaped_search, "$options": "i"}}
        ]
    if language:
        query["language"] = language

    snippets = await snippets_collection.find(query).to_list(100)
    return [format_snippet(s) for s in snippets]


@router.post("/", response_model=SnippetResponse)
async def create_snippet(snippet: SnippetCreate):
    now = datetime.now(timezone.utc)
    data = snippet.model_dump()
    data["times_copied"] = 0
    data["created_at"] = now
    data["updated_at"] = now

    result = await snippets_collection.insert_one(data)
    created = await snippets_collection.find_one({"_id": result.inserted_id})
    return format_snippet(created)


@router.put("/{snippet_id}", response_model=SnippetResponse)
async def update_snippet(snippet_id: str, snippet: SnippetUpdate):
    data = {k: v for k, v in snippet.model_dump().items() if v is not None}
    data["updated_at"] = datetime.now(timezone.utc)
    object_id = parse_object_id(snippet_id)

    result = await snippets_collection.find_one_and_update(
        {"_id": object_id},
        {"$set": data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return format_snippet(result)


@router.delete("/{snippet_id}")
async def delete_snippet(snippet_id: str):
    object_id = parse_object_id(snippet_id)
    result = await snippets_collection.find_one_and_delete(
        {"_id": object_id}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Snippet not found")
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

