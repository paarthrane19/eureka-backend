from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app.database import get_db
from app.schemas import (
    ChatRoomPublic,
    ContactPublic,
    DirectMessagePublic,
    DMThreadPublic,
    MessagePublic,
    SendMessageRequest,
)
from app.security import get_current_user, user_from_token
from app.serializers import (
    chat_room_public,
    contact_public,
    direct_message_public,
    dm_thread_public,
    message_public,
)

router = APIRouter()


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


# --------------------------------------------------------------------------
# WebSocket connection manager
# --------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, set[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket) -> None:
        self.active.setdefault(channel, set()).add(ws)

    def disconnect(self, channel: str, ws: WebSocket) -> None:
        sockets = self.active.get(channel)
        if not sockets:
            return
        sockets.discard(ws)
        if not sockets:
            self.active.pop(channel, None)

    async def broadcast(self, channel: str, payload: dict) -> None:
        for ws in list(self.active.get(channel, set())):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001 — drop dead sockets silently
                self.disconnect(channel, ws)


manager = ConnectionManager()


# --------------------------------------------------------------------------
# Mutual-follow helper
# --------------------------------------------------------------------------
async def _mutual_follow_ids(db, user_id: ObjectId) -> set[ObjectId]:
    """Return the set of user ids the given user mutually follows."""
    following = {
        f["following_id"]
        async for f in db.follows.find({"follower_id": user_id})
    }
    followers = {
        f["follower_id"]
        async for f in db.follows.find({"following_id": user_id})
    }
    return following & followers


def _sorted_participants(a: ObjectId, b: ObjectId) -> list[ObjectId]:
    return sorted([a, b], key=lambda x: str(x))


# --------------------------------------------------------------------------
# Rooms
# --------------------------------------------------------------------------
@router.get("/rooms", response_model=list[ChatRoomPublic])
async def list_rooms(current_user: dict = Depends(get_current_user)):
    db = get_db()
    me = current_user["_id"]
    rooms = await db.chat_rooms.find({}).to_list(length=200)

    memberships = {
        m["room_id"]: m
        async for m in db.room_members.find({"user_id": me})
    }

    results = []
    for room in rooms:
        room_id = room["_id"]
        member_count = await db.room_members.count_documents({"room_id": room_id})
        membership = memberships.get(room_id)
        joined = membership is not None

        latest = await db.messages.find({"room_id": room_id}).sort(
            "created_at", -1
        ).limit(1).to_list(length=1)
        last_message = latest[0]["body"] if latest else None
        last_message_at = latest[0]["created_at"] if latest else None

        unread = 0
        if joined:
            last_read = membership.get("last_read_at")
            unread_query: dict = {"room_id": room_id}
            if last_read is not None:
                unread_query["created_at"] = {"$gt": last_read}
            unread = await db.messages.count_documents(unread_query)

        results.append(
            chat_room_public(
                room,
                member_count=member_count,
                joined=joined,
                unread=unread,
                last_message=last_message,
                last_message_at=last_message_at,
            )
        )

    # Sort by last_message_at desc, nulls last.
    results.sort(
        key=lambda r: (r["last_message_at"] is not None, r["last_message_at"]),
        reverse=True,
    )
    return results


