"""Hand-written depth levels for batch 05 — Physics and Technology.

Safety behaviour lives in backfill_runner.py: length check before the db
connection, dry run by default, flagged headlines excluded.

    MONGODB_URI='<connection string>' DRY_RUN=true  python backfill_batch_05.py
    MONGODB_URI='<connection string>' DRY_RUN=false python backfill_batch_05.py
"""

from __future__ import annotations

import asyncio
import sys

from backfill_runner import run

FLAGGED: dict[str, str] = {
    "Your keyboard likely has more bacteria than a toilet seat": (
        "The comparison traces to a small unpublished consumer survey, not to "
        "the CDC source attached to the post, and it measures raw colony "
        "counts rather than anything harmful — toilet seats are dry, smooth "
        "and cleaned often, so they are a low bar. Needs a real source or "
        "retirement rather than a deeper explanation."
    ),
}

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    # ------------------------------------------------------------------ Physics
    "A spinning figure skater speeds up by pulling in their arms": (
        "A spinning object carries a fixed amount of rotational motion unless "
        "something outside it interferes. Pulling mass closer to the axis of "
        "the spin means the body has to turn faster to keep that total "
        "quantity unchanged.",
        "The conserved quantity is angular momentum, which depends on both "
        "how fast you spin and how far your mass sits from the axis. Shrink "
        "the second and the first must rise to compensate. The skater is not "
        "getting the speed for free — muscles do real work hauling the arms "
        "inward against the outward pull, and that energy goes into the "
        "faster spin. The same principle governs a collapsing star spinning "
        "up into a pulsar, and it is why a cat can twist mid-air to land on "
        "its feet without pushing against anything.",
    ),
    "Electrons are not tiny balls; they behave like waves of probability": (
        "An electron has no definite position until measured. What physics "
        "tracks instead is a wave describing where it is likely to be found, "
        "and that wave spreads out, interferes with itself and reshapes as it "
        "moves.",
        "Fire electrons one at a time at a barrier with two slits and each "
        "lands as a single dot, yet the accumulated pattern shows "
        "interference — as though every electron passed through both slits "
        "and interfered with itself. Detect which slit it uses and the "
        "pattern disappears. Around an atom this wave picture explains why "
        "electrons occupy fixed energy levels: only certain standing wave "
        "shapes fit, so energies come in steps. What the wave actually is, "
        "rather than what it predicts, remains genuinely disputed after a "
        "century.",
    ),
    "Light takes 100,000 years to escape the Sun's core": (
        "Energy made by fusion in the core cannot travel straight out. The "
        "interior is so dense that a photon is absorbed and re-emitted in a "
        "random direction constantly, staggering outward in a drunken walk "
        "rather than a straight line.",
        "Each step is a fraction of a millimetre before the next collision, "
        "and because the direction is random the photon makes progress "
        "agonisingly slowly. Estimates of the crossing time vary hugely — "
        "thousands to hundreds of thousands of years, depending on the "
        "density model — so the specific figure should be read loosely. "
        "Strictly, no single photon survives the journey: energy is passed "
        "along through countless absorptions and re-emissions. Once free, the "
        "same energy reaches Earth in eight minutes. Neutrinos leave "
        "immediately, which is how the core is observed directly.",
    ),
    "Neutron stars are so dense a sugar-cube of them would weigh a billion tons": (
        "A neutron star packs more mass than the entire Sun into a sphere about "
        "the width of a city. Atoms have been crushed until the empty space "
        "inside them is gone completely, leaving bare neutrons packed shoulder "
        "to shoulder.",
        "The density matches the inside of an atomic nucleus, roughly a "
        "hundred trillion times that of water. Gravity at the surface is "
        "billions of times Earth's, and the star is almost perfectly smooth — "
        "its tallest features are millimetres high, because nothing can pile "
        "higher against that pull. Many spin hundreds of times a second, "
        "carrying magnetic fields trillions of times stronger than Earth's. "
        "What happens at the very centre, under still greater pressure, is "
        "unknown: the neutrons may break down into free quarks, and "
        "gravitational-wave data is starting to constrain it.",
    ),
    "Quantum entanglement links particles no matter how far apart they are": (
        "Two particles can be prepared so that their properties are tied "
        "together. Measure one of them and you instantly know the matching "
        "result for the other, whether it happens to be sitting in the next "
        "room or right across the galaxy.",
        "Einstein called it spooky and argued the particles must simply carry "
        "hidden instructions from the start. John Bell showed that idea makes "
        "different statistical predictions than quantum mechanics, and "
        "decades of increasingly careful experiments have come down "
        "decisively against hidden instructions — work that won the 2022 "
        "Nobel Prize. Crucially this sends no signal: each individual result "
        "looks random, and only comparing both sets afterwards, over an "
        "ordinary channel limited by light speed, reveals the correlation. It "
        "underpins quantum computing and quantum cryptography.",
    ),
    "Sound cannot travel through the vacuum of space": (
        "Sound is a pressure wave passed along from particle to particle. Space "
        "is close enough to empty that the particles are far too sparse to "
        "hand a vibration between them, so there is simply nothing there to "
        "carry the wave.",
        "The density is around one atom per cubic centimetre in interstellar "
        "space, against roughly 10 billion billion in air. Sound does not "
        "travel slowly there; it has no medium at all. Denser regions are "
        "different: gas in galaxy clusters carries genuine pressure waves, "
        "including one rippling through the Perseus cluster at a pitch some "
        "57 octaves below middle C. NASA sonifications convert such "
        "measurements into audible sound, which is translation rather than "
        "recording. Radio, being electromagnetic, crosses vacuum without "
        "trouble.",
    ),
    "Static electricity can generate tens of thousands of volts": (
        "Rubbing two materials together transfers electrons, leaving one surface "
        "positively charged and the other negative. Because almost no charge "
        "actually moves, the voltage can climb to tens of thousands before it "
        "finally jumps across as a spark.",
        "Voltage measures the push behind the charge, not how much energy is "
        "available. A doorknob shock may reach 20,000 volts and be harmless, "
        "because the total charge and the duration are minuscule — whereas "
        "240 volts from a socket can kill by delivering sustained current. "
        "That distinction is why the same effect that is trivial at home is "
        "taken very seriously in industry: a spark too faint to feel will "
        "destroy a microchip or ignite fuel vapour, which is why electronics "
        "workers wear grounding straps and fuel tankers are bonded before "
        "loading.",
    ),
    "The Casimir effect pushes two metal plates together using nothing": (
        "Empty space is not truly empty — it seethes with fleeting "
        "fluctuations of electromagnetic fields. Place two uncharged plates "
        "extremely close and fewer fluctuations fit between them than "
        "outside, so the outside pushes them together.",
        "The gap has to be tiny, well under a micrometre, and the force grows "
        "sharply as it narrows. Predicted by Hendrik Casimir in 1948, it was "
        "measured convincingly only in 1997, and the results match theory "
        "closely. It is a real engineering concern in microscopic machines, "
        "where the attraction can make delicate parts stick together "
        "permanently. Interpretation is contested — some physicists argue it "
        "is better described as ordinary forces between the atoms in the "
        "plates than as an effect of vacuum energy itself.",
    ),
    "The universe has a background hum left over from the Big Bang": (
        "About 380,000 years after the Big Bang the universe cooled enough "
        "for light to travel freely. That first release of light still fills "
        "space, stretched by expansion into faint microwaves reaching us from "
        "every direction.",
        "It was found by accident in 1964 by Penzias and Wilson, who blamed a "
        "persistent hiss in their antenna on pigeon droppings before "
        "realising it came from the sky itself. The glow is remarkably "
        "uniform, but the tiny variations across it — about one part in "
        "100,000 — are the seeds that grew into galaxies, and mapping them "
        "with WMAP and Planck is how the universe's age, geometry and "
        "composition were pinned down. A separate genuine hum was reported in "
        "2023: a background of gravitational waves from merging supermassive "
        "black holes.",
    ),
    "Tungsten does not melt until over 3,400 degrees Celsius": (
        "Tungsten atoms bond to one another exceptionally strongly, so an "
        "enormous amount of heat is needed to shake them loose. At 3,422°C it "
        "has the highest melting point of any metal, and of any element "
        "except carbon.",
        "That property made it the filament in incandescent bulbs for a "
        "century: it could glow white-hot without melting, though it "
        "gradually evaporated and blackened the glass. It is brittle at room "
        "temperature and hard to machine, so parts are usually pressed from "
        "powder and sintered rather than cast. Modern uses lean on its "
        "density instead — nearly that of gold — in armour-piercing "
        "ammunition, radiation shielding, and increasingly in jewellery. "
        "Tungsten carbide, harder still, tips most industrial cutting tools.",
    ),
    "You can boil water and freeze it at the same time": (
        "At one specific combination of temperature and pressure, water can "
        "exist as solid, liquid and gas all at the same time. Sitting exactly "
        "at that point it boils and freezes simultaneously, in the same "
        "container, right in front of you.",
        "This is the triple point, at 0.01°C and a pressure roughly a "
        "hundredth of sea level. All three phases sit in equilibrium, "
        "constantly converting into one another with no net change. Because "
        "the conditions are reproducible anywhere to extraordinary precision, "
        "the triple point of water defined the kelvin scale for decades, "
        "until the definition was tied to a fundamental constant in 2019. "
        "Every substance has its own triple point — carbon dioxide's sits "
        "above atmospheric pressure, which is exactly why dry ice sublimes "
        "instead of melting.",
    ),
    # --------------------------------------------------------------- Technology
    "A single Google search draws on data centers around the globe": (
        "Your query is routed to whichever data centre can answer fastest, "
        "and the answer is assembled from an index spread across thousands of "
        "machines. Hundreds of computers may touch a single search before you "
        "see results.",
        "The index is far too large for one machine, so it is split into "
        "shards queried in parallel and merged. The whole round trip "
        "typically finishes in under a fifth of a second, most of it network "
        "delay rather than computation. Copies are held in multiple regions, "
        "so a failure anywhere is routed around invisibly. The energy cost "
        "per search is small — comparable to running a lightbulb briefly — "
        "but multiplied by billions daily it is substantial, which is why "
        "operators buy renewable power and site facilities where cooling is "
        "cheap.",
    ),
    "Early hard drives could crash if you jumped near them": (
        "A drive head floats microscopically above a spinning platter, closer "
        "than the width of a hair. A hard enough jolt could knock it into the "
        "surface, gouging the magnetic coating and destroying the data "
        "beneath.",
        "That is the literal origin of head crash, and of calling a computer "
        "failure a crash at all. Early drives were the size of washing "
        "machines and genuinely sensitive to floor vibration, so machine "
        "rooms were built on solid foundations. Modern drives park the head "
        "when idle and include accelerometers that detect a fall and retract "
        "it mid-drop, which is why a dropped laptop usually survives. "
        "Solid-state drives removed the problem entirely by having nothing "
        "that moves, though they fail in their own quieter ways.",
    ),
    "Emoji are governed by an international standards body": (
        "Emoji are characters in Unicode, the same standard that assigns a "
        "number to every letter and symbol computers exchange. The Unicode "
        "Consortium decides which ones exist, so a message means the same "
        "thing across devices.",
        "Anyone can submit a proposal, but it must argue for expected usage, "
        "distinctiveness and lack of overlap with existing emoji, and the "
        "process takes about two years. The standard defines meaning and a "
        "code number, not appearance — Apple, Google and Samsung each draw "
        "their own, which is how the same emoji can read as friendly on one "
        "phone and hostile on another. Divergent designs have caused real "
        "confusion, and vendors have quietly redrawn emoji to converge after "
        "complaints.",
    ),
    "Fiber-optic cables send data as flashes of light": (
        "A fibre is a hair-thin strand of extraordinarily pure glass. A laser "
        "flickers light into one end of it, and that light bounces along the "
        "inside without ever escaping, carrying your data as rapid pulses all "
        "the way to the far end.",
        "It stays inside through total internal reflection: the core is "
        "surrounded by glass of slightly different composition, so light "
        "striking the boundary at a shallow angle reflects rather than "
        "leaking out. Glass purity is the engineering achievement — "
        "kilometres of it are more transparent than a window pane. A single "
        "fibre carries many wavelengths simultaneously, each an independent "
        "channel, which is how capacity keeps rising without laying new "
        "cable. Signals still weaken over distance, so repeaters spaced along "
        "undersea routes amplify them optically.",
    ),
    "Modern chips pack tens of billions of transistors onto a fingernail": (
        "A transistor is simply a switch with no moving parts. Manufacturers now "
        "print them with features only a few tens of atoms across, so tens of "
        "billions of them fit onto a piece of silicon you could comfortably "
        "cover with a fingertip.",
        "They are made by photolithography — projecting a pattern onto "
        "light-sensitive coating and etching it, repeated in layers. The "
        "newest machines use extreme ultraviolet light generated by "
        "vaporising tin droplets with lasers, and only one company in the "
        "world builds them. Moore's law, the observation that transistor "
        "counts roughly double every two years, held for decades but has "
        "slowed as features approach sizes where electrons leak across "
        "barriers. Progress now comes from stacking chips vertically and "
        "specialising them rather than shrinking further.",
    ),
    "Quantum computers could crack codes that classical machines cannot": (
        "Much of today's encryption relies on multiplying two huge primes "
        "being easy while working backwards is impractically slow. A quantum "
        "algorithm can do that reversal efficiently, undoing the assumption "
        "the security rests on.",
        "Peter Shor published the algorithm in 1994, but running it on "
        "keys of real size needs far more stable qubits than anyone has "
        "built — quantum states collapse easily, and error correction "
        "demands thousands of physical qubits per usable one. The threat is "
        "still taken seriously because of harvest now, decrypt later: "
        "encrypted traffic captured today could be read once machines "
        "improve. NIST finalised post-quantum encryption standards in 2024, "
        "built on mathematical problems quantum computers are not known to "
        "solve quickly, and migration is underway.",
    ),
    "The cloud is really just someone else's computers in a big building": (
        "Cloud storage means your files are sitting on physical servers in a "
        "data centre somewhere, owned and maintained by a company. Nothing is "
        "floating anywhere — the metaphor simply hides where the hardware "
        "actually lives and who is looking after it.",
        "The genuine shift is economic rather than technical: renting "
        "capacity by the hour instead of buying servers lets a small team "
        "scale instantly and pay only for what it uses. Your data is "
        "typically split and copied across multiple buildings, so a fire in "
        "one loses nothing. Concentration is the trade-off — a handful of "
        "providers host much of the internet, and a single misconfiguration "
        "has repeatedly taken large parts of it offline. Physical location "
        "also determines which government can compel access, which is why "
        "data residency laws exist.",
    ),
    "The first digital image was scanned in 1957 of a baby": (
        "Russell Kirsch and his team at the US National Bureau of Standards "
        "built a drum scanner and fed it a photograph of his three-month-old "
        "son Walden. The result was a 176 by 176 grid of black and white "
        "squares.",
        "The machine was attached to SEAC, one of the earliest programmable "
        "computers, and the point was to find out whether a computer could "
        "take in a picture at all. That grid of squares established the "
        "pixel as the unit of digital imaging, and everything from medical "
        "scanning to satellite imagery descends from it. Kirsch later "
        "regretted choosing square pixels, arguing other shapes would "
        "reproduce curves with fewer of them, and spent time in retirement "
        "exploring alternatives. The original image is held by the "
        "Smithsonian.",
    ),
    "The first text message ever sent simply said Merry Christmas": (
        "On 3 December 1992 the engineer Neil Papworth sent the words Merry "
        "Christmas from a computer to a colleague's handset on the Vodafone "
        "network. Phones of the day could not yet send messages themselves, "
        "only receive them.",
        "SMS was designed as an afterthought, squeezed into spare capacity in "
        "the signalling channel phones already used to talk to the network — "
        "which is where the 160-character limit comes from, since that was "
        "what fitted. Nobody expected people to want it, and operators "
        "initially gave it away. It became enormously profitable, and the "
        "constraint shaped how a generation wrote. The original message no "
        "longer exists as data; what survives is documentation and the "
        "recollection of those involved.",
    ),
    "The first webcam watched a coffee pot": (
        "Researchers in the Cambridge computer lab were tired of walking "
        "downstairs to find the pot empty. In 1991 they pointed a camera at "
        "it and piped a small greyscale image onto the building's network, "
        "refreshed a few times a minute.",
        "It reached the wider world in 1993 when the lab connected it to the "
        "young web, making it visible globally — a coffee pot in England "
        "watched by strangers on other continents, and an early demonstration "
        "that people will look at almost anything if it is live. The feed ran "
        "until 2001, when the lab moved buildings and switched it off in "
        "front of press. The pot itself was auctioned on eBay for around "
        "£3,350 to a German magazine, which restored and rehosted it.",
    ),
    "The whole early internet fit on a map you could sketch by hand": (
        "In 1969 the ARPANET connected four sites — three Californian "
        "universities and one in Utah. The diagram of the entire network was "
        "four labelled boxes joined by lines, easily drawn on a single sheet "
        "of paper.",
        "Hand-drawn maps stayed practical for years as it grew to dozens of "
        "nodes, and those sketches survive as documents. The founding idea "
        "was packet switching: chopping messages into pieces routed "
        "independently and reassembled at the far end, so no single failure "
        "breaks the conversation. The first message crashed the system — "
        "operators typed LOGIN and it died after LO. Nobody now has a "
        "complete map, because the internet is a voluntary network of "
        "networks with no central registry of its own shape.",
    ),
    "The word robot comes from a Czech play about artificial workers": (
        "Karel Čapek's 1920 play R.U.R. introduced the word, taken from robota, "
        "an old term meaning forced labour. His robots were manufactured "
        "biological workers built to serve people, rather than the machines of "
        "metal and gears we picture today.",
        "Čapek credited his brother Josef with coining it. The play ends with "
        "the robots rebelling and wiping out humanity, so the very first "
        "robot story was already an uprising story — a template science "
        "fiction has followed ever since, long before any machine could do "
        "anything of the kind. It was translated widely within a few years "
        "and the word entered English almost immediately. Isaac Asimov later "
        "coined robotics, assuming he was using an existing term rather than "
        "inventing one.",
    ),
    "Wi-Fi, Bluetooth, and your microwave all share a frequency band": (
        "All three use frequencies around 2.4 gigahertz, a slice of spectrum set "
        "aside internationally for unlicensed use. Anyone can transmit there "
        "without applying for permission, which is precisely why so many "
        "different devices crowd into it.",
        "Water molecules absorb energy well at these frequencies, which is "
        "what a microwave oven exploits — and why a leaky oven can visibly "
        "slow a nearby Wi-Fi connection. Devices cope through politeness "
        "protocols: Bluetooth hops between narrow channels over a thousand "
        "times a second, while Wi-Fi listens before transmitting and retries "
        "after collisions. Congestion in the band is the main reason 5 GHz "
        "and 6 GHz Wi-Fi exist, trading range for room, since higher "
        "frequencies pass through walls far less well.",
    ),
    "Your smartphone is millions of times more powerful than Apollo's computers": (
        "The Apollo Guidance Computer ran at about 43 kilohertz with roughly "
        "four kilobytes of working memory. A modern phone has billions of "
        "times more storage and a processor running tens of thousands of "
        "times faster.",
        "The comparison flatters the phone unfairly. The Apollo computer was "
        "purpose-built, ran a single verified program, and had priority "
        "scheduling that let it shed low-priority work under load — which is "
        "exactly what saved the Apollo 11 landing when alarms fired during "
        "descent. Its software was literally woven by hand into core rope "
        "memory, making it physically impossible to corrupt. It never crashed "
        "on a mission. The real lesson is that reliability and raw power are "
        "different things, and modern spacecraft still fly deliberately "
        "modest processors.",
    ),
}


if __name__ == "__main__":
    sys.exit(asyncio.run(run("batch 05", CONTENT, FLAGGED)))
