"""Publish the 2026-08-30 editorial batch: 10 science posts, three depth levels each.

Copy is held in content/drafts/2026-08-30-science-posts.md; this script is the
thing that actually writes it to the database, attributed to the official
account. Keep the two in sync — the markdown carries the visual-concept notes
and source provenance that have no column here.

Idempotent: posts are matched on headline, so re-running skips anything already
published rather than creating duplicates.

    MONGODB_URI='<connection string>' DRY_RUN=true  python publish_drafts_2026_08_30.py
    MONGODB_URI='<connection string>' DRY_RUN=false python publish_drafts_2026_08_30.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.database import close_mongo_connection, connect_to_mongo, get_db
from app.routers.admin import _get_or_create_official
from app.schemas import LEVEL_LIMITS
from app.urls import normalize_external_url

HEADLINE_LIMIT = 100

# headline, l1 (hook), l2 (explain), l3 (deep dive), category, source_url.
POSTS: list[dict] = [
    {
        "headline": "Clocks run measurably slower closer to Earth's centre",
        "l1": "Your head ages faster than your feet. It's been measured.",
        "l2": "Gravity slows time. The closer you are to Earth's centre, the slower your clock runs — so your feet, being lower, age fractionally slower than your head.",
        "l3": "In 2010, NIST physicists measured this at a scale of 33 centimetres — about a foot — showing you age faster standing a couple of steps higher on a staircase. The difference is far too small to perceive: roughly 90 billionths of a second across a 79-year lifetime. In 2022, JILA physicists pushed the measurement down to one millimetre, roughly the width of a pencil tip, published in Nature.",
        "category": "Physics",
        "source_url": "https://www.nist.gov/news-events/news/2010/09/nist-clock-experiment-demonstrates-your-head-older-your-feet",
    },
    {
        "headline": "The 10-to-1 microbe ratio was an estimate nobody rechecked",
        "l1": "\u201cMicrobes outnumber your cells 10 to 1\u201d was never actually measured.",
        "l2": "It's one of the most repeated facts in popular biology. It came from a back-of-the-envelope estimate in 1972 that was never meant to be quoted widely.",
        "l3": "In 2016, Sender, Fuchs and Milo revisited the claim in Cell and found the real ratio is much closer to 1:1. They traced the 10:1 figure back to a single 1972 paper. One researcher had already called it a \u201cfake fact\u201d in 2014. The better payoff is buried in their results: red blood cells account for 84 percent of all cells in your body by number.",
        "category": "Biology",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/26824647/",
    },
    {
        "headline": "Tardigrades survived ten days exposed to open space",
        "l1": "Animals were opened to the vacuum of space. They came back and laid eggs.",
        "l2": "Tardigrades — microscopic eight-legged animals — were bolted to the outside of a spacecraft in trays open to the void.",
        "l3": "The TARDIS experiment flew on ESA's Biopan-6 platform during the FOTON-M3 mission in September 2007. Desiccated adults of two species were exposed to space vacuum and UV radiation at 258–281 km altitude for ten days. Those shielded from solar UV survived at rates similar to Earthbound controls and laid eggs that hatched normally after rehydration. Crucially, the animals were dehydrated before launch — the experiment did not test whether an active, hydrated tardigrade could survive.",
        "category": "Biology",
        "source_url": "https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/Research/Tiny_animals_survive_exposure_to_space",
    },
    {
        "headline": "Laser ranging shows the Moon receding 3.8 cm a year",
        "l1": "The Moon retreats 3.8 cm a year, and mirrors on its surface prove it.",
        "l2": "Apollo astronauts left retroreflector arrays on the lunar surface. Fire a laser at them from Earth, time the round trip, and you get the distance.",
        "l3": "Lunar laser ranging has shown the Earth-Moon distance increases by 3.8 centimetres a year. Five reflector arrays sit on the Moon — three from Apollo, two on Soviet rovers. Over half a century, measurement precision has improved from a few hundred millimetres to a few millimetres. It is the only Apollo science experiment still running.",
        "category": "Astronomy",
        "source_url": "https://www.jpl.nasa.gov/news/the-apollo-experiment-that-keeps-on-giving/",
    },
    {
        "headline": "Natural nuclear reactors ran at Oklo two billion years ago",
        "l1": "Nuclear reactors ran in Gabon two billion years ago. Nobody built them.",
        "l2": "In 1972, a French processing plant found uranium ore with slightly too little U-235. The only explanation was that fission had already happened, naturally, underground.",
        "l3": "Physicist Francis Perrin traced the anomaly to natural fission around two billion years ago. Groundwater acted as the neutron moderator, the same role water plays in a modern light-water reactor. At that time U-235 made up about 3.68% of natural uranium, compared with 0.72% today — enrichment comparable to commercial fuel. Sixteen reactor zones were eventually found at Oklo, plus a seventeenth at Bangombé 30 km away.",
        "category": "Earth Science",
        "source_url": "https://www.iaea.org/newscenter/news/meet-oklo-the-earths-two-billion-year-old-only-known-natural-nuclear-reactor",
    },
    {
        "headline": "Venus rotates more slowly than it orbits the Sun",
        "l1": "Venus takes longer to turn once than to circle the Sun.",
        "l2": "It spins so slowly that it finishes a full lap of the Sun before completing a single rotation.",
        "l3": "Venus rotates once every 243 Earth days relative to the distant stars, while orbiting the Sun in about 225. Its rotation is also retrograde — clockwise viewed from the north pole, meaning the Sun rises in the west. There's a catch worth knowing: the sunrise-to-sunrise “solar day” is only about 117 Earth days, because the retrograde spin and orbital motion pull against each other. The fact is only true once you specify which clock you mean. The cause of the backwards rotation is still poorly understood.",
        "category": "Astronomy",
        "source_url": "https://www.aeronomie.be/en/encyclopedia/venus-backwards-rotation-and-orbital-period",
    },
    {
        "headline": "Quantum tunnelling is what keeps the Sun burning",
        "l1": "The Sun's core isn't hot enough to fuse hydrogen. It fuses anyway.",
        "l2": "Protons repel each other. Classically, they'd never get close enough for the strong force to take over — the core just isn't hot enough to force it.",
        "l3": "Classically, a proton-proton reaction requires kinetic energy above roughly 550 keV to clear the Coulomb barrier, far more than the core provides. Faced with this, Eddington famously remarked that if the centre of the Sun wasn't hot enough for the nuclear physicists, they should find a hotter place. Quantum mechanics resolved it: protons behave as waves, and there's a small probability of tunnelling straight through the barrier. The probability per pair is tiny, but there are so many protons that it's enough to keep the Sun shining for billions of years.",
        "category": "Physics",
        "source_url": "https://vikdhillon.staff.shef.ac.uk/teaching/phy213/phy213_fusion2.html",
    },
    {
        "headline": "Solar neutrinos pass through the Earth almost untouched",
        "l1": "Tens of billions of solar neutrinos cross every square centimetre of you each second.",
        "l2": "They're produced by fusion in the Sun's core, and matter is almost perfectly transparent to them.",
        "l3": "The solar neutrino flux at Earth is roughly 65 billion per square centimetre per second, and the flux is identical on the night side because the planet is transparent to them. Only about one in every 100 billion produced in the solar core is stopped or deflected on its way out, which is exactly why they're useful — they escape directly into space, letting us see into the solar interior. A mismatch between predicted and measured flux, first spotted in the mid-1960s, went unresolved until around 2002.",
        "category": "Astronomy",
        "source_url": "https://en.wikipedia.org/wiki/Solar_neutrino_problem",
    },
    {
        "headline": "Most of an octopus's neurons are in its arms",
        "l1": "Two-thirds of an octopus's neurons sit outside its brain.",
        "l2": "Most of its nervous system lives in its arms, which can sense and act with a striking amount of local independence.",
        "l3": "The common octopus has around 500 million neurons — comparable to a dog — with about two-thirds of them in the arms rather than the central brain. The central brain holds roughly 170-180 million, while each arm carries its own bundle plus a brachial ganglion at its base. Severed arms, when electrically stimulated, still move in the same basic patterns as arms under normal control. Worth noting: a study suggests arms and brain are more connected than previously thought, so \u201cnine brains\u201d is a metaphor, not a literal claim.",
        "category": "Biology",
        "source_url": "https://www.nhm.ac.uk/discover/octopuses-keep-surprising-us-here-are-eight-examples-how.html",
    },
    {
        "headline": "The Banach-Tarski paradox splits one ball into two",
        "l1": "A solid ball can be cut into pieces and rebuilt as two identical balls.",
        "l2": "Not a trick or an approximation. It's a proven theorem — the catch is in what \u201cpieces\u201d means.",
        "l3": "Banach and Tarski proved in 1924 that a solid three-dimensional ball can be split into pieces that recombine into two identical copies of the original, using only rotations and translations. The pieces have no well-defined volume — their existence depends on the axiom of choice. They aren't chunks or slices but infinitely complex, dust-like clouds of points. Most mathematicians don't treat it as a flaw, but as a demonstration that maths can depart from physical intuition without contradicting itself.",
        "category": "Math",
        "source_url": "https://www.quantamagazine.org/how-a-mathematical-paradox-allows-infinite-cloning-20210826/",
    },
]


def validate() -> list[str]:
    """Check every post against the same limits the API enforces on write."""
    errors: list[str] = []
    for i, p in enumerate(POSTS, 1):
        if len(p["headline"]) > HEADLINE_LIMIT:
            errors.append(f"#{i} headline {len(p['headline'])} > {HEADLINE_LIMIT}")
        levels = [p["l1"], p["l2"], p["l3"]]
        for name, text, limit in zip(("l1", "l2", "l3"), levels, LEVEL_LIMITS):
            if not text.strip():
                errors.append(f"#{i} {name} is empty")
            if len(text) > limit:
                errors.append(f"#{i} {name} {len(text)} > {limit}")
        # The API rejects identical levels — the depth arrows would step
        # between three copies of the same paragraph.
        if len(set(levels)) != 3:
            errors.append(f"#{i} levels are not all distinct")
        try:
            normalize_external_url(p["source_url"])
        except ValueError as exc:
            errors.append(f"#{i} source_url: {exc}")
    return errors


async def main() -> int:
    errors = validate()
    if errors:
        print("Refusing to publish — copy does not fit the API limits:")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"{len(POSTS)} posts pass headline/level/source validation.\n")

    if not (os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")):
        print("MONGODB_URI is not set.")
        return 1

    # Default to true so a typo in the env var can never cause a write.
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() != "false"
    print(f"mode: {'DRY RUN' if dry_run else 'WRITING'}\n")

    await connect_to_mongo()
    db = get_db()
    # _get_or_create_official writes, so a dry run must not call it.
    if dry_run:
        official = await db.users.find_one({"username": get_settings().agent_username})
        if not official:
            print(
                f"No @{get_settings().agent_username} account yet; "
                "it would be created on the real run."
            )
            official = {"username": get_settings().agent_username, "_id": None}
    else:
        official = await _get_or_create_official(db)
    print(f"author: @{official['username']} ({official['_id']})\n")

    now = datetime.now(timezone.utc)
    created = skipped = 0

    for i, p in enumerate(POSTS):
        if await db.posts.find_one({"headline": p["headline"]}):
            print(f"  SKIP    already published: {p['headline']}")
            skipped += 1
            continue

        doc = {
            "headline": p["headline"],
            "body": p["l1"],
            "levels": [p["l1"], p["l2"], p["l3"]],
            "category": p["category"],
            "source_url": normalize_external_url(p["source_url"]),
            "images": [],
            "author_id": official["_id"],
            # Space the batch out so the feed doesn't show ten posts on one
            # timestamp, which would make the ordering arbitrary.
            "created_at": now - timedelta(minutes=7 * (len(POSTS) - i)),
            "upvotes": 0,
            "comment_count": 0,
        }
        print(f"  PUBLISH [{p['category']}] {p['headline']}")
        if not dry_run:
            await db.posts.insert_one(doc)
        created += 1

    print(
        f"\ntotal: {created} {'would be ' if dry_run else ''}published, "
        f"{skipped} skipped"
    )
    if dry_run and created:
        print("Re-run with DRY_RUN=false to publish.")

    await close_mongo_connection()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
