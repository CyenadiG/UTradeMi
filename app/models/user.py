from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UpdateProfileRequest(BaseModel):
    bio: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    bio: str = ""
    avatar_url: str | None = None
    followers_count: int = 0
    following_count: int = 0
    avg_rating: float | None = None
    avg_shipping_time: str | None = None