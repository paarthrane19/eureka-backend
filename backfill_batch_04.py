"""Hand-written depth levels for batch 04 — Earth Science, Math, Medicine.

Safety behaviour lives in backfill_runner.py: length check before the db
connection, dry run by default, flagged headlines excluded.

    MONGODB_URI='<connection string>' DRY_RUN=true  python backfill_batch_04.py
    MONGODB_URI='<connection string>' DRY_RUN=false python backfill_batch_04.py
"""

from __future__ import annotations

import asyncio
import sys

from backfill_runner import run

FLAGGED: dict[str, str] = {}

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    # ------------------------------------------------------------ Earth Science
    "A lake in Tanzania can turn animals to stone-like mummies": (
        "Lake Natron is fed by springs carrying sodium carbonate washed out "
        "of nearby volcanic rock. The water is caustic and salty enough that "
        "animals dying in it are chemically preserved and crusted in mineral "
        "rather than rotting away.",
        "The chemistry is close to natron, the salt Egyptians used for "
        "mummification, which is where the comparison comes from. The famous "
        "photographs need a caveat, though: the photographer arranged the "
        "already-dead animals into lifelike poses, so the images are staged "
        "even though the preservation is real. Nothing turns to stone on "
        "contact, and the lake is not lethal to touch. Despite conditions "
        "that kill most life, it supports salt-loving microbes that tint the "
        "water red, and it is the main breeding site on Earth for lesser "
        "flamingos.",
    ),
    "Earthquakes can make the entire planet ring like a bell": (
        "A large earthquake sets the whole Earth vibrating at particular "
        "frequencies, the way a struck bell rings at its own notes. The "
        "planet flexes and relaxes by millimetres, and sensitive instruments "
        "detect it for weeks.",
        "These are called free oscillations, and the slowest takes about 54 "
        "minutes to complete a single cycle — roughly two million times below "
        "human hearing. The 1960 Chile earthquake was the first clearly "
        "recorded, and the 2004 Sumatra quake rang the planet for months. The "
        "notes themselves are informative: their exact frequencies depend on "
        "the density and stiffness of everything the waves pass through, so "
        "measuring them is one of the main ways we know the interior is "
        "layered and that the inner core is solid.",
    ),
    "Grand Canyon rock at the bottom is nearly two billion years old": (
        "The Colorado River has cut down through stacked layers of rock, and "
        "the deeper you go the older the layer. At the bottom of the inner "
        "gorge sit dark schists and granites formed close to two billion "
        "years ago.",
        "Those basement rocks are not sediment but the roots of an ancient "
        "mountain range, cooked and squeezed deep in the crust before being "
        "exposed. Above them the layers read as a sequence of vanished "
        "worlds: shallow seas, deserts, coastal swamps. There is also a "
        "famous gap — the Great Unconformity — where more than a billion "
        "years of record is simply missing, eroded away before the next layer "
        "was laid down. The canyon itself is young by comparison, carved "
        "mostly within the last six million years.",
    ),
    "Lightning strikes the Earth about 8 million times a day": (
        "Satellites and ground-based sensor networks count flashes continuously, "
        "around the clock. The global rate works out to roughly 100 every "
        "second, which adds up to somewhere near eight million strikes a day "
        "across the whole planet.",
        "The distribution is wildly uneven: land generates far more than "
        "ocean because it heats faster and drives stronger updraughts, and "
        "the tropics dominate, with central Africa the busiest region on "
        "Earth. Counting improved sharply once satellite optical detectors "
        "arrived, since earlier estimates relied on scattered ground stations "
        "and extrapolation. The totals matter beyond curiosity — lightning "
        "produces nitrogen oxides that affect atmospheric chemistry, and "
        "flash rates are tracked as one indicator of a warming climate.",
    ),
    "Rivers of fog can flow like water over coastal mountains": (
        "Fog is a cloud sitting on the ground, and cold damp air is denser "
        "than the air above it. Pushed inland, that heavy layer pours through "
        "gaps and over ridges, spilling downhill in a way that looks "
        "unmistakably like a waterfall.",
        "The classic setting is a coast where cold ocean water chills the air "
        "above it while inland valleys stay warm. Air is a fluid, so the same "
        "physics that governs a river applies — it seeks the lowest path and "
        "accelerates through narrow gaps. San Francisco's fog pouring over "
        "the Golden Gate is the best-known example. It is ecologically "
        "important too: California's coastal redwoods absorb fog moisture "
        "directly through their needles and depend on it through the dry "
        "summer, and measurements suggest coastal fog has been declining.",
    ),
    "Sand from the Sahara fertilizes the Amazon rainforest": (
        "Winds lift dust from the Sahara and carry it across the Atlantic. "
        "That dust is rich in phosphorus, a nutrient the Amazon's heavily "
        "weathered soils lack, so the delivery quietly replaces what the "
        "rainforest loses to its rivers.",
        "NASA's CALIPSO satellite measured the plume with a laser and put the "
        "transfer at roughly 27 million tonnes of dust reaching the Amazon "
        "basin each year — carrying phosphorus in the same rough quantity the "
        "forest loses to runoff. Much of it originates in the Bodélé "
        "Depression in Chad, an ancient lake bed full of dead microorganisms. "
        "The amount varies a great deal from year to year with rainfall in "
        "the Sahel, and how tightly the two systems are coupled over long "
        "periods is still being worked out.",
    ),
    "Some of Earth's water is older than the Sun": (
        "Water molecules form in cold interstellar clouds long before stars "
        "ignite. Some of that ancient water survived the Sun's formation "
        "intact rather than being broken apart, and ended up in comets and "
        "eventually in our oceans.",
        "The evidence is deuterium, a heavy form of hydrogen. Water made in "
        "the frigid conditions between stars carries far more of it than "
        "water made in the warm disc around a young Sun, and some solar "
        "system water shows that interstellar signature. Models suggest a "
        "substantial fraction — perhaps a third or more — predates the Sun. "
        "It matters for how common life might be: if water routinely survives "
        "star formation rather than having to be manufactured each time, "
        "young planetary systems start out already wet.",
    ),
    "The Earth's inner core is as hot as the surface of the Sun": (
        "The solid iron ball at Earth's centre sits at roughly 5,400°C, close "
        "to the Sun's 5,500°C surface. The heat is left over from the "
        "planet's formation plus energy from radioactive elements decaying in "
        "the interior.",
        "Nobody has measured it directly — the deepest borehole barely "
        "scratches the crust. The figure comes from squeezing iron between "
        "diamond anvils and firing lasers at it to find the melting point at "
        "core pressures, combined with seismic waves that reveal where the "
        "material is solid or liquid. Despite the temperature the inner core "
        "is solid, because immense pressure forces the atoms into place. The "
        "liquid layer around it churns and generates Earth's magnetic field, "
        "which shields the atmosphere from being stripped by the solar wind.",
    ),
    "The Pacific Ocean is shrinking while the Atlantic grows": (
        "New seafloor is being created along a ridge running down the middle "
        "of the Atlantic, pushing the continents apart. The Pacific has "
        "subduction zones around its rim where old seafloor dives back into "
        "the mantle faster than new crust forms.",
        "The rates are slow but relentless — the Atlantic widens a few "
        "centimetres a year, about as fast as fingernails grow, and the "
        "Pacific narrows. Those Pacific subduction zones are the Ring of "
        "Fire, and they generate most of the world's large earthquakes and "
        "volcanoes. Extended far enough forward, the trend closes the Pacific "
        "and gathers the continents into a new supercontinent in a couple of "
        "hundred million years. Which arrangement they end up in is genuinely "
        "uncertain, and several rival models exist.",
    ),
    "The ground beneath Yellowstone breathes up and down": (
        "A body of partly molten rock sits beneath the park. As magma and hot "
        "water move and pressure shifts, the ground above rises and falls by "
        "centimetres a year — measurable by GPS and satellite radar, "
        "invisible to a visitor.",
        "Parts of the caldera floor rose more than 20 centimetres over "
        "several years in the mid-2000s, then subsided again. The motion "
        "reflects fluids redistributing rather than an eruption building, and "
        "surveys consistently find the magma chamber is mostly solid crystal "
        "with only a small fraction of melt — well short of what an eruption "
        "would require. Yellowstone's supervolcano reputation outpaces the "
        "monitoring data, which is why the observatory publishes readings "
        "publicly. The same heat drives the geysers the park is known for.",
    ),
    "There are more trees on Earth than stars in the Milky Way": (
        "A global survey combining ground counts with satellite imagery put "
        "the number of trees at roughly three trillion. The Milky Way holds "
        "somewhere between 100 and 400 billion stars, so trees win by close "
        "to a factor of ten.",
        "The 2015 study revised earlier estimates upward by more than "
        "sevenfold, because previous work relied on satellite images alone "
        "while this pooled hundreds of thousands of on-the-ground plot "
        "counts. The same study found humans remove about 15 billion trees a "
        "year and that the global total has fallen by nearly half since "
        "civilisation began. Both figures carry real uncertainty — the star "
        "count depends on how many faint dwarfs go undetected, and tree "
        "counts depend on where you draw the line between tree and shrub.",
    ),
    "There is a permanent storm-fed lightning capital on Earth": (
        "Where the Catatumbo River meets Lake Maracaibo in Venezuela, "
        "thunderstorms form almost nightly. Warm moist air off the lake is "
        "pushed up against surrounding mountains, and the result is lightning "
        "on close to 300 nights a year.",
        "NASA satellite data confirmed it as the most lightning-dense place "
        "measured anywhere, with hundreds of flashes per square kilometre "
        "annually and storms that can run for nine hours at a stretch. The "
        "geography does it: a basin enclosed on three sides by mountains "
        "traps humid air, and cool mountain air sliding down at night forces "
        "it upward. Sailors used it as a navigation beacon for centuries. It "
        "is not truly permanent — a drought in 2010 stopped it for weeks, "
        "which caused genuine alarm locally.",
    ),
    "There is a river of sand and rock flowing beneath Antarctica's ice": (
        "Meltwater at the base of the ice sheet, kept liquid by pressure and "
        "geothermal heat, carries sediment along in channels. The result "
        "behaves like a river system — but running under kilometres of ice "
        "rather than in open air.",
        "Radar surveys and seismic imaging have traced these channels, "
        "including one system hundreds of kilometres long, along with lakes "
        "that periodically fill and drain. The sediment matters more than it "
        "sounds: a soft, wet, deformable layer beneath a glacier lets the ice "
        "above slide far faster than it would over bare rock, so these "
        "systems help set how quickly Antarctic ice reaches the sea. That "
        "makes them a real source of uncertainty in sea-level projections, "
        "and they are among the hardest things on Earth to observe directly.",
    ),
    "Volcanic lightning can crackle inside erupting ash clouds": (
        "An eruption blasts out ash particles that collide and rub against "
        "each other, stripping electrons and building up static charge. When "
        "the separation grows large enough it discharges — lightning inside "
        "the plume.",
        "Two mechanisms appear to operate. Near the vent, fragmenting rock "
        "charges by friction and produces small rapid sparks; higher up, ice "
        "forming on ash particles charges the plume much as it does in an "
        "ordinary thunderstorm. Because the flashes are detectable at long "
        "range and through darkness, monitoring agencies use them to confirm "
        "an eruption is underway when satellites are obscured — genuinely "
        "useful for warning aircraft, since ash melts inside jet engines and "
        "can stall them. The lightning may also help fuse ash into small "
        "spheres.",
    ),
    # --------------------------------------------------------------------- Math
    "A knot in higher dimensions can always be untied": (
        "A knot works because a loop of string in three dimensions has "
        "nowhere to pass through itself. Give it a fourth dimension to move "
        "in and you can lift one strand around another, so any ordinary knot "
        "falls apart.",
        "The analogy is a two-dimensional creature facing a circle drawn "
        "around it — trapped in its plane, trivially free if lifted into the "
        "third dimension. The extra room provides exactly that escape route. "
        "Knotting is not impossible in four dimensions, though; it just needs "
        "a higher-dimensional object. Surfaces such as spheres can be knotted "
        "in four dimensions, and knotted-surface theory is an active field. "
        "Dimension four turns out to be the strangest case of all, with "
        "phenomena that appear in no other.",
    ),
    "A prime number was found with over 41 million digits": (
        "Prime numbers divide by nothing but themselves and one. In 2024 a "
        "distributed computing project turned up one with 41,024,320 digits — "
        "printed at normal size it would run to tens of thousands of pages, "
        "far more than any book.",
        "It is a Mersenne prime, one less than a power of two, and that form "
        "is no accident: a specialised test makes numbers of this shape far "
        "cheaper to check than arbitrary ones, so nearly every record holder "
        "is a Mersenne. The Great Internet Mersenne Prime Search coordinates "
        "volunteers' spare computing power, and this find used graphics cards "
        "in a cloud cluster. Euclid proved there is no largest prime, so the "
        "record only ever reflects available computing. Whether infinitely "
        "many Mersenne primes exist is still unproven.",
    ),
    "Folding a paper 42 times would reach the Moon": (
        "Each fold doubles the thickness rather than adding to it. Starting "
        "from ordinary paper a tenth of a millimetre thick, doubling 42 times "
        "gives a stack of roughly 440,000 kilometres — beyond the Moon's "
        "average distance.",
        "The arithmetic is exact; the physical claim is not. Every fold also "
        "halves the surface area, so paper runs out of width long before it "
        "runs out of thickness, and material at the crease has to stretch "
        "around an ever-thicker bend. Seven folds was long considered the "
        "practical limit until a student named Britney Gallivan derived the "
        "governing equation and managed twelve using an enormous roll of "
        "tissue paper. The real lesson is how badly human intuition handles "
        "repeated doubling, which is why compound growth surprises people.",
    ),
    "Fractals look the same no matter how far you zoom in": (
        "A fractal is built so that its parts echo the shape of the whole. "
        "Magnify any piece and you find structure resembling what you started "
        "with, and magnifying that piece does the same thing again, and again, "
        "without ever bottoming out.",
        "Mathematically these shapes can have a dimension that is not a whole "
        "number — a coastline is more than a line but less than a surface, "
        "and its measured length grows the finer your ruler, never settling "
        "on an answer. Nature only approximates this: ferns, blood vessels, "
        "river networks and lungs repeat their pattern across a handful of "
        "scales before hitting the size of a cell or a molecule. The "
        "repetition is efficient, packing enormous surface area into small "
        "volume, which is exactly what a lung needs.",
    ),
    "Randomness is impossible to prove but easy to assume": (
        "You can show a sequence fails to be random by spotting a pattern in "
        "it. You cannot show the reverse, because no amount of testing rules "
        "out a pattern that is simply too subtle, or too long, to have "
        "surfaced in what you have looked at so far.",
        "Formally, a sequence counts as random if no description of it is "
        "shorter than the sequence itself — and that property is provably "
        "impossible to verify in general. So randomness testing is a battery "
        "of checks for known weaknesses, and passing means only that nothing "
        "was caught. This matters for security: most computers produce "
        "pseudorandom numbers from a starting seed, perfectly predictable if "
        "you know it. Serious applications mix in physical noise, and "
        "cryptographic failures have repeatedly traced back to weak "
        "randomness.",
    ),
    "Shuffling a deck likely creates an order never seen before": (
        "A 52-card deck can be arranged in about 8 followed by 67 zeros ways. "
        "That number so vastly exceeds every shuffle ever performed in human "
        "history that a properly shuffled deck is almost certainly in a new "
        "order.",
        "For scale, if every person alive shuffled once a second since the "
        "universe began, the arrangements covered would still round to zero "
        "against the total. The catch is properly shuffled: a riffle shuffle "
        "is far less effective than it looks, and mathematicians showed about "
        "seven are needed before a deck is thoroughly mixed. Fewer than that "
        "leaves detectable structure from the previous order, which is why "
        "casinos are specific about procedure and why card counting and "
        "shuffle tracking are possible at all.",
    ),
    "The Fibonacci sequence shows up all over nature": (
        "Each number is the sum of the two before it: 1, 1, 2, 3, 5, 8, 13. The "
        "sequence turns up in the spiral counts of pine cones, sunflower heads "
        "and pineapples, and in the angles at which leaves are spaced out "
        "around a growing stem.",
        "There is a reason rather than a mystery. Growing new parts at an "
        "angle related to the golden ratio packs them without any two lining "
        "up, which maximises light and space — and that arrangement produces "
        "Fibonacci counts as a side effect. So the pattern follows from "
        "efficient packing. Plenty of popular examples are simply wrong, "
        "though: the nautilus shell is a logarithmic spiral but not the "
        "golden one, and claims about faces, art and the Parthenon mostly "
        "come from loose measurement. Some plants use other sequences "
        "entirely.",
    ),
    "The digits of pi have never repeated and never will": (
        "Pi is irrational, meaning it cannot be written as one whole number "
        "divided by another. That property is exactly what guarantees its "
        "decimal expansion never terminates and never settles into a repeating "
        "block, however far out you compute it.",
        "Every fraction eventually repeats — a seventh gives 142857 forever — "
        "so proving pi is not a fraction proves the digits never cycle. "
        "Lambert established this in 1761. A separate and much harder "
        "question is whether pi is normal: whether every digit and every "
        "sequence of digits appears equally often in the long run. It looks "
        "that way across the trillions of digits computed, but nobody has "
        "proved it. If true, any number you can name — a phone number, a "
        "birthday — appears somewhere in the expansion.",
    ),
    "The four color theorem was the first proved mostly by computer": (
        "The claim is that any map can be coloured with four colours so no "
        "two neighbouring regions match. The 1976 proof reduced the problem "
        "to nearly 2,000 special cases, then had a computer grind through "
        "every one.",
        "The reduction was human work: showing that if a counterexample "
        "existed it would have to contain one of a finite catalogue of "
        "configurations. Checking that catalogue by hand was infeasible, so a "
        "machine did it. That provoked a genuine philosophical argument — a "
        "proof no human can read in full asks mathematicians to trust "
        "hardware and code rather than an argument they can follow. Later "
        "work shrank the case count and verified it inside a proof assistant, "
        "and computer-assisted proof is now routine, though the discomfort "
        "has never entirely gone.",
    ),
    "The golden ratio is the most irrational number there is": (
        "Every irrational number can be approximated by fractions. The golden "
        "ratio resists that approximation more stubbornly than any other, so "
        "in a precise technical sense it is the hardest of all to pin down "
        "with a fraction.",
        "The measure is continued fractions, which express a number as nested "
        "reciprocals. Large terms in that expansion mean an unusually good "
        "fractional approximation is available — pi has one, which is why "
        "22/7 works so well. The golden ratio's expansion is nothing but ones, "
        "the slowest possible convergence. Plants exploit this: growing "
        "successive leaves at the corresponding angle means they never line "
        "up, since lining up would require a good fractional approximation. "
        "The most irrational number is therefore the best possible packing "
        "angle.",
    ),
    "The number graham once held the record for largest used in a proof": (
        "Graham's number came out of a genuine problem in combinatorics as an "
        "upper bound on an answer. It is so vast that ordinary notation "
        "fails, and it has to be built from repeated layers of exponentiation "
        "instead.",
        "Writing it is impossible in principle: even one digit per Planck "
        "volume would exhaust the observable universe many times over. It is "
        "defined by starting with a tower of threes, then using that result "
        "to decide how tall the next tower is, and repeating 64 times. Yet "
        "the last digits are known, because the final digits of such towers "
        "settle into a pattern. The joke is that the true answer is thought "
        "to be small — the proven lower bound is around 13 — so the bound was "
        "spectacularly loose, and better ones have since replaced it.",
    ),
    "The sum of all positive integers is bizarrely linked to minus one twelfth": (
        "Add 1 plus 2 plus 3 forever and the total grows without limit. But "
        "an entirely different procedure, which extends a related function "
        "into territory where the naive sum breaks down, assigns that series "
        "the value -1/12.",
        "The function is the Riemann zeta function. Written as a sum it only "
        "makes sense for certain inputs, but there is exactly one smooth way "
        "to extend it everywhere else, and at the relevant point that "
        "extension gives -1/12. So the number is a property of the extension, "
        "not of the addition — popular videos claiming the sum equals -1/12 "
        "are wrong. The strange part is that it works physically: the same "
        "value appears in calculations of the Casimir effect and in string "
        "theory, matching experiment.",
    ),
    "There are more possible chess games than atoms in the universe": (
        "Every move branches into many replies, and games run for dozens of "
        "moves. Multiplying those choices gives an estimate around 10 "
        "followed by 120 zeros, against perhaps 10 followed by 80 zeros for "
        "atoms in the observable universe.",
        "Claude Shannon produced that estimate in 1950 to argue chess could "
        "never be solved by brute force, and he was right — no computer will "
        "ever enumerate every game. Engines succeed by pruning: evaluating "
        "positions and discarding most branches without examining them, and "
        "more recently by learning from self-play. Simpler games have "
        "genuinely been solved, including checkers in 2007, which is a draw "
        "with perfect play. Chess endgames with seven pieces or fewer are "
        "solved completely and stored in lookup tables.",
    ),
    "There are unsolved math problems worth a million dollars each": (
        "In 2000 the Clay Mathematics Institute named seven Millennium Prize "
        "Problems, offering a million dollars for a solution to any of them. "
        "They are long-standing questions at the centre of modern "
        "mathematics.",
        "One is solved. Grigori Perelman proved the Poincaré conjecture in "
        "2003 and then refused both the prize and the Fields Medal, saying "
        "the recognition was unfair to others. The rest remain open, "
        "including the Riemann hypothesis about how prime numbers are "
        "distributed and P versus NP, which asks whether every problem with "
        "a quickly checkable answer also has a quickly findable one. The "
        "stakes are practical as well as abstract — most modern encryption "
        "would be in serious trouble if P turned out to equal NP.",
    ),
    "Zero was a revolutionary invention, not an obvious one": (
        "Counting systems can manage without a symbol for nothing. Treating "
        "zero as a number in its own right, one you can add and subtract and "
        "calculate with, took thousands of years and was resisted when it "
        "arrived.",
        "Babylonians used a placeholder mark to distinguish 26 from 206, but "
        "not a number. Indian mathematicians took the decisive step around "
        "the seventh century, when Brahmagupta wrote rules for arithmetic "
        "with zero and with negative numbers. The idea travelled through the "
        "Islamic world to Europe, where it met genuine hostility — some "
        "Italian cities banned Arabic numerals, partly because a zero is easy "
        "to alter on a ledger. Without it there is no place-value notation, "
        "no algebra as we know it, and no binary computing.",
    ),
    # ----------------------------------------------------------------- Medicine
    "A single sneeze can launch droplets at up to 160 km per hour": (
        "A sneeze is a sharp involuntary blast: the chest compresses, "
        "pressure builds behind a closed throat, and the release fires air "
        "and droplets out of the nose and mouth far faster than ordinary "
        "breathing ever manages.",
        "The 160 km/h figure is widely repeated but poorly supported. Careful "
        "high-speed measurements put sneeze velocities considerably lower, "
        "typically tens of kilometres per hour rather than motorway speed. "
        "What the same imaging revealed is arguably more important: a sneeze "
        "is not a spray of separate droplets but a turbulent gas cloud that "
        "carries them much further than simple ballistics predicts — up to "
        "seven or eight metres, with the smallest lingering in the air "
        "afterwards. That work directly reshaped ventilation guidance during "
        "the COVID-19 pandemic.",
    ),
    "A transplanted organ carries the donor's DNA for life": (
        "A transplanted kidney or heart is built from the donor's cells, and "
        "those cells keep their original DNA. The recipient's body does not "
        "convert them, so the organ stays genetically someone else "
        "indefinitely.",
        "This is exactly why rejection happens: the immune system reads the "
        "donor's cell-surface markers as foreign, which is why recipients "
        "take immunosuppressants for life and why tissue matching matters so "
        "much. Bone marrow transplants go further and genuinely strange — the "
        "donor's stem cells take over blood production, so the recipient's "
        "blood permanently carries donor DNA while their skin and hair do "
        "not. Forensic laboratories have to account for these chimeras, and "
        "there are documented cases of blood samples matching the wrong "
        "person entirely.",
    ),
    "Antibiotics do nothing against viruses like the common cold": (
        "Antibiotics attack structures bacteria have and viruses do not — "
        "cell walls, bacterial ribosomes, their particular enzymes. A virus "
        "has none of that machinery, so there is simply nothing for the drug "
        "to target.",
        "Viruses hijack your own cells to reproduce, which is what makes them "
        "hard to treat: anything toxic to a virus mid-replication tends to be "
        "toxic to the cell hosting it. Antivirals exist but must be far more "
        "narrowly targeted. Prescribing antibiotics for a cold does nothing "
        "for the patient while killing off useful bacteria and helping "
        "resistant strains spread, which is why the WHO treats unnecessary "
        "prescribing as a global health threat. Resistant infections already "
        "cause well over a million deaths a year.",
    ),
    "Blushing is your nervous system dilating blood vessels in your face": (
        "Embarrassment triggers the fight-or-flight response, which releases "
        "adrenaline. In most of the body that narrows blood vessels, but the "
        "vessels in your face respond by widening instead, so more blood "
        "flows close to the skin and it reddens.",
        "Facial veins carry receptors that respond to adrenaline by relaxing, "
        "which is why the effect is confined to the face, neck and upper "
        "chest. Nobody knows quite why humans evolved a visible, "
        "uncontrollable signal of embarrassment — the leading idea is social: "
        "an involuntary display of remorse is hard to fake, so it functions "
        "as a credible apology and helps repair relationships. Darwin called "
        "it the most peculiar and most human of all expressions. No other "
        "animal appears to do it.",
    ),
    "Broken bones can become stronger than before at the healing site": (
        "Healing bone forms a bulky collar of new tissue, called a callus, right "
        "around the break. For a period of weeks to months that repair is "
        "thicker and stronger than the original bone was, which is where the "
        "claim comes from.",
        "The advantage is temporary. Over months to years the body remodels "
        "the callus away, dissolving surplus material and rebuilding the bone "
        "back to its normal shape and strength — so the healed site ends up "
        "about as strong as before, not permanently reinforced. The idea that "
        "a break makes you stronger for good is a myth. Previously fractured "
        "bones can in fact be more vulnerable, particularly if the break "
        "involved a joint surface or healed out of alignment. Bone remodels "
        "constantly regardless, replacing itself throughout your life.",
    ),
    "CRISPR lets scientists edit genes with molecular scissors": (
        "CRISPR pairs a guide molecule that recognises a specific DNA "
        "sequence with an enzyme that cuts. Point the guide at a chosen spot "
        "in the genome and the enzyme snips it, letting the cell's repair "
        "machinery disable or replace the gene.",
        "It was borrowed from bacteria, which use it to store fragments of "
        "viruses they have survived and shred any that return — an immune "
        "system with a memory. What made it revolutionary is cost: earlier "
        "editing tools required custom protein engineering for each target, "
        "while CRISPR needs only a new guide sequence, putting gene editing "
        "within reach of ordinary labs. The first CRISPR therapy was approved "
        "in 2023 for sickle cell disease. Off-target cuts and the ethics of "
        "editing embryos remain unresolved.",
    ),
    "Fever is a defense, not just a symptom": (
        "Your body raises its own temperature deliberately. The brain shifts "
        "its thermostat upward in response to infection, because many "
        "pathogens replicate poorly when warm while your immune cells work "
        "faster.",
        "Raised temperature speeds white blood cell activity and slows some "
        "bacteria and viruses, and the shivering and chills at fever onset "
        "are the body actively generating heat to reach the new set point. "
        "The effect is old enough to be shared with reptiles, which seek out "
        "warm spots when infected. That does not make fever harmless — very "
        "high temperatures are dangerous and treatment relieves genuine "
        "misery — but evidence that routinely suppressing a moderate fever "
        "helps recovery is weak, and some studies suggest it slightly "
        "prolongs illness.",
    ),
    "Laughter measurably reduces stress hormones": (
        "Studies measuring cortisol and adrenaline in blood have found levels "
        "drop after bouts of laughter. It also relaxes muscles and briefly "
        "raises heart rate before settling it, resembling a small burst of "
        "exercise.",
        "The physical effects are reasonably well documented; the strength of "
        "the health claims around them is not. Most studies are small, "
        "short-term and hard to blind — you cannot give someone a placebo "
        "comedy — and effects on pain tolerance and immune markers vary a lot "
        "between trials. Social context appears to matter more than humour "
        "itself, since most laughter happens in conversation rather than at "
        "jokes, which suggests part of the benefit is really connection. "
        "Laughter as medicine is plausible and modest, not a treatment.",
    ),
    "Placebos can produce real, measurable improvements": (
        "Given an inert pill they believe is a real drug, patients often improve "
        "in ways that show up in objective measurements, not just in what they "
        "say about how they feel. Expectation on its own changes what the "
        "body actually does.",
        "Brain imaging shows placebo pain relief releases the body's own "
        "opioids, and a drug that blocks those opioids blocks the placebo "
        "effect too, which demonstrates real biology rather than politeness. "
        "Effects are strongest for pain, nausea and depression, and absent "
        "for things belief cannot touch — a placebo will not shrink a tumour. "
        "Strangest of all, open-label placebos, where patients are told "
        "outright the pill is inert, still work in some trials. It is why "
        "controlled studies exist: without a placebo arm you cannot tell what "
        "the drug did.",
    ),
    "The appendix may not be useless after all": (
        "The appendix appears to act as a reservoir for gut bacteria. Its "
        "narrow dead-end shape shelters a population of beneficial microbes, "
        "which can repopulate the intestine after illness flushes the gut "
        "out.",
        "It is rich in immune tissue and hosts bacterial biofilms, supporting "
        "the safe house idea. Evidence includes patients without an appendix "
        "being markedly more likely to suffer recurrent Clostridioides "
        "difficile infection, and the structure having evolved independently "
        "many times across mammals — a strong hint it does something. That "
        "said, removing it causes no obvious long-term harm in a world with "
        "clean water and antibiotics, and appendicitis kills without "
        "treatment, so surgery remains standard. Useful is not the same as "
        "essential.",
    ),
    "The human body produces about 25 million new cells every second": (
        "Your body constantly replaces worn-out cells. Adding up blood, gut "
        "lining, skin and everything else, the turnover works out to tens of "
        "millions of new cells every second — several hundred billion over a "
        "day.",
        "Red blood cells dominate the count: bone marrow makes around two "
        "million a second because each one survives only four months and "
        "cannot repair itself, having ejected its nucleus. Gut lining renews "
        "every few days under constant chemical assault, while heart muscle "
        "and most brain neurons barely renew at all, which is why damage "
        "there is permanent. Total production roughly balances loss, so your "
        "weight stays stable. Cancer is fundamentally this system failing — "
        "cells that keep dividing when they should stop.",
    ),
    "The smallpox vaccine came from cowpox and dairymaids": (
        "Milkmaids who caught cowpox, a mild disease from cattle, seemed not "
        "to get smallpox. In 1796 Edward Jenner deliberately infected a boy "
        "with cowpox, then exposed him to smallpox — and he did not fall ill.",
        "The two viruses are similar enough that immunity to one protects "
        "against the other, so cowpox trained the immune system without the "
        "risk. The word vaccine comes from vacca, Latin for cow. The "
        "experiment would fail every modern ethics review, and Jenner was not "
        "quite first — a farmer named Benjamin Jesty had done something "
        "similar decades earlier — but Jenner published and pushed it. "
        "Smallpox was declared eradicated in 1980, the only human disease "
        "ever wiped out, having killed hundreds of millions.",
    ),
    "Your bone marrow makes billions of red blood cells daily": (
        "Red blood cells last about four months and cannot repair themselves, "
        "so they need constant replacement. Marrow inside your larger bones "
        "produces them at roughly two million a second — around 200 billion "
        "a day.",
        "Production is regulated by the kidneys, which sense oxygen levels and "
        "release a hormone telling marrow to speed up. That is why living at "
        "altitude raises your red cell count, and why a synthetic version of "
        "the hormone became a notorious endurance-doping drug. Each new cell "
        "ejects its nucleus to make room for haemoglobin, which is what makes "
        "it efficient at carrying oxygen and also why it cannot divide or "
        "repair. Worn-out cells are broken down in the spleen and the iron "
        "recycled almost entirely.",
    ),
}


if __name__ == "__main__":
    sys.exit(asyncio.run(run("batch 04", CONTENT, FLAGGED)))
