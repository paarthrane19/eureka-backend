"""Hand-written depth levels for batch 01 of the posts v1 didn't cover.

Same shape and safety behaviour as backfill_depth_levels.py — checked-in copy,
reviewed in the diff, dry run by default — but for a different set of
headlines. No API calls: this content was written by hand against each post's
existing hook, category and source_url.

Production carries many posts as duplicate pairs, so each headline here may
match more than one document. Every incomplete copy is updated; complete ones
are never touched.

    # 1. Review what it would write (writes nothing):
    MONGODB_URI='<railway connection string>' DRY_RUN=true python backfill_batch_01.py

    # 2. Apply it:
    MONGODB_URI='<railway connection string>' DRY_RUN=false python backfill_batch_01.py

DRY_RUN defaults to true. The two periodic-table 'J' posts are inherited from
v1's UNVERIFIABLE dict and are excluded automatically.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict

from motor.motor_asyncio import AsyncIOMotorClient

from backfill_depth_levels import (
    DEEP_DIVE_RANGE,
    EXPLAIN_RANGE,
    UNVERIFIABLE,
    is_incomplete,
)

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    "The Sahara Desert was green and full of lakes just a few thousand years ago": (
        "Earth's tilt and the shape of its orbit drift over thousands of "
        "years. Around 10,000 years ago that drift pushed more summer "
        "sunlight onto the northern hemisphere, strengthening the monsoon and "
        "pulling rain deep into North Africa.",
        "Rock art across the Sahara shows cattle, hippos and swimmers, and "
        "lake sediments record deep standing water where there is now sand. "
        "The return to desert may not have been gradual: some records suggest "
        "it took only centuries once the vegetation collapsed, because bare "
        "sand reflects more sunlight than plants do and reinforces the drought "
        "that created it. How abrupt the shift really was is still argued, "
        "since cores from different parts of the region disagree.",
    ),
    "Your stomach lining is replaced every few days to avoid digesting itself": (
        "The stomach makes acid strong enough to strip metal. Its wall "
        "survives by coating itself in a thick layer of mucus and by replacing "
        "its surface cells every few days, faster than the acid can wear them "
        "away.",
        "The defence is layered. The mucus traps bicarbonate, a mild alkali, "
        "holding a near-neutral film against the wall while the cavity itself "
        "stays fiercely acidic. Cells in the pits below divide constantly to "
        "resurface the lining. When the system fails the result is an ulcer, "
        "and the usual cause is not stress or spicy food but Helicobacter "
        "pylori, a bacterium that survives the acid and inflames the wall — a "
        "finding that overturned decades of assumption and won a Nobel Prize.",
    ),
    "Chlorophyll and hemoglobin are almost the same molecule": (
        "Both are built around a porphyrin ring, a flat cage of carbon and "
        "nitrogen that grips a single metal atom at its centre. Change the "
        "metal and the molecule changes job entirely, while the surrounding "
        "scaffold stays nearly identical.",
        "Magnesium at the centre makes chlorophyll absorb red and blue light "
        "while reflecting green, which is why plants look green and why "
        "sunlight can be captured at all. Iron at the centre lets haemoglobin "
        "grab and release oxygen, and reflects red. The shared design is no "
        "coincidence: the ring is ancient, and life reuses it across oxygen "
        "transport, photosynthesis and energy enzymes. \"Almost\" is doing "
        "real work, though — the side chains differ, and chlorophyll carries a "
        "long tail that anchors it in membranes.",
    ),
    "Some infinities are genuinely bigger than others": (
        "Two collections are the same size if you can pair their members off "
        "with none left over. Whole numbers pair neatly with even numbers, so "
        "those infinities match. The real numbers cannot be paired with the "
        "whole numbers at all.",
        "Cantor's diagonal argument shows why. Suppose you had a complete "
        "numbered list of every real number between 0 and 1. Build a new "
        "number by changing the first digit of the first entry, the second "
        "digit of the second, and so on. The result differs from every line, "
        "so the list was never complete. Infinity is therefore not one "
        "quantity but a hierarchy, each level with a strictly larger one above "
        "it. Whether a size sits between the whole numbers and the reals is "
        "the continuum hypothesis — shown to be unanswerable from the standard "
        "axioms.",
    ),
    "Teflon is so slippery almost nothing sticks to it, including itself": (
        "Teflon is a carbon chain wrapped in fluorine atoms. Fluorine holds "
        "its own electrons so tightly that it barely interacts with anything "
        "nearby, so other molecules find nothing to grip and slide straight "
        "off.",
        "The bond between carbon and fluorine is among the strongest in "
        "organic chemistry, which is also why the material shrugs off heat and "
        "corrosion. Roy Plunkett found it by accident in 1938, when a cylinder "
        "of gas polymerised into a waxy solid instead of staying gaseous. "
        "Getting it onto cookware meant roughening the metal first so the "
        "coating grips mechanically rather than chemically. That same "
        "durability is now a liability: related fluorinated compounds break "
        "down so slowly they are called forever chemicals.",
    ),
    "Pulsars keep time more precisely than atomic clocks": (
        "A pulsar is the collapsed core of a dead star, city-sized but heavier "
        "than the Sun, spinning up to hundreds of times a second. A beam of "
        "radio waves sweeps out from it, and we see a pulse each time that "
        "beam crosses Earth.",
        "The regularity comes from sheer mass: so much momentum is locked into "
        "the spin that almost nothing disturbs it, and the fastest pulsars keep "
        "rhythm to within nanoseconds. Their advantage is long-term stability "
        "rather than short-term precision — an individual atomic clock drifts "
        "over decades while a millisecond pulsar ticks on unchanged. That "
        "turns them into instruments: timing arrays watch dozens at once, "
        "hunting for tiny correlated shifts in their pulses as gravitational "
        "waves stretch the space between us.",
    ),
    "A single lightning bolt is five times hotter than the Sun's surface": (
        "Lightning is a burst of current forcing its way through air, which "
        "resists it fiercely. That resistance dumps enormous energy into a "
        "narrow channel in a few millionths of a second, heating it before it "
        "has any chance to spread.",
        "Temperature here means the energy of the particles in that thin "
        "channel, not the total heat available — the bolt is scorching but "
        "carries far less energy overall than the Sun's surface, which is why "
        "it does not set the sky alight. The air is torn into glowing plasma, "
        "then expands faster than sound, and that shock wave is the thunder. "
        "How a strike gets started is still unsettled: air insulates well, and "
        "measured fields inside thunderclouds are usually too weak to break it "
        "down. Cosmic rays may seed the first conductive path.",
    ),
    "The heart has its own electrical pacemaker and can beat outside the body": (
        "A small patch of cells in the heart's upper right chamber leaks "
        "charge in a slow, repeating cycle. Each time it reaches a threshold "
        "it fires, and that signal spreads through the muscle and makes it "
        "contract. No instruction from the brain is needed.",
        "Left alone, that node would set a pace near 100 beats a minute; "
        "nerves from the brain mostly slow it down, which is why a resting "
        "pulse sits closer to 60 or 70. Backup sites further down can take "
        "over at a slower rate if it fails. Because the rhythm is generated "
        "locally, a heart supplied with oxygenated fluid keeps beating outside "
        "the body — the basis of transplant preservation, where donor hearts "
        "are kept perfused rather than merely chilled. Artificial pacemakers "
        "do the same job electrically.",
    ),
    "The largest living organism is a fungus covering four square miles": (
        "Most of a fungus is not the mushroom but a network of thread-like "
        "filaments spreading through soil and wood. In Oregon's Malheur "
        "National Forest, genetic testing showed one such network is a single "
        "individual rather than many separate ones.",
        "Researchers sampled fungal tissue across the forest and kept finding "
        "the same genetic fingerprint, meaning it all descends from one spore "
        "and stays connected underground. Age estimates run from 2,000 to "
        "8,000 years, calculated from how fast the network spreads, so they "
        "are inferences rather than measurements. \"Largest organism\" also "
        "depends on definition: by mass a giant sequoia or an aspen grove "
        "competes, and whether a sprawling clonal network counts as one "
        "individual is a real argument in biology.",
    ),
    "Vaccines train your immune system without causing the disease": (
        "Your immune system remembers shapes. A vaccine shows it a fragment of "
        "a pathogen, or a weakened version that cannot make you ill, so it "
        "builds recognition and a stock of memory cells without you having to "
        "survive the real infection first.",
        "Memory is the whole point. After exposure the body keeps cells primed "
        "to produce matching antibodies, so a later encounter is met in hours "
        "rather than the days an unprepared response needs — often before "
        "symptoms appear at all. Protection also extends outward: when enough "
        "of a population is immune, chains of transmission break and people "
        "who cannot be vaccinated are shielded too. How long it lasts varies "
        "by disease and vaccine, which is why some need boosters, and "
        "predicting that in advance is still difficult.",
    ),
    "Deep sleep helps the brain flush out waste products": (
        "The brain has none of the drainage vessels the rest of the body uses, "
        "so it clears waste by pushing fluid along the outside of its blood "
        "vessels. During deep sleep the gaps between brain cells widen, "
        "letting that flow move faster and carry more away.",
        "The waste includes amyloid-beta, the protein that accumulates in "
        "Alzheimer's disease, and its levels measurably rise after a night of "
        "lost sleep. That has made poor sleep a suspected contributor to "
        "dementia rather than only a symptom of it, though whether it is "
        "genuinely a cause is unresolved. Most direct evidence comes from "
        "mice, because watching fluid move through a living human brain is "
        "hard, and some researchers dispute how much of the clearance really "
        "depends on sleep at all.",
    ),
    "Antarctica is technically the world's largest desert": (
        "A desert is defined by how little water falls from the sky, not by "
        "temperature. Much of Antarctica's interior receives the equivalent of "
        "a few centimetres of water a year, less than the Sahara, across an "
        "area larger than Europe.",
        "Cold air holds very little moisture, so the interior is starved of "
        "snowfall even though it sits on kilometres of ice. That ice is old "
        "accumulation, built up grain by grain over hundreds of thousands of "
        "years rather than topped up quickly. The McMurdo Dry Valleys take it "
        "furthest: wind strips away what little snow arrives, leaving bare "
        "rock that has seen almost no precipitation for millennia and is "
        "studied as a stand-in for Mars. That slow accumulation is also what "
        "makes Antarctic ice cores such precise climate records.",
    ),
    "Axolotls can regrow limbs, organs, and even parts of their brain": (
        "After an injury, cells near the wound revert to a flexible, "
        "unspecialised state and gather into a bud. That bud then rebuilds "
        "whatever was lost, in the right shape and orientation, instead of "
        "sealing the gap with scar tissue.",
        "The key difference from mammals is what happens first. Human wounds "
        "prioritise fast closure, and the resulting scar blocks any regrowth. "
        "Axolotls suppress that scarring response, which buys time to rebuild. "
        "They also stay in a juvenile form their whole lives, keeping "
        "developmental programmes switched on that most animals shut down at "
        "maturity. Whether those programmes are absent in mammals or merely "
        "dormant is the open question. Ironically the species is critically "
        "endangered in the wild.",
    ),
    "0.999 repeating forever is exactly equal to 1": (
        "An infinite decimal is defined as the value its ever-growing string "
        "of digits closes in on. The gap between 0.999... and 1 shrinks below "
        "any number you could name, and since no gap survives, the two "
        "expressions describe the same point.",
        "The simple demonstrations hold up: a third is 0.333..., and three "
        "thirds is both 1 and 0.999.... Resistance usually comes from picturing "
        "the decimal as a process that never quite arrives, when it is really "
        "a fixed value defined by where that process leads. Nothing is being "
        "rounded. The deeper lesson is that decimal notation is not unique — "
        "every terminating decimal has a second form ending in repeating "
        "nines, so 2.5 can equally be written 2.4999.... The number is one "
        "thing; the way we write it is another.",
    ),
    "A day on Mercury lasts longer than its year": (
        "Mercury turns on its axis three times for every two trips around the "
        "Sun. Those two motions combine so that bringing the Sun back to the "
        "same place in its sky takes 176 Earth days, while a full orbit takes "
        "only 88.",
        "That 3:2 lock was set by the Sun's gravity pulling on Mercury's "
        "slightly uneven shape, a stable arrangement it settled into rather "
        "than the 1:1 lock many moons have. The result is a strange sky: from "
        "some spots the Sun rises, briefly reverses direction, then carries "
        "on, because near its closest approach Mercury's orbital speed "
        "outpaces its own rotation. Surface temperatures swing from around "
        "430°C in daylight to -180°C at night, yet craters near the poles "
        "never see sunlight at all, and spacecraft data indicate water ice "
        "sitting inside them.",
    ),
    "Glass is not a slow-flowing liquid, despite the myth": (
        "Glass has no orderly crystal structure, which is what makes the myth "
        "tempting, but at room temperature its atoms are locked in place. Old "
        "panes are uneven because they were spun or drawn by hand, and glaziers "
        "usually set the thicker edge at the bottom.",
        "Flowing would require atoms to slide past one another, and in glass "
        "at everyday temperatures that would take far longer than the age of "
        "the universe. Roman glass thousands of years old shows no measurable "
        "sagging, which settles it empirically. What is genuinely interesting "
        "is the transition itself: as glass cools it stiffens without ever "
        "crystallising, and exactly what changes at that moment remains one of "
        "the better-known unsolved problems in physics. Calling glass an "
        "amorphous solid names the state without explaining how it arrives.",
    ),
    "If you fell into a black hole, you would be stretched into spaghetti": (
        "Gravity weakens with distance, so your feet, being closer, would be "
        "pulled harder than your head. Near a small black hole that difference "
        "grows so large that the stretch overwhelms whatever holds your body "
        "together.",
        "The effect depends on size in a way people find surprising. Around a "
        "stellar-mass black hole the tearing happens well outside the point of "
        "no return, but a supermassive one is so large that its pull changes "
        "gently near the edge, and you could cross without noticing anything "
        "unusual, only to be stretched later. Astronomers watch the same "
        "process happen to whole stars: a tidal disruption event, where a star "
        "strays too close and is drawn into a stream of gas that flares "
        "brightly as it falls in.",
    ),
    "Superfluid helium can climb up and out of its own container": (
        "Below about 2.17 kelvin, helium stops behaving like an ordinary "
        "liquid and flows with no internal friction at all. A thin film "
        "spreads up the container wall, and because nothing resists it, the "
        "film keeps going over the rim and drips off the outside.",
        "The behaviour is quantum mechanics made visible at human scale. The "
        "atoms drop into a single shared state and move in unison, so the "
        "usual drag between layers of liquid simply vanishes. The same cause "
        "produces the other oddities: it carries heat extraordinarily well, it "
        "refuses to spin the way a normal fluid does and forms tiny fixed "
        "whirlpools instead, and it seeps through gaps too small for ordinary "
        "liquid helium. Helium is also the only element that stays liquid down "
        "to absolute zero at normal pressure.",
    ),
    "Bananas share about 60 percent of their DNA with humans": (
        "The figure counts genes with a recognisable counterpart, not DNA "
        "matching letter for letter. Roughly six in ten human genes have a "
        "relative somewhere in the banana genome, because both species "
        "inherited the same basic toolkit for running a cell.",
        "Those shared genes are the housekeeping ones: copying DNA, building "
        "proteins, releasing energy from sugar. They have changed little in "
        "over a billion years because almost any alteration breaks something "
        "essential. Where a counterpart does exist, the sequences themselves "
        "typically match only around 40 percent of the way, so the headline "
        "number describes shared inventory rather than shared text. It is a "
        "good reminder that such percentages need care — the same relationship "
        "is quoted as 60 or 40 percent depending on what you count.",
    ),
}

# Post 1 from the batch, held separately. Unlike the other 19 this is a
# user-written post: lowercase headline, no source_url, a typo in the body and
# an informal worked example. Expanding it means editing someone's own words
# rather than completing curated seed content, which is a product decision
# rather than a data fix. Set INCLUDE_USER_POSTS=yes to write it too.
USER_AUTHORED: dict[str, tuple[str, str]] = {
    "newtons 3rd law of motion": (
        "Forces always come in pairs. When you push on something it pushes "
        "back on you, equally hard, in the opposite direction. The two forces "
        "act on different objects, which is exactly why they do not simply "
        "cancel each other out.",
        "That pairing is what makes movement possible at all. A rocket pushes "
        "exhaust gas backwards and the gas pushes the rocket forwards; you "
        "push down and back against the ground and the ground drives you "
        "along. Because the two forces act on different bodies, they never "
        "cancel — cancelling would require both to act on the same object. The "
        "wall example holds up too: your fist and the wall feel equal force, "
        "but your knuckles cover a smaller area and are made of weaker "
        "material, so the same force does much more damage to you.",
    ),
}


def check_lengths(content: dict[str, tuple[str, str]]) -> list[str]:
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


async def main() -> int:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("MONGODB_URI is not set.")
        return 1

    dry_run = os.getenv("DRY_RUN", "true").strip().lower() != "false"
    include_user = os.getenv("INCLUDE_USER_POSTS", "").strip().lower() == "yes"

    active = dict(CONTENT)
    if include_user:
        active.update(USER_AUTHORED)

    problems = check_lengths({**CONTENT, **USER_AUTHORED})
    if problems:
        print("Checked-in copy is outside the target length ranges:")
        print("\n".join(problems))
        return 1

    db_name = os.getenv("MONGODB_DB", "eureka")
    print(f"[batch 01] Connecting to {uri.split('@')[-1]} (db: {db_name})")
    db = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=15000)[db_name]

    total = 0
    incomplete: list[dict] = []
    async for post in db.posts.find({}):
        total += 1
        if is_incomplete(post):
            incomplete.append(post)

    # Production stores many of these as duplicate pairs, so group by headline.
    targets: dict[str, list[dict]] = defaultdict(list)
    for post in incomplete:
        if post["headline"] in UNVERIFIABLE:
            continue  # the two periodic-table 'J' copies
        if post["headline"] in active:
            targets[post["headline"]].append(post)

    doc_count = sum(len(v) for v in targets.values())

    print()
    print("=" * 72)
    print(f"  Posts in database:            {total}")
    print(f"  Missing level 2 or 3:         {len(incomplete)}")
    print(f"  Headlines in this batch:      {len(active)}")
    print(f"  Headlines matched in db:      {len(targets)}")
    print(f"  Documents to update:          {doc_count}")
    print(f"  User-authored post included:  {'yes' if include_user else 'no (INCLUDE_USER_POSTS=yes to add)'}")
    print("=" * 72)

    missing = [h for h in active if h not in targets]
    if missing:
        print("\nIn this batch but NOT matched in the database:")
        for h in missing:
            print(f"  {h}")

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
        for headline, posts in sorted(targets.items(), key=lambda kv: kv[1][0].get("category", "")):
            explain, deep_dive = active[headline]
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
        explain, deep_dive = active[headline]
        for post in posts:
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


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
