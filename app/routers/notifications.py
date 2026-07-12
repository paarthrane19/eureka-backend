from bson import ObjectId
from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas import NotificationPublic
from app.security import get_current_user
from app.serializers import author_from_user

router = APIRouter()


def _serialize(notif: dict, actor: dict | None) -> dict:
    return {
        "id": str(notif["_id"]),
        "type": notif["type"],
        "actor": author_from_user(actor) if actor else None,
        "post_id": str(notif["post_id"]) if notif.get("post_id") else None,
        "message": notif["message"],
        "read": notif.get("read", False),
        "created_at": notif["created_at"],
    }


@router.get("", response_model=list[NotificationPublic])
async def list_notifications(current_user: dict = Depends(get_current_user)):
    db = get_db()
    notifs = await db.notifications.find({"user_id": current_user["_id"]}).sort(
        "created_at", -1
    ).to_list(length=100)

    actor_ids = list({n["actor_id"] for n in notifs if n.get("actor_id")})
    actors = {
        u["_id"]: u async for u in db.users.find({"_id": {"$in": actor_ids}})
    }
    return [_serialize(n, actors.get(n.get("actor_id"))) for n in notifs]


@router.get("/unread-count")
async def unread_count(current_user: dict = Depends(get_current_user)):
    db = get_db()
    count = await db.notifications.count_documents(
        {"user_id": current_user["_id"], "read": False}
    )
    return {"count": count}


@router.post("/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    db = get_db()
    await db.notifications.update_many(
        {"user_id": current_user["_id"], "read": False}, {"$set": {"read": True}}
    )
    return {"status": "ok"}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str, current_user: dict = Depends(get_current_user)
):
    db = get_db()
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": current_user["_id"]},
        {"$set": {"read": True}},
    )
    return {"status": "ok"}
