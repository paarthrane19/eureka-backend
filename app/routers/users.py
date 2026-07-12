from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.schemas import (
    OnboardingRequest,
    PinPostRequest,
    PostPublic,
    UpdateProfileRequest,
    UserPublic,
)
from app.security import get_current_user
from app.serializers import post_public, user_public

router = APIRouter()


async def _stats(db, user_id: ObjectId) -> tuple[int, int]:
    """Return (post_count, average credibility score) for a user."""
    posts = await db.posts.find({"author_id": user_id}).to_list(length=None)
    post_count = len(posts)
    if not post_count:
        return 0, 0
    scores = [p.get("credibility", {}).get("score", 70) for p in posts]
    return post_count, round(sum(scores) / len(scores))


@router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: UpdateProfileRequest, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
    fresh = await db.users.find_one({"_id": current_user["_id"]})
    post_count, credibility_score = await _stats(db, current_user["_id"])
    return user_public(fresh, post_count=post_count, credibility_score=credibility_score)


@router.post("/me/onboarding", response_model=UserPublic)
async def complete_onboarding(
    payload: OnboardingRequest, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"interests": payload.interests}},
    )
    fresh = await db.users.find_one({"_id": current_user["_id"]})
    post_count, credibility_score = await _stats(db, current_user["_id"])
    return user_public(fresh, post_count=post_count, credibility_score=credibility_score)


@router.put("/me/pin", response_model=UserPublic)
async def pin_post(
    payload: PinPostRequest, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    if payload.post_id is None:
        pinned_id = None
    else:
        try:
            oid = ObjectId(payload.post_id)
        except InvalidId:
            raise HTTPException(status_code=404, detail="Post not found")
        post = await db.posts.find_one({"_id": oid, "author_id": current_user["_id"]})
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        pinned_id = oid
    await db.users.update_one(
        {"_id": current_user["_id"]}, {"$set": {"pinned_post_id": pinned_id}}
    )
    fresh = await db.users.find_one({"_id": current_user["_id"]})
    post_count, credibility_score = await _stats(db, current_user["_id"])
    return user_public(fresh, post_count=post_count, credibility_score=credibility_score)


@router.get("/by-username/{username}", response_model=UserPublic)
async def get_user_by_username(username: str):
    db = get_db()
    user = await db.users.find_one({"username": username.lower()})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    post_count, credibility_score = await _stats(db, user["_id"])
    return user_public(user, post_count=post_count, credibility_score=credibility_score)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: str):
    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    post_count, credibility_score = await _stats(db, user["_id"])
    return user_public(user, post_count=post_count, credibility_score=credibility_score)


@router.get("/{user_id}/posts", response_model=list[PostPublic])
async def get_user_posts(
    user_id: str, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    author = await db.users.find_one({"_id": oid})
    if not author:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    cursor = db.posts.find({"author_id": oid}).sort("created_at", -1)
    posts = await cursor.to_list(length=200)

    post_ids = [p["_id"] for p in posts]
    voted = {
        v["post_id"]
        async for v in db.votes.find(
            {"user_id": current_user["_id"], "post_id": {"$in": post_ids}}
        )
    }
    marked = {
        b["post_id"]
        async for b in db.bookmarks.find(
            {"user_id": current_user["_id"], "post_id": {"$in": post_ids}}
        )
    }
    pinned_id = author.get("pinned_post_id")
    return [
        post_public(
            p,
            author,
            upvoted=p["_id"] in voted,
            bookmarked=p["_id"] in marked,
            pinned=pinned_id == p["_id"],
        )
        for p in posts
    ]
