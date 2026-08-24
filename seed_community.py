"""Seed the community surfaces: topic chat rooms and study-circle discussions.

Fills in the two collections that made Chat and Circles look broken:

  * `chat_rooms` + `messages` — one room per science category, each with a
    realistic 8-12 message conversation between the existing seed users.
  * `study_circles.members` + `circle_messages` — real (not synthetic) member
    rosters and a 5-8 message discussion per circle.

Safe to re-run: the room/message/circle-message collections are rebuilt from
scratch each time, and circles are matched by name so their _ids stay stable
(existing links and any real user memberships survive).

Requires users and study circles to exist already — run seed_posts.py first.

    MONGODB_URI='<railway connection string>' python seed_community.py
"""

import asyncio
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from app.database import close_mongo_connection, connect_to_mongo, get_db

# ---------------------------------------------------------------------------
# Chat rooms — one per science category, so the room list mirrors the feed
# filters a user already knows.
# ---------------------------------------------------------------------------
ROOMS: list[tuple[str, str, str]] = [
    (
        "physics",
        "Physics",
        "Forces, fields, and the rules everything else is built on.",
    ),
    (
        "astronomy",
        "Astronomy",
        "Telescopes, missions, and everything past the atmosphere.",
    ),
    (
        "biology",
        "Biology",
        "Cells, genomes, ecosystems, and the machinery of life.",
    ),
    (
        "chemistry",
        "Chemistry",
        "Bonds, reactions, and the materials they make possible.",
    ),
    (
        "math",
        "Math",
        "Proofs, patterns, and the occasional beautiful counterexample.",
    ),
    (
        "earth-science",
        "Earth Science",
        "Climate, oceans, tectonics, and deep time.",
    ),
    (
        "technology",
        "Technology",
        "Computing, instrumentation, and the tools that move science.",
    ),
    (
        "medicine",
        "Medicine",
        "Trials, treatments, and translating research into care.",
    ),
]

# Conversations keyed by room slug. Each entry is (username, body) and is laid
# out oldest → newest; timestamps are assigned on insert.
ROOM_CONVERSATIONS: dict[str, list[tuple[str, str]]] = {
    "physics": [
        ("quantumleo", "Trying to build better intuition for why entanglement isn't faster-than-light signalling. I get the math, but the story I tell myself keeps being wrong."),
        ("mirachandra", "The trick is that neither side sees anything unusual in their own data. Alice's outcomes look like fair coin flips no matter what Bob does. The correlation only shows up when you compare notes over a classical channel."),
        ("quantumleo", "So the 'spooky' part is entirely in the comparison, not in either measurement."),
        ("mirachandra", "Exactly. No-signalling is a theorem, not an accident — the marginal distribution on one side is independent of the other side's setting."),
        ("rajpatel", "The thing that finally made it click for me was realising a shared random seed reproduces classical correlation just fine. Bell's inequality is the test for whether you need something stronger than a shared seed."),
        ("quantumleo", "And experiment says you do. CHSH violations up past 2.7 at this point?"),
        ("mirachandra", "With the loophole-free runs from 2015 onward, yes. Detection and locality loopholes closed in the same experiment, which is the part that took decades."),
        ("tomnowak", "Worth adding that 'no faster-than-light signalling' survives even in interpretations that are explicitly nonlocal, like Bohmian mechanics. The nonlocality just isn't controllable."),
        ("rajpatel", "That's a nice framing. Nonlocal but not usable."),
        ("quantumleo", "Okay, this helped. The mistake I kept making was imagining Bob could tell his qubit had been measured."),
        ("mirachandra", "Very common mistake. He can't — his reduced density matrix is maximally mixed either way."),
    ],
    "astronomy": [
        ("astrokat", "JWST's latest early-galaxy candidates are still coming in brighter and more massive than most pre-launch models predicted. Curious how people here are reading it."),
        ("elenavasquez", "My read is that it's a star-formation-efficiency problem before it's a cosmology problem. You can get a long way with burstier early star formation and a top-heavy IMF."),
        ("astrokat", "Agreed on ordering. The 'JWST breaks cosmology' headlines skipped straight past several astrophysical knobs."),
        ("rajpatel", "How much of the tension survived once spectroscopic redshifts replaced the photometric ones?"),
        ("astrokat", "A meaningful chunk of the most extreme candidates dropped out. Some were lower-redshift interlopers with strong emission lines faking the photometric break."),
        ("elenavasquez", "That's the usual pattern. Photometric samples are for finding things, spectroscopy is for believing things."),
        ("tomnowak", "Is the AGN contribution settled? A faint accreting black hole would inflate the inferred stellar mass quite a bit."),
        ("astrokat", "Not settled, and it's now one of the more interesting threads — several of these objects look like they host little red dot AGN."),
        ("elenavasquez", "Which would be its own remarkable result. Early massive black holes are a harder puzzle than early massive galaxies, in my opinion."),
        ("astrokat", "Strongly agree. Seeding mechanisms are still wide open."),
        ("rajpatel", "Any of this within reach of ground-based follow-up, or is it JWST-only for now?"),
        ("elenavasquez", "ALMA can chase dust and [CII] for the brighter ones. But for the rest, it's JWST or wait."),
    ],
    "biology": [
        ("biomaya", "Reading through the latest brain-organoid work again. The oscillatory activity results are genuinely interesting but the coverage around them is a mess."),
        ("neuralnina", "The EEG comparison did a lot of damage. Comparing organoid multi-electrode traces to preterm-infant EEG was a methodological illustration, not a claim about experience."),
        ("biomaya", "Right. And organoids have no vasculature, no sensory input, and no body. The necrotic core alone caps how far they develop."),
        ("neuralnina", "Which is the actual bottleneck for the field. Size is limited by diffusion, so anything past a few millimetres starts dying from the inside."),
        ("mirachandra", "Are the vascularised co-culture approaches getting anywhere?"),
        ("biomaya", "Some. Transplanting into rodent cortex gets you real perfusion and noticeably better maturation, at the cost of a much messier ethical picture."),
        ("neuralnina", "And assembloids are helping on the circuit side — fusing region-specific organoids to study interneuron migration is a genuinely elegant trick."),
        ("biomaya", "Batch variability is still the thing that would stop me trusting any single-organoid result."),
        ("neuralnina", "Agreed. Unguided protocols self-pattern beautifully and reproducibly differently every time."),
        ("biomaya", "Perfect summary of the field, honestly."),
    ],
    "chemistry": [
        ("sanaokonkwo", "Anyone following the machine-learned interatomic potentials work for catalyst screening? The speedups being reported look almost too good."),
        ("tomnowak", "They're real, with the usual caveat: the model is only trustworthy inside the chemistry its training set covered."),
        ("sanaokonkwo", "So the failure mode is silent extrapolation rather than obvious error."),
        ("tomnowak", "Exactly, and that's what makes it dangerous. It returns a confident number for a reaction path it has never seen."),
        ("rajpatel", "Are people doing uncertainty quantification on these, or is it still mostly vibes and validation sets?"),
        ("tomnowak", "Ensembles are the practical answer right now. Train several, look at the spread, flag disagreement for DFT."),
        ("sanaokonkwo", "That's the workflow I've settled on too. ML for the sweep, DFT for anything that looks promising."),
        ("mirachandra", "Which is a sensible division of labour. Cheap filter, expensive confirmation."),
        ("sanaokonkwo", "The part I did not expect was how much the training data curation matters relative to architecture choice."),
        ("tomnowak", "That's been the story across most of applied ML, to be fair."),
    ],
    "math": [
        ("rajpatel", "Formalisation question: how much of a working mathematician's day could Lean realistically absorb today?"),
        ("tomnowak", "Verification of a finished argument, quite a lot. Discovery of the argument, much less."),
        ("rajpatel", "That matches what I've seen. The bottleneck is that a paper proof compresses enormous amounts of 'obviously'."),
        ("mirachandra", "The mathlib effort is slowly attacking exactly that, though. Every routine lemma someone formalises is one less 'obviously' for the next person."),
        ("tomnowak", "The Liquid Tensor Experiment was the proof of concept that changed a lot of minds. A serious modern result, fully checked."),
        ("rajpatel", "And it surfaced real gaps in the informal write-up, which was the more interesting outcome."),
        ("mirachandra", "Not errors that invalidated it, but places where the argument was thinner than it looked."),
        ("tomnowak", "Which is arguably the strongest argument for formalisation. Not catching wrong proofs, but catching underspecified ones."),
        ("rajpatel", "Okay, that reframes it for me. Less about trust, more about precision."),
    ],
    "earth-science": [
        ("geodesam", "The AMOC weakening literature is in a frustrating state. Strong theoretical basis, genuinely thin direct observational record."),
        ("elenavasquez", "RAPID only goes back to 2004, which is short relative to the variability you're trying to detect a trend in."),
        ("geodesam", "Exactly the problem. Twenty years of data, and multidecadal internal variability sitting right on top of any forced signal."),
        ("biomaya", "So the proxy reconstructions are doing most of the load-bearing work?"),
        ("geodesam", "They are, and they disagree with each other more than the headlines suggest. Sea-surface-temperature fingerprints and sediment records tell somewhat different stories."),
        ("elenavasquez", "The models are also known to be biased toward a too-stable AMOC, which cuts the other direction on risk."),
        ("geodesam", "Right — that's the uncomfortable part. The observational uncertainty is not symmetric in its consequences."),
        ("biomaya", "How much would a longer array actually buy you?"),
        ("geodesam", "Sustained observations are the only real fix. There's no clever analysis that manufactures a fifty-year record from twenty years of data."),
        ("elenavasquez", "Which is a hard case to make to funders, because the payoff is decades out."),
        ("geodesam", "And yet it's the single highest-value thing we could be doing here."),
    ],
    "technology": [
        ("tomnowak", "Curious what people are using for reproducible analysis pipelines these days. Every lab I talk to has a different answer."),
        ("sanaokonkwo", "Containers plus a workflow manager, in our case. Nextflow for the DAG, Docker for the environment."),
        ("rajpatel", "Same idea, different tools — Snakemake and Conda here. The important part is that neither of us is relying on a README."),
        ("tomnowak", "That's the real lesson. The specific tool matters much less than whether the environment is declared somewhere executable."),
        ("neuralnina", "The failure mode I keep seeing is pinned top-level dependencies with unpinned transitive ones. Works today, breaks in eight months."),
        ("sanaokonkwo", "Lockfiles or it didn't happen."),
        ("rajpatel", "Has anyone here actually gone as far as content-addressed data, or is that still overkill for most groups?"),
        ("tomnowak", "We hash inputs and outputs. It's saved us twice from silently reanalysing a stale file, which paid for the setup cost immediately."),
        ("neuralnina", "That specific failure is terrifying because nothing errors. You just get a slightly wrong answer."),
        ("tomnowak", "Which is the general theme of computational reproducibility, unfortunately."),
    ],
    "medicine": [
        ("elenavasquez", "Worth talking about how badly surrogate endpoints get reported. A drug moving a biomarker is not a drug helping a patient."),
        ("neuralnina", "The amyloid story is the case study everyone will be teaching for the next thirty years."),
        ("elenavasquez", "Plaque clearance was dramatic and the cognitive benefit was, charitably, modest. Those two facts sat side by side for years."),
        ("biomaya", "Is the current read that the hypothesis was wrong, or that the intervention came too late in the disease course?"),
        ("neuralnina", "Genuinely contested. The timing argument is not unreasonable — by the time of symptoms, a lot of damage is done."),
        ("elenavasquez", "But it's also unfalsifiable-adjacent if every failure gets explained as 'too late'."),
        ("neuralnina", "Which is why the prevention trials in at-risk asymptomatic populations matter so much. That's the actual test."),
        ("biomaya", "And those take a decade to read out."),
        ("elenavasquez", "They do. Meanwhile the effect sizes that did reach significance are below what most clinicians would call noticeable."),
        ("neuralnina", "Statistical significance and clinical meaningfulness diverging is the recurring theme of the last decade."),
        ("elenavasquez", "Every field, not just ours."),
    ],
}

# ---------------------------------------------------------------------------
# Study circles — real rosters and a short discussion each, keyed by circle name.
# ---------------------------------------------------------------------------
CIRCLE_MEMBERS: dict[str, list[str]] = {
    "Black Hole Physics": ["mirachandra", "quantumleo", "astrokat", "rajpatel", "tomnowak"],
    "Quantum Mechanics 101": ["quantumleo", "mirachandra", "rajpatel", "sanaokonkwo"],
    "Astrobiology": ["biomaya", "elenavasquez", "astrokat", "neuralnina", "geodesam"],
    "Particle Physics": ["mirachandra", "tomnowak", "quantumleo", "rajpatel"],
    "Dark Matter & Energy": ["astrokat", "elenavasquez", "mirachandra", "rajpatel", "tomnowak"],
    "Space Exploration": ["astrokat", "elenavasquez", "geodesam", "sanaokonkwo", "quantumleo"],
}

CIRCLE_CONVERSATIONS: dict[str, list[tuple[str, str]]] = {
    "Black Hole Physics": [
        ("mirachandra", "Starting us off with the information paradox, since everything else in this circle eventually reduces to it. Reading suggestion: the original Hawking 1976 argument first, then the island formula papers."),
        ("quantumleo", "Reading the 1976 paper cold was harder than expected. The claim is simple, the framework around it isn't."),
        ("astrokat", "The core tension is clean though: unitary evolution says information is preserved, semiclassical Hawking radiation says it's thermal and carries none."),
        ("mirachandra", "And you can't just wave at quantum gravity to fix it, because the paradox lives in a regime where curvature is small and effective field theory should be fine."),
        ("rajpatel", "That's the part I hadn't appreciated. The problem shows up well before Planck-scale physics is supposed to matter."),
        ("tomnowak", "The Page curve results are the genuine progress here. Getting entropy to turn over at the right time from a gravitational path integral was not obviously going to work."),
        ("mirachandra", "Next session let's work through the replica wormhole calculation properly. It's the technical heart of the recent story."),
        ("quantumleo", "I'll prepare the entanglement-entropy background so we don't stall on it."),
    ],
    "Quantum Mechanics 101": [
        ("quantumleo", "Ground rules for this circle: no question is too basic, and 'shut up and calculate' is not an acceptable final answer."),
        ("mirachandra", "Seconded. Though calculating first and interpreting second is genuinely good practice."),
        ("sanaokonkwo", "Week one question then: why is the wavefunction complex? Every textbook introduces it and none of them justify it."),
        ("mirachandra", "Good question, and there's a real answer. You need a continuous, norm-preserving time evolution with a conserved probability current — real amplitudes can't do that."),
        ("rajpatel", "Stone's theorem is the formal version. Unitary one-parameter groups need a complex Hilbert space."),
        ("sanaokonkwo", "That's more satisfying than 'because it works'."),
        ("quantumleo", "Next up: the double slit, done properly with amplitudes rather than hand-waving about wave-particle duality."),
    ],
    "Astrobiology": [
        ("biomaya", "Framing question for the circle: what would actually convince you a biosignature was biological rather than geochemical?"),
        ("elenavasquez", "Nothing single. It has to be a disequilibrium argument — a combination of gases no abiotic process maintains together."),
        ("astrokat", "Oxygen plus methane being the canonical Earth example. Individually explainable, jointly hard."),
        ("neuralnina", "The phosphine episode was a useful lesson in how thin the abiotic-baseline literature can be."),
        ("biomaya", "Very. The detection itself became contested, but the deeper issue was how little we knew about non-biological phosphine chemistry."),
        ("geodesam", "Same problem in the rock record here on Earth, incidentally. Distinguishing biogenic from abiogenic microstructures is genuinely unresolved for the oldest samples."),
        ("elenavasquez", "Which is humbling. We can't fully settle it with samples in hand, on our own planet."),
    ],
    "Particle Physics": [
        ("mirachandra", "The Standard Model's problem is not that it fails. It's that it succeeds while looking obviously incomplete."),
        ("tomnowak", "Nineteen free parameters and no explanation for three generations. It reads like an effective theory of something."),
        ("quantumleo", "Where does the muon g-2 situation stand now? I've lost the thread between the measurement and the theory updates."),
        ("mirachandra", "Measurement side keeps tightening. The theory side moved when lattice calculations of hadronic vacuum polarisation disagreed with the data-driven estimate."),
        ("rajpatel", "So the tension may be theory-versus-theory rather than theory-versus-experiment."),
        ("tomnowak", "That's the honest current summary, yes. Unsatisfying but accurate."),
        ("mirachandra", "Let's do a session on why the hadronic contribution is so hard to compute. It explains the whole shape of this disagreement."),
    ],
    "Dark Matter & Energy": [
        ("astrokat", "Opening position for debate: the evidence for dark matter is strong, and the evidence for any particular dark matter candidate is weak."),
        ("elenavasquez", "Hard to argue with. The gravitational evidence is overdetermined — rotation curves, lensing, the CMB acoustic peaks, structure formation all agree."),
        ("mirachandra", "And the direct-detection exclusion plots keep marching down toward the neutrino floor without a signal."),
        ("rajpatel", "At what point does sustained non-detection become evidence about the candidate rather than the technique?"),
        ("astrokat", "For the vanilla WIMP parameter space, arguably already. Which is why axions and lighter candidates are getting the attention now."),
        ("tomnowak", "Modified gravity still can't handle the Bullet Cluster or the CMB peak ratios, so the alternative isn't in better shape."),
        ("elenavasquez", "Right. 'We don't know what it is' is very different from 'it isn't there'."),
    ],
    "Space Exploration": [
        ("astrokat", "Proposal for this circle: focus on mission design tradeoffs rather than mission news. The engineering constraints are the interesting part."),
        ("quantumleo", "Agreed. Starting with propulsion? Every ambitious plan dies on the same rocket equation."),
        ("elenavasquez", "The delta-v budget is the whole story for anything past Mars. Chemical propulsion runs out of headroom fast."),
        ("geodesam", "Which is why in-situ resource utilisation keeps reappearing. If you can make propellant at the destination you change the mass ratio entirely."),
        ("sanaokonkwo", "The chemistry there is well understood — Sabatier for methane on Mars given water and atmospheric CO2. Doing it reliably and unattended is the hard part."),
        ("astrokat", "That's the pattern across the whole field. The physics is settled, the reliability engineering is not."),
        ("elenavasquez", "Next session: radiation shielding mass budgets. Another constraint that quietly dominates crewed designs."),
    ],
}


def _resolve_target() -> str:
    uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
    if not uri:
        sys.exit(
            "MONGODB_URI is not set. Point it at the target database, e.g.:\n"
            "    MONGODB_URI='<railway connection string>' python seed_community.py"
        )
    return uri


def _mask(uri: str) -> str:
    parts = urlsplit(uri)
    host = parts.hostname or "?"
    port = f":{parts.port}" if parts.port else ""
    netloc = f"***@{host}{port}" if parts.username else f"{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def _timeline(count: int, *, newest_minutes_ago: int, span_hours: int) -> list[datetime]:
    """Spread `count` timestamps over the past `span_hours`, oldest first.

    Gaps are jittered so conversations don't look metronomic, and the most
    recent message lands `newest_minutes_ago` minutes back so room previews
    read as freshly active.
    """
    now = datetime.now(timezone.utc)
    end = now - timedelta(minutes=newest_minutes_ago)
    start = end - timedelta(hours=span_hours)
    total = (end - start).total_seconds()

    # Random offsets, sorted, so spacing varies but order is preserved.
    offsets = sorted(random.uniform(0, total) for _ in range(count))
    return [start + timedelta(seconds=o) for o in offsets]


async def seed_community(db) -> tuple[int, int, int, int]:
    """Seed chat rooms/messages and circle rosters/messages.

    Returns (room_count, room_message_count, circle_count, circle_message_count).
    """
    users = {u["username"]: u async for u in db.users.find({})}
    if not users:
        sys.exit("No users found. Run seed_posts.py first.")

    def uid(username: str):
        user = users.get(username)
        if not user:
            sys.exit(f"Seed user @{username} is missing. Run seed_posts.py first.")
        return user["_id"]

    now = datetime.now(timezone.utc)

    # ---- Chat rooms ----------------------------------------------------
    # Rebuilt from scratch so re-running never duplicates rooms.
    await db.chat_rooms.delete_many({})
    await db.messages.delete_many({})
    await db.room_members.delete_many({})

    room_message_total = 0
    for i, (slug, category, description) in enumerate(ROOMS):
        room_doc = {
            "name": category,
            "slug": slug,
            "category": category,
            "description": description,
            "created_at": now - timedelta(days=30 - i),
        }
        result = await db.chat_rooms.insert_one(room_doc)
        room_id = result.inserted_id

        convo = ROOM_CONVERSATIONS[slug]
        # Stagger rooms so they don't all show the same "2 minutes ago".
        stamps = _timeline(
            len(convo),
            newest_minutes_ago=random.randint(3, 240) + i * 17,
            span_hours=random.randint(30, 96),
        )

        participants = set()
        for (username, body), created_at in zip(convo, stamps):
            author_id = uid(username)
            participants.add(author_id)
            await db.messages.insert_one(
                {
                    "room_id": room_id,
                    "author_id": author_id,
                    "body": body,
                    "created_at": created_at,
                }
            )
            room_message_total += 1

        # Everyone who spoke is a member, plus a few quiet lurkers so member
        # counts read like a real room rather than exactly the speaker list.
        lurkers = [
            u["_id"]
            for u in random.sample(
                [u for u in users.values() if u["_id"] not in participants],
                k=min(3, max(0, len(users) - len(participants))),
            )
        ]
        for member_id in list(participants) + lurkers:
            await db.room_members.update_one(
                {"room_id": room_id, "user_id": member_id},
                {
                    "$set": {"last_read_at": now},
                    "$setOnInsert": {"joined_at": room_doc["created_at"]},
                },
                upsert=True,
            )

    # ---- Study circle rosters + discussions -----------------------------
    # Circles themselves are seeded by seed_sidebar.py; we match on name so
    # their _ids (and therefore any existing links) stay stable.
    await db.circle_messages.delete_many({})

    circle_total = 0
    circle_message_total = 0
    for name, usernames in CIRCLE_MEMBERS.items():
        circle = await db.study_circles.find_one({"name": name})
        if not circle:
            print(f"  ! Circle '{name}' not found — skipping. Run seed_sidebar.py.")
            continue

        member_ids = [uid(u) for u in usernames]
        # Preserve any real users who joined through the UI and aren't part of
        # the scripted roster.
        existing_real = [
            m
            for m in (circle.get("members", []) or [])
            if m in {u["_id"] for u in users.values()} and m not in member_ids
        ]
        await db.study_circles.update_one(
            {"_id": circle["_id"]},
            {"$set": {"members": member_ids + existing_real}},
        )
        circle_total += 1

        convo = CIRCLE_CONVERSATIONS.get(name, [])
        stamps = _timeline(
            len(convo),
            newest_minutes_ago=random.randint(30, 600),
            span_hours=random.randint(72, 240),
        )
        for (username, body), created_at in zip(convo, stamps):
            await db.circle_messages.insert_one(
                {
                    "circle_id": circle["_id"],
                    "author_id": uid(username),
                    "body": body,
                    "created_at": created_at,
                }
            )
            circle_message_total += 1

    # Indexes backing the read paths added for these features. The
    # room_members (room_id, user_id) unique index is owned by seed.py, so we
    # deliberately don't redeclare it here — a non-unique duplicate conflicts.
    await db.messages.create_index([("room_id", 1), ("created_at", -1)])
    await db.circle_messages.create_index([("circle_id", 1), ("created_at", -1)])

    return len(ROOMS), room_message_total, circle_total, circle_message_total


async def main() -> None:
    uri = _resolve_target()
    print(f"[seed] Connecting to {_mask(uri)}")
    await connect_to_mongo()
    db = get_db()
    rooms, room_msgs, circles, circle_msgs = await seed_community(db)
    print(f"Seeded {rooms} chat rooms with {room_msgs} messages.")
    print(f"Seeded {circles} circle rosters with {circle_msgs} discussion messages.")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
