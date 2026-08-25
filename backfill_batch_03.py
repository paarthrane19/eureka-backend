"""Hand-written depth levels for batch 03 — Astronomy, Biology, Chemistry.

Safety behaviour lives in backfill_runner.py: length check before the db
connection, dry run by default, flagged headlines excluded.

    MONGODB_URI='<connection string>' DRY_RUN=true  python backfill_batch_03.py
    MONGODB_URI='<connection string>' DRY_RUN=false python backfill_batch_03.py
"""

from __future__ import annotations

import asyncio
import sys

from backfill_runner import run

FLAGGED: dict[str, str] = {}

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    # ---------------------------------------------------------------- Astronomy
    "A spoonful of a neutron star would weigh billions of tons": (
        "A neutron star is the crushed core left when a massive star dies. "
        "Gravity squeezes its matter until the empty space inside atoms is "
        "gone entirely, packing the mass of a sun into a ball the width of a "
        "city.",
        "Ordinary matter is mostly gap: a nucleus with electrons orbiting far "
        "out. Under enough pressure electrons are forced into protons, leaving "
        "almost pure neutrons touching one another, at roughly the density "
        "inside an atomic nucleus. A teaspoon would outweigh Mount Everest. "
        "The spoonful could not actually be removed — released from that "
        "gravity it would explode violently, since nothing but the star's own "
        "weight holds it together. What sits at the very centre, where "
        "pressure is highest, is still unknown; the neutrons may dissolve "
        "into free quarks.",
    ),
    "A year on Venus is shorter than a single Venusian day": (
        "Venus circles the Sun in 225 Earth days but turns on its axis so "
        "slowly that a single rotation takes 243 — longer than its entire "
        "year. Because it also spins backwards, sunrise to sunrise works out "
        "at about 117 Earth days.",
        "Venus rotates the opposite way to almost everything else in the "
        "solar system, so the Sun rises in the west. The likely cause is a "
        "giant early impact, a slow flip driven by its thick atmosphere, or "
        "some combination — none of it settled. That atmosphere is the more "
        "dramatic fact: crushing surface pressure and a runaway greenhouse "
        "effect hold the ground near 465°C, hot enough to melt lead and "
        "hotter than Mercury despite being further out. Oddly, the upper "
        "atmosphere races around the planet in just four days.",
    ),
    "Black holes can spin at nearly the speed of light": (
        "A collapsing star keeps the rotation it already had, and shrinking "
        "makes it spin faster — the same effect as a skater pulling in their "
        "arms. Compressed into a black hole, the surface can end up whirling "
        "at close to light speed.",
        "Spin is one of only three things a black hole can have, alongside "
        "mass and charge, and there is a hard ceiling: past a certain rate "
        "the horizon would vanish and expose the singularity, which physics "
        "appears to forbid. Measured black holes sit remarkably close to that "
        "limit. A spinning one also drags space around with it, so nothing "
        "nearby can stay still, and that twisting is thought to power the "
        "enormous jets seen blasting out of galactic centres — energy "
        "extracted from the rotation itself.",
    ),
    "It rains diamonds on Neptune and Uranus": (
        "Both planets are rich in methane, a molecule of one carbon and four "
        "hydrogens. Deep inside, immense pressure and heat tear it apart and "
        "squeeze the freed carbon into crystals that sink through the "
        "interior.",
        "The conditions are extreme — millions of atmospheres, thousands of "
        "degrees — and laboratories have reproduced them, shocking "
        "hydrocarbons with lasers and watching nanodiamonds form in "
        "nanoseconds. That turned a prediction into something demonstrated. "
        "The falling crystals may release heat as they sink, which could "
        "explain why Neptune radiates more energy than it receives from the "
        "Sun. Nobody has seen it happen directly, since the region lies "
        "thousands of kilometres below cloud tops no probe has entered, so "
        "the picture rests on models and lab analogues.",
    ),
    "Jupiter's Great Red Spot is a storm wider than Earth": (
        "It is a colossal high-pressure storm that has been spinning in "
        "Jupiter's southern hemisphere for centuries. With no land surface to "
        "break it up and no coastline to run into, nothing stops it the way "
        "hurricanes are stopped on Earth.",
        "Winds at its edge run past 400 km/h, and the whole system rotates "
        "roughly once a week, counter-clockwise. It is shrinking: once wide "
        "enough to swallow three Earths, it now barely exceeds one, and it "
        "has grown taller as it narrowed. Why it is red remains genuinely "
        "unsettled — sunlight breaking down chemicals dredged up from below "
        "is the leading idea, but no laboratory has matched the colour "
        "convincingly. Whether it will fade away entirely or stabilise is "
        "something astronomers are still watching.",
    ),
    "Saturn would float in water if you had a big enough bathtub": (
        "Saturn is mostly hydrogen and helium, the two lightest elements, "
        "spread across an enormous volume. Divide its mass by its size and "
        "the result is about 70 percent the density of water — so on average "
        "it is lighter than the stuff.",
        "The image is charming and the arithmetic is right, but it hides how "
        "the planet is built. Density rises steeply with depth: the outer "
        "layers are wispy gas while the core is rock and metal denser than "
        "anything on Earth, so only the average floats. A bathtub that size "
        "would also collapse under its own gravity long before you filled it. "
        "The low density has a real consequence, though — spinning fast on so "
        "little substance visibly squashes the planet, leaving it noticeably "
        "wider across the equator than pole to pole.",
    ),
    "Space is completely silent": (
        "Sound is a pressure wave that needs a material to travel through — "
        "air, water, metal. Space is close enough to empty that the "
        "particles are too far apart to pass a vibration along, so nothing "
        "reaches an ear.",
        "The nuance is that space is not perfectly empty. Thin plasma between "
        "the stars carries pressure waves over vast distances, just far below "
        "human hearing: waves rippling through the gas of the Perseus cluster "
        "correspond to a note roughly 57 octaves below middle C. NASA's "
        "sonifications convert such data into audible sound, which is "
        "translation rather than recording. Inside a spacecraft, where air is "
        "present, sound behaves normally — and astronauts report the "
        "International Space Station is a surprisingly noisy place to live.",
    ),
    "The Sun makes up 99.86 percent of the mass of the solar system": (
        "Everything else — all eight planets, every moon, asteroid and comet "
        "— adds up to less than a seventh of one percent. Jupiter alone "
        "accounts for most of that remainder, and the rest is close to a "
        "rounding error.",
        "The imbalance is why orbits are so orderly: the Sun's gravity "
        "dominates everything, and planets barely tug back. Barely is not "
        "never, though. Jupiter is heavy enough that the pair actually orbit "
        "a shared centre of mass sitting just outside the Sun's surface, so "
        "the Sun wobbles slightly. That wobble is exactly how the first "
        "planets around other stars were found — not by seeing them, but by "
        "detecting the star rocking in response. The proportion also explains "
        "fusion: only that much mass generates the crushing core pressure it "
        "requires.",
    ),
    "The Voyager 1 probe is the most distant human-made object": (
        "Launched in 1977, Voyager 1 used the gravity of Jupiter and Saturn "
        "to fling itself outward and has been coasting ever since. It is now "
        "well over 20 billion kilometres away and still climbing, with "
        "nothing to slow it down.",
        "In 2012 it crossed into interstellar space, where the Sun's outflow "
        "of particles gives way to the gas between the stars — detected not "
        "by a boundary marker but by a change in the plasma around it. Its "
        "radio signal, weaker than a fridge bulb by the time it arrives, "
        "takes over 22 hours to reach Earth. A decaying plutonium supply "
        "powers it, and instruments are being switched off one by one to "
        "stretch the remaining output into the 2030s. After that it drifts on "
        "silently, carrying the Golden Record.",
    ),
    "The coldest known place in the universe was made by humans": (
        "The natural universe has a floor: leftover heat from the Big Bang "
        "keeps empty space near 2.7 kelvin. Laboratories go far below that by "
        "using lasers and magnets to strip motion out of a small cloud of "
        "atoms.",
        "Laser cooling works by tuning light so that atoms moving toward the "
        "beam absorb photons and get nudged backwards, bleeding away speed "
        "until the cloud barely moves. Physicists have reached billionths and "
        "even trillionths of a degree above absolute zero — colder than "
        "anywhere known in nature. The Boomerang Nebula, chilled by its own "
        "rapid expansion to about 1 kelvin, is the coldest natural place "
        "found. Absolute zero itself stays out of reach: it would mean "
        "removing all motion, which quantum mechanics forbids.",
    ),
    "The footprints on the Moon will last for millions of years": (
        "The Moon has essentially no atmosphere, so there is no wind and no "
        "rain to sweep anything away. Its dust is sharp and jagged rather "
        "than rounded by weather, so the grains lock together under a boot "
        "and hold the impression indefinitely.",
        "Lunar dust was ground out by micrometeorite impacts rather than by "
        "weather, leaving grains that interlock instead of flowing. What does "
        "erode the surface is that same slow bombardment, plus charged "
        "particles from the Sun — a process measured in millions of years "
        "rather than the days a beach footprint gets. The Apollo prints are "
        "therefore safe from nature but not from us: preserving the landing "
        "sites from future missions and rovers is now an active question, and "
        "NASA has issued guidance on how close spacecraft should come.",
    ),
    "The largest known star could hold billions of Suns": (
        "The biggest stars are red hypergiants — enormous but extremely "
        "diffuse, having swollen late in life. Stephenson 2-18 is over 2,000 "
        "times the Sun's width, and since volume scales with the cube of "
        "radius, billions of Suns would fit inside.",
        "Placed at the centre of our solar system such a star would swallow "
        "everything out past Saturn. Its mass is nothing like as extreme, "
        "perhaps a few tens of Suns, so the average density is thinner than a "
        "laboratory vacuum — vast but wispy. Measuring these sizes is hard: "
        "the outer layers fade gradually rather than ending at a surface, "
        "distances carry large error bars, and the record holder changes as "
        "estimates are revised. Stars this bloated are also short-lived, and "
        "will end as supernovae.",
    ),
    "There is a giant reservoir of water floating in deep space": (
        "Water is simply hydrogen and oxygen, two of the most abundant "
        "elements, so it forms readily wherever they meet. Astronomers found "
        "a cloud of water vapour around a distant quasar holding perhaps a "
        "hundred trillion times the water in Earth's oceans.",
        "It surrounds a supermassive black hole roughly 12 billion light "
        "years away, meaning the light left when the universe was young — so "
        "water existed remarkably early. Detection works through microwave "
        "emission at a characteristic frequency, the vapour glowing as it is "
        "warmed by the quasar. Despite the staggering total it is thinner "
        "than most laboratory vacuums, spread across hundreds of light years. "
        "Finding water that early matters because it suggests the ingredients "
        "for life were common long before our own planet formed.",
    ),
    # ------------------------------------------------------------------ Biology
    "A blue whale's heart is roughly the size of a small car": (
        "A blue whale can reach 30 metres and 150 tonnes, and blood has to "
        "reach every part of it. The heart scales with the animal: it weighs "
        "a few hundred kilograms, spans well over a metre, and pushes "
        "hundreds of litres of blood with every single beat.",
        "The often-repeated claim that a child could crawl through the aorta "
        "is an exaggeration — the vessel is roughly the width of a dinner "
        "plate, wide but not a tunnel. The genuinely strange finding came "
        "from a tagged whale: the heart beats as slowly as two times a minute "
        "during a deep dive, then rises to around 37 at the surface, close to "
        "the physical limit for a heart that size. That range is far wider "
        "than models predicted, and it may be part of what caps how large a "
        "whale can grow.",
    ),
    "A hummingbird's heart can beat over 1,200 times a minute": (
        "Hovering is one of the most demanding things any animal does, and "
        "small bodies lose heat fast. Both push a hummingbird's metabolism to "
        "extremes, and the heart has to race to keep oxygen moving quickly "
        "enough to sustain it.",
        "The wings beat up to 80 times a second and the bird burns sugar "
        "almost as fast as it drinks it, visiting hundreds of flowers a day "
        "and still ending close to empty. The solution at night is torpor: "
        "body temperature drops sharply and the heart slows to a fraction of "
        "its daytime rate, cutting energy use enough to survive until "
        "morning. Waking from that state takes time, which is why a "
        "hummingbird found cold and unresponsive at dawn is usually not dead "
        "but still coming round.",
    ),
    "A single teaspoon of soil holds more organisms than people on Earth": (
        "Healthy soil is not inert dirt but dense habitat. A teaspoon can "
        "contain billions of bacteria plus fungi, protozoa and microscopic "
        "animals — comfortably more individual organisms than the eight "
        "billion humans alive.",
        "Those organisms do the work farming depends on: breaking down dead "
        "material into nutrients plants can absorb, binding particles into "
        "crumbs that hold water, and pulling nitrogen out of the air. Miles "
        "of fungal thread can run through a single handful. Most of these "
        "species have never been named, because the vast majority refuse to "
        "grow in a laboratory and are known only from fragments of their DNA. "
        "Soil is also where many antibiotics were found, which is why "
        "degradation is treated as more than an agricultural problem.",
    ),
    "Ants have colonized nearly every landmass and outnumber us vastly": (
        "Ants live almost everywhere except the polar extremes and a few "
        "islands. A careful estimate published in 2022 put the global "
        "population near 20 quadrillion — roughly 2.5 million ants for every "
        "person alive.",
        "That study pooled nearly 500 field surveys from every continent "
        "rather than extrapolating from one region, and the resulting biomass "
        "is startling: more than all wild birds and wild mammals combined. "
        "Their success comes from being social, dividing labour among "
        "specialists so a colony behaves like one organism. They turn over "
        "more soil than earthworms in many places, disperse seeds and control "
        "insect numbers. The estimate remains conservative, since ants "
        "underground and in tree canopies are the hardest of all to count.",
    ),
    "Bees can recognize human faces": (
        "Trained with sugar rewards, honeybees learn to tell photographed "
        "human faces apart and pick the right one later. They appear to treat "
        "a face as an unusual arrangement of features rather than as a "
        "person.",
        "The bees are configuring — combining eyes, nose and mouth into a "
        "single pattern, the same broad strategy people use — but there is no "
        "sign they understand what a face is. Scrambling the features breaks "
        "recognition, and the working interpretation is that the bee "
        "processes it as a strange flower. What makes it remarkable is the "
        "hardware: under a million neurons doing a job long assumed to need a "
        "large brain and dedicated circuitry. That has drawn interest from "
        "engineers, since it suggests recognition need not be expensive.",
    ),
    "Cows have best friends and get stressed when separated": (
        "Penned with a preferred partner, a cow's heart rate and stress "
        "hormones stay lower than when penned with a stranger. Separate the "
        "pair and both measures climb, which is why the relationship gets "
        "described as friendship.",
        "The finding comes from research on social preference in dairy herds, "
        "where cattle repeatedly seek out particular individuals and groom "
        "them more often. It matters commercially as well as ethically: "
        "stressed animals eat less and produce less milk, so keeping stable "
        "pairs together is an argument that lands with farmers. The caution "
        "is about language. Measuring a preference and lower stress is not "
        "the same as measuring friendship in the human sense, and how much "
        "inner life to read into it is genuinely contested.",
    ),
    "Mushrooms are more closely related to animals than to plants": (
        "Fungi cannot photosynthesise. Like us they take in ready-made "
        "organic matter to survive, and genetic comparison puts them on our "
        "branch of the tree of life — the split from animals came after both "
        "had already parted from plants.",
        "The shared traits run deeper than diet. Fungi store energy as "
        "glycogen exactly as animals do rather than as starch, and build "
        "their cell walls from chitin, the same material as an insect "
        "exoskeleton, instead of cellulose. The close relationship is also a "
        "medical problem: because fungal cells resemble ours, drugs that kill "
        "them tend to harm the patient too, which is why antifungals are far "
        "harder to develop than antibiotics. Rising drug-resistant fungal "
        "infections have made that a serious concern.",
    ),
    "Photosynthesis is only a few percent efficient, yet feeds the planet": (
        "Of the sunlight landing on a leaf, most is the wrong wavelength, "
        "reflected, or lost as heat. Only a small percentage ends up stored "
        "as sugar — typically one to two percent for a crop across a growing "
        "season.",
        "The theoretical ceiling is around 11 percent and no plant approaches "
        "it, partly because a key enzyme is slow and sometimes grabs oxygen "
        "instead of carbon dioxide, wasting energy to undo the mistake. Solar "
        "panels convert twenty percent or more. What plants have is scale and "
        "self-assembly: they cover the planet, build themselves from air and "
        "water, and have been running for billions of years. Engineering the "
        "process to work better is an active field, and modified plants with "
        "streamlined repair pathways have already shown large yield gains.",
    ),
    "Plants can hear the sound of chewing and defend themselves": (
        "Researchers played recordings of caterpillar chewing vibrations to "
        "plants with no insect present. Those plants went on to produce more "
        "defensive chemicals than plants exposed to silence or to wind and "
        "insect song.",
        "The work used thale cress and measured mustard oils, the compounds "
        "that make the family taste unpleasant. Crucially the plants "
        "discriminated: chewing vibrations triggered a response while other "
        "vibrations did not, so this is not a generic reaction to being "
        "disturbed. Hearing is the wrong word, since there are no ears — the "
        "plant senses mechanical vibration in its tissue. How the signal is "
        "detected and relayed is still being worked out, and whether it "
        "matters much in noisy real-world conditions is not established.",
    ),
    "Some frogs freeze solid in winter and thaw back to life": (
        "Wood frogs let much of the water in their bodies turn to ice as "
        "winter closes in. The heart stops, breathing stops and brain "
        "activity ceases for weeks on end — then in spring the frog thaws "
        "out, restarts and hops away as though nothing happened.",
        "The trick is controlling where the ice forms. The frog floods its "
        "cells with glucose, which acts as antifreeze and keeps the interiors "
        "liquid, so ice is confined to the spaces between cells where it does "
        "less damage. Cells burst when they freeze; this arrangement means "
        "they mostly do not. Some individuals survive being frozen and thawed "
        "repeatedly through a season. Medical researchers watch this closely, "
        "because preserving human organs for transplant runs into exactly the "
        "problem the frog has solved.",
    ),
    "Some jellyfish can effectively reverse their aging": (
        "Turritopsis dohrnii, a jellyfish a few millimetres across, responds "
        "to injury or starvation by settling onto a surface and reorganising "
        "its entire body back into the juvenile polyp stage it originally "
        "grew from, then developing all over again.",
        "Its cells transdifferentiate — a muscle cell can become a nerve cell "
        "— rebuilding the animal into an earlier form rather than repairing "
        "it. In principle the cycle repeats indefinitely, which is why it is "
        "called biologically immortal. That phrase oversells it: the animal "
        "is easily eaten or killed by disease, and reverting is an escape "
        "from stress rather than eternal youth. Genome comparisons have "
        "flagged differences in DNA repair and gene regulation, and the "
        "interest for human ageing is in those mechanisms, not in copying the "
        "reset.",
    ),
    "Your DNA would stretch to the Sun and back dozens of times": (
        "Each of your cells holds about two metres of DNA, coiled into a "
        "nucleus far too small to see without a microscope. Multiply that by "
        "roughly 30 trillion cells and the total length runs to tens of "
        "billions of kilometres.",
        "Packing it is the real feat: the DNA winds around spool-like "
        "proteins, coils, and coils again, compressing two metres into a few "
        "millionths of a metre. That packing is not just storage — how "
        "tightly a stretch is wound determines whether it can be read, so it "
        "acts as a control system for which genes are switched on. Cells in "
        "the same body run different programmes from identical instructions "
        "largely this way. Mature red blood cells are the exception, having "
        "ejected their nucleus entirely to carry more oxygen.",
    ),
    "Your eyes can distinguish around ten million colors": (
        "Three types of cone cell in the retina respond to roughly red, green "
        "and blue light. The brain reads their relative signals as colour, "
        "and the number of combinations it can tell apart runs into the "
        "millions.",
        "The ten million figure is a rough calculation rather than a "
        "measurement, and estimates vary widely depending on method. Real "
        "vision is worse than the arithmetic suggests: distinguishing shades "
        "is much easier side by side than from memory. Some people carry a "
        "fourth cone type and may see finer distinctions, though confirmed "
        "cases are rare and hard to test. Colour also is not purely optical — "
        "the brain corrects for lighting so a white shirt looks white indoors "
        "and out, which is why arguments about photographed dresses happen at "
        "all.",
    ),
    "Your gut can operate almost independently of your brain": (
        "The intestine has its own dense nerve network in its wall, able to "
        "sense what is passing through and drive the muscle contractions that "
        "move it along. Cut the nerve to the brain and digestion continues "
        "regardless.",
        "This enteric system holds hundreds of millions of neurons and runs "
        "reflexes locally, which is efficient — routing every contraction "
        "through the brain would be needlessly slow. Traffic on the "
        "connecting nerve mostly flows upward, gut informing brain, which is "
        "part of why digestive trouble affects mood and why anxiety shows up "
        "in the stomach. Gut bacteria produce compounds that influence those "
        "signals too, though claims that they steer human behaviour run well "
        "ahead of the evidence, which is largely from mice.",
    ),
    # ---------------------------------------------------------------- Chemistry
    "A teaspoon of neutronium would not fit in normal chemistry at all": (
        "Chemistry is essentially what electrons do when atoms meet. Neutron "
        "star matter has had its electrons crushed into its protons, leaving "
        "nothing but neutrons behind — so there is simply nothing left for "
        "chemistry to work with.",
        "Without electrons there are no bonds, no molecules, no reactions and "
        "no place on the periodic table, which organises elements by proton "
        "count. Neutronium is really a physics state held together by "
        "gravity, not a substance. Remove a spoonful from the star and the "
        "confining pressure vanishes: free neutrons decay in about fifteen "
        "minutes, and the sample would blow apart long before that with "
        "enormous force. The name mostly survives in fiction, where it tends "
        "to be treated as a metal you could machine.",
    ),
    "Adding salt to water makes it boil at a higher temperature": (
        "Dissolved salt gets in the way of water molecules escaping into "
        "vapour, so the liquid needs a little more heat before it boils. The "
        "shift is real but small — a few tenths of a degree for normal "
        "cooking amounts.",
        "The effect is called boiling point elevation and depends on how many "
        "particles are dissolved, not what they are; salt counts double "
        "because it splits into sodium and chloride. To raise the boiling "
        "point by a noticeable amount you would need water far saltier than "
        "seawater and unpleasant to eat. So salting pasta water does almost "
        "nothing to cooking time — it is for flavour. The same principle "
        "working downward is why salt melts ice on roads and why antifreeze "
        "keeps an engine from freezing.",
    ),
    "Bombardier beetles fire a boiling chemical spray from their abdomen": (
        "The beetle stores two harmless chemicals in separate chambers. "
        "Threatened, it mixes them with enzymes in a reinforced compartment, "
        "and the reaction releases so much heat that the spray leaves at "
        "around 100°C.",
        "High-speed imaging showed it is not a steady jet but a pulsed one, "
        "firing up to 500 times a second. Each pulse builds pressure until an "
        "inlet valve slams shut, the charge fires, and the valve reopens — "
        "the same principle as a pulse jet engine, and it protects the beetle "
        "from its own weapon. The outlet swivels, letting it aim in almost "
        "any direction. Creationist arguments long cited it as too complex to "
        "have evolved, but related beetles show every intermediate stage of "
        "the mechanism.",
    ),
    "Caffeine is a natural pesticide plants make to poison insects": (
        "Coffee, tea and cacao plants concentrate caffeine in leaves, beans "
        "and seedlings. In an insect it disrupts the nervous system, so the "
        "compound deters or kills the things that would otherwise eat the "
        "plant.",
        "Caffeine leaches into surrounding soil too, suppressing competing "
        "seedlings. The twist is that plants also use it to manipulate rather "
        "than repel: some flowers lace their nectar with a dose too small to "
        "taste, and bees that drink it remember the flower better and return "
        "more often — a caffeinated pollinator working harder for the plant. "
        "The same molecule affects us because it resembles a brain chemical "
        "that signals tiredness, and blocking that receptor is what makes "
        "coffee feel like alertness.",
    ),
    "Gallium is a metal that melts in the warmth of your hand": (
        "Gallium melts at about 29.8°C, comfortably below body temperature. A "
        "solid lump held in your palm slumps into a bright silvery liquid "
        "within a couple of minutes, then sets hard again once you put it "
        "down and it cools.",
        "The low melting point comes from an unusual structure: gallium "
        "atoms pair up rather than packing into a standard metallic lattice, "
        "and those pairs come apart easily. Its boiling point, by contrast, "
        "is above 2,200°C — one of the widest liquid ranges of any element. "
        "Unlike mercury it is not acutely toxic, which is why it appears in "
        "classroom demonstrations and in the trick of a spoon vanishing in "
        "hot tea. It attacks aluminium aggressively, soaking into the metal "
        "and leaving it crumbly, so it is banned from aircraft.",
    ),
    "Glass can be recycled endlessly without losing quality": (
        "Glass is melted sand, soda ash and limestone. Melting it again "
        "returns it to the same liquid it started as, with no shortening of "
        "fibres or breakdown of polymers of the kind that degrades paper and "
        "plastic.",
        "Recycled glass also melts at a lower temperature than raw materials, "
        "so each use saves energy and cuts emissions. The practical limits "
        "are about sorting rather than chemistry: colours cannot be "
        "unmixed, so mixed cullet only becomes green or brown containers, and "
        "ceramics, heat-resistant cookware or window glass contaminate a "
        "batch because they melt differently. Recycling rates therefore vary "
        "enormously by country and depend far more on collection systems than "
        "on the material itself.",
    ),
    "Helium is the only element that never freezes at normal pressure": (
        "Cool almost anything far enough and it solidifies. Helium does not — "
        "its atoms attract one another so weakly, and jitter so persistently, "
        "that even at absolute zero it remains liquid unless you also squeeze "
        "it under pressure.",
        "The jitter is quantum zero-point motion: particles cannot be "
        "completely still, and helium is light enough that this residual "
        "movement outmuscles the feeble forces trying to lock it in place. "
        "Around 25 atmospheres of pressure is enough to force solid helium. "
        "Below about 2 kelvin it instead becomes a superfluid, flowing "
        "without friction and creeping up container walls. All of this makes "
        "it the standard coolant for superconducting magnets, from MRI "
        "scanners to particle accelerators — and supplies are genuinely "
        "finite.",
    ),
    "Mercury is the only metal that is liquid at room temperature": (
        "Mercury melts at -39°C, so it pools as a liquid in conditions where "
        "every other metal is solid. Its electrons are held unusually tightly "
        "to each atom, which weakens the bonds that would otherwise hold a "
        "rigid structure.",
        "The tight grip is a relativistic effect: mercury's inner electrons "
        "move so fast that they behave as if heavier, drawing in and shielding "
        "the outer ones from sharing. Two metals sit close behind — gallium "
        "melts at 29.8°C and caesium at 28.5°C, so a warm room can liquefy "
        "either, which is why the claim is usually stated for standard room "
        "temperature. Mercury's usefulness in thermometers and switches has "
        "been steadily outweighed by its toxicity, and an international "
        "treaty now phases most uses out.",
    ),
    "Nitrogen makes up most of the air, not oxygen": (
        "Air is about 78 percent nitrogen and only 21 percent oxygen, with "
        "argon and trace gases making up the rest. Every breath you take is "
        "therefore mostly a gas your body does nothing at all with, and you "
        "breathe the nitrogen straight back out unchanged.",
        "Nitrogen dominates because it is remarkably unreactive: its two "
        "atoms are locked by one of the strongest bonds in chemistry, so it "
        "accumulates in the atmosphere rather than being consumed. That "
        "inertness is also a problem, since life needs nitrogen for proteins "
        "and DNA but cannot use it straight from the air. Bacteria and "
        "lightning break the bond naturally; industrially the Haber-Bosch "
        "process does it with heat and pressure, and the resulting fertiliser "
        "supports a large share of the world's food supply. The dilution "
        "matters too — pure oxygen would make fires uncontrollable.",
    ),
    "Oxygen is what makes fire, but pure oxygen does not burn": (
        "Burning is fuel combining with oxygen. Oxygen is the partner in that "
        "reaction rather than the fuel, so on its own there is nothing for it "
        "to react with — it makes other things burn ferociously instead.",
        "The distinction is called being an oxidiser. Raise the oxygen "
        "concentration and materials ignite more easily and burn far hotter: "
        "steel wool that merely glows in air will burn vigorously in pure "
        "oxygen. That is why hospital oxygen carries strict fire warnings and "
        "why grease near an oxygen fitting is dangerous. It is also why the "
        "Apollo 1 fire in 1967 was so catastrophic — a pure oxygen cabin at "
        "raised pressure turned a small electrical fault into an "
        "unsurvivable fire in seconds, and the design was changed afterwards.",
    ),
    "Rust is just iron slowly returning to the ore it came from": (
        "Iron in the ground exists mostly as iron oxide. Smelting forces the "
        "oxygen out to make metal, and rusting is that oxygen coming back — "
        "the metal relaxing into the more stable compound it was refined "
        "from.",
        "Smelting is essentially storing energy in the metal, and rust "
        "releases it again, which is why the reaction needs no encouragement. "
        "Water and dissolved salts accelerate it by carrying charge between "
        "spots on the surface, so coastal air and road salt are so "
        "destructive. What makes iron unusually vulnerable is that rust "
        "flakes: it is bulkier than the metal beneath, so it cracks away and "
        "exposes fresh iron. Aluminium oxidises just as readily but forms a "
        "tight transparent film that seals the surface and stops there.",
    ),
    "Some metals catch fire on contact with water": (
        "Alkali metals like sodium and potassium hold their outermost "
        "electron very loosely. Dropped in water they surrender it "
        "immediately, ripping the water apart and releasing hydrogen plus "
        "enough heat to set that hydrogen alight.",
        "The violence increases down the group — lithium fizzes, sodium "
        "skitters and ignites, caesium detonates on contact. High-speed "
        "footage revealed why it is explosive rather than merely hot: the "
        "metal surface becomes so positively charged that it tears itself "
        "apart into spikes, exposing vast fresh area in milliseconds. This is "
        "also why these metals are stored under oil and never exist pure in "
        "nature. Sodium's reactivity is exactly why it is safe as table salt, "
        "where its electron is already given away.",
    ),
    "Stainless steel resists rust thanks to an invisible self-healing layer": (
        "Stainless steel contains chromium, which reacts with oxygen faster "
        "than iron does. It forms a chromium oxide film only a few atoms "
        "thick that seals the surface, and if scratched it re-forms almost "
        "instantly.",
        "The film is transparent and tightly bonded, unlike rust, so it "
        "blocks oxygen instead of flaking away. Around 10.5 percent chromium "
        "is the threshold for the effect. It is not invincible: chloride ions "
        "punch through locally, which is why seawater and de-icing salt cause "
        "pitting, and starving the surface of oxygen — under a gasket, say — "
        "prevents the layer re-forming. Different grades add nickel or "
        "molybdenum for marine use. Passivation treatments deliberately "
        "thicken the film before a part enters service.",
    ),
    "Superglue was invented by accident, twice": (
        "Harry Coover found cyanoacrylate in 1942 while trying to make clear "
        "gun sights, and dismissed it for sticking to everything. Nine years "
        "later his team hit the same compound again while developing "
        "aircraft canopies — and this time saw the point.",
        "It bonds through moisture rather than drying: traces of water on "
        "almost any surface trigger the small molecules to link into long "
        "chains within seconds, which is why humid air speeds it up and why "
        "it grips skin so eagerly. Its most consequential use was medical. "
        "Coover promoted it for closing wounds, and a variant was carried in "
        "Vietnam to seal injuries in the field long enough to reach surgery. "
        "Purpose-made surgical formulations, gentler on tissue, are standard "
        "today.",
    ),
    "The hottest chili heat is measured on the Scoville scale": (
        "The scale rates how much capsaicin a chilli contains — the molecule "
        "that triggers heat. Originally a pepper extract was diluted in sugar "
        "water until a taste panel could no longer detect any burn, and the "
        "dilution needed became the score.",
        "That panel method was unavoidably subjective, so laboratories now "
        "measure capsaicin directly by chromatography and convert to Scoville "
        "units for familiarity. A bell pepper scores zero, jalapeños a few "
        "thousand, and the hottest cultivated varieties exceed two million. "
        "Capsaicin works by activating the receptor that normally detects "
        "physical heat, so the brain reads genuine burning where there is no "
        "damage. Because it does not dissolve in water, milk clears it far "
        "better than a drink of water does.",
    ),
    "The smell of rain has a name and a chemical source": (
        "The smell is called petrichor, and much of it comes from geosmin, a "
        "compound produced by bacteria living in soil. Raindrops fling it "
        "into the air along with oils that plants have shed onto the dry "
        "ground during the preceding spell.",
        "High-speed imaging at MIT showed the mechanism: a drop landing on "
        "porous ground traps tiny air bubbles, which shoot upward and burst, "
        "spraying aerosol carrying whatever was on the surface. Gentle rain "
        "on dry soil produces the most, which is why the smell is strongest "
        "after a dry spell. Human noses are extraordinarily sensitive to "
        "geosmin, detecting a few parts per trillion — better than sharks "
        "detect blood. Why is unclear, though finding water would have been "
        "worth a great deal to our ancestors.",
    ),
    "There is enough gold dissolved in the oceans to give everyone kilos": (
        "Seawater carries gold in trace amounts, and the oceans are "
        "enormous. Multiplied out the total comes to around 20 million "
        "tonnes, which divided among eight billion people is a couple of "
        "kilograms each.",
        "The catch is concentration: roughly one gram in a hundred million "
        "tonnes of water, so extracting a single gram means processing more "
        "water than most rivers carry in a day. Every serious attempt has "
        "cost far more than the gold recovered. Fritz Haber spent years in "
        "the 1920s trying to pay German war reparations this way before "
        "concluding the concentration was hopelessly lower than early "
        "estimates suggested. It stands as a useful reminder that a huge "
        "total and a usable resource are not the same thing.",
    ),
}


if __name__ == "__main__":
    sys.exit(asyncio.run(run("batch 03", CONTENT, FLAGGED)))
