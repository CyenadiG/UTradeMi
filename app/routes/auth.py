from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import db
from app.models.user import LoginRequest, RegisterRequest
from app.utils.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.utils.object_id import doc_to_json

router = APIRouter()


@router.post("/register")
async def register(payload: RegisterRequest) -> dict:
    existing_email = await db.users.find_one({"email": payload.email.lower()})
    if existing_email:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    existing_username = await db.users.find_one({"username": payload.username})
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already in use")

    doc = {
        "username": payload.username,
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "bio": "",
        "avatar_url": None,
        "followers_count": 0,
        "following_count": 0,
        "avg_rating": None,
        "avg_shipping_time": None,
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.users.insert_one(doc)
    user = await db.users.find_one({"_id": result.inserted_id})
    user_json = doc_to_json(user)

    token = create_access_token(user_json["id"], user_json["username"])
    return {"token": token, "user": user_json}


@router.post("/login")
async def login(payload: LoginRequest) -> dict:
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_json = doc_to_json(user)
    token = create_access_token(user_json["id"], user_json["username"])
    return {"token": token, "user": user_json}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)) -> dict:
    return {"user": current_user}