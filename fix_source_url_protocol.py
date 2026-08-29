"""Prepend https:// to stored source_url values that have no scheme.

A source_url written as "cam.ac.uk/research/news/..." has no protocol, so the
browser resolves it as a *relative path*: the link renders as
supasift.com/app/post/cam.ac.uk/... and 404s. Every stored source_url must be
fully protocol-qualified.

app/schemas.py now normalises source_url on write, so this only has to repair
rows created before that validator existed. It is idempotent — already-qualified
values are not matched, so re-running is a no-op.

Values that cannot be safely qualified (unsafe schemes like javascript:, or a
value with no real domain) are reported and skipped rather than guessed at.

    MONGODB_URI='<connection string>' DRY_RUN=true  python fix_source_url_protocol.py
    MONGODB_URI='<connection string>' DRY_RUN=false python fix_source_url_protocol.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient

from app.urls import InvalidExternalURL, needs_migration, normalize_external_url

# Collections that carry a source_url, per app/serializers.py. Collection
# reading-list items live in curated_content, not a separate items collection.
COLLECTIONS = ("posts", "curated_content", "daily_discovery")

FIELD = "source_url"


async def main() -> int:
    uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    if not uri:
        print("MONGODB_URI is not set.")
        return 1

    # Default to true so a typo in the env var can never cause a write.
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() != "false"
    db_name = os.getenv("MONGO_DB", "eureka")

    client = AsyncIOMotorClient(uri)
    db = client[db_name]

    print(f"database: {db_name}   mode: {'DRY RUN' if dry_run else 'WRITING'}\n")

    existing = set(await db.list_collection_names())
    total_scanned = total_fixed = total_skipped = 0

    for name in COLLECTIONS:
        if name not in existing:
            continue

        fixed = skipped = scanned = 0
        cursor = db[name].find({FIELD: {"$type": "string"}}, {FIELD: 1})

        async for doc in cursor:
            raw = doc.get(FIELD)
            scanned += 1
            if not needs_migration(raw):
                continue

            try:
                normalized = normalize_external_url(raw)
            except InvalidExternalURL as exc:
                skipped += 1
                print(f"  SKIP  {name}/{doc['_id']}: {raw!r} — {exc}")
                continue

            if not normalized or normalized == raw:
                continue

            print(f"  FIX   {name}/{doc['_id']}: {raw!r} -> {normalized!r}")
            if not dry_run:
                await db[name].update_one(
                    {"_id": doc["_id"]}, {"$set": {FIELD: normalized}}
                )
            fixed += 1

        total_scanned += scanned
        total_fixed += fixed
        total_skipped += skipped
        print(f"{name}: {scanned} scanned, {fixed} to fix, {skipped} unfixable")

    print(
        f"\ntotal: {total_scanned} scanned, {total_fixed} "
        f"{'would be ' if dry_run else ''}updated, {total_skipped} skipped"
    )
    if dry_run and total_fixed:
        print("Re-run with DRY_RUN=false to apply.")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
