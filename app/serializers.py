"""Helpers to convert raw MongoDB documents into API-shaped dicts."""


def author_from_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user.get("username", ""),
        "name": user.get("name", "Unknown"),
        "avatar_color": user.get("avatar_color", "#D97757"),
        "avatar_url": user.get("avatar_url"),
        "verified": user.get("verified", False),
    }


def user_public(user: dict, *, post_count: int = 0, credibility_score: int = 0) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user.get("username", ""),
        "email": user["email"],
        "name": user.get("name", ""),
        "bio": user.get("bio", ""),
        "interests": user.get("interests", []),
        "avatar_color": user.get("avatar_color", "#D97757"),
        "avatar_url": user.get("avatar_url"),
        "cover_image": user.get("cover_image"),
        "link": user.get("link"),
        "location": user.get("location"),
        "working_at": user.get("working_at"),
        "verified": user.get("verified", False),
        "pinned_post_id": (
            str(user["pinned_post_id"]) if user.get("pinned_post_id") else None
        ),
        "post_count": post_count,
        "credibility_score": credibility_score,
        "created_at": user["created_at"],
    }


def _post_levels(post: dict) -> list[str]:
    """Return exactly 3 depth levels, defaulting to the body when absent."""
    levels = post.get("levels")
    body = post.get("body", "")
    if isinstance(levels, list) and len(levels) >= 3:
        return [str(lvl) for lvl in levels[:3]]
    # Defensive fallback for legacy docs without depth levels.
    if isinstance(levels, list) and levels:
        base = [str(lvl) for lvl in levels]
        while len(base) < 3:
            base.append(base[-1])
        return base[:3]
    return [body, body, body]


def _post_credibility(post: dict) -> dict:
    """Return a Credibility sub-doc, synthesizing sane defaults if missing."""
    cred = post.get("credibility")
    if isinstance(cred, dict):
        return {
            "score": int(cred.get("score", 70)),
            "verified_count": int(cred.get("verified_count", 0)),
            "sources": [
                {
                    "title": s.get("title", "Source"),
                    "url": s.get("url", ""),
                    "source_type": s.get("source_type", "article"),
                }
                for s in cred.get("sources", [])
                if isinstance(s, dict)
            ],
        }
    # Legacy docs: synthesize a score biased by engagement, no sources.
    upvotes = post.get("upvotes", 0)
    score = max(55, min(90, 60 + upvotes // 10))
    sources: list[dict] = []
    if post.get("source_url"):
        sources.append(
            {
                "title": "Primary source",
                "url": post["source_url"],
                "source_type": "article",
            }
        )
    return {"score": score, "verified_count": 0, "sources": sources}


def post_public(
    post: dict, author: dict, *, upvoted: bool, bookmarked: bool, pinned: bool = False
) -> dict:
    return {
        "id": str(post["_id"]),
        "headline": post["headline"],
        "body": post["body"],
        "category": post["category"],
        "source_url": post.get("source_url"),
        "author": author_from_user(author),
        "created_at": post["created_at"],
        "upvotes": post.get("upvotes", 0),
        "comment_count": post.get("comment_count", 0),
        "upvoted": upvoted,
        "bookmarked": bookmarked,
        "levels": _post_levels(post),
        "credibility": _post_credibility(post),
        "images": post.get("images", []),
        "pinned": pinned,
    }


# ---------- Questions ----------
def question_public(question: dict, *, following: bool) -> dict:
    followers = question.get("followers", []) or []
    return {
        "id": str(question["_id"]),
        "text": question["text"],
        "category": question["category"],
        "follower_count": len(followers),
        "following": following,
        "answer_count": question.get("answer_count", 0),
        "created_at": question["created_at"],
    }


# ---------- Study Circles ----------
def study_circle_public(circle: dict, *, joined: bool) -> dict:
    members = circle.get("members", []) or []
    return {
        "id": str(circle["_id"]),
        "name": circle["name"],
        "topic": circle["topic"],
        "category": circle["category"],
        "description": circle.get("description", ""),
        "member_count": len(members),
        "capacity": circle.get("capacity", 20),
        "joined": joined,
        "created_at": circle["created_at"],
    }


def comment_public(comment: dict, author: dict) -> dict:
    return {
        "id": str(comment["_id"]),
        "post_id": str(comment["post_id"]),
        "body": comment["body"],
        "parent_id": (
            str(comment["parent_id"]) if comment.get("parent_id") else None
        ),
        "author": author_from_user(author),
        "created_at": comment["created_at"],
    }


# ---------- Chat ----------
def message_public(message: dict, author: dict) -> dict:
    return {
        "id": str(message["_id"]),
        "room_id": str(message["room_id"]),
        "author": author_from_user(author),
        "body": message["body"],
        "created_at": message["created_at"],
    }


def direct_message_public(dm: dict, sender: dict) -> dict:
    return {
        "id": str(dm["_id"]),
        "thread_id": str(dm["thread_id"]),
        "sender": author_from_user(sender),
        "body": dm["body"],
        "created_at": dm["created_at"],
        "read": dm.get("read", False),
    }


def chat_room_public(
    room: dict,
    *,
    member_count: int = 0,
    joined: bool = False,
    unread: int = 0,
    last_message: str | None = None,
    last_message_at=None,
) -> dict:
    return {
        "id": str(room["_id"]),
        "name": room["name"],
        "category": room["category"],
        "description": room.get("description", ""),
        "member_count": member_count,
        "joined": joined,
        "unread": unread,
        "last_message": last_message,
        "last_message_at": last_message_at,
    }


def dm_thread_public(
    thread: dict, other: dict, *, unread: int = 0
) -> dict:
    return {
        "id": str(thread["_id"]),
        "other": author_from_user(other),
        "last_message": thread.get("last_message"),
        "last_message_at": thread.get("last_message_at"),
        "unread": unread,
    }


def contact_public(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user.get("name", "Unknown"),
        "avatar_color": user.get("avatar_color", "#D97757"),
        "bio": user.get("bio", ""),
    }


# ---------- Content ----------
def collection_public(collection: dict, *, item_count: int = 0) -> dict:
    return {
        "id": str(collection["_id"]),
        "title": collection["title"],
        "subtitle": collection.get("subtitle", ""),
        "category": collection["category"],
        "accent": collection.get("accent", "#D97757"),
        "emoji": collection.get("emoji", ""),
        "item_count": item_count,
    }


def curated_content_public(item: dict) -> dict:
    return {
        "id": str(item["_id"]),
        "collection_id": str(item["collection_id"]),
        "title": item["title"],
        "body": item["body"],
        "source_url": item.get("source_url"),
        "category": item["category"],
    }


def daily_discovery_public(item: dict) -> dict:
    return {
        "id": str(item["_id"]),
        "date": item["date"],
        "title": item["title"],
        "body": item["body"],
        "category": item["category"],
        "source_url": item.get("source_url"),
        "emoji": item.get("emoji", ""),
    }
