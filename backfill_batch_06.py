"""Hand-written depth levels for batch 06 — the tail end.

One newly posted curated headline, plus the user-authored posts that carry
enough real subject matter to expand. Unlike batches 03-05 these mostly have
no source_url, so each is grounded in the claims the author already made in
the post body rather than in an external link.

Safety behaviour lives in backfill_runner.py: length check before the db
connection, dry run by default, flagged headlines excluded.

    MONGODB_URI='<connection string>' DRY_RUN=true  python backfill_batch_06.py
    MONGODB_URI='<connection string>' DRY_RUN=false python backfill_batch_06.py
"""

from __future__ import annotations

import asyncio
import sys

from backfill_runner import run

FLAGGED: dict[str, str] = {
    "The Lamoka1": (
        "A personal project announcement with a GitHub link, not a science "
        "claim — there is no mechanism to explain at three depths, and "
        "writing one would mean inventing details about someone else's "
        "hardware. Belongs in a different post type rather than the depth "
        "ladder."
    ),
}

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    "The Milky Way and Andromeda are on a collision course": (
        "Andromeda is the nearest large galaxy and it is moving toward us at "
        "about 110 kilometres a second. Gravity has been pulling the two "
        "together for billions of years, and eventually they are expected to "
        "meet and merge.",
        "Galaxies are mostly empty space, so almost no stars would actually "
        "hit one another — the merger reshapes orbits rather than causing "
        "collisions, and the Sun would simply be flung onto a new path. "
        "Compressed gas would trigger a burst of star formation, and the two "
        "central black holes would eventually spiral together. Recent work "
        "has made the outcome much less certain than the textbook version: "
        "accounting for the pull of nearby galaxies, some analyses put the "
        "odds of a merger within the next 10 billion years at closer to a "
        "coin flip.",
    ),
    "ASML - creating EUV light": (
        "Printing features a few nanometres wide needs light with a "
        "correspondingly tiny wavelength. Ordinary lasers cannot produce it, "
        "so the machine makes 13.5 nanometre light by blasting molten tin "
        "droplets into plasma tens of times hotter than the Sun's surface.",
        "The two-pulse scheme is the clever part: a first weak pulse flattens "
        "the falling droplet into a pancake, and a second enormous pulse "
        "vaporises that sheet into plasma, which converts far more of the "
        "laser energy into usable light than hitting a sphere would. It runs "
        "50,000 droplets a second, each one tracked and struck in flight. "
        "Even so the process is brutally inefficient, only a small fraction "
        "of the input becoming light, which is why these machines draw around "
        "a megawatt and cost hundreds of millions.",
    ),
    "ASML -  The Mirrors That Shouldn't Exist": (
        "Extreme ultraviolet light is absorbed by essentially everything it "
        "touches, including glass and ordinary air, so it cannot be focused "
        "with lenses the way visible light can. The only option left is "
        "mirrors — and no ordinary mirror reflects it either.",
        "The solution stacks about a hundred alternating layers of molybdenum "
        "and silicon, each only a few atoms thick. Every boundary reflects a "
        "sliver of the light, and the spacing is tuned so those slivers "
        "arrive in step and reinforce one another, which lifts total "
        "reflectivity to around 70 percent from nearly nothing. The surface "
        "is polished to under 0.1 nanometres of error — scaled to the size of "
        "Germany, the tallest bump would be under a millimetre. The whole "
        "light path runs in vacuum, since air alone would absorb the beam.",
    ),
    "ASMR - Where Physics Meets Precision": (
        "The wafer stage has to slide a silicon wafer under the light at high "
        "speed and still know where it is to within a fraction of a "
        "nanometre. Each new layer of a chip must line up with the patterns "
        "already printed beneath it.",
        "It works by floating the stage on magnetic fields rather than "
        "bearings, so nothing rubs and nothing wears, with laser "
        "interferometers measuring position continuously and correcting "
        "thousands of times a second. Acceleration is several times gravity, "
        "then it must settle instantly — vibration from a passing truck or a "
        "cooling fan is enough to blur a layer. The machines sit on isolated "
        "foundations for that reason. The headline says ASMR, which appears "
        "to be a slip for ASML, the company that builds them.",
    ),
    "heartbreak affects your whole body": (
        "Rejection and grief activate some of the same brain regions as "
        "physical pain, which is part of why heartbreak genuinely hurts. "
        "Sustained stress hormones then ripple outward, disturbing sleep, "
        "appetite, energy and the immune system.",
        "The most dramatic version is real and has a name: takotsubo "
        "cardiomyopathy, or broken heart syndrome, where a surge of stress "
        "hormones temporarily weakens the heart muscle so severely it mimics "
        "a heart attack. It usually recovers within weeks. Prolonged grief "
        "also raises cortisol, and chronically raised cortisol dampens immune "
        "response, which is the mechanism behind getting ill after a loss. "
        "Effect sizes vary a lot between people and studies, so the general "
        "pattern is well supported even where specific claims are not.",
    ),
}


if __name__ == "__main__":
    sys.exit(asyncio.run(run("batch 06", CONTENT, FLAGGED)))
