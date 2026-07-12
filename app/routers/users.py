from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.schemas import (
    OnboardingRequest,
    PostPublic,
    UpdateProfileRequest,
    UserPublic,
)
from app.security import get_current_user
from app.serializers import post_public, user_public

router = APIRouter()


@router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: UpdateProfileRequest, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": updates})
    fresh = await db.users.find_one({"_id": current_user["_id"]})
    return user_public(fresh)


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
    return user_public(fresh)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: str):
    db = get_db()
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_public(user)


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
    return [
        post_public(
            p, author, upvoted=p["_id"] in voted, bookmarked=p["_id"] in marked
        )
        for p in posts
    ]
