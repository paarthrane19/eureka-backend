from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent_scheduler import start_agent_scheduler, stop_agent_scheduler
from app.config import get_settings
from app.database import close_mongo_connection, connect_to_mongo
from app.routers import (
    auth,
    chat,
    circles,
    comments,
    content,
    notifications,
    posts,
    questions,
    uploads,
    users,
    waitlist,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    start_agent_scheduler()
    yield
    stop_agent_scheduler()
    await close_mongo_connection()


app = FastAPI(title="Eureka API", version="1.0.0", lifespan=lifespan)

# Native/mobile clients (Expo Go, etc.) aren't subject to CORS at all, so this
# only gates browser access. Explicit origins come from CORS_ORIGINS (see
# app/config.py); *.vercel.app is also allowed via regex so Vercel preview
# deployments work without redeploying the backend for every branch.
_settings = get_settings()
_cors_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(posts.router, prefix="/posts", tags=["posts"])
app.include_router(comments.router, tags=["comments"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(content.router, prefix="/content", tags=["content"])
app.include_router(questions.router, prefix="/questions", tags=["questions"])
app.include_router(circles.router, prefix="/circles", tags=["circles"])
app.include_router(waitlist.router, prefix="/waitlist", tags=["waitlist"])
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": "eureka-api"}


@app.get("/categories", tags=["meta"])
async def categories():
    return {"categories": get_settings().categories}