@router.post("/rooms/{room_id}/join", response_model=ChatRoomPublic)
async def join_room(room_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    oid = _oid(room_id)
    room = await db.chat_rooms.find_one({"_id": oid})
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    now = datetime.now(timezone.utc)
    await db.room_members.update_one(
        {"room_id": oid, "user_id": current_user["_id"]},
        {"$set": {"last_read_at": now}, "$setOnInsert": {"joined_at": now}},
        upsert=True,
    )

    member_count = await db.room_members.count_documents({"room_id": oid})
    latest = await db.messages.find({"room_id": oid}).sort(
        "created_at", -1
    ).limit(1).to_list(length=1)
    return chat_room_public(
        room,
        member_count=member_count,
        joined=True,
        unread=0,
        last_message=latest[0]["body"] if latest else None,
        last_message_at=latest[0]["created_at"] if latest else None,
    )


@router.post("/rooms/{room_id}/leave")
async def leave_room(room_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    oid = _oid(room_id)
    await db.room_members.delete_one({"room_id": oid, "user_id": current_user["_id"]})
    return {"status": "ok"}


@router.get("/rooms/{room_id}/messages", response_model=list[MessagePublic])
async def room_messages(
    room_id: str,
    before: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    oid = _oid(room_id)
    room = await db.chat_rooms.find_one({"_id": oid})
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    query: dict = {"room_id": oid}
    if before:
        try:
            query["created_at"] = {"$lt": datetime.fromisoformat(before)}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid `before` cursor.")

    # Newest-first keyset, then reverse to oldest-first for display.
    docs = await db.messages.find(query).sort("created_at", -1).limit(limit).to_list(
        length=limit
    )
    docs.reverse()

    now = datetime.now(timezone.utc)
    await db.room_members.update_one(
        {"room_id": oid, "user_id": current_user["_id"]},
        {"$set": {"last_read_at": now}},
    )

    return await _decorate_messages(docs, db)


@router.post("/rooms/{room_id}/messages", response_model=MessagePublic)
async def send_room_message(
    room_id: str,
    payload: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    oid = _oid(room_id)
    room = await db.chat_rooms.find_one({"_id": oid})
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    doc = await _insert_room_message(db, oid, current_user["_id"], payload.body)
    message = message_public(doc, current_user)
    await manager.broadcast(f"room:{room_id}", {"type": "message", "message": message})
    return message


# --------------------------------------------------------------------------
# Direct messages
# --------------------------------------------------------------------------
@router.get("/contacts", response_model=list[ContactPublic])
async def list_contacts(current_user: dict = Depends(get_current_user)):
    db = get_db()
    ids = await _mutual_follow_ids(db, current_user["_id"])
    if not ids:
        return []
    users = await db.users.find({"_id": {"$in": list(ids)}}).to_list(length=500)
    return [contact_public(u) for u in users]


@router.get("/dms", response_model=list[DMThreadPublic])
async def list_dms(current_user: dict = Depends(get_current_user)):
    db = get_db()
    me = current_user["_id"]
    threads = await db.dm_threads.find({"participants": me}).to_list(length=500)

    results = []
    for thread in threads:
        other_id = next((p for p in thread["participants"] if p != me), None)
        if other_id is None:
            continue
        other = await db.users.find_one({"_id": other_id})
        if not other:
            continue
        unread = await db.direct_messages.count_documents(
            {"thread_id": thread["_id"], "sender_id": {"$ne": me}, "read": False}
        )
        results.append(dm_thread_public(thread, other, unread=unread))

    results.sort(
        key=lambda t: (t["last_message_at"] is not None, t["last_message_at"]),
        reverse=True,
    )
    return results


@router.post("/dms/with/{user_id}", response_model=DMThreadPublic)
async def open_dm(user_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    me = current_user["_id"]
    other_id = _oid(user_id)

    other = await db.users.find_one({"_id": other_id})
    if not other:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    mutual = await _mutual_follow_ids(db, me)
    if other_id not in mutual:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only message people you mutually follow.",
        )

    participants = _sorted_participants(me, other_id)
    thread = await db.dm_threads.find_one({"participants": participants})
    if not thread:
        now = datetime.now(timezone.utc)
        thread = {
            "participants": participants,
            "created_at": now,
            "last_message": None,
            "last_message_at": None,
        }
        result = await db.dm_threads.insert_one(thread)
        thread["_id"] = result.inserted_id

    unread = await db.direct_messages.count_documents(
        {"thread_id": thread["_id"], "sender_id": {"$ne": me}, "read": False}
    )
    return dm_thread_public(thread, other, unread=unread)


@router.get("/dms/{thread_id}/messages", response_model=list[DirectMessagePublic])
async def dm_messages(
    thread_id: str,
    before: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    oid = _oid(thread_id)
    me = current_user["_id"]
    thread = await db.dm_threads.find_one({"_id": oid})
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if me not in thread["participants"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")

    query: dict = {"thread_id": oid}
    if before:
        try:
            query["created_at"] = {"$lt": datetime.fromisoformat(before)}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid `before` cursor.")

    docs = await db.direct_messages.find(query).sort("created_at", -1).limit(
        limit
    ).to_list(length=limit)
    docs.reverse()

    # Mark incoming messages as read.
    await db.direct_messages.update_many(
        {"thread_id": oid, "sender_id": {"$ne": me}, "read": False},
        {"$set": {"read": True}},
    )

    return await _decorate_direct_messages(docs, db)


@router.post("/dms/{thread_id}/messages", response_model=DirectMessagePublic)
async def send_dm(
    thread_id: str,
    payload: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    oid = _oid(thread_id)
    me = current_user["_id"]
    thread = await db.dm_threads.find_one({"_id": oid})
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if me not in thread["participants"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")

    doc = await _insert_direct_message(db, oid, me, payload.body)
    message = direct_message_public(doc, current_user)
    await manager.broadcast(f"dm:{thread_id}", {"type": "message", "message": message})
    return message


# --------------------------------------------------------------------------
# Shared insert + decorate helpers
# --------------------------------------------------------------------------
async def _insert_room_message(
    db, room_id: ObjectId, author_id: ObjectId, body: str
) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "room_id": room_id,
        "author_id": author_id,
        "body": body.strip(),
        "created_at": now,
    }
    result = await db.messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.room_members.update_one(
        {"room_id": room_id, "user_id": author_id},
        {"$set": {"last_read_at": now}, "$setOnInsert": {"joined_at": now}},
        upsert=True,
    )
    return doc


async def _insert_direct_message(
    db, thread_id: ObjectId, sender_id: ObjectId, body: str
) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "thread_id": thread_id,
        "sender_id": sender_id,
        "body": body.strip(),
        "created_at": now,
        "read": False,
    }
    result = await db.direct_messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.dm_threads.update_one(
        {"_id": thread_id},
        {"$set": {"last_message": doc["body"], "last_message_at": now}},
    )
    return doc


async def _decorate_messages(messages: list[dict], db) -> list[dict]:
    if not messages:
        return []
    author_ids = list({m["author_id"] for m in messages})
    authors = {
        u["_id"]: u async for u in db.users.find({"_id": {"$in": author_ids}})
    }
    result = []
    for m in messages:
        author = authors.get(m["author_id"])
        if author:
            result.append(message_public(m, author))
    return result


async def _decorate_direct_messages(messages: list[dict], db) -> list[dict]:
    if not messages:
        return []
    sender_ids = list({m["sender_id"] for m in messages})
    senders = {
        u["_id"]: u async for u in db.users.find({"_id": {"$in": sender_ids}})
    }
    result = []
    for m in messages:
        sender = senders.get(m["sender_id"])
        if sender:
            result.append(direct_message_public(m, sender))
    return result


# --------------------------------------------------------------------------
# WebSockets
# --------------------------------------------------------------------------
@router.websocket("/ws/room/{room_id}")
async def ws_room(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token")
    user = await user_from_token(token) if token else None
    if user is None:
        await websocket.close(code=1008)
        return

    db = get_db()
    try:
        oid = ObjectId(room_id)
    except InvalidId:
        await websocket.close(code=1008)
        return
    room = await db.chat_rooms.find_one({"_id": oid})
    if not room:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    channel = f"room:{room_id}"
    await manager.connect(channel, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            kind = data.get("type")
            if kind == "message":
                body = (data.get("body") or "").strip()
                if not body:
                    continue
                doc = await _insert_room_message(db, oid, user["_id"], body)
                message = message_public(doc, user)
                await manager.broadcast(
                    channel, {"type": "message", "message": message}
                )
            elif kind == "typing":
                await manager.broadcast(
                    channel,
                    {
                        "type": "typing",
                        "user": {"id": str(user["_id"]), "name": user.get("name", "")},
                        "is_typing": data.get("is_typing", True),
                    },
                )
            elif kind == "read":
                await db.room_members.update_one(
                    {"room_id": oid, "user_id": user["_id"]},
                    {"$set": {"last_read_at": datetime.now(timezone.utc)}},
                )
                await manager.broadcast(
                    channel, {"type": "read", "user_id": str(user["_id"])}
                )
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)


@router.websocket("/ws/dm/{thread_id}")
async def ws_dm(websocket: WebSocket, thread_id: str):
    token = websocket.query_params.get("token")
    user = await user_from_token(token) if token else None
    if user is None:
        await websocket.close(code=1008)
        return

    db = get_db()
    try:
        oid = ObjectId(thread_id)
    except InvalidId:
        await websocket.close(code=1008)
        return
    thread = await db.dm_threads.find_one({"_id": oid})
    if not thread or user["_id"] not in thread["participants"]:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    channel = f"dm:{thread_id}"
    await manager.connect(channel, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            kind = data.get("type")
            if kind == "message":
                body = (data.get("body") or "").strip()
                if not body:
                    continue
                doc = await _insert_direct_message(db, oid, user["_id"], body)
                message = direct_message_public(doc, user)
                await manager.broadcast(
                    channel, {"type": "message", "message": message}
                )
            elif kind == "typing":
                await manager.broadcast(
                    channel,
                    {
                        "type": "typing",
                        "user": {"id": str(user["_id"]), "name": user.get("name", "")},
                        "is_typing": data.get("is_typing", True),
                    },
                )
            elif kind == "read":
                await db.direct_messages.update_many(
                    {"thread_id": oid, "sender_id": {"$ne": user["_id"]}, "read": False},
                    {"$set": {"read": True}},
                )
                await manager.broadcast(
                    channel, {"type": "read", "user_id": str(user["_id"])}
                )
    except WebSocketDisconnect:
        manager.disconnect(channel, websocket)
