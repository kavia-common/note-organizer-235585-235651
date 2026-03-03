from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ApiMessage(BaseModel):
    message: str = Field(..., description="Human-readable message.")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token.")
    token_type: str = Field("bearer", description="Token type; always 'bearer'.")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email; used as login identifier.")
    password: str = Field(..., min_length=8, description="Plaintext password (min 8 chars).")
    display_name: str | None = Field(None, description="Optional display name.")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email.")
    password: str = Field(..., description="User password.")


class UserMeResponse(BaseModel):
    id: UUID = Field(..., description="User UUID.")
    email: EmailStr = Field(..., description="User email.")
    display_name: str | None = Field(None, description="Optional display name.")
    created_at: datetime = Field(..., description="Account creation timestamp.")
    updated_at: datetime = Field(..., description="Last account update timestamp.")


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Tag name (unique per user).")
    color: str | None = Field(None, max_length=32, description="Optional tag color (e.g. hex or label).")


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128, description="New tag name.")
    color: str | None = Field(None, max_length=32, description="New tag color.")


class TagResponse(BaseModel):
    id: UUID = Field(..., description="Tag UUID.")
    name: str = Field(..., description="Tag name.")
    color: str | None = Field(None, description="Tag color.")
    created_at: datetime = Field(..., description="Creation timestamp.")


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500, description="Note title.")
    content: str = Field(..., min_length=1, description="Note content.")
    content_format: str = Field("markdown", description="Content format; e.g. 'markdown'.")
    tag_ids: list[UUID] = Field(default_factory=list, description="Optional list of tag IDs to attach.")


class NoteUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500, description="Updated title.")
    content: str | None = Field(None, min_length=1, description="Updated content.")
    content_format: str | None = Field(None, description="Updated content format.")
    is_archived: bool | None = Field(None, description="Archive status.")
    tag_ids: list[UUID] | None = Field(None, description="If provided, replaces the note's tag set.")


class NoteResponse(BaseModel):
    id: UUID = Field(..., description="Note UUID.")
    title: str = Field(..., description="Title.")
    content: str = Field(..., description="Content.")
    content_format: str = Field(..., description="Content format.")
    is_archived: bool = Field(..., description="Archive status.")
    created_at: datetime = Field(..., description="Created timestamp.")
    updated_at: datetime = Field(..., description="Updated timestamp.")
    tags: list[TagResponse] = Field(default_factory=list, description="Attached tags.")


class NotesListResponse(BaseModel):
    items: list[NoteResponse] = Field(..., description="Notes page items.")
    total: int = Field(..., description="Total notes matching filter.")
