from datetime import datetime
from pydantic import BaseModel, Field


class CreateReviewRequest(BaseModel):
    reviewed_user_id: str
    rating: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=1000)
    shipping_time: str | None = Field(default=None, max_length=100)


class ReviewResponse(BaseModel):
    id: str
    reviewer_id: str
    reviewed_user_id: str
    rating: int
    review_text: str | None = None
    shipping_time: str | None = None
    created_at: datetime