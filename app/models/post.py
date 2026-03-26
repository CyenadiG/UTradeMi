from datetime import datetime
from pydantic import BaseModel, Field


class CreatePostRequest(BaseModel):
    type: str = Field(pattern="^(trading|iso|selling|for_purchase)$")
    title: str | None = Field(default=None, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    image_url: str | None = None
    tags: list[str] = []


class UpdatePostRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = None
    tags: list[str] | None = None
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class PostResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str | None = None
    description: str
    image_url: str | None = None
    tags: list[str] = []
    status: str = "active"
    created_at: datetime