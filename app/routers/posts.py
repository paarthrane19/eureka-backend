from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import get_settings
from app.database import get_db
from app.schemas import CreatePostRequest, PostPublic
from app.security import get_current_user
from app.serializers import post_public

router = APIRouter()


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def _decorate(posts: list[dict], user_id: ObjectId, db) -> list[dict]:
    """Attach author, upvoted and bookmarked flags to raw post docs."""
    if not posts:
        return []
    author_ids = list({p["author_id"] for p in posts})
    authors = {
        u["_id"]: u
        async for u in db.users.find({"_id": {"$in": author_ids}})
    }
    post_ids = [p["_id"] for p in posts]
    voted = {
        v["post_id"]
        async for v in db.votes.find(
            {"user_id": user_id, "post_id": {"$in": post_ids}}
        )
    }
    marked = {
        b["post_id"]
        async for b in db.bookmarks.find(
            {"user_id": user_id, "post_id": {"$in": post_ids}}
        )
    }
    result = []
    for p in posts:
        author = authors.get(p["author_id"])
        if not author:
            continue
        result.append(
            post_public(
                p,
                author,
                upvoted=p["_id"] in voted,
                bookmarked=p["_id"] in marked,
                pinned=author.get("pinned_post_id") == p["_id"],
            )
        )
    return result


@router.get("", response_model=list[PostPublic])
async def list_posts(
    feed: str = Query("all", pattern="^(all|for-you)$"),
    category: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    before: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    query: dict = {}

    if category and category.lower() != "all":
        query["category"] = category

    # "For You" narrows to the user's chosen interests when they have any.
    if feed == "for-you":
        interests = current_user.get("interests") or []
        if interests:
            existing = query.get("category")
            if existing:
                if existing not in interests:
                    return []
            else:
                query["category"] = {"$in": interests}

    # Keyset pagination by created_at for stable infinite scroll.
    if before:
        try:
            query["created_at"] = {"$lt": datetime.fromisoformat(before)}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid `before` cursor.")

    cursor = db.posts.find(query).sort("created_at", -1).limit(limit)
    posts = await cursor.to_list(length=limit)
    return await _decorate(posts, current_user["_id"], db)


@router.post("", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: CreatePostRequest, current_user: dict = Depends(get_current_user)
):
    if payload.category not in get_settings().categories:
        raise HTTPException(status_code=422, detail="Unknown category.")
    if len(payload.images) > 2:
        raise HTTPException(status_code=422, detail="Maximum 2 images per post.")
    db = get_db()
    doc = {
        "headline": payload.headline.strip(),
        "body": payload.body.strip(),
        "category": payload.category,
        "source_url": payload.source_url,
        "images": payload.images,
        "author_id": current_user["_id"],
        "created_at": datetime.now(timezone.utc),
        "upvotes": 0,
        "comment_count": 0,
    }
    result = await db.posts.insert_one(doc)
    doc["_id"] = result.inserted_id
    return post_public(doc, current_user, upvoted=False, bookmarked=False)


@router.get("/library", response_model=list[PostPublic])
async def library(current_user: dict = Depends(get_current_user)):
    db = get_db()
    bookmarks = await db.bookmarks.find({"user_id": current_user["_id"]}).sort(
        "created_at", -1
    ).to_list(length=500)
    post_ids = [b["post_id"] for b in bookmarks]
    if not post_ids:
        return []
    posts = await db.posts.find({"_id": {"$in": post_ids}}).to_list(length=500)
    # Preserve bookmark order (most recently saved first).
    order = {pid: i for i, pid in enumerate(post_ids)}
    posts.sort(key=lambda p: order.get(p["_id"], 0))
    return await _decorate(posts, current_user["_id"], db)


@router.get("/trending", response_model=list[PostPublic])
async def trending(current_user: dict = Depends(get_current_user)):
    """Top 5 most-upvoted posts from the last 7 days."""
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=7)
    posts = (
        await db.posts.find({"created_at": {"$gte": since}})
        .sort("upvotes", -1)
        .limit(5)
        .to_list(length=5)
    )
    return await _decorate(posts, current_user["_id"], db)


@router.get("/daily-discovery", response_model=PostPublic | None)
async def daily_discovery(current_user: dict = Depends(get_current_user)):
    """The most-upvoted post from the last 24h, falling back to the last 7 days."""
    db = get_db()
    now = datetime.now(timezone.utc)
    for window in (timedelta(hours=24), timedelta(days=7)):
        posts = (
            await db.posts.find({"created_at": {"$gte": now - window}})
            .sort("upvotes", -1)
            .limit(1)
            .to_list(length=1)
        )
        decorated = await _decorate(posts, current_user["_id"], db)
        if decorated:
            return decorated[0]
    return None


@router.get("/{post_id}", response_model=PostPublic)
async def get_post(post_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    post = await db.posts.find_one({"_id": _oid(post_id)})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    decorated = await _decorate([post], current_user["_id"], db)
    if not decorated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return decorated[0]


@router.post("/{post_id}/upvote", response_model=PostPublic)
async def upvote(post_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    oid = _oid(post_id)
    post = await db.posts.find_one({"_id": oid})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = await db.votes.find_one(
        {"post_id": oid, "user_id": current_user["_id"]}
    )
    if existing:
        await db.votes.delete_one({"_id": existing["_id"]})
        await db.posts.update_one({"_id": oid}, {"$inc": {"upvotes": -1}})
    else:
        await db.votes.insert_one(
            {
                "post_id": oid,
                "user_id": current_user["_id"],
                "created_at": datetime.now(timezone.utc),
            }
        )
        await db.posts.update_one({"_id": oid}, {"$inc": {"upvotes": 1}})
        await _notify_upvote(db, post, current_user)

    fresh = await db.posts.find_one({"_id": oid})
    decorated = await _decorate([fresh], current_user["_id"], db)
    return decorated[0]


@router.put("/{post_id}/bookmark", response_model=PostPublic)
async def set_bookmark(
    post_id: str, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    oid = _oid(post_id)
    post = await db.posts.find_one({"_id": oid})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    existing = await db.bookmarks.find_one(
        {"post_id": oid, "user_id": current_user["_id"]}
    )
    if existing:
        await db.bookmarks.delete_one({"_id": existing["_id"]})
    else:
        await db.bookmarks.insert_one(
            {
                "post_id": oid,
                "user_id": current_user["_id"],
                "created_at": datetime.now(timezone.utc),
            }
        )
    decorated = await _decorate([post], current_user["_id"], db)
    return decorated[0]


async def _notify_upvote(db, post: dict, actor: dict) -> None:
    if post["author_id"] == actor["_id"]:
        return
    await db.notifications.insert_one(
        {
            "user_id": post["author_id"],
            "type": "upvote",
            "actor_id": actor["_id"],
            "post_id": post["_id"],
            "message": f'{actor.get("name", "Someone")} upvoted "{post["headline"]}"',
            "read": False,
            "created_at": datetime.now(timezone.utc),
        }
    )
