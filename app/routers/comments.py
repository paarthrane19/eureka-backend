from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.schemas import CommentPublic, CreateCommentRequest
from app.security import get_current_user
from app.serializers import comment_public

router = APIRouter()


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/posts/{post_id}/comments", response_model=list[CommentPublic])
async def list_comments(post_id: str, _: dict = Depends(get_current_user)):
    db = get_db()
    oid = _oid(post_id)
    comments = await db.comments.find({"post_id": oid}).sort(
        "created_at", 1
    ).to_list(length=1000)

    author_ids = list({c["author_id"] for c in comments})
    authors = {
        u["_id"]: u async for u in db.users.find({"_id": {"$in": author_ids}})
    }
    return [
        comment_public(c, authors[c["author_id"]])
        for c in comments
        if c["author_id"] in authors
    ]


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    post_id: str,
    payload: CreateCommentRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    oid = _oid(post_id)
    post = await db.posts.find_one({"_id": oid})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    parent_oid = None
    if payload.parent_id:
        parent_oid = _oid(payload.parent_id)

    doc = {
        "post_id": oid,
        "author_id": current_user["_id"],
        "body": payload.body.strip(),
        "parent_id": parent_oid,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.comments.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.posts.update_one({"_id": oid}, {"$inc": {"comment_count": 1}})

    if post["author_id"] != current_user["_id"]:
        await db.notifications.insert_one(
            {
                "user_id": post["author_id"],
                "type": "comment",
                "actor_id": current_user["_id"],
                "post_id": oid,
                "message": (
                    f'{current_user.get("name", "Someone")} commented on '
                    f'"{post["headline"]}"'
                ),
                "read": False,
                "created_at": datetime.now(timezone.utc),
            }
        )

    return comment_public(doc, current_user)
