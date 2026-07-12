import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.database import get_db
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserPublic
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.serializers import user_public

router = APIRouter()

# A small warm palette used to give each account a distinct avatar colour.
_AVATAR_COLORS = ["#D97757", "#6A8D73", "#7C6BAA", "#C48B3F", "#4F7CAC", "#B0654E"]


def _pick_color(email: str) -> str:
    return _AVATAR_COLORS[sum(ord(c) for c in email) % len(_AVATAR_COLORS)]


async def _unique_username(db, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "", name.lower())[:16] or "user"
    if len(base) < 3:
        base = (base + "user")[:16]
    candidate = base
    suffix = 0
    while await db.users.find_one({"username": candidate}):
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest):
    db = get_db()
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    doc = {
        "username": await _unique_username(db, payload.name.strip()),
        "email": payload.email.lower(),
        "name": payload.name.strip(),
        "password_hash": hash_password(payload.password),
        "bio": "",
        "interests": [],
        "avatar_color": _pick_color(payload.email.lower()),
        "avatar_url": None,
        "cover_image": None,
        "link": None,
        "location": None,
        "working_at": None,
        "verified": False,
        "pinned_post_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    token = create_access_token(str(result.inserted_id))
    return {"access_token": token, "user": user_public(doc)}


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm uses `username`; we treat it as the email.
    db = get_db()
    user = await db.users.find_one({"email": form.username.lower()})
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    token = create_access_token(str(user["_id"]))
    return {"access_token": token, "user": user_public(user)}


@router.post("/login-json", response_model=TokenResponse)
async def login_json(payload: LoginRequest):
    """JSON-friendly login for the mobile client."""
    db = get_db()
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    token = create_access_token(str(user["_id"]))
    return {"access_token": token, "user": user_public(user)}


@router.get("/me", response_model=UserPublic)
async def me(current_user: dict = Depends(get_current_user)):
    db = get_db()
    posts = await db.posts.find({"author_id": current_user["_id"]}).to_list(length=None)
    post_count = len(posts)
    credibility_score = (
        round(sum(p.get("credibility", {}).get("score", 70) for p in posts) / post_count)
        if post_count
        else 0
    )
    return user_public(
        current_user, post_count=post_count, credibility_score=credibility_score
    )
