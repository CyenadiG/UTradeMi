from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db import db
from app.models.user import UpdateProfileRequest
from app.utils.object_id import doc_to_json, parse_object_id
from app.utils.security import get_current_user

router = APIRouter()


@router.get("/{user_id}")
async def get_user(user_id: str) -> dict:
    user = await db.users.find_one({"_id": parse_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_json = doc_to_json(user)
    user_json.pop("password_hash", None)
    return {"user": user_json}


@router.patch("/me")
async def update_me(
    payload: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}

    if update_data:
        await db.users.update_one(
            {"_id": parse_object_id(current_user["id"])},
            {"$set": update_data},
        )

    user = await db.users.find_one({"_id": parse_object_id(current_user["id"])})
    user_json = doc_to_json(user)
    user_json.pop("password_hash", None)
    return {"user": user_json}


@router.get("/{user_id}/posts")
async def get_user_posts(user_id: str, type: str | None = Query(default=None)) -> dict:
    query: dict = {"user_id": user_id}
    if type:
        query["type"] = type

    user = await db.users.find_one({"_id": parse_object_id(user_id)})
    username = user.get("username") if user else None

    posts = await db.posts.find(query).sort("created_at", -1).to_list(100)

    result = []
    for post in posts:
        post_json = doc_to_json(post)
        post_json["username"] = username
        result.append(post_json)

    return {"posts": result}

@router.get("/{user_id}/likes")
async def get_user_liked_posts(user_id: str) -> dict:
    likes = await db.likes.find({"user_id": user_id}).to_list(100)
    post_ids = [like["post_id"] for like in likes]
    posts = await db.posts.find({"_id": {"$in": [parse_object_id(pid) for pid in post_ids]}}).to_list(100)
    return {"posts": [doc_to_json(post) for post in posts]}


@router.get("/{user_id}/reviews")
async def get_user_reviews(user_id: str) -> dict:
    reviews = await db.reviews.find({"reviewed_user_id": user_id}).sort("created_at", -1).to_list(100)

    result = []
    for review in reviews:
        review_json = doc_to_json(review)

        reviewer = await db.users.find_one({"_id": parse_object_id(review_json["reviewer_id"])})
        reviewer_json = doc_to_json(reviewer) if reviewer else None

        review_json["reviewer_username"] = reviewer_json.get("username") if reviewer_json else "user"
        result.append(review_json)

    return {"reviews": result}

@router.post("/{user_id}/follow")
async def follow_user(user_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    if user_id == current_user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself")

    target_user = await db.users.find_one({"_id": parse_object_id(user_id)})
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await db.follows.find_one({
        "follower_id": current_user["id"],
        "following_id": user_id,
    })
    if existing:
        return {"message": "Already following"}

    await db.follows.insert_one({
        "follower_id": current_user["id"],
        "following_id": user_id,
        "created_at": datetime.now(timezone.utc),
    })

    await db.users.update_one({"_id": parse_object_id(current_user["id"])}, {"$inc": {"following_count": 1}})
    await db.users.update_one({"_id": parse_object_id(user_id)}, {"$inc": {"followers_count": 1}})

    return {"message": "Followed user"}


@router.delete("/{user_id}/follow")
async def unfollow_user(user_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    existing = await db.follows.find_one({
        "follower_id": current_user["id"],
        "following_id": user_id,
    })

    if not existing:
        return {"message": "Not following"}

    await db.follows.delete_one({
        "follower_id": current_user["id"],
        "following_id": user_id,
    })

    await db.users.update_one({"_id": parse_object_id(current_user["id"])}, {"$inc": {"following_count": -1}})
    await db.users.update_one({"_id": parse_object_id(user_id)}, {"$inc": {"followers_count": -1}})

    return {"message": "Unfollowed user"}