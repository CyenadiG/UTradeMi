from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import db
from app.models.post import CreatePostRequest, UpdatePostRequest
from app.utils.object_id import doc_to_json, parse_object_id
from app.utils.security import get_current_user

router = APIRouter()


@router.get("/discover")
async def discover_posts() -> dict:
    posts = await db.posts.find({"status": "active"}).sort("created_at", -1).to_list(50)

    enriched_posts = []
    for post in posts:
        post_json = doc_to_json(post)

        owner = await db.users.find_one({"_id": parse_object_id(post_json["user_id"])})
        owner_json = doc_to_json(owner) if owner else None

        if owner_json:
            owner_json.pop("password_hash", None)
            post_json["username"] = owner_json.get("username")

        enriched_posts.append(post_json)

    return {"posts": enriched_posts}


@router.get("/{post_id}")
async def get_post(post_id: str) -> dict:
    post = await db.posts.find_one({"_id": parse_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post_json = doc_to_json(post)

    owner = await db.users.find_one({"_id": parse_object_id(post_json["user_id"])})
    owner_json = doc_to_json(owner) if owner else None
    if owner_json:
        owner_json.pop("password_hash", None)

    return {
        "post": post_json,
        "user": owner_json,
    }


@router.post("")
async def create_post(
    payload: CreatePostRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    doc = {
        "user_id": current_user["id"],
        "type": payload.type,
        "title": payload.title,
        "description": payload.description,
        "image_url": payload.image_url,
        "tags": payload.tags,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.posts.insert_one(doc)
    post = await db.posts.find_one({"_id": result.inserted_id})
    post_json = doc_to_json(post)
    post_json["username"] = current_user["username"]
    return {"post": post_json}


@router.patch("/{post_id}")
async def update_post(
    post_id: str,
    payload: UpdatePostRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    post = await db.posts.find_one({"_id": parse_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post["user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if update_data:
        await db.posts.update_one({"_id": parse_object_id(post_id)}, {"$set": update_data})

    updated = await db.posts.find_one({"_id": parse_object_id(post_id)})
    return {"post": doc_to_json(updated)}


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    post = await db.posts.find_one({"_id": parse_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post["user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    await db.posts.delete_one({"_id": parse_object_id(post_id)})
    await db.likes.delete_many({"post_id": post_id})
    return {"message": "Post deleted"}


@router.post("/{post_id}/like")
async def like_post(post_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    post = await db.posts.find_one({"_id": parse_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = await db.likes.find_one({"user_id": current_user["id"], "post_id": post_id})
    if existing:
        return {"message": "Already liked"}

    await db.likes.insert_one({
        "user_id": current_user["id"],
        "post_id": post_id,
        "created_at": datetime.now(timezone.utc),
    })
    return {"message": "Post liked"}


@router.delete("/{post_id}/like")
async def unlike_post(post_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    await db.likes.delete_one({"user_id": current_user["id"], "post_id": post_id})
    return {"message": "Post unliked"}