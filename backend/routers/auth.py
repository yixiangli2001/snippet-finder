import os
import re
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from database import users_collection
from models.user import ResetPasswordRequest, UserCreate, UserResponse
from utils.auth_rate_limit import (
    enforce_forgot_password_rate_limit,
    enforce_login_rate_limit,
    enforce_register_rate_limit,
)
from utils.auth_tokens import RESET_PASSWORD_TTL, VERIFY_EMAIL_TTL, consume_auth_token, create_auth_token
from utils.breach_check import is_password_breached
from utils.email import send_reset_email, send_verification_email
from utils.security import create_token, hash_password, verify_password
from utils.turnstile import verify_turnstile_token

router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    turnstile_token: str = ""


def format_user(user: dict) -> dict:
    formatted = {**user, "id": str(user["_id"])}
    del formatted["_id"]
    # Legacy accounts predate this field — treat them as already verified.
    formatted.setdefault("is_verified", True)
    return formatted


async def _send_verification_link(user_id: str, email: str) -> None:
    token = await create_auth_token(user_id, "verify_email", VERIFY_EMAIL_TTL)
    send_verification_email(email, f"{FRONTEND_URL}/verify-email?token={token}")


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, request: Request):
    enforce_register_rate_limit(request.client.host)

    if not await verify_turnstile_token(user.turnstile_token, request.client.host):
        raise HTTPException(status_code=400, detail="Captcha verification failed")

    if await is_password_breached(user.password):
        raise HTTPException(
            status_code=400,
            detail="This password has appeared in a known data breach. Please choose a different one.",
        )

    existing = await users_collection.find_one({
        "$or": [
            {"email": user.email},
            {"username": {"$regex": f"^{re.escape(user.username)}$", "$options": "i"}},
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
        "is_verified": False,
        "created_at": now,
        "updated_at": now,
    }

    result = await users_collection.insert_one(data)
    created = await users_collection.find_one({"_id": result.inserted_id})

    await _send_verification_link(str(result.inserted_id), user.email)

    return format_user(created)


@router.post("/login")
async def login(credentials: LoginRequest, request: Request):
    enforce_login_rate_limit(f"{request.client.host}:{credentials.email}")

    user = await users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_verified", True):
        raise HTTPException(status_code=403, detail="Please verify your email before logging in")

    token = create_token(str(user["_id"]), user.get("role", "user"))
    return {"access_token": token, "token_type": "bearer"}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest):
    user_id = await consume_auth_token(body.token, "verify_email")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    await users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_verified": True}})
    return {"message": "Email verified"}


@router.post("/resend-verification")
async def resend_verification(body: ResendVerificationRequest):
    # Always return the same response, whether or not the email exists or is
    # already verified — otherwise this endpoint becomes an account-enumeration tool.
    user = await users_collection.find_one({"email": body.email})
    if user and not user.get("is_verified", True):
        await _send_verification_link(str(user["_id"]), body.email)

    return {"message": "If an account with that email exists and is unverified, we've sent a new link"}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    enforce_forgot_password_rate_limit(f"{request.client.host}:{body.email}")

    if not await verify_turnstile_token(body.turnstile_token, request.client.host):
        raise HTTPException(status_code=400, detail="Captcha verification failed")

    # Always return the same response whether or not the email exists —
    # otherwise this endpoint becomes an account-enumeration tool.
    user = await users_collection.find_one({"email": body.email})
    if user:
        token = await create_auth_token(str(user["_id"]), "reset_password", RESET_PASSWORD_TTL)
        send_reset_email(body.email, f"{FRONTEND_URL}/reset-password?token={token}")

    return {"message": "If an account with that email exists, we've sent a password reset link"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    if await is_password_breached(body.new_password):
        raise HTTPException(
            status_code=400,
            detail="This password has appeared in a known data breach. Please choose a different one.",
        )

    user_id = await consume_auth_token(body.token, "reset_password")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    # Clicking the emailed reset link proves email ownership just as strongly
    # as the verification link, so verify the account here too — otherwise an
    # unverified user could reset their password and still be blocked at login.
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": hash_password(body.new_password), "is_verified": True}},
    )
    return {"message": "Password updated"}
