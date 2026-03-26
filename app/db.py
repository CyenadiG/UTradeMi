from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

from app.config import settings

print("MONGODB_URI =", settings.MONGODB_URI)
client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client[settings.MONGODB_DB_NAME]


async def create_indexes() -> None:
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index([("username", ASCENDING)], unique=True)

    await db.posts.create_index([("user_id", ASCENDING)])
    await db.posts.create_index([("type", ASCENDING)])
    await db.posts.create_index([("created_at", DESCENDING)])

    await db.likes.create_index([("user_id", ASCENDING), ("post_id", ASCENDING)], unique=True)
    await db.follows.create_index([("follower_id", ASCENDING), ("following_id", ASCENDING)], unique=True)

    await db.reviews.create_index([("reviewed_user_id", ASCENDING)])
    await db.reviews.create_index([("created_at", DESCENDING)])

    # Messages: index on participants array for fast thread lookup
    await db.messages.create_index([("participants", ASCENDING)])
    await db.messages.create_index([("created_at", DESCENDING)])
    await db.messages.create_index([("sender_id", ASCENDING), ("recipient_id", ASCENDING)])