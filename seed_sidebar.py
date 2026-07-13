"""Seed the discover sidebar: 8 followable questions and 6 study circles.

Replaces any existing questions/circles with a curated set so the right
sidebar (Follow questions, Study circles) renders real, clickable data. Point
it at a database with MONGODB_URI, e.g. the Railway production string:

    MONGODB_URI='mongodb://user:pass@host:port' python seed_sidebar.py

Study circles are seeded with 3-15 synthetic members so member counts look
organic; real users are added on top when they tap Join.
"""

import asyncio
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from bson import ObjectId

from app.database import close_mongo_connection, connect_to_mongo, get_db

# 8 big open science questions, styled as monospace pill badges in the UI.
QUESTIONS: list[tuple[str, str]] = [
    ("Why do black holes evaporate?", "Physics"),
    ("What is dark matter made of?", "Astronomy"),
    ("Is time travel possible?", "Physics"),
    ("What existed before the Big Bang?", "Astronomy"),
    ("Are we alone in the universe?", "Astronomy"),
    ("What is consciousness?", "Biology"),
    ("Can we reverse aging?", "Medicine"),
    ("What is inside a black hole?", "Physics"),
]

# 6 study circles. (name, topic, category, description)
CIRCLES: list[tuple[str, str, str, str]] = [
    (
        "Black Hole Physics",
        "Event horizons, singularities, and Hawking radiation",
        "Physics",
        "Reading group on the strangest objects in the universe.",
    ),
    (
        "Quantum Mechanics 101",
        "From wavefunctions to entanglement, the ground up",
        "Physics",
        "A gentle, rigorous walk through the quantum world.",
    ),
    (
        "Astrobiology",
        "The search for life beyond Earth",
        "Biology",
        "Biosignatures, extremophiles, and habitable worlds.",
    ),
    (
        "Particle Physics",
        "The Standard Model and what lies beyond it",
        "Physics",
        "Quarks, bosons, and the hunt for new physics.",
    ),
    (
        "Dark Matter & Energy",
        "The 95% of the universe we can't see",
        "Astronomy",
        "Tracking the invisible scaffolding of the cosmos.",
    ),
    (
        "Space Exploration",
        "Missions, propulsion, and life off-world",
        "Astronomy",
        "From Artemis to interstellar probes.",
    ),
]


def _resolve_target() -> str:
    uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    if not uri:
        sys.exit(
            "MONGODB_URI is not set. Point it at the target database, e.g.:\n"
            "    MONGODB_URI='<railway connection string>' python seed_sidebar.py"
        )
    return uri


def _mask(uri: str) -> str:
    parts = urlsplit(uri)
    host = parts.hostname or "?"
    port = f":{parts.port}" if parts.port else ""
    netloc = f"***@{host}{port}" if parts.username else f"{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


async def main() -> None:
    uri = _resolve_target()
    print(f"[seed] Connecting to {_mask(uri)}")
    await connect_to_mongo()
    db = get_db()
    now = datetime.now(timezone.utc)

    # Replace any prior set so the sidebar shows exactly this curated content.
    await db.questions.delete_many({})
    await db.study_circles.delete_many({})

    question_docs = []
    for i, (text, category) in enumerate(QUESTIONS):
        followers = [ObjectId() for _ in range(random.randint(40, 900))]
        question_docs.append(
            {
                "text": text,
                "category": category,
                "followers": followers,
                "answer_count": random.randint(5, 45),
                "created_at": now - timedelta(days=i, hours=random.randint(0, 20)),
            }
        )
    await db.questions.insert_many(question_docs)

    circle_docs = []
    for i, (name, topic, category, description) in enumerate(CIRCLES):
        members = [ObjectId() for _ in range(random.randint(3, 15))]
        circle_docs.append(
            {
                "name": name,
                "topic": topic,
                "category": category,
                "description": description,
                "members": members,
                "capacity": 20,
                "created_at": now - timedelta(days=i * 2, hours=random.randint(0, 20)),
            }
        )
    await db.study_circles.insert_many(circle_docs)

    print(
        f"Inserted {len(question_docs)} questions and {len(circle_docs)} study circles."
    )
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
