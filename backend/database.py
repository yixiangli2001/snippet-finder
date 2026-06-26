from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

client = AsyncIOMotorClient(MONGO_URL)
db = client["snippet_finder"]

snippets_collection = db["snippets"]
users_collection = db["users"]
collections_collection = db["collections"]
auth_tokens_collection = db["auth_tokens"]