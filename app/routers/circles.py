from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.schemas import StudyCirclePublic
from app.security import get_current_user
from app.serializers import study_circle_public

router = APIRouter()

CAPACITY = 20


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("", response_model=list[StudyCirclePublic])
async def list_circles(current_user: dict = Depends(get_current_user)):
    db = get_db()
    me = current_user["_id"]
    circles = await db.study_circles.find({}).sort("created_at", -1).to_list(length=200)
    return [
        study_circle_public(c, joined=me in (c.get("members", []) or []))
        for c in circles
    ]


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
