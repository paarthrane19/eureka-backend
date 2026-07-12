from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings


class _Mongo:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo = _Mongo()


async def connect_to_mongo() -> None:
    settings = get_settings()
    # Fail fast (5s) instead of the 30s default so requests error quickly when
    # MongoDB is down, and the dev server stays responsive.
    mongo.client = AsyncIOMotorClient(
        settings.mongo_uri, serverSelectionTimeoutMS=5000
    )
    mongo.db = mongo.client[settings.mongo_db]
    try:
        await _ensure_indexes()
    except Exception as exc:  # noqa: BLE001
        # Don't crash the dev server if Mongo isn't up yet — log and continue.
        # Endpoints will surface a clear error until MongoDB is reachable.
        print(f"[eureka] WARNING: could not reach MongoDB at startup: {exc}")
        print("[eureka] Start MongoDB (e.g. `brew services start mongodb-community`)")


async def close_mongo_connection() -> None:
    if mongo.client is not None:
        mongo.client.close()


def get_db() -> AsyncIOMotorDatabase:
    if mongo.db is None:
        raise RuntimeError("Database not initialised. Did the app start correctly?")
    return mongo.db


async def _ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.posts.create_index([("created_at", -1)])
    await db.posts.create_index("category")
    await db.posts.create_index("author_id")
    await db.comments.create_index([("post_id", 1), ("created_at", 1)])
    await db.votes.create_index([("post_id", 1), ("user_id", 1)], unique=True)
    await db.bookmarks.create_index([("user_id", 1), ("post_id", 1)], unique=True)
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    # Chat + social graph
    await db.messages.create_index([("room_id", 1), ("created_at", 1)])
    await db.room_members.create_index([("room_id", 1), ("user_id", 1)], unique=True)
    await db.direct_messages.create_index([("thread_id", 1), ("created_at", 1)])
    await db.dm_threads.create_index("participants")
    await db.follows.create_index(
        [("follower_id", 1), ("following_id", 1)], unique=True
    )
    # Curated content
    await db.curated_content.create_index([("collection_id", 1), ("order", 1)])
    await db.daily_discovery.create_index("date")
    # Followable questions + study circles
    await db.questions.create_index([("created_at", -1)])
    await db.questions.create_index("category")
    await db.study_circles.create_index([("created_at", -1)])
    await db.study_circles.create_index("category")
    # Landing-page waitlist
    await db.waitlist.create_index("email", unique=True)
