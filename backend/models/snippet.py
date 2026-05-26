from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SnippetCreate(BaseModel):
    """Input model for creating a snippet."""
    title: str
    language: str
    code: str
    description: Optional[str] = None
    tags: list[str] = []


class SnippetUpdate(BaseModel):
    """Input model for updating a snippet. All fields are optional."""
    title: Optional[str] = None
    language: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None


class SnippetResponse(BaseModel):
    """API response model for a snippet."""
    id: str
    owner_id: Optional[str] = None
    owner_username: Optional[str] = None
    title: str
    language: str
    code: str
    description: Optional[str] = None
    tags: list[str] = []
    is_public: bool = True
    times_copied: int = 0
    created_at: datetime
    updated_at: datetime


class SnippetListResponse(BaseModel):
    """API response model for a list of snippets."""
    items: list[SnippetResponse]
    total: int
