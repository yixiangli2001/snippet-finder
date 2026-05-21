from fastapi import APIRouter, Depends

from models.user import UserInDB, UserResponse
from routers.auth import format_user
from utils.security import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    return format_user(current_user.model_dump(by_alias=True))
