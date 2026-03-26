from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import db
from app.models.review import CreateReviewRequest
from app.utils.object_id import doc_to_json, parse_object_id
from app.utils.security import get_current_user

router = APIRouter()


def _parse_shipping_minutes(s: str) -> float | None:
    """
    Convert a plain-text shipping_time string like '3 days', '2 weeks', '5 days'
    into a total number of days (float) so we can average it.
    Returns None if unparseable.
    """
    if not s:
        return None
    s = s.lower().strip()
    try:
        parts = s.split()
        value = float(parts[0])
        unit = parts[1] if len(parts) > 1 else ""
        if "week" in unit:
            return value * 7
        if "month" in unit:
            return value * 30
        return value          # assume days by default
    except Exception:
        return None


def _format_days(days: float) -> str:
    """Turn an average number of days back into a readable string."""
    if days < 1:
        return "< 1 day"
    if days < 7:
        d = round(days)
        return f"{d} day{'s' if d != 1 else ''}"
    if days < 30:
        w = round(days / 7, 1)
        return f"{w} week{'s' if w != 1.0 else ''}"
    m = round(days / 30, 1)
    return f"{m} month{'s' if m != 1.0 else ''}"


@router.post("")
async def create_review(
    payload: CreateReviewRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if payload.reviewed_user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot review yourself",
        )

    reviewed_user = await db.users.find_one(
        {"_id": parse_object_id(payload.reviewed_user_id)}
    )
    if not reviewed_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    doc = {
        "reviewer_id": current_user["id"],
        "reviewed_user_id": payload.reviewed_user_id,
        "rating": payload.rating,
        "review_text": payload.review_text,
        "shipping_time": payload.shipping_time,
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.reviews.insert_one(doc)

    # ── Recalculate averages across ALL reviews for this user ──
    reviews = (
        await db.reviews.find({"reviewed_user_id": payload.reviewed_user_id})
        .to_list(1000)
    )

    avg_rating = None
    avg_shipping_time = None

    if reviews:
        # Average star rating
        avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 2)

        # Average shipping time — only include reviews that have a parseable value
        shipping_days = [
            d
            for r in reviews
            if (d := _parse_shipping_minutes(r.get("shipping_time"))) is not None
        ]
        if shipping_days:
            avg_days = sum(shipping_days) / len(shipping_days)
            avg_shipping_time = _format_days(avg_days)

    await db.users.update_one(
        {"_id": parse_object_id(payload.reviewed_user_id)},
        {"$set": {"avg_rating": avg_rating, "avg_shipping_time": avg_shipping_time}},
    )

    review = await db.reviews.find_one({"_id": result.inserted_id})
    return {"review": doc_to_json(review)}