import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from limits import parse as parse_rate_limit

from app.config import get_settings
from app.database import get_db
from app.email import send_password_reset_email
from app.ratelimit import limiter
from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserPublic,
)
from app.security import (
    create_access_token,
    generate_reset_token,
    get_current_user,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.serializers import user_public

router = APIRouter()

RESET_TOKEN_LIFETIME = timedelta(hours=1)
# Same response whether or not the email has an account, so the endpoint
# never reveals which emails are registered.
_FORGOT_PASSWORD_RESPONSE = {
    "message": "If that email exists, we've sent a reset link."
}
# Per-email cap, independent of the per-IP limit on the route below — someone
# rotating IPs shouldn't be able to spam a single inbox with reset emails.
_FORGOT_PASSWORD_EMAIL_LIMIT = parse_rate_limit("3/hour")

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


# Auth routes get tight per-IP limits (well below the global 240/min default) to
# blunt credential stuffing and signup spam now that the site is public. slowapi
# reads the client IP off `request`, so these handlers must accept it explicitly.
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def signup(request: Request, payload: SignupRequest):
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
@limiter.limit("10/minute")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
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
@limiter.limit("10/minute")
async def login_json(request: Request, payload: LoginRequest):
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


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def forgot_password(request: Request, payload: ForgotPasswordRequest):
    email = payload.email.lower()

    # Hit the per-email limit before touching the database. Still returning
    # the generic response when it's exceeded — a distinct "you're being rate
    # limited" reply would itself leak that the email has been targeted.
    within_limit = limiter.limiter.hit(_FORGOT_PASSWORD_EMAIL_LIMIT, "forgot-password", email)
    if not within_limit:
        return _FORGOT_PASSWORD_RESPONSE

    db = get_db()
    user = await db.users.find_one({"email": email})
    if user:
        raw_token = generate_reset_token()
        await db.password_resets.insert_one(
            {
                "user_id": user["_id"],
                "token_hash": hash_reset_token(raw_token),
                "expires_at": datetime.now(timezone.utc) + RESET_TOKEN_LIFETIME,
                "used": False,
                "created_at": datetime.now(timezone.utc),
            }
        )
        reset_url = f"{get_settings().frontend_url}/reset-password?token={raw_token}"
        await send_password_reset_email(email, reset_url)

    return _FORGOT_PASSWORD_RESPONSE


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def reset_password(request: Request, payload: ResetPasswordRequest):
    db = get_db()
    token_hash = hash_reset_token(payload.token)

    # Atomically claim the token: only a record that's unused and unexpired
    # matches, and marking it used in the same operation closes the race
    # where two requests both read "unused" before either writes back.
    record = await db.password_resets.find_one_and_update(
        {
            "token_hash": token_hash,
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        },
        {"$set": {"used": True}},
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired.",
        )

    await db.users.update_one(
        {"_id": record["user_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    return {"message": "Your password has been reset. You can now sign in."}
