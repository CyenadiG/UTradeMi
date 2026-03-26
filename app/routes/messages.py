from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db import db
from app.utils.object_id import doc_to_json, parse_object_id
from app.utils.security import get_current_user

router = APIRouter()


class SendMessageRequest(BaseModel):
    recipient_id: str
    text: str
    post_id: Optional[str] = None   # post being discussed


@router.post("")
async def send_message(
    payload: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if payload.recipient_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot message yourself",
        )

    recipient = await db.users.find_one({"_id": parse_object_id(payload.recipient_id)})
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    participants = sorted([current_user["id"], payload.recipient_id])

    # Carry forward post_id from earlier messages in this thread
    # so the card stays attached even after the first message
    post_id = payload.post_id
    if not post_id:
        earlier = await db.messages.find_one(
            {"participants": participants, "post_id": {"$exists": True, "$ne": None}},
            sort=[("created_at", 1)]
        )
        if earlier:
            post_id = earlier.get("post_id")

    doc = {
        "sender_id":    current_user["id"],
        "recipient_id": payload.recipient_id,
        "participants": participants,
        "text":         payload.text.strip(),
        "post_id":      post_id,
        "read":         False,
        "created_at":   datetime.now(timezone.utc),
    }

    result = await db.messages.insert_one(doc)
    msg = await db.messages.find_one({"_id": result.inserted_id})
    return {"message": doc_to_json(msg)}


@router.get("/threads")
async def get_threads(current_user: dict = Depends(get_current_user)) -> dict:
    uid = current_user["id"]

    cursor = db.messages.find({"participants": uid}).sort("created_at", -1)
    all_msgs = await cursor.to_list(500)

    # One entry per unique conversation partner
    seen: dict = {}
    for m in all_msgs:
        other = m["recipient_id"] if m["sender_id"] == uid else m["sender_id"]
        if other not in seen:
            seen[other] = m

    threads = []
    for other_id, last_msg in seen.items():
        other_user = await db.users.find_one({"_id": parse_object_id(other_id)})
        if not other_user:
            continue

        unread_count = await db.messages.count_documents({
            "sender_id":    other_id,
            "recipient_id": uid,
            "read":         False,
        })

        # Earliest message in this thread that has a post attached
        post_msg = await db.messages.find_one(
            {"participants": sorted([uid, other_id]),
             "post_id": {"$exists": True, "$ne": None}},
            sort=[("created_at", 1)]
        )
        post_id = post_msg.get("post_id") if post_msg else None

        threads.append({
            "other_user_id":  other_id,
            "other_username": other_user.get("username", "user"),
            "other_avatar":   other_user.get("avatar_url"),
            "last_message":   last_msg.get("text", ""),
            "last_time":      last_msg.get("created_at"),
            "unread":         unread_count > 0,
            "post_id":        post_id,
        })

    return {"threads": threads}


@router.get("/{other_user_id}")
async def get_messages(
    other_user_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    uid = current_user["id"]
    participants = sorted([uid, other_user_id])

    msgs = (
        await db.messages.find({"participants": participants})
        .sort("created_at", 1)
        .to_list(500)
    )

    # Mark incoming messages as read
    await db.messages.update_many(
        {"sender_id": other_user_id, "recipient_id": uid, "read": False},
        {"$set": {"read": True}},
    )

    return {"messages": [doc_to_json(m) for m in msgs]}