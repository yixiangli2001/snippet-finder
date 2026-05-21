from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from database import users_collection
from models.user import UserCreate, UserResponse
from utils.security import create_token, hash_password, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def format_user(user: dict) -> dict:
    formatted = {**user, "id": str(user["_id"])}
    del formatted["_id"]
    return formatted


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    existing = await users_collection.find_one({
        "$or": [
            {"email": user.email},
            {"username": user.username},
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already exists")

    now = datetime.now(timezone.utc)
    data = {
        "email": user.email,
        "username": user.username,
        "password_hash": hash_password(user.password),
        "role": "user",
        "created_at": now,
        "updated_at": now,
    }

    result = await users_collection.insert_one(data)
    created = await users_collection.find_one({"_id": result.inserted_id})
    return format_user(created)


@router.post("/login")
async def login(credentials: LoginRequest):
    user = await users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(str(user["_id"]), user.get("role", "user"))
    return {"access_token": token, "token_type": "bearer"}
