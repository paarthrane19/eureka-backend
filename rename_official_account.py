"""Rename the official content account from @eureka to @supasift.

The account is looked up by username (settings.agent_username), so flipping
that default without renaming the existing row would make
`_get_or_create_official` miss the live account and create a second one —
leaving every published official post attributed to an orphaned @eureka.

Run this once against each deployed database, before or right after the
rebrand deploy. It is idempotent: if the account has already been renamed
there is nothing to match and it exits cleanly.

    MONGODB_URI='<connection string>' DRY_RUN=true  python rename_official_account.py
    MONGODB_URI='<connection string>' DRY_RUN=false python rename_official_account.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient

OLD_USERNAME = "eureka"
NEW_USERNAME = "supasift"

UPDATES = {
    "username": NEW_USERNAME,
    "display_name": "Supasift Official",
    "name": "Supasift Official",
    "email": "agent@supasift.com",
    "bio": "The official Supasift account. One genuinely fascinating, sourced science discovery at a time.",
    "working_at": "Supasift",
    "link": "https://supasift.com",
}


async def main() -> int:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("MONGODB_URI is not set.")
        return 1

    # Default to true so a typo in the env var can never cause a write.
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() != "false"

    db_name = os.getenv("MONGODB_DB", "eureka")
    print(f"[rename] Connecting to {uri.split('@')[-1]} (db: {db_name})")
    db = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=15000)[db_name]

    old = await db.users.find_one({"username": OLD_USERNAME})
    new = await db.users.find_one({"username": NEW_USERNAME})

    if new and old:
        print(
            f"Both @{OLD_USERNAME} and @{NEW_USERNAME} exist. Refusing to guess "
            "which is canonical — merge them by hand."
        )
        return 1

    if not old:
        print(
            f"No @{OLD_USERNAME} account found."
            + (f" @{NEW_USERNAME} already exists — nothing to do." if new else "")
        )
        return 0

    post_count = await db.posts.count_documents({"author_id": old["_id"]})

    print()
    print("=" * 72)
    print(f"  Account _id:        {old['_id']}")
    print(f"  Posts attributed:   {post_count}")
    print("=" * 72)
    for field, value in UPDATES.items():
        print(f"  {field:<14} {old.get(field)!r}\n  {'':<14} -> {value!r}")

    if dry_run:
        print("\nDRY RUN — no writes. Re-run with DRY_RUN=false to apply.")
        return 0

    result = await db.users.update_one({"_id": old["_id"]}, {"$set": UPDATES})
    print(f"\nUpdated {result.modified_count} account.")
    print(f"{post_count} posts keep their author_id, so attribution is preserved.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
