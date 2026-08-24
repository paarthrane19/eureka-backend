from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db
from app.schemas import (
    CircleMessagePublic,
    SendCircleMessageRequest,
    StudyCircleDetail,
    StudyCirclePublic,
)
from app.security import get_current_user, get_optional_user
from app.serializers import (
    circle_message_public,
    study_circle_detail,
    study_circle_public,
)

router = APIRouter()

CAPACITY = 20

# Cap on the roster we resolve for the circle page — circles are capped at 20
# members, so this is generous headroom rather than a real limit.
MEMBER_FETCH_LIMIT = 100


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("", response_model=list[StudyCirclePublic])
async def list_circles(current_user: dict | None = Depends(get_optional_user)):
    # Public discovery: anyone can browse study circles. The `joined` flag is
    # personalised only when a signed-in user is present.
    db = get_db()
    me = current_user["_id"] if current_user else None
    circles = await db.study_circles.find({}).sort("created_at", -1).to_list(length=200)
    return [
        study_circle_public(
            c, joined=me is not None and me in (c.get("members", []) or [])
        )
        for c in circles
    ]


async def _load_circle(db, oid: ObjectId) -> dict:
    circle = await db.study_circles.find_one({"_id": oid})
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found"
        )
    return circle


async def _roster(db, circle: dict) -> list[dict]:
    """Resolve a circle's member ids to user docs, in join order."""
    member_ids = (circle.get("members", []) or [])[:MEMBER_FETCH_LIMIT]
    if not member_ids:
        return []
    users = {
        u["_id"]: u
        async for u in db.users.find({"_id": {"$in": member_ids}})
    }
    # Preserve membership order so the roster is stable between requests.
    return [users[mid] for mid in member_ids if mid in users]


@router.get("/{circle_id}", response_model=StudyCircleDetail)
async def get_circle(
    circle_id: str, current_user: dict | None = Depends(get_optional_user)
):
    # Public preview: anyone can read a circle's details and roster. Joining
    # and posting are gated separately.
    db = get_db()
    circle = await _load_circle(db, _oid(circle_id))
    me = current_user["_id"] if current_user else None
    return study_circle_detail(
        circle,
        joined=me is not None and me in (circle.get("members", []) or []),
        members=await _roster(db, circle),
    )


@router.get("/{circle_id}/messages", response_model=list[CircleMessagePublic])
async def list_circle_messages(
    circle_id: str,
    before: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    _: dict | None = Depends(get_optional_user),
):
    # Readable by anyone so non-members can preview the discussion before
    # deciding to join. Posting still requires membership.
    db = get_db()
    oid = _oid(circle_id)
    await _load_circle(db, oid)

    query: dict = {"circle_id": oid}
    if before:
        try:
            query["created_at"] = {"$lt": datetime.fromisoformat(before)}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid `before` cursor.")

    # Newest-first keyset for pagination, reversed to oldest-first for display.
    docs = await db.circle_messages.find(query).sort("created_at", -1).limit(
        limit
    ).to_list(length=limit)
    docs.reverse()
    if not docs:
        return []

    author_ids = list({m["author_id"] for m in docs})
    authors = {
        u["_id"]: u async for u in db.users.find({"_id": {"$in": author_ids}})
    }
    return [
        circle_message_public(m, authors[m["author_id"]])
        for m in docs
        if m["author_id"] in authors
    ]


@router.post("/{circle_id}/messages", response_model=CircleMessagePublic)
async def send_circle_message(
    circle_id: str,
    payload: SendCircleMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    oid = _oid(circle_id)
    circle = await _load_circle(db, oid)
    me = current_user["_id"]

    # Only members may post — the UI shows a Join prompt for everyone else.
    if me not in (circle.get("members", []) or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Join this circle to post in the discussion.",
        )

    doc = {
        "circle_id": oid,
        "author_id": me,
        "body": payload.body.strip(),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.circle_messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return circle_message_public(doc, current_user)


@router.post("/{circle_id}/join", response_model=StudyCirclePublic)
async def join_circle(circle_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    oid = _oid(circle_id)
    me = current_user["_id"]
    circle = await db.study_circles.find_one({"_id": oid})
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found"
        )

    members = circle.get("members", []) or []
    if me in members:
        # Already a member — no-op success.
        return study_circle_public(circle, joined=True)

    capacity = circle.get("capacity", CAPACITY)
    if len(members) >= capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This circle is full"
        )

    await db.study_circles.update_one({"_id": oid}, {"$addToSet": {"members": me}})
    fresh = await db.study_circles.find_one({"_id": oid})
    return study_circle_public(fresh, joined=True)


@router.post("/{circle_id}/leave", response_model=StudyCirclePublic)
async def leave_circle(circle_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    oid = _oid(circle_id)
    me = current_user["_id"]
    circle = await db.study_circles.find_one({"_id": oid})
    if not circle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found"
        )

    await db.study_circles.update_one({"_id": oid}, {"$pull": {"members": me}})
    fresh = await db.study_circles.find_one({"_id": oid})
    return study_circle_public(fresh, joined=False)
