"""Hand-written depth levels for batch 02.

Twenty more production posts, spread across all eight categories. Content is
written by hand against each post's existing hook, category and source_url —
no API calls. Safety behaviour lives in backfill_runner.py: length check
before the db connection, dry run by default, flagged headlines excluded.

    # 1. Review what it would write (writes nothing):
    MONGODB_URI='<railway connection string>' DRY_RUN=true python backfill_batch_02.py

    # 2. Apply it:
    MONGODB_URI='<railway connection string>' DRY_RUN=false python backfill_batch_02.py
"""

from __future__ import annotations

import asyncio
import sys

from backfill_runner import run

# Claims in the remaining pool that shouldn't be expanded as written. Writing a
# confident explanation under a false headline makes the error worse, so these
# get surfaced for a human to correct or retire instead.
FLAGGED: dict[str, str] = {
    "A proton is about 99.9999999996 percent empty space": (
        "The figure belongs to the atom, not the proton. A proton is dense "
        "and made of tightly bound quarks and gluons; it is the electron "
        "cloud around a nucleus that leaves an atom mostly empty. The "
        "headline needs correcting to 'atom' rather than explaining."
    ),
    "The QWERTY keyboard was designed to slow typists down": (
        "Widely repeated but not supported by the historical record. The "
        "layout grew from telegraph operators' needs and from separating "
        "common letter pairs so typebars jammed less — which speeds typing "
        "up, not down. Needs rewriting rather than a deeper explanation."
    ),
}

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    "Mars appears red because it is literally rusting": (
        "Martian dust is rich in iron. Over billions of years that iron "
        "reacted with oxygen to form iron oxide — the same compound as rust "
        "on a bike chain — and the fine red powder now coats the planet and "
        "tints its sky.",
        "The oxygen source is the interesting part, since Mars has almost "
        "none in its thin air today. Liquid water is the likely culprit, and "
        "ultraviolet light can also split water vapour, freeing oxygen to "
        "bind with iron. Wind then ground the rusted rock into dust and "
        "spread it worldwide, which is why the planet looks uniformly red "
        "from Earth despite varied terrain beneath. Under that layer the rock "
        "is grey-brown. Recent work points to ferrihydrite as the dominant "
        "mineral, which forms in cool water, hinting the rusting happened "
        "while Mars was still wet.",
    ),
    "Most of the gold on Earth came from colliding neutron stars": (
        "Stars fuse elements up to iron and no further, because anything "
        "heavier consumes energy instead of releasing it. Gold needs a "
        "setting that floods atoms with neutrons faster than they can decay, "
        "and colliding neutron stars supply exactly that.",
        "In 2017 LIGO caught two neutron stars merging and telescopes watched "
        "the afterglow. Its fading colours matched the signature of freshly "
        "forged heavy elements — roughly an Earth's mass of gold and platinum "
        "flung out in the debris. That turned a theory into an observation. "
        "Whether mergers account for all of it is still argued: they may be "
        "too rare and too slow to explain how much gold already existed early "
        "in the galaxy's history, so certain rare supernovae probably "
        "contribute as well.",
    ),
    "You are made of stardust from ancient supernovae": (
        "The Big Bang produced almost nothing but hydrogen and helium. Every "
        "carbon atom in your cells and every oxygen atom in your blood was "
        "fused inside a star and scattered when that star died, long before "
        "the Sun existed.",
        "Stars build heavier elements from lighter ones, each generation "
        "seeding the next. Carbon, nitrogen and oxygen come mostly from dying "
        "stars shedding their outer layers; iron and heavier elements need "
        "supernovae or neutron-star collisions. That debris mixes into gas "
        "clouds, and new stars and planets condense from the enriched "
        "material. The hydrogen in your water is the exception — it dates to "
        "the first minutes after the Big Bang. So you are a blend of the "
        "oldest matter there is and elements forged much later.",
    ),
    "Your body has more bacterial cells than human ones": (
        "Trillions of bacteria live in your gut, on your skin and in your "
        "mouth. They are far smaller than your own cells, so despite "
        "outnumbering them they account for only a couple of pounds of your "
        "body weight.",
        "The familiar figure was ten bacteria per human cell, repeated for "
        "decades from a rough 1970s estimate. A careful recount in 2016 put "
        "it nearer 1.3 to 1, and because you shed bacteria constantly the "
        "ratio drifts back and forth around parity through the day. "
        "Capability matters more than the count: those microbes carry far "
        "more genes than you do, digest fibre you cannot, produce certain "
        "vitamins and help train your immune system. Which particular "
        "communities count as healthy is still poorly defined.",
    ),
    "Tardigrades can survive the vacuum of outer space": (
        "Faced with hostile conditions a tardigrade expels most of its water "
        "and curls into a dormant barrel shape. Its metabolism nearly stops, "
        "and with almost no liquid left there is little to boil away in "
        "vacuum or freeze into damaging ice.",
        "A 2007 European Space Agency mission exposed tardigrades to open "
        "space. Vacuum alone they survived, and some withstood full solar "
        "ultraviolet too, reproducing normally afterwards. The trick appears "
        "to be proteins that turn the cell interior into a glass-like solid, "
        "holding structures in place, plus a protein that shields their DNA "
        "from radiation. Survival is not invulnerability, though: they endure "
        "these extremes dormant rather than living through them, and while "
        "active they are as fragile as any other small animal.",
    ),
    "Trees can communicate and share nutrients through fungal networks": (
        "Fungal threads sheathe tree roots and link separate trees "
        "underground. The fungus trades minerals and water for sugar from the "
        "tree, and labelled carbon has been tracked moving out of one tree "
        "and into another through that network.",
        "Suzanne Simard's experiments showed transfer between birch and fir, "
        "with shaded seedlings receiving more than they gave. That became the "
        "wood-wide web, including claims that mother trees deliberately feed "
        "their offspring. The transfers are real, but the interpretation is "
        "now sharply contested: much of the carbon may stay in the fungus "
        "rather than reaching the second tree, and the fungus has interests "
        "of its own rather than acting as a courier. Cooperation versus a "
        "marketplace of trade and parasitism remains unsettled.",
    ),
    "A diamond and pencil lead are made of the exact same element": (
        "Both are pure carbon, and the difference is arrangement. Diamond "
        "locks every atom to four neighbours in a rigid three-dimensional "
        "cage, while graphite stacks flat sheets that slide over one another "
        "with almost no resistance.",
        "Those sliding sheets are what makes a pencil work, flaking onto "
        "paper under light pressure. Within a single sheet the bonds are "
        "actually stronger than diamond's, but very little holds one sheet to "
        "the next. Diamond's cage has no weak direction, making it the "
        "hardest natural material — though hard is not tough, and a sharp "
        "blow can split it along a cleavage plane. Oddly, at room temperature "
        "diamond is the less stable form and is slowly turning into graphite, "
        "on a timescale far longer than the age of the universe.",
    ),
    "Honey never spoils, even after thousands of years": (
        "Honey holds very little free water, so microbes landing in it are "
        "drawn dry rather than able to grow. Bees also add an enzyme that "
        "generates small amounts of hydrogen peroxide, and the result is "
        "mildly acidic on top of that.",
        "Archaeologists have recovered honey from Egyptian tombs still "
        "chemically recognisable after three thousand years, though whether "
        "anyone should eat it is a separate question. Preservation depends "
        "entirely on staying sealed: honey pulls moisture from the air, and "
        "once diluted enough it ferments like anything else. Crystallisation "
        "is not spoilage but glucose leaving solution, and gentle warming "
        "reverses it. One hazard does survive the sugar — Clostridium spores, "
        "harmless to adults but the reason honey is kept from infants.",
    ),
    "Dry ice does not melt; it turns straight into gas": (
        "Dry ice is frozen carbon dioxide. At normal atmospheric pressure it "
        "has no liquid state available to it at all, so as it warms it passes "
        "directly from solid to gas — a change called sublimation — and "
        "leaves no puddle behind.",
        "Whether a substance can be liquid depends on pressure. Carbon "
        "dioxide needs roughly five times atmospheric pressure before a "
        "liquid phase exists, so at sea level the solid skips straight past "
        "it at about -78°C. That is what makes it useful for shipping: it "
        "holds a far lower temperature than water ice and leaves nothing to "
        "mop up. The fog is not the gas, which is invisible, but water vapour "
        "condensing out of the air around it. Sealed in a container, the "
        "pressure it builds is genuinely dangerous.",
    ),
    "Earth's magnetic poles have flipped many times in the past": (
        "Earth's magnetic field is generated by churning liquid iron in the "
        "outer core. That flow is not steady, and every so often it "
        "reorganises so completely that the north and south magnetic poles "
        "swap places.",
        "The record is written in rock: lava locks in the field direction as "
        "it cools, and the stripes either side of mid-ocean ridges alternate "
        "in polarity, which helped confirm plate tectonics. Reversals have "
        "happened hundreds of times, irregularly, averaging a few hundred "
        "thousand years apart, with the most recent about 780,000 years ago. "
        "A flip takes centuries to millennia rather than happening overnight, "
        "and the field weakens and grows tangled in between. There is no "
        "reliable way to predict the next one.",
    ),
    "Most of Earth's oxygen comes from the ocean, not forests": (
        "Microscopic drifting plants near the ocean surface photosynthesise "
        "exactly as trees do. There are so many of them, across so much of "
        "the planet, that they are estimated to produce at least half the "
        "oxygen entering the atmosphere.",
        "Estimates run from 50 to 80 percent, the width of that range "
        "reflecting how hard this is to measure globally. Production is only "
        "half the story, though: nearly all of that oxygen is consumed again "
        "as the same organisms are eaten and decay, and mature forests sit "
        "close to break-even too. The oxygen we actually breathe accumulated "
        "over hundreds of millions of years from the small fraction of "
        "organic matter buried before it could rot. The atmosphere is a "
        "legacy of ancient burial, not a daily supply.",
    ),
    "The oldest ice cores hold air bubbles over 800,000 years old": (
        "Snow falling on Antarctica traps air between its flakes. As more "
        "snow piles on top, the layers compress into solid ice and seal those "
        "pockets, preserving genuine samples of the atmosphere from the year "
        "they were buried.",
        "Drilling down through those layers walks backwards in time, and the "
        "Dome C core in Antarctica reached ice around 800,000 years old. "
        "Measuring the trapped gas gives direct carbon dioxide readings "
        "across eight ice age cycles, showing it never passed roughly 300 "
        "parts per million in all that time. Oxygen isotopes in the ice "
        "itself record temperature, so gas and climate come from one sample. "
        "Newer drilling has recovered ice thought to be 1.2 million years "
        "old, where the layers are thin and badly distorted.",
    ),
    "A Mobius strip has only one side and one edge": (
        "Take a paper strip, half-twist one end and join it into a loop. Draw "
        "a line along it without lifting your pen and you return to the start "
        "having covered what looked like both faces, because the twist joins "
        "them into one continuous surface.",
        "The same holds for the boundary: what appear to be two rims are a "
        "single edge, twice as long as the original strip. Mathematicians "
        "call the surface non-orientable — there is no consistent way to "
        "label a side as inside or out, so a shape slid around the loop comes "
        "back mirrored. Cutting behaves strangely too: slicing down the "
        "middle gives one longer two-sided loop rather than two rings. The "
        "idea extends to the Klein bottle, a closed surface with no inside, "
        "which cannot exist in three dimensions without self-intersecting.",
    ),
    "A single equation, Euler's identity, links five fundamental constants": (
        "The identity says that e raised to the power of i times pi, plus "
        "one, equals zero. It ties together e from growth, pi from circles, i "
        "from imaginary numbers, and the two most basic numbers there are, "
        "one and zero.",
        "The connection is rotation. Raising e to an imaginary power does not "
        "scale a number, it turns it around the origin, and pi is exactly "
        "half a turn — which carries 1 to -1. Add one and you land on zero. "
        "What makes it striking is that the constants come from unrelated "
        "corners of mathematics: compound interest, geometry, the square root "
        "of a negative number. It is also useful rather than merely elegant, "
        "underpinning how engineers handle waves, signals and alternating "
        "current.",
    ),
    "Penicillin was discovered because of a moldy, forgotten petri dish": (
        "In 1928 Alexander Fleming came back from holiday to find a bacterial "
        "culture contaminated by mould. The bacteria around the mould had "
        "been killed off, and the substance responsible turned out to be a "
        "compound the mould makes to defend itself.",
        "Fleming named it penicillin but could not purify enough to be "
        "useful, and the work stalled for a decade. Howard Florey and Ernst "
        "Chain took it up at Oxford, showed it cured infected mice in 1940, "
        "and drove the mass production that reached wounded soldiers by the "
        "war's end; all three shared the Nobel Prize. The accident was less "
        "luck than preparedness — Fleming recognised what he was looking at. "
        "He also warned early that careless use would breed resistant "
        "bacteria, a prediction that has aged uncomfortably well.",
    ),
    "You have a second brain of neurons in your gut": (
        "The gut wall carries a network of several hundred million nerve "
        "cells, more than the spinal cord holds. It senses conditions inside "
        "the intestine and coordinates the muscle contractions that move food "
        "along, without waiting for instructions from your brain.",
        "Called the enteric nervous system, it keeps working even when the "
        "nerve connecting it to the brain is cut. Most traffic on that nerve "
        "runs upward, gut reporting to brain rather than the reverse, which "
        "is part of why digestive state colours mood. It also makes most of "
        "the body's serotonin, though that supply acts locally on gut "
        "movement rather than crossing into the brain. Claims that gut "
        "bacteria shape your personality outrun the evidence: the "
        "correlations are real, the causal chain in humans mostly is not.",
    ),
    "Gravitational waves stretch and squeeze space itself": (
        "When very heavy objects accelerate — two black holes spiralling "
        "together, say — they send ripples through space itself at the speed "
        "of light. As a ripple passes, distances briefly grow in one "
        "direction while shrinking in the perpendicular one.",
        "The effect is minuscule. LIGO measures a change smaller than a "
        "thousandth of a proton's width across four-kilometre arms, by "
        "splitting a laser down both arms and watching the beams fall out of "
        "step. The first detection came in 2015, from two black holes merging "
        "over a billion light years away, confirming a prediction Einstein "
        "made in 1916 and then doubted himself. It opened a genuinely new way "
        "to observe: gravitational waves pass through matter unimpeded, so "
        "they carry information out of places no light can escape.",
    ),
    "The Large Hadron Collider is colder than outer space": (
        "The collider's magnets are cooled with liquid helium to about 1.9 "
        "kelvin, just under two degrees above absolute zero. Deep space sits "
        "at roughly 2.7 kelvin, so the machine really is colder than the void "
        "around it.",
        "The cold is a requirement rather than the point. Magnets steering "
        "proton beams around the 27-kilometre ring have to be superconducting "
        "to carry enough current without melting, and that only happens below "
        "a critical temperature. Helium at 1.9 kelvin is also superfluid, "
        "flowing without friction and conducting heat extraordinarily well, "
        "so it draws heat out of the magnets far better than an ordinary "
        "coolant could. Cooling the ring takes weeks. The collisions "
        "themselves, meanwhile, briefly reach the hottest temperatures ever "
        "made on Earth.",
    ),
    "The first computer bug was a literal moth": (
        "In 1947 operators of the Harvard Mark II traced a fault to a moth "
        "caught in a relay. They taped the insect into the logbook with a "
        "note calling it the first actual case of a bug being found, and that "
        "page survives at the Smithsonian.",
        "The joke only works because the word was already in use — engineers "
        "had been calling faults bugs since at least Edison's day, which is "
        "exactly why the note says actual case. Grace Hopper, on the team at "
        "the time, later helped make the story famous. The moth was real and "
        "so was the fault; what is wrong is the common claim that this coined "
        "the term. It survives because it is a tidy origin story, and because "
        "the evidence is still there taped to a page, which few etymologies "
        "can offer.",
    ),
    "The internet is held together by undersea cables, not satellites": (
        "Well over ninety percent of international data crosses the ocean "
        "floor through fibre-optic cables, some barely thicker than a garden "
        "hose. Satellites carry only a small share, because light through "
        "glass is faster and far higher in capacity.",
        "A signal to a geostationary satellite has to travel 36,000 "
        "kilometres up and the same back, adding delay no technology can "
        "remove, while a cable path is far shorter and carries vastly more "
        "traffic. Hundreds of cables cross the seabed, often funnelled "
        "through the same narrow chokepoints, which makes them a strategic "
        "weak point — though most breaks are accidental, from anchors and "
        "fishing gear, and repair ships take days to reach a fault. "
        "Low-orbit constellations cut the delay but still cannot approach the "
        "capacity of glass.",
    ),
}


if __name__ == "__main__":
    sys.exit(asyncio.run(run("batch 02", CONTENT, FLAGGED)))
