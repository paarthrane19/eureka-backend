from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

router = APIRouter()


class WaitlistRequest(BaseModel):
    email: EmailStr


# Eureka has launched publicly, so the waitlist is closed. We intentionally keep
# the `db.waitlist` collection (existing emails are preserved for a possible
# launch announcement) but no longer accept new signups or expose the count.
# The POST route is retained so old clients/links get a clear 410 instead of a
# 404, and so the archived endpoint is documented in one place.


@router.post("", status_code=status.HTTP_410_GONE)
async def join_waitlist(payload: WaitlistRequest):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Supasift has launched — the waitlist is closed. Sign up to join.",
    )
