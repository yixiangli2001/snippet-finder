from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SnippetCreate(BaseModel):
    title: str
    language: str
    code: str
    description: Optional[str] = None
    tags: list[str] = []


class SnippetUpdate(BaseModel):
    title: Optional[str] = None
    language: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class SnippetResponse(BaseModel):
    id: str
    title: str
    language: str
    code: str
    description: Optional[str] = None
    tags: list[str] = []
    times_copied: int = 0
    created_at: datetime
    updated_at: datetime