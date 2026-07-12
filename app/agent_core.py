"""Shared posting logic for the automated @eureka content agent.

Used by both the in-process APScheduler (app/agent_scheduler.py, the default
in production) and the standalone `agent.py` script, which can be pointed at
by a Railway cron job instead if you'd rather schedule outside the app
process. Both paths call `post_next()` so the non-repeating pool logic only
lives in one place.
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.database import get_db

_POSTS_PATH = Path(__file__).parent / "data" / "agent_posts.json"
_pool_cache: list[dict] | None = None


def _load_pool() -> list[dict]:
    global _pool_cache
    if _pool_cache is None:
        with open(_POSTS_PATH, encoding="utf-8") as f:
            _pool_cache = json.load(f)
    return _pool_cache


async def _get_eureka_user(db) -> dict | None:
    return await db.users.find_one({"username": get_settings().agent_username})


async def _next_index(db, pool_size: int) -> int:
    """Pop a random, non-repeating index from persisted agent state.

    Reshuffles a fresh cycle once the pool is exhausted so every post gets
    used before any repeats.
    """
    state = await db.agent_state.find_one({"_id": "pool"})
    remaining = state.get("remaining", []) if state else []
    if not remaining:
        remaining = list(range(pool_size))
        random.shuffle(remaining)
    index = remaining.pop()
    await db.agent_state.update_one(
        {"_id": "pool"}, {"$set": {"remaining": remaining}}, upsert=True
    )
    return index


async def post_next() -> dict | None:
    """Publish the next curated post as the official @eureka account.

    Returns the inserted post's raw dict, or None if the agent account
    hasn't been seeded (run seed.py first) or is disabled.
    """
    db = get_db()
    eureka = await _get_eureka_user(db)
    if not eureka:
        print("[agent] no @eureka account found - run seed.py first, skipping.")
        return None

    pool = _load_pool()
    index = await _next_index(db, len(pool))
    item = pool[index]

    doc = {
        "headline": item["headline"],
        "body": item["body"],
        "category": item["category"],
        "source_url": item.get("source_url"),
        "images": [],
        "author_id": eureka["_id"],
        "created_at": datetime.now(timezone.utc),
        "upvotes": 0,
        "comment_count": 0,
    }
    result = await db.posts.insert_one(doc)
    doc["_id"] = result.inserted_id
    print(f"[agent] posted: {item['headline']!r}")
    return doc
