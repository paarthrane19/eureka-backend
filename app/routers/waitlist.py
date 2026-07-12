from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.database import get_db

router = APIRouter()


class WaitlistRequest(BaseModel):
    email: EmailStr


class WaitlistResponse(BaseModel):
    ok: bool
    count: int


class WaitlistCount(BaseModel):
    count: int


# A small base so the public counter never reads as empty in early days.
_BASE_COUNT = 1240


@router.post("", response_model=WaitlistResponse)
async def join_waitlist(payload: WaitlistRequest):
    db = get_db()
    email = payload.email.lower()
    # Idempotent: upsert so re-submitting the same email is a no-op success.
    await db.waitlist.update_one(
        {"email": email},
        {"$setOnInsert": {"email": email, "created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    total = await db.waitlist.count_documents({})
    return {"ok": True, "count": _BASE_COUNT + total}


@router.get("/count", response_model=WaitlistCount)
async def waitlist_count():
    db = get_db()
    total = await db.waitlist.count_documents({})
    return {"count": _BASE_COUNT + total}
