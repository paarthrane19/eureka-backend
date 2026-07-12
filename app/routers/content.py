from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status

from app.schemas import CollectionPublic, CuratedContentPublic, DailyDiscoveryPublic
from app.database import get_db
from app.serializers import (
    collection_public,
    curated_content_public,
    daily_discovery_public,
)

router = APIRouter()


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/daily", response_model=DailyDiscoveryPublic)
async def daily():
    db = get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = await db.daily_discovery.find_one({"date": today})
    if not doc:
        # Fall back to the most recent discovery available.
        recent = await db.daily_discovery.find({}).sort("date", -1).limit(1).to_list(
            length=1
        )
        doc = recent[0] if recent else None
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No discovery available"
        )
    return daily_discovery_public(doc)


@router.get("/collections", response_model=list[CollectionPublic])
async def list_collections():
    db = get_db()
    collections = await db.collections.find({}).sort("created_at", -1).to_list(
        length=200
    )
    results = []
    for coll in collections:
        item_count = await db.curated_content.count_documents(
            {"collection_id": coll["_id"]}
        )
        results.append(collection_public(coll, item_count=item_count))
    return results


@router.get("/collections/{collection_id}")
async def get_collection(collection_id: str):
    db = get_db()
    oid = _oid(collection_id)
    coll = await db.collections.find_one({"_id": oid})
    if not coll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
        )
    items = await db.curated_content.find({"collection_id": oid}).sort(
        "order", 1
    ).to_list(length=200)
    return {
        "collection": collection_public(coll, item_count=len(items)),
        "items": [curated_content_public(i) for i in items],
    }


@router.get("/category/{category}")
async def by_category(category: str):
    db = get_db()
    collections = await db.collections.find({"category": category}).to_list(length=200)
    coll_results = []
    for coll in collections:
        item_count = await db.curated_content.count_documents(
            {"collection_id": coll["_id"]}
        )
        coll_results.append(collection_public(coll, item_count=item_count))

    items = await db.curated_content.find({"category": category}).sort(
        "order", 1
    ).limit(20).to_list(length=20)
    return {
        "category": category,
        "collections": coll_results,
        "items": [curated_content_public(i) for i in items],
    }
