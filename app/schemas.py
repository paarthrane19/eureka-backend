from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPublic"


# ---------- Users ----------
class UserPublic(BaseModel):
    id: str
    username: str
    email: EmailStr
    name: str
    bio: str = ""
    interests: list[str] = []
    avatar_color: str = "#D97757"
    avatar_url: str | None = None
    cover_image: str | None = None
    link: str | None = None
    location: str | None = None
    working_at: str | None = None
    verified: bool = False
    pinned_post_id: str | None = None
    post_count: int = 0
    credibility_score: int = 0
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    bio: str | None = Field(default=None, max_length=160)
    interests: list[str] | None = None
    link: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=60)
    working_at: str | None = Field(default=None, max_length=60)
    avatar_url: str | None = None
    cover_image: str | None = None


class PinPostRequest(BaseModel):
    post_id: str | None = None  # None unpins


class OnboardingRequest(BaseModel):
    interests: list[str] = Field(min_length=3)


# ---------- Posts ----------
class CreatePostRequest(BaseModel):
    headline: str = Field(min_length=1, max_length=140)
    body: str = Field(min_length=1, max_length=280)
    category: str
    source_url: str | None = Field(default=None, max_length=500)
    images: list[str] = Field(default_factory=list, max_length=2)


class Author(BaseModel):
    id: str
    username: str
    name: str
    avatar_color: str = "#D97757"
    avatar_url: str | None = None
    verified: bool = False


class Source(BaseModel):
    title: str
    url: str
    source_type: str  # one of: "journal", "university", "article", "dataset", "preprint"


class Credibility(BaseModel):
    score: int  # 0-100 integer
    verified_count: int  # how many users verified it
    sources: list[Source] = []


class PostPublic(BaseModel):
    id: str
    headline: str
    body: str
    category: str
    source_url: str | None = None
    author: Author
    created_at: datetime
    upvotes: int = 0
    comment_count: int = 0
    upvoted: bool = False
    bookmarked: bool = False
    levels: list[str] = []
    credibility: Credibility
    images: list[str] = []
    pinned: bool = False


# ---------- Questions ----------
class QuestionPublic(BaseModel):
    id: str
    text: str
    category: str
    follower_count: int = 0
    following: bool = False
    answer_count: int = 0
    created_at: datetime


# ---------- Study Circles ----------
class StudyCirclePublic(BaseModel):
    id: str
    name: str
    topic: str
    category: str
    description: str
    member_count: int = 0
    capacity: int = 20
    joined: bool = False
    created_at: datetime


# ---------- Comments ----------
class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=280)
    parent_id: str | None = None


class CommentPublic(BaseModel):
    id: str
    post_id: str
    body: str
    parent_id: str | None = None
    author: Author
    created_at: datetime


# ---------- Notifications ----------
class NotificationPublic(BaseModel):
    id: str
    type: str
    actor: Author | None = None
    post_id: str | None = None
    message: str
    read: bool = False
    created_at: datetime


# ---------- Chat ----------
class ChatRoomPublic(BaseModel):
    id: str
    name: str
    category: str
    description: str
    member_count: int = 0
    joined: bool = False
    unread: int = 0
    last_message: str | None = None
    last_message_at: datetime | None = None


class MessagePublic(BaseModel):
    id: str
    room_id: str
    author: Author
    body: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class DMThreadPublic(BaseModel):
    id: str
    other: Author
    last_message: str | None = None
    last_message_at: datetime | None = None
    unread: int = 0


class DirectMessagePublic(BaseModel):
    id: str
    thread_id: str
    sender: Author
    body: str
    created_at: datetime
    read: bool


class ContactPublic(BaseModel):
    id: str
    name: str
    avatar_color: str = "#D97757"
    bio: str = ""


# ---------- Content ----------
class CollectionPublic(BaseModel):
    id: str
    title: str
    subtitle: str
    category: str
    accent: str
    emoji: str
    item_count: int = 0


class CuratedContentPublic(BaseModel):
    id: str
    collection_id: str
    title: str
    body: str
    source_url: str | None = None
    category: str


class DailyDiscoveryPublic(BaseModel):
    id: str
    date: str
    title: str
    body: str
    category: str
    source_url: str | None = None
    emoji: str


# ---------- Uploads ----------
class UploadResponse(BaseModel):
    data_url: str


TokenResponse.model_rebuild()
