from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.db import db
from app.utils.object_id import doc_to_json, parse_object_id
from app.utils.security import get_current_user

router = APIRouter()


class SendMessageRequest(BaseModel):
    recipient_id: str
    text: str


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

    # Store with both participant IDs so either side can query it
    participants = sorted([current_user["id"], payload.recipient_id])
    doc = {
        "sender_id":    current_user["id"],
        "recipient_id": payload.recipient_id,
        "participants": participants,   # sorted tuple for easy thread lookup
        "text":         payload.text.strip(),
        "read":         False,
        "created_at":   datetime.now(timezone.utc),
    }

    result = await db.messages.insert_one(doc)
    msg = await db.messages.find_one({"_id": result.inserted_id})
    return {"message": doc_to_json(msg)}


@router.get("/threads")
async def get_threads(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Return one summary entry per unique conversation partner,
    showing the latest message and unread count.
    """
    uid = current_user["id"]

    # Get all messages involving this user
    cursor = db.messages.find({"participants": uid}).sort("created_at", -1)
    all_msgs = await cursor.to_list(500)

    # Group by the other participant
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

        threads.append({
            "other_user_id":  other_id,
            "other_username": other_user.get("username", "user"),
            "other_avatar":   other_user.get("avatar_url"),
            "last_message":   last_msg.get("text", ""),
            "last_time":      last_msg.get("created_at"),
            "unread":         unread_count > 0,
        })

    return {"threads": threads}


@router.get("/{other_user_id}")
async def get_messages(
    other_user_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Return the full message history between the current user and another user,
    and mark all incoming messages as read.
    """
    uid = current_user["id"]
    participants = sorted([uid, other_user_id])

    msgs = (
        await db.messages.find({"participants": participants})
        .sort("created_at", 1)
        .to_list(500)
    )

    # Mark unread messages from the other user as read
    await db.messages.update_many(
        {"sender_id": other_user_id, "recipient_id": uid, "read": False},
        {"$set": {"read": True}},
    )

    return {"messages": [doc_to_json(m) for m in msgs]}