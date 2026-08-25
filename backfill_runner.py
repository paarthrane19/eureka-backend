"""Shared machinery for the hand-written depth-level backfill batches.

batch 01 carried its own copy of this logic. Everything from batch 02 on
imports `run()` instead, so the safety behaviour — length check before any
connection, dry run by default, flagged headlines excluded — is defined once.

A batch module supplies only content:

    from backfill_runner import run

    CONTENT = {"some headline": ("explain text", "deep dive text")}
    FLAGGED = {"a wrong headline": "why it should not be expanded"}

    if __name__ == "__main__":
        sys.exit(asyncio.run(run("batch 02", CONTENT, FLAGGED)))
"""

from __future__ import annotations

import os
from collections import defaultdict

from motor.motor_asyncio import AsyncIOMotorClient

from backfill_depth_levels import (
    DEEP_DIVE_RANGE,
    EXPLAIN_RANGE,
    UNVERIFIABLE,
    is_incomplete,
)


def check_lengths(content: dict[str, tuple[str, str]]) -> list[str]:
    """Report any copy outside the target ranges. Runs before we touch the db."""
    problems = []
    for headline, (explain, deep_dive) in content.items():
        if not EXPLAIN_RANGE[0] <= len(explain) <= EXPLAIN_RANGE[1]:
            problems.append(
                f"  explain {len(explain):>4} chars (want {EXPLAIN_RANGE[0]}-"
                f"{EXPLAIN_RANGE[1]}): {headline}"
            )
        if not DEEP_DIVE_RANGE[0] <= len(deep_dive) <= DEEP_DIVE_RANGE[1]:
            problems.append(
                f"  deep dive {len(deep_dive):>4} chars (want {DEEP_DIVE_RANGE[0]}-"
                f"{DEEP_DIVE_RANGE[1]}): {headline}"
            )
    return problems


async def run(
    label: str,
    content: dict[str, tuple[str, str]],
    flagged: dict[str, str] | None = None,
) -> int:
    flagged = flagged or {}

    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("MONGODB_URI is not set.")
        return 1

    # Default to true so a typo in the env var can never cause a write.
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() != "false"

    overlap = set(content) & set(flagged)
    if overlap:
        print(f"Headlines are both written and flagged: {sorted(overlap)}")
        return 1

    problems = check_lengths(content)
    if problems:
        print("Checked-in copy is outside the target length ranges:")
        print("\n".join(problems))
        return 1

    db_name = os.getenv("MONGODB_DB", "eureka")
    print(f"[{label}] Connecting to {uri.split('@')[-1]} (db: {db_name})")
    db = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=15000)[db_name]

    # Never expand a claim we believe is wrong, whether it was flagged by an
    # earlier batch or by this one.
    skip = set(UNVERIFIABLE) | set(flagged)

    total = 0
    incomplete: list[dict] = []
    async for post in db.posts.find({}):
        total += 1
        if is_incomplete(post):
            incomplete.append(post)

    # Production stores many of these as duplicate pairs, so group by headline
    # and update every incomplete copy.
    targets: dict[str, list[dict]] = defaultdict(list)
    for post in incomplete:
        headline = post["headline"]
        if headline in skip:
            continue
        if headline in content:
            targets[headline].append(post)

    doc_count = sum(len(v) for v in targets.values())

    print()
    print("=" * 72)
    print(f"  Posts in database:            {total}")
    print(f"  Missing level 2 or 3:         {len(incomplete)}")
    print(f"  Headlines in this batch:      {len(content)}")
    print(f"  Headlines matched in db:      {len(targets)}")
    print(f"  Documents to update:          {doc_count}")
    print(f"  Newly flagged, not written:   {len(flagged)}")
    print("=" * 72)

    if flagged:
        print("\nFlagged for manual review — no content written:")
        for headline, reason in flagged.items():
            copies = sum(1 for p in incomplete if p["headline"] == headline)
            print(f"  [{copies}x] {headline}\n        {reason}")

    missing = [h for h in content if h not in targets]
    if missing:
        print("\nIn this batch but NOT matched in the database:")
        for headline in missing:
            print(f"  {headline}")

    print("\nMatched headlines (copies found):")
    for headline, posts in sorted(targets.items()):
        print(f"  {len(posts)}x  [{posts[0].get('category', '?')}] {headline}")

    if not targets:
        print("\nNothing to write.")
        return 0

    if dry_run:
        print("\n" + "=" * 72)
        print("  DRY RUN — no writes. Content that would be applied:")
        print("=" * 72)
        ordered = sorted(targets.items(), key=lambda kv: (kv[1][0].get("category", ""), kv[0]))
        for headline, posts in ordered:
            explain, deep_dive = content[headline]
            post = posts[0]
            hook = (post.get("body") or "").strip()
            print(f"\n[{post.get('category', '?')}] {headline}  ({len(posts)} copy/copies)")
            print(f"  source: {post.get('source_url') or 'none'}")
            print(f"\n  L1 HOOK      ({len(hook)} chars, unchanged)\n    {hook}")
            print(f"\n  L2 EXPLAIN   ({len(explain)} chars)\n    {explain}")
            print(f"\n  L3 DEEP DIVE ({len(deep_dive)} chars)\n    {deep_dive}")
            print("\n" + "-" * 72)
        print(f"\nWould update {doc_count} documents. Re-run with DRY_RUN=false to apply.")
        return 0

    print(f"\nApplying to {doc_count} documents…")
    updated = 0
    for headline, posts in targets.items():
        explain, deep_dive = content[headline]
        for post in posts:
            # Each copy keeps its own body, so body == levels[0] still holds.
            hook = (post.get("body") or "").strip()
            if not hook:
                print(f"  skipped (empty body): {headline}")
                continue
            result = await db.posts.update_one(
                {"_id": post["_id"]},
                {"$set": {"levels": [hook, explain, deep_dive], "body": hook}},
            )
            updated += result.modified_count
    print(f"Updated {updated} documents.")

    remaining = 0
    async for post in db.posts.find({}):
        if is_incomplete(post):
            remaining += 1
    print(f"Still incomplete after this batch: {remaining}")
    return 0
