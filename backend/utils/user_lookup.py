from database import users_collection


async def build_username_map(documents: list[dict]) -> dict:
    """Return owner usernames for a list of documents with owner_id fields."""
    owner_ids = list({document["owner_id"] for document in documents if document.get("owner_id")})
    if not owner_ids:
        return {}

    users = await users_collection.find({"_id": {"$in": owner_ids}}).to_list(None)
    return {user["_id"]: user["username"] for user in users}


async def get_owner_username(owner_id) -> str | None:
    """Return one owner's username, or None for anonymous/deleted owners."""
    if not owner_id:
        return None

    user = await users_collection.find_one({"_id": owner_id})
    return user["username"] if user else None
