"""Protected admin endpoints for programmatically managing official content."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from app.config import get_settings
from app.database import get_db
from app.security import hash_password

router = APIRouter()

# The admin endpoint accepts lowercase, hyphenated category slugs.
AdminCategory = Literal[
    "physics",
    "astronomy",
    "biology",
    "chemistry",
    "math",
    "earth-science",
    "technology",
    "medicine",
]


class AdminAgentPostRequest(BaseModel):
    headline: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=280)
    category: AdminCategory
    source_url: HttpUrl


def _require_admin(authorization: str | None) -> None:
    """Reject anything without a valid Bearer EUREKA_ADMIN_TOKEN with a 401.

    The token is compared in constant time and never logged or echoed back.
    """
    expected = get_settings().eureka_admin_token
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing admin credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # A blank server-side token means the admin routes are effectively disabled.
    if not expected:
        raise unauthorized
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized
    token = authorization[len("Bearer ") :].strip()
    if not secrets.compare_digest(token, expected):
        raise unauthorized


async def _get_or_create_official(db) -> dict:
    """Return the official @eureka account, creating it if it doesn't exist."""
    username = get_settings().agent_username
    user = await db.users.find_one({"username": username})
    if user:
        return user
    doc = {
        "username": username,
        "display_name": "Eureka Official",
        # `name`/`verified` mirror display_name/is_verified so the rest of the
        # app (feed serializers read these keys) renders this account correctly.
        "name": "Eureka Official",
        "email": "agent@projecteureka.app",
        "password_hash": hash_password(secrets.token_urlsafe(32)),
        "is_verified": True,
        "is_official": True,
        "verified": True,
        "bio": "",
        "interests": [],
        "avatar_color": "#00E676",
        "avatar_url": None,
        "cover_image": None,
        "link": None,
        "location": None,
        "working_at": None,
        "pinned_post_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


# Lets an authorized operator publish an official @eureka post (used by the
# external content agent) via a shared admin token rather than a user JWT.
@router.post("/agent/post", status_code=status.HTTP_201_CREATED, tags=["admin"])
async def create_agent_post(
    payload: AdminAgentPostRequest,
    authorization: str | None = Header(default=None),
):
    _require_admin(authorization)
    db = get_db()
    official = await _get_or_create_official(db)
    post = {
        "headline": payload.headline,
        "body": payload.body,
        "category": payload.category,
        "source_url": str(payload.source_url),
        "author_id": official["_id"],
        "created_at": datetime.now(timezone.utc),
        "upvotes": 0,
        "comments": 0,
        # `comment_count` is the key the feed serializer reads; keep it in sync.
        "comment_count": 0,
        "images": [],
        "is_agent_post": True,
    }
    result = await db.posts.insert_one(post)
    return {"id": str(result.inserted_id), "headline": payload.headline}


# Lightweight ops dashboard counts (users, posts, comments, last-24h posts)
# for the admin, gated by the same shared token.
@router.get("/stats", tags=["admin"])
async def admin_stats(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return {
        "total_users": await db.users.count_documents({}),
        "total_posts": await db.posts.count_documents({}),
        "total_comments": await db.comments.count_documents({}),
        "posts_last_24h": await db.posts.count_documents({"created_at": {"$gte": since}}),
    }
