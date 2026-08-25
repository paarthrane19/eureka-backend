"""One-time backfill for posts that are "stuck on hook".

Posts store their depth ladder as `levels`: [hook, explanation, deep dive].
Posts created before the compose form collected all three never got a `levels`
array at all, so `_post_levels` in app/serializers.py expanded them to
[body, body, body] — the depth arrows stepped through three copies of the same
paragraph.

This script fills in levels 2 and 3 for those posts. It is deliberately NOT
wired into startup or the seed scripts: run it by hand, review the dry run,
then run it for real.

    # 1. Review what it would write (writes nothing):
    MONGODB_URI='<railway connection string>' DRY_RUN=true python backfill_depth_levels.py

    # 2. Apply it:
    MONGODB_URI='<railway connection string>' DRY_RUN=false python backfill_depth_levels.py

DRY_RUN defaults to true, so a run with the variable missing or misspelled
reports instead of writing.

The replacement text is checked in rather than generated at runtime: every
entry was written against the post's existing hook, category and source, and
is meant to be reviewed in the diff like any other content change. Posts whose
hook could not be confidently grounded in a source are listed in UNVERIFIABLE
and are reported, never rewritten.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter, defaultdict

from motor.motor_asyncio import AsyncIOMotorClient

# Level 2 must land in 200-300 characters, level 3 in 400-600, matching the
# compose form's counters and LEVEL_LIMITS in app/schemas.py.
EXPLAIN_RANGE = (200, 300)
DEEP_DIVE_RANGE = (400, 600)

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    "Your sense of smell is tied directly to memory and emotion": (
        "Most senses are routed through the thalamus, which sorts and filters "
        "them before you become aware of anything. Smell is the exception: "
        "olfactory neurons reach the amygdala and hippocampus, the brain's "
        "emotion and memory centres, almost directly.",
        "That shortcut is why a smell can return a memory whole, with its mood "
        "attached, while a photograph of the same scene feels like a fact you "
        "are recalling. The effect is strong enough to have a name in the "
        "literature, the Proust phenomenon, and odour-cued memories reliably "
        "test as more emotional and more vivid than those cued by words or "
        "images. What is still debated is how much of this is wiring and how "
        "much is circumstance: we encounter most odours rarely and rehearse "
        "them almost never, so the memories attached to them may simply be "
        "less worn down by repetition.",
    ),
    "Sharks existed before trees and before Saturn's rings": (
        "Sharks appear in the fossil record roughly 450 million years ago. The "
        "first true trees came about 385 million years ago, and evidence from "
        "the Cassini mission suggests Saturn's rings may be only tens of "
        "millions of years old — younger than the dinosaurs.",
        "Cassini measured how much the rings weigh and how quickly meteoritic "
        "dust is darkening them. Both point to a young, bright system, "
        "possibly formed when a moon or comet was torn apart relatively "
        "recently, though the estimate is contested and some models still "
        "allow ancient rings that were somehow kept clean. The shark side is "
        "firmer. Sharks are not unchanged living fossils, but the lineage has "
        "persisted through all five mass extinctions, helped by cartilage "
        "skeletons, continuously replaced teeth, and a spread of body plans "
        "from plankton feeders to deep-sea hunters.",
    ),
    "A day on Earth is slowly getting longer": (
        "The Moon's gravity raises tidal bulges in the oceans. Earth's "
        "rotation drags those bulges slightly ahead of the Moon, and the "
        "gravitational tug back on them acts as a brake, bleeding rotational "
        "energy away as heat in shallow seas.",
        "Angular momentum is conserved, so what Earth loses the Moon gains: it "
        "is receding from us by about 3.8 centimetres a year, a rate measured "
        "by bouncing lasers off reflectors left by the Apollo missions. Fossil "
        "corals and tidal sediments record the history directly, with growth "
        "bands showing that days ran closer to 22 hours in the late "
        "Cretaceous. The 1.8 milliseconds per century figure is a long-run "
        "average, not a steady tick: shifting ice mass, core-mantle coupling "
        "and large earthquakes all nudge the rate, which is why leap seconds "
        "arrive on no fixed schedule.",
    ),
    "Light from the Andromeda galaxy left before humans existed": (
        "Andromeda is about 2.5 million light-years away, so its light takes "
        "2.5 million years to reach us. Anatomically modern humans are roughly "
        "300,000 years old, meaning that light departed long before our "
        "species existed to look at it.",
        "This is not a quirk of one galaxy but the ordinary condition of "
        "astronomy: every observation is a look into the past, and the further "
        "out you point a telescope the further back you see. Andromeda is "
        "notable mainly for being the most distant thing most people can see "
        "without equipment, a faint smudge in Andromeda on a dark night. The "
        "distance itself was the discovery that redefined the universe. In the "
        "1920s Edwin Hubble found Cepheid variable stars in what was then "
        "called the Andromeda Nebula and showed it lay far outside the Milky "
        "Way, proving that other galaxies exist at all.",
    ),
    "The body has enough iron to make a small nail": (
        "An adult carries roughly three to four grams of iron, and most of it "
        "is not structural. It sits at the centre of haemoglobin, the protein "
        "in red blood cells that binds oxygen in the lungs and releases it in "
        "the tissues that need it.",
        "Iron is useful for the same reason it is dangerous: it readily swaps "
        "electrons, which lets haemoglobin pick up and drop oxygen, but also "
        "lets loose iron drive reactions that damage cells. The body therefore "
        "keeps almost none of it free, binding it to transferrin and ferritin, "
        "and recycling it from worn-out red cells rather than excreting it. "
        "There is no regulated route to shed a surplus, which is why both "
        "deficiency and overload cause disease: anaemia is the most common "
        "nutritional disorder worldwide, while haemochromatosis lets iron "
        "build up until it injures the liver and heart.",
    ),
    "mRNA vaccines deliver instructions, not the virus itself": (
        "The vaccine carries a strand of messenger RNA wrapped in a lipid "
        "nanoparticle. Your cells read it like any other mRNA and build one "
        "harmless viral protein, the spike. Your immune system learns to "
        "recognise that protein and destroys the cells displaying it.",
        "The mRNA never reaches the nucleus, where DNA is kept, and human "
        "cells have no enzyme that could write RNA back into the genome. It is "
        "also short-lived: cells degrade it within days, so protection depends "
        "on the immune memory formed, not on the mRNA persisting. The approach "
        "took decades of unglamorous work, particularly Katalin Kariko and "
        "Drew Weissman's discovery that modified nucleosides stop the body "
        "treating the strand as an intruder, which won them the 2023 Nobel "
        "Prize. Because only the sequence changes between targets, the "
        "platform is now being trialled against influenza and RSV.",
    ),
    "Prime numbers thin out but never run out": (
        "Euclid's proof is short: assume the primes are a finite list, "
        "multiply them all together and add one. The result leaves remainder 1 "
        "when divided by any prime on the list, so either it is a new prime or "
        "it has one as a factor. Either way the list was incomplete.",
        "How thinly they spread is a harder question. The prime number "
        "theorem, proved in 1896, says the count of primes below n is close to "
        "n divided by the natural logarithm of n, so primes near a million turn "
        "up roughly once every fourteen numbers. That gives the average density "
        "but not the local irregularity, and how far the true count can stray "
        "from the estimate is what the Riemann Hypothesis governs. It remains "
        "unproven and carries a million-dollar Clay prize. The primes also "
        "clump: twin primes two apart keep appearing far out, and nobody has "
        "proved they never stop.",
    ),
    "You cannot cut most angles into three equal parts with ruler and compass": (
        "Straightedge and compass constructions can only reach lengths built "
        "from whole numbers by adding, subtracting, multiplying, dividing and "
        "taking square roots. Trisecting a general angle requires solving a "
        "cubic equation, which falls outside that reach.",
        "Pierre Wantzel settled it in 1837 by recasting geometry as algebra: "
        "each new point a construction produces lies in a field extension of "
        "degree a power of two, so any constructible number satisfies a "
        "polynomial whose degree is a power of two. Trisecting 60 degrees "
        "needs a root of an irreducible cubic, degree three, so no sequence of "
        "steps reaches it. The proof does not say trisection is hard, it says "
        "the tools are the wrong shape for the job. Loosen them and it becomes "
        "easy: a marked ruler or an origami fold trisects angles, and specific "
        "angles like 90 degrees were always constructible.",
    ),
    "Glaciers store about 70 percent of the world's fresh water": (
        "Nearly all of Earth's water is salt water. Of the small fraction that "
        "is fresh, roughly 69 percent is frozen into ice sheets and glaciers, "
        "overwhelmingly in Antarctica and Greenland. Most of the rest is "
        "groundwater; lakes and rivers are a rounding error.",
        "That distribution matters because the accessible portion is so thin. "
        "Rivers and lakes hold well under one percent of fresh water yet "
        "supply most of what people drink and irrigate with, and mountain "
        "glaciers act as buffers releasing meltwater through dry seasons "
        "across the Andes, the Alps and High Mountain Asia. Those glaciers are "
        "losing mass almost everywhere, which raises flows briefly and then "
        "reduces them permanently once the ice is gone. The polar ice sheets "
        "are the larger question: Greenland alone holds enough water to raise "
        "sea level by about seven metres.",
    ),
    "Human skin sheds and regrows entirely about every month": (
        "New skin cells are made in the deepest layer of the epidermis. They "
        "are pushed upward, flattening and filling with keratin as they go, "
        "die on the way, and are shed from the surface. The full journey takes "
        "roughly four weeks.",
        "The dead outer layer is the point, not a by-product: flattened cells "
        "packed with keratin and sealed with lipids form the stratum corneum, "
        "the barrier that keeps water in and microbes out. Turnover speed is "
        "tightly regulated, and when that fails the consequences are visible. "
        "In psoriasis the cycle compresses to a few days, so cells reach the "
        "surface before maturing and pile up as plaques. Rate also varies by "
        "site and slows with age, part of why older skin heals more slowly. "
        "The shed cells become a major component of household dust.",
    ),
    "The observable universe is 93 billion light-years across": (
        "The universe is 13.8 billion years old, but space itself has stretched "
        "while light travelled through it. The most distant light we can "
        "detect set out 13.8 billion years ago; the matter that emitted it has "
        "since been carried to about 46 billion light-years away.",
        "Doubling that comoving radius gives the roughly 93 billion light-year "
        "diameter. Nothing here outruns light locally — the expansion is of "
        "space between objects, not motion through it, so the usual speed "
        "limit is untouched. The boundary is not a wall but a horizon set by "
        "our position and the time light has had to travel; an observer "
        "elsewhere sees a different sphere of the same size. Beyond it the "
        "universe continues, and measurements of its flatness imply it may be "
        "vastly larger or infinite. Because expansion is accelerating, "
        "galaxies near the edge are drifting permanently out of reach.",
    ),
    "More than half the world's web traffic is not human": (
        "Every request a browser makes is logged, and so is every request from "
        "software. Search engine crawlers, monitoring tools, scrapers, "
        "vulnerability scanners and credential-stuffing scripts all generate "
        "traffic, and in several recent measurement years their combined share "
        "has edged past human visits.",
        "The figure moves with definitions and with who is counting, since it "
        "depends on how each network classifies a request it cannot directly "
        "attribute. The useful split is not human versus bot but wanted versus "
        "unwanted: search crawlers and uptime checkers are why sites are "
        "findable and monitored, while much automated traffic exists to test "
        "stolen passwords, scrape pricing or probe for unpatched software. "
        "Bots increasingly imitate real browsers to evade filtering, so "
        "detection has shifted toward behavioural signals — and AI training "
        "crawlers are a large new and contested share.",
    ),
    "Time runs faster on your head than on your feet": (
        "General relativity says clocks run slower deeper in a gravitational "
        "field. Your feet sit marginally closer to Earth's centre than your "
        "head, so they age marginally more slowly. The difference is real, not "
        "an illusion of measurement.",
        "In 2010 a NIST team demonstrated it in a laboratory, using optical "
        "atomic clocks precise enough to resolve a height change of about 33 "
        "centimetres. Over a lifetime the difference across a human body is a "
        "tiny fraction of a second, so nobody notices, but the effect is not "
        "academic. GPS satellites orbit where gravity is weaker and their "
        "clocks gain roughly 45 microseconds a day, partly offset by a loss "
        "from orbital speed; uncorrected, positions would drift kilometres in "
        "a day. Clocks are now precise enough to survey elevation by comparing "
        "how fast they tick.",
    ),
    "There may be more stars in the universe than grains of sand on Earth": (
        "Estimates put the observable universe at hundreds of billions of "
        "galaxies averaging hundreds of billions of stars, giving something "
        "like 10^22 stars. Adding up the world's beaches and deserts gives "
        "roughly 10^19 grains of sand — about a thousand times fewer.",
        "Neither number is a count; both are extrapolations, with honest "
        "uncertainty of a factor of ten or more each way. The star estimate "
        "comes from surveying small patches of sky and scaling up, while the "
        "sand estimate multiplies an assumed grain size by estimated sand "
        "volumes. The gap is wide enough that the comparison survives those "
        "error bars. Two caveats keep it honest. It covers only the observable "
        "universe, since anything beyond the horizon is uncounted. And it "
        "compares stars to sand, not atoms: one grain contains far more atoms "
        "than there are stars.",
    ),
    "The fastest thing you own is probably your microwave's light": (
        "A microwave oven works by flooding its cavity with electromagnetic "
        "radiation at about 2.45 gigahertz. That radiation is light, just at a "
        "wavelength your eyes cannot see, and like all light it travels at "
        "roughly 300,000 kilometres per second.",
        "The heating comes from frequency, not speed. Water molecules are "
        "electrically lopsided, and the oscillating field twists them billions "
        "of times a second; the resulting friction warms food from within "
        "rather than conducting heat in from a hot surface. That explains the "
        "oven's quirks. Ice heats poorly because its molecules are locked in a "
        "lattice and cannot rotate, which is why defrost cycles pulse. "
        "Standing waves create hot spots, which is what the turntable is for. "
        "The door's mesh has holes far smaller than the 12-centimetre "
        "wavelength, so microwaves reflect while light passes.",
    ),
    "Training a large AI model can use as much power as many homes": (
        "Training runs on thousands of specialised chips continuously for "
        "weeks. The chips draw power, and roughly as much again goes to "
        "cooling them. A single frontier training run can consume gigawatt-"
        "hours, comparable to the annual electricity use of hundreds or "
        "thousands of households.",
        "Training is only part of the bill. Inference — actually answering "
        "queries — is individually tiny but constant, and at scale it now "
        "dominates lifetime energy use for widely deployed models. Water "
        "matters too, since evaporative cooling consumes it in quantities that "
        "are contentious where data centres sit in dry regions. What the total "
        "means environmentally depends mostly on the grid supplying it, which "
        "is why operators build near hydro, nuclear and wind. Comparisons are "
        "hard to audit because few companies publish per-model figures, and "
        "efficiency improves while total demand grows faster.",
    ),
    "Hurricanes release more energy than the world uses in a year": (
        "A hurricane is an engine driven by warm ocean water. As seawater "
        "evaporates and later condenses into cloud and rain, it releases the "
        "latent heat stored in that phase change — an estimated 5 x 10^19 "
        "joules a day for a mature storm.",
        "That is roughly two hundred times the world's electricity generating "
        "capacity, though the comparison needs care: almost all of it goes "
        "into moving air and water, and only about a percent converts into the "
        "wind that does the damage. Even that fraction exceeds global "
        "generating capacity several times over. The heat engine framing "
        "explains why warm water matters, and why storms weaken over land once "
        "the fuel is cut off. It also frames a live research question: warming "
        "seas raise the ceiling on intensity, and while storm numbers may not "
        "rise, the share reaching severe categories appears to be.",
    ),
    "The first 1GB hard drive weighed over 250 kilograms": (
        "IBM's 3380, announced in 1980, was the first disk unit to reach "
        "gigabyte capacity. It stood about the size of a refrigerator, weighed "
        "roughly 250 kilograms, and cost around $40,000 — well over $100,000 "
        "in today's money.",
        "Capacity came from spinning platters of magnetic material with heads "
        "flying microscopic distances above them, and for decades progress "
        "meant shrinking the magnetised region holding each bit. Density has "
        "since improved enormously, so a fingernail-sized microSD card holds a "
        "thousand times more than the 3380 did. The physics pushed back: below "
        "a certain size, magnetic domains go unstable at room temperature. "
        "Flash memory, which stores charge and has no moving parts, has taken "
        "most consumer storage, while hard drives persist where cost per "
        "terabyte wins.",
    ),
    "Aerogel is 99 percent air yet can hold thousands of times its weight": (
        "Aerogel is made by growing a wet silica gel, then removing the liquid "
        "without letting surface tension collapse the structure. What remains "
        "is a solid lattice of silica strands with nearly all of its volume as "
        "trapped air.",
        "The trick is supercritical drying: the solvent is taken above its "
        "critical point, where the liquid-gas boundary disappears, so no "
        "menisci form to crush the delicate network as it dries. The result is "
        "a rigid open skeleton that spreads load along continuous strands, "
        "letting a fragile-looking block support thousands of times its own "
        "mass while shattering under a sharp knock. Because heat moves poorly "
        "through both the thin strands and the trapped air, aerogel is among "
        "the best solid insulators known. NASA's Stardust mission used it to "
        "catch comet particles travelling at kilometres per second.",
    ),
    "Anesthesia works, but exactly how it switches off consciousness is unclear": (
        "General anaesthetics reliably and reversibly remove awareness, and "
        "their molecular targets are largely known — mostly receptors that "
        "damp neural activity or block excitation. What is missing is the step "
        "from those molecular effects to the disappearance of experience.",
        "Different drugs act on different receptors yet converge on the same "
        "outcome, suggesting the endpoint is a network property rather than a "
        "single switch. Imaging supports that: under anaesthesia the cortex "
        "stays active but stops integrating, with long-range communication "
        "breaking down while local activity continues. That is now central to "
        "competing theories of consciousness, which is why anaesthesia has "
        "become a tool for studying it. Gaps remain: depth is inferred "
        "indirectly, rare cases of awareness during surgery still occur, and "
        "postoperative confusion is unexplained.",
    ),
    "The immortal cells of Henrietta Lacks still grow in labs worldwide": (
        "Most human cells stop dividing after a limited number of generations. "
        "Cells taken from Henrietta Lacks's cervical tumour in 1951 did not, "
        "and became the first human cell line to grow indefinitely in culture. "
        "They are called HeLa.",
        "Their immortality traces largely to human papillomavirus DNA in the "
        "genome, which disables the brakes on division and keeps telomerase "
        "active so chromosome ends are rebuilt rather than eroded. HeLa cells "
        "underpinned the polio vaccine trials and much of cell biology since. "
        "They were also taken without consent, and her family learned of them "
        "only decades later while companies profited; in 2013 the NIH gave "
        "relatives a say over access to the HeLa genome. The line has a "
        "scientific problem too: it is aggressive enough to have overgrown "
        "many other cell cultures, invalidating published work.",
    ),
    "The first computer programmer was a woman in the 1840s": (
        "Ada Lovelace was translating an Italian account of Charles Babbage's "
        "proposed Analytical Engine when she added notes three times longer "
        "than the original. One contained a step-by-step method for the "
        "machine to compute Bernoulli numbers.",
        "That sequence is generally described as the first published algorithm "
        "intended for a machine to execute. Her more striking contribution was "
        "conceptual: Babbage saw a calculator, while Lovelace argued that if "
        "the engine could manipulate symbols by rules, it could act on "
        "anything representable as symbols, including music. That is "
        "general-purpose computing, a century before the hardware existed. "
        "Historians do argue about credit: Babbage had written similar "
        "routines earlier, unpublished, and the two collaborated closely. What "
        "is not disputed is that the program appeared under her initials.",
    ),
    "In a room of just 23 people, two likely share a birthday": (
        "The intuition fails because you are not comparing yourself to "
        "everyone else. Any two people in the room can match, and 23 people "
        "form 253 possible pairs — enough that a collision becomes more likely "
        "than not, at about 50.7 percent.",
        "The calculation runs backwards. The chance that everyone differs is "
        "365/365 x 364/365 x 363/365 and so on for 23 terms, which falls just "
        "below one half; subtract from one for the answer. Growth is fast: 50 "
        "people give 97 percent and 70 people over 99.9 percent, while "
        "certainty needs 366. This is not a party trick but the core of the "
        "birthday attack in cryptography. Finding any two inputs that hash to "
        "the same value takes roughly the square root of the number of "
        "possible outputs, which is why a hash needs 256 bits to deliver 128 "
        "bits of collision resistance.",
    ),
    "Diamonds can be made from peanut butter under enough pressure": (
        "Diamond is nothing but carbon locked in a particular crystal lattice. "
        "Peanut butter is rich in carbon, so squeezing it hard enough while "
        "heating it can rearrange those atoms into diamond — as researchers "
        "have demonstrated experimentally.",
        "The work came out of a laboratory studying Earth's lower mantle, "
        "where diamonds actually form under tens of gigapascals at high "
        "temperature. The peanut butter demonstrated the principle rather than "
        "offering a production method, and it was a poor feedstock: released "
        "hydrogen interfered with the press, and the crystals were small and "
        "impure. Cleaner routes have existed for decades. High-pressure "
        "synthesis has made industrial diamond since the 1950s, and chemical "
        "vapour deposition now grows gem-quality stones from methane, "
        "physically identical to mined diamond.",
    ),
    "Your liver can regenerate even after losing most of its mass": (
        "Remove a large portion of a liver and the remaining tissue grows back "
        "to the original mass within weeks. Existing mature liver cells, which "
        "normally sit quiet, re-enter the cell cycle and divide until the "
        "organ matches the body's needs.",
        "It is regrowth of mass rather than shape: lost lobes do not reappear, "
        "the remaining ones enlarge, which is why compensatory hyperplasia is "
        "the more accurate term. The process is demand-driven, governed by "
        "blood flow and signals including HGF and IL-6, and it stops when "
        "function is restored rather than overshooting. This is what makes "
        "living-donor transplantation possible, since donor and recipient both "
        "regenerate adequate livers from partial organs. The limits matter "
        "clinically: it needs healthy surviving tissue, so cirrhosis, which "
        "replaces working cells with scar, largely destroys it.",
    ),
    "The first computer mouse was carved from wood": (
        "Douglas Engelbart's 1964 prototype was a hand-sized wooden block with "
        "a single button and two metal wheels underneath, set at right angles. "
        "One wheel measured horizontal movement and the other vertical, "
        "translating hand motion into cursor position.",
        "The mouse was a minor part of a larger project. In a 1968 "
        "presentation later called the Mother of All Demos, Engelbart's team "
        "showed windows, hypertext links, version control and video "
        "conferencing, in an era when computing meant submitting punched cards "
        "and waiting. The goal was augmenting human intellect, not automating "
        "tasks. Engelbart's patent expired before the mouse became widespread "
        "and he earned essentially nothing from it; the design reached the "
        "public through Xerox PARC and then Apple. The name was lab shorthand, "
        "after the cord trailing from the back.",
    ),
    "Most of your body's cells are replaced over your lifetime": (
        "Different tissues renew on very different schedules. The gut lining "
        "turns over in days, red blood cells in about four months, skin in "
        "weeks, and bone across roughly a decade. Cell by cell, most of you is "
        "considerably younger than you are.",
        "The often-quoted claim that you are entirely replaced every seven "
        "years is wrong, because some cells are never replaced. Carbon dating "
        "cells using the spike in atmospheric carbon-14 from twentieth-century "
        "nuclear testing allows direct measurement of cell ages, and it shows "
        "most neurons in the cerebral cortex, the lens cells of the eye and "
        "the core of heart muscle are as old as the person. That permanence "
        "may be the point: an identity built on memory arguably needs cells "
        "that persist. The same technique showed new neurons do form in "
        "adults, though how many remains disputed.",
    ),
    "Statistics can prove almost opposite conclusions from the same data": (
        "Simpson's paradox: a trend can hold in every subgroup and reverse "
        "when the subgroups are pooled. It happens when a lurking variable is "
        "distributed unevenly, so aggregation quietly compares groups that "
        "were never comparable.",
        "The best-known case is a 1973 Berkeley admissions review, where the "
        "university appeared to favour men overall while most individual "
        "departments slightly favoured women. Women had applied "
        "disproportionately to departments with low admission rates, and "
        "pooling hid that. The uncomfortable part is that the arithmetic says "
        "nothing about which view is right: both summarise the same numbers "
        "correctly, and choosing requires knowing how the data was generated. "
        "That is a causal question, which is why controlling for more "
        "variables is not automatically better — the wrong one manufactures "
        "bias.",
    ),
    "It is impossible to comb a hairy ball flat without a cowlick": (
        "The hairy ball theorem states that any continuous tangent vector "
        "field on a sphere must vanish somewhere. Comb a hairy sphere however "
        "you like and at least one point ends up with no direction to lie "
        "in — a cowlick or a parting.",
        "The obstruction is topological, not practical. It follows from the "
        "sphere's Euler characteristic being 2, and it is genuinely about the "
        "shape: a torus has characteristic 0, so a doughnut can be combed flat "
        "everywhere without a cowlick. Applied to Earth's atmosphere, where "
        "surface wind is a tangent field, it guarantees at every moment at "
        "least one point of zero horizontal wind, typically the eye of a "
        "cyclone. The same result explains why no antenna can radiate evenly "
        "in every direction, and it generalises: such fields exist on "
        "odd-dimensional spheres but never even-dimensional ones.",
    ),
    "Nothing with mass can ever reach the speed of light": (
        "Accelerating an object takes energy, and the faster it already moves "
        "the more each further increment costs. As speed approaches light "
        "speed the energy required grows without limit, so reaching it would "
        "take infinite energy.",
        "The deeper statement is geometric rather than mechanical. In "
        "spacetime, massive particles travel along paths that stay inside the "
        "light cone, while massless particles like photons travel exactly "
        "along it; no amount of pushing rotates one path into the other. The "
        "limit is also less of a barrier than it seems, because time dilates "
        "for the traveller: under sustained acceleration a crew could cross "
        "the galaxy within a lifetime while millennia pass at home. "
        "Accelerators demonstrate this daily, pushing protons to 99.9999991 "
        "percent of light speed while the last fraction stays out of reach.",
    ),
    "Absolute zero can never actually be reached": (
        "Cooling works by moving heat from one thing into another. As a system "
        "approaches absolute zero it has less and less energy left to remove, "
        "and each remaining step extracts less, so the target needs infinitely "
        "many steps to reach.",
        "This is the third law of thermodynamics, usually stated as entropy "
        "approaching a constant as temperature approaches zero, which implies "
        "no finite process completes the journey. It is a statement about "
        "cooling procedures, not a claim that zero is meaningless. Quantum "
        "mechanics adds a separate floor: even at zero, particles retain "
        "zero-point energy and cannot be brought fully to rest, since that "
        "would fix position and momentum at once. Laboratories get close, "
        "using laser and evaporative cooling to reach billionths of a kelvin, "
        "cold enough for atoms to merge into Bose-Einstein condensates.",
    ),
    "Helium was discovered on the Sun before it was found on Earth": (
        "During an 1868 solar eclipse, astronomers examining sunlight split "
        "into its spectrum found a bright yellow line matching no known "
        "element. It was attributed to a new one, named helium after Helios, "
        "the Greek sun.",
        "Spectroscopy made this possible: each element absorbs and emits light "
        "at a fixed set of wavelengths, a fingerprint identifying it across "
        "any distance. The claim stayed contested for decades until William "
        "Ramsay isolated helium from a uranium mineral in 1895 and found the "
        "same line in the laboratory. It was missed on Earth because helium is "
        "chemically inert, so it forms no compounds, and is light enough to "
        "escape the atmosphere. What we use is almost entirely radioactive "
        "decay product trapped underground with natural gas — a finite "
        "resource, and shortages periodically disrupt MRI scanners.",
    ),
    "Octopuses have three hearts and blue blood": (
        "Two branchial hearts push blood through the gills to pick up oxygen, "
        "and a larger systemic heart sends it to the rest of the body. The "
        "blood is blue because it carries oxygen using hemocyanin, which is "
        "built around copper rather than iron.",
        "Hemocyanin is less efficient than haemoglobin in warm, oxygen-rich "
        "water but performs better in the cold, low-oxygen conditions where "
        "many octopuses live, which is part of why it persists. It has a cost: "
        "the systemic heart stops beating when an octopus swims by jet "
        "propulsion, so swimming is exhausting and they prefer to crawl. The "
        "unusual anatomy extends further. Roughly two thirds of their neurons "
        "sit in the arms rather than the brain, so arms move with considerable "
        "independence, and they edit their own RNA extensively — possibly to "
        "adapt neural proteins to temperature.",
    ),
    "The deepest part of the ocean is nearly 11 kilometers down": (
        "Challenger Deep, at the southern end of the Mariana Trench in the "
        "western Pacific, reaches about 10,935 metres below the surface. Drop "
        "Mount Everest into it and the summit would still sit more than two "
        "kilometres underwater, with no part of the mountain breaking through.",
        "The trench exists because the Pacific plate is being forced beneath "
        "the smaller Mariana plate, and the descending slab drags the seafloor "
        "down with it. Pressure at the bottom exceeds a thousand atmospheres, "
        "roughly a tonne per square centimetre, which is why so few vehicles "
        "have made the trip: the Trieste in 1960, an uncrewed Japanese probe, "
        "James Cameron alone in 2012, and repeated dives since. Life persists "
        "regardless, including amphipods and microbes living on chemical "
        "energy. So does contamination — trench amphipods carry industrial "
        "pollutants rivalling the most polluted rivers on land.",
    ),
    "The Milky Way and Andromeda are on a collision course": (
        "Andromeda's spectrum is blueshifted, meaning it is approaching at "
        "roughly 110 kilometres per second. Current models have the two "
        "galaxies meeting in about four to five billion years and eventually "
        "merging into a single elliptical galaxy.",
        "Stars will almost certainly not collide. Galaxies are overwhelmingly "
        "empty, with typical separations millions of times stellar diameters, "
        "so the merger is a gravitational rearrangement rather than a pile-up: "
        "orbits are disrupted, gas clouds compress into bursts of star "
        "formation, and the spiral structure is destroyed. The prediction is "
        "less certain than usually presented. The approach speed is measured "
        "directly, but the sideways motion is tiny and hard to pin down, and "
        "it decides whether the galaxies strike or pass. Analyses using recent "
        "Gaia data put the odds closer to a coin flip.",
    ),
    "The eye can detect a single photon under ideal conditions": (
        "Carefully controlled experiments have shown that dark-adapted human "
        "observers can report single photons at rates better than chance. A "
        "rod cell can be triggered by one photon; the harder question is "
        "whether that signal survives the journey to awareness.",
        "The path is lossy. Many photons are absorbed or scattered before "
        "reaching the retina, and the visual system deliberately discards weak "
        "signals to avoid reporting the spontaneous noise rod cells generate "
        "on their own. Mid-century work established that perceiving a flash "
        "took several photons, and modern single-photon sources were needed to "
        "isolate the single-photon case; a 2016 study found detection slightly "
        "above chance, with observers more accurate when they felt confident. "
        "Because the effect sits so close to the noise floor, demonstrating it "
        "takes many trials.",
    ),
    "A gram of antimatter would release the energy of a large nuclear bomb": (
        "When matter meets antimatter both are converted entirely to energy, "
        "following E=mc squared with no leftover mass. A gram of antimatter "
        "annihilating with a gram of matter releases roughly 1.8 x 10^14 "
        "joules, comparable to a 43-kilotonne detonation.",
        "That makes annihilation the most energy-dense reaction known, "
        "hundreds of times more efficient than nuclear fission, which converts "
        "well under one percent of its fuel's mass. The catch is production. "
        "Antimatter is made a few particles at a time in accelerators, at "
        "colossal energy cost and with no natural reservoir to mine, so all "
        "the antiprotons ever produced at CERN would power a light bulb only "
        "briefly. It is a research subject, not a fuel. The open question is "
        "why any matter exists: the Big Bang should have made equal amounts of "
        "both, and experiments hunt for the asymmetry that spared us.",
    ),
    "The Sun burns 600 million tons of hydrogen every second": (
        "It is fusion, not burning: nothing is combusting. In the Sun's core, "
        "at roughly 15 million degrees, hydrogen nuclei are pressed together "
        "hard enough to fuse into helium, consuming about 600 million tonnes "
        "of hydrogen a second.",
        "The helium produced weighs slightly less than the hydrogen that went "
        "in — around four million tonnes a second goes missing, converted to "
        "energy via E=mc squared. That is where sunlight comes from. The "
        "process is self-regulating: if the core heats up it expands and cools "
        "slightly, which is why the Sun shines steadily rather than exploding. "
        "The energy takes a long time to escape, bouncing between particles in "
        "the dense interior for tens of thousands of years before reaching the "
        "surface, then crossing to Earth in eight minutes. At this rate the "
        "Sun has hydrogen for about five billion years more.",
    ),
    "There is no formula that generates all prime numbers": (
        "Formulas that output only primes do exist, but they are useless in "
        "practice: they either encode the answer in a constant that must be "
        "known to absurd precision beforehand, or they take longer to evaluate "
        "than simply testing numbers directly.",
        "Mills' theorem guarantees a constant whose repeated cubing and "
        "flooring always yields primes, yet computing the constant requires "
        "already knowing those primes. A known polynomial in 26 variables has "
        "the primes as exactly its positive values, but mostly returns "
        "negative numbers and gives no way to generate them in order. What "
        "does not exist is an efficient formula for the nth prime. Their "
        "distribution follows the prime number theorem at large scale while "
        "staying locally erratic, and bounding the count is the Riemann "
        "Hypothesis. Cryptography sidesteps this by testing random candidates.",
    ),
}

# Hooks whose central claim could not be confidently grounded, even though the
# post carries a source. These are reported and left untouched — inventing an
# explanation for a claim that may be wrong would only make the error look
# better researched.
UNVERIFIABLE: dict[str, str] = {
    "The only letter not in the periodic table is J": (
        "The hook's supporting line says Q appears in element names while J "
        "never does. No current IUPAC element name or symbol contains either "
        "letter — Q appeared only in retired placeholder names such as "
        "ununquadium. The claim as written is at best outdated and the post "
        "likely needs correcting rather than expanding."
    ),
}


def is_incomplete(post: dict) -> bool:
    """True when a post has no usable level 2 or level 3.

    Mirrors _post_levels in app/serializers.py: a post with no `levels` array
    is served as [body, body, body], so posts that merely repeat themselves are
    just as stuck as posts missing the field entirely.
    """
    levels = post.get("levels")
    if not isinstance(levels, list) or len(levels) < 3:
        return True
    texts = [str(level).strip() for level in levels[:3]]
    if any(not text for text in texts):
        return True
    # Level 2 or 3 that merely repeats the hook is not real depth.
    return len(set(texts)) < 3


def check_lengths() -> list[str]:
    """Validate the checked-in copy against the compose form's limits."""
    problems = []
    for headline, (explain, deep_dive) in CONTENT.items():
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
        print(
            "MONGODB_URI is not set. Point it at the target database, e.g.:\n"
            "    MONGODB_URI='<railway connection string>' DRY_RUN=true "
            "python backfill_depth_levels.py"
        )
        return 1

    # Default to a dry run: a typo in the variable name must not write.
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() != "false"

    problems = check_lengths()
    if problems:
        print("Checked-in copy is outside the target length ranges:")
        print("\n".join(problems))
        return 1

    db_name = os.getenv("MONGODB_DB", "eureka")
    print(f"[backfill] Connecting to {uri.split('@')[-1]} (db: {db_name})")
    client = AsyncIOMotorClient(uri)
    db = client[db_name]

    total = 0
    incomplete: list[dict] = []
    async for post in db.posts.find({}):
        total += 1
        if is_incomplete(post):
            incomplete.append(post)

    matched = [p for p in incomplete if p["headline"] in CONTENT]
    flagged = [p for p in incomplete if p["headline"] in UNVERIFIABLE]
    unmatched = [
        p
        for p in incomplete
        if p["headline"] not in CONTENT and p["headline"] not in UNVERIFIABLE
    ]

    # ---- Report, before touching anything ----
    print()
    print("=" * 72)
    print(f"  Posts in database:        {total}")
    print(f"  Missing level 2 or 3:     {len(incomplete)}")
    print(f"  Have prepared content:    {len(matched)}")
    print(f"  Flagged, not groundable:  {len(flagged)}")
    print(f"  No prepared content:      {len(unmatched)}")
    print("=" * 72)

    by_category: dict[str, list[dict]] = defaultdict(list)
    for post in incomplete:
        by_category[post.get("category", "Uncategorised")].append(post)

    print("\nIncomplete posts by category:")
    for category, posts in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
        ready = sum(1 for p in posts if p["headline"] in CONTENT)
        print(f"  {category:<16} {len(posts):>3}  ({ready} ready to fill)")

    missing_source = [p for p in matched if not p.get("source_url")]
    if missing_source:
        print(f"\n{len(missing_source)} of the matched posts have no source_url.")

    if flagged:
        print("\n" + "-" * 72)
        print("FLAGGED — left untouched, review these by hand:")
        for post in flagged:
            print(f"\n  {post['headline']}")
            print(f"    reason: {UNVERIFIABLE[post['headline']]}")

    if unmatched:
        print("\n" + "-" * 72)
        print("NO PREPARED CONTENT — left untouched:")
        for post in unmatched:
            src = post.get("source_url") or "no source"
            print(f"  [{post.get('category', '?')}] {post['headline']}  ({src})")
        print(
            "\n  These are incomplete but have no entry in this script. That "
            "normally\n  means production carries posts the script was not "
            "written against.\n  Add entries for them rather than letting the "
            "script guess."
        )

    if not matched:
        print("\nNothing to backfill.")
        return 0

    # ---- Dry run: print everything that would be written ----
    if dry_run:
        print("\n" + "=" * 72)
        print("  DRY RUN — no writes. Content that would be applied:")
        print("=" * 72)
        for post in sorted(matched, key=lambda p: p.get("category", "")):
            explain, deep_dive = CONTENT[post["headline"]]
            hook = (post.get("body") or "").strip()
            print(f"\n[{post.get('category', '?')}] {post['headline']}")
            print(f"  source: {post.get('source_url') or 'none'}")
            print(f"\n  L1 HOOK      ({len(hook)} chars, unchanged)\n    {hook}")
            print(f"\n  L2 EXPLAIN   ({len(explain)} chars)\n    {explain}")
            print(f"\n  L3 DEEP DIVE ({len(deep_dive)} chars)\n    {deep_dive}")
            print("\n" + "-" * 72)
        print(
            f"\nWould update {len(matched)} posts. Re-run with DRY_RUN=false to "
            "apply."
        )
        return 0

    # ---- Apply ----
    print(f"\nApplying to {len(matched)} posts…")
    updated = 0
    for post in matched:
        explain, deep_dive = CONTENT[post["headline"]]
        hook = (post.get("body") or "").strip()
        if not hook:
            print(f"  skipped (empty body): {post['headline']}")
            continue
        result = await db.posts.update_one(
            {"_id": post["_id"]},
            # body stays the hook, preserving the body == levels[0] invariant
            # the API relies on for feed previews.
            {"$set": {"levels": [hook, explain, deep_dive], "body": hook}},
        )
        updated += result.modified_count

    print(f"Updated {updated} posts.")

    remaining = 0
    async for post in db.posts.find({}):
        if is_incomplete(post):
            remaining += 1
    print(f"Still incomplete after backfill: {remaining}")
    if remaining:
        print("  (expected: flagged posts and any without prepared content)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
