from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class CollectionCreate(BaseModel):
    """Input model for creating a collection."""

    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, name: str) -> str:
        stripped = name.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped


class CollectionUpdate(BaseModel):
    """Input model for updating a collection. All fields are optional."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, name: Optional[str]) -> Optional[str]:
        if name is None:
            return name
        stripped = name.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        return stripped


class AddSnippet(BaseModel):
    """Input model for adding a snippet to a collection."""

    snippet_id: str


class CollectionResponse(BaseModel):
    """API response model for a collection."""

    id: str
    owner_id: str
    owner_username: Optional[str] = None
    name: str
    description: Optional[str] = None
    snippet_ids: list[str] = []
    is_public: bool
    created_at: datetime
    updated_at: datetime
