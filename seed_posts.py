"""Re-seed Eureka with 50 real science posts using the three-level depth model.

Every post carries three progressively deeper levels:
  levels[0] = HOOK       (<=100 chars) one curiosity-triggering line
  levels[1] = EXPLAIN    (200-300)     the accessible science behind the hook
  levels[2] = DEEP_DIVE  (400-600)     mechanism, context, why it matters

Posts are spread across all 8 categories and attributed to the official
@eureka account plus 5 realistic seed users. Images are topic-matched
Wikimedia Commons files, and each URL is validated (HTTP 200 + image
content-type) before the post is inserted — failures are skipped and reported.

Point it at a database with MONGODB_URI (defaults to localhost for dev):

    MONGODB_URI='<railway connection string>' python seed_posts.py
"""

import asyncio
import os
import random
import secrets
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from app.database import close_mongo_connection, connect_to_mongo, get_db
from app.security import hash_password
from seed_sidebar import seed_sidebar

# Special:FilePath resolves a Commons filename to its direct upload.wikimedia.org
# URL (following the redirect), so we can reference stable, human-readable names.
_COMMONS_FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"

SEED_PASSWORD = "eureka123"

# ---------------------------------------------------------------------------
# Seed users (non-official). Attributed 15 of the 50 posts so the feed feels
# like a community rather than a single broadcaster.
# ---------------------------------------------------------------------------
SEED_USERS = [
    {
        "email": "kat@eureka.dev",
        "username": "astrokat",
        "name": "Dr. Katherine Reyes",
        "bio": "Observational astronomer. I chase light that left home billions of years ago.",
        "interests": ["Astronomy", "Physics", "Technology"],
        "avatar_color": "#7C4DFF",
    },
    {
        "email": "leo@eureka.dev",
        "username": "quantumleo",
        "name": "Leo Fenwick",
        "bio": "Quantum information researcher. Superpositions of coffee and curiosity.",
        "interests": ["Physics", "Math", "Technology"],
        "avatar_color": "#00B0FF",
    },
    {
        "email": "maya@eureka.dev",
        "username": "biomaya",
        "name": "Dr. Maya Osei",
        "bio": "Molecular biologist. Obsessed with the machinery inside every cell.",
        "interests": ["Biology", "Medicine", "Chemistry"],
        "avatar_color": "#00E676",
    },
    {
        "email": "sam@eureka.dev",
        "username": "geodesam",
        "name": "Sam Halvorsen",
        "bio": "Geologist reading the planet's diary, one rock layer at a time.",
        "interests": ["Earth Science", "Chemistry", "Biology"],
        "avatar_color": "#FF9100",
    },
    {
        "email": "nina@eureka.dev",
        "username": "neuralnina",
        "name": "Dr. Nina Varga",
        "bio": "Neuroscientist mapping how three pounds of tissue become a mind.",
        "interests": ["Medicine", "Biology", "Technology"],
        "avatar_color": "#FF5252",
    },
]

# ---------------------------------------------------------------------------
# The 50 posts. Each: dict with headline, l1/l2/l3, category, source_url,
# image (a Commons filename), and author (username; "eureka" for official).
# ---------------------------------------------------------------------------
POSTS: list[dict] = [
    # ===================== ASTRONOMY (6) =====================
    {
        "headline": "Saturn's rings are far younger than the planet itself",
        "l1": "Saturn's dazzling rings may be younger than the first dinosaurs.",
        "l2": "By weighing the ring material and measuring how quickly falling micrometeoroids darken its ice, scientists estimate the rings formed only 100 to 400 million years ago — while Saturn itself is about 4.5 billion years old.",
        "l3": "During its 2017 Grand Finale, the Cassini probe dived between Saturn and its rings and let the planet's gravity reveal the rings' total mass. A low mass points to a young age, because constant cosmic dust steadily pollutes bright ice, and the rings are still almost pure water ice. That ice is also slowly raining down onto Saturn, so the rings may disappear within a few hundred million years. What created them — a shattered icy moon or a stray comet torn apart by tides — is still an open question.",
        "category": "Astronomy",
        "source_url": "https://en.wikipedia.org/wiki/Rings_of_Saturn",
        "image": "Saturn_during_Equinox.jpg",
        "author": "astrokat",
    },
    {
        "headline": "Pluto's icy heart may hide a buried ocean",
        "l1": "Pluto's giant frozen 'heart' might be floating on a hidden ocean.",
        "l2": "New Horizons revealed a vast nitrogen-ice plain called Sputnik Planitia shaped like half a heart. Its position and the way Pluto is oriented in space suggest a dense layer — most likely a subsurface liquid-water ocean — lies beneath it.",
        "l3": "In 2015 NASA's New Horizons flew past Pluto and sent back the first sharp images of this distant world. The heart's smooth left lobe is a basin filled with frozen nitrogen that churns in slow convection cells, erasing craters over time. Curiously, the basin sits almost exactly on the line connecting Pluto and its big moon Charon — a balance point that works best if extra mass hides there. A slushy, salty ocean kept liquid by leftover heat and insulating ice would supply that mass, hinting that even tiny, frigid worlds can stay geologically alive.",
        "category": "Astronomy",
        "source_url": "https://en.wikipedia.org/wiki/Sputnik_Planitia",
        "image": "Pluto-01_Stern_03_Pluto_Color_TXT.jpg",
        "author": "eureka",
    },
    {
        "headline": "Webb telescope found galaxies that shouldn't exist so early",
        "l1": "Webb spotted galaxies so early and bright they break our timeline of the cosmos.",
        "l2": "The James Webb Space Telescope confirmed galaxies that formed within about 300 to 500 million years after the Big Bang. Several look far brighter and more massive than models predicted for such a young universe, forcing astronomers to rethink how fast the first galaxies grew.",
        "l3": "Webb sees in infrared, letting it catch light stretched by the universe's expansion over more than 13 billion years. In its first deep-field images it revealed thousands of galaxies, some of them record-breakers from cosmic dawn. The puzzle is that a few early galaxies appear to hold as many stars as much older ones, which is hard to explain if stars formed at normal rates. Possible fixes include unusually efficient star formation, brighter-than-expected young stars, or light from feeding black holes. Either way, the infant universe was busier than anyone expected.",
        "category": "Astronomy",
        "source_url": "https://en.wikipedia.org/wiki/James_Webb_Space_Telescope",
        "image": "Webb's First Deep Field.jpg",
        "author": "astrokat",
    },
    {
        "headline": "Voyager 1 is now billions of miles into interstellar space",
        "l1": "A 1977 probe is still calling home from beyond the Sun's bubble.",
        "l2": "Voyager 1 is the most distant human-made object, over 24 billion kilometers away. In 2012 it crossed the heliopause — the edge of the Sun's protective bubble of particles — becoming the first spacecraft to enter interstellar space.",
        "l3": "Launched in 1977 to tour the outer planets, Voyager 1 kept going after its flybys of Jupiter and Saturn. It carries the Golden Record, a disc of sounds and images meant for any intelligence that might find it. Its plutonium power source fades a little each year, so instruments are switched off one by one to stretch the mission. A radio signal from the probe now takes more than 22 hours to reach Earth. Sometime in the 2030s it will fall silent, but it will keep drifting among the stars, outlasting the civilization that built it.",
        "category": "Astronomy",
        "source_url": "https://en.wikipedia.org/wiki/Voyager_1",
        "image": "Voyager_Golden_Record_fx.png",
        "author": "eureka",
    },
    {
        "headline": "We took the first real photograph of a black hole",
        "l1": "In 2019 humanity saw a black hole for the first time — a ring of fire around a shadow.",
        "l2": "The Event Horizon Telescope linked radio dishes across the planet into one Earth-sized virtual telescope. It imaged the supermassive black hole in galaxy M87, showing a bright ring of superheated gas circling a dark central shadow.",
        "l3": "A black hole itself emits no light, but gas swirling just outside its point of no return glows fiercely, and the hole's gravity bends that light into a ring. To resolve something so small and far away, scientists combined data from telescopes in Hawaii, Chile, Spain, and the South Pole, using atomic clocks to sync them and petabytes of recorded data. The resulting image of M87's black hole — as massive as 6.5 billion Suns — matched Einstein's century-old predictions almost exactly. The team later imaged Sagittarius A*, the smaller black hole at the center of our own Milky Way.",
        "category": "Astronomy",
        "source_url": "https://en.wikipedia.org/wiki/Messier_87",
        "image": "Black_hole_-_Messier_87_crop_max_res.jpg",
        "author": "astrokat",
    },
    {
        "headline": "A star system 40 light-years away has seven Earth-sized worlds",
        "l1": "One nearby red dwarf hosts seven rocky planets, several in the zone where water could flow.",
        "l2": "TRAPPIST-1 is a cool, dim star circled by seven Earth-sized planets packed tightly together. Three or four orbit in the 'habitable zone,' where temperatures might allow liquid water — making it a prime target in the search for life.",
        "l3": "Discovered by watching the star dim as each planet crossed its face, the TRAPPIST-1 planets huddle so close that from one you would see the others looming like moons. Because the star is small and cool, its habitable zone sits very near in, so these worlds complete an orbit in just days. They are likely tidally locked, keeping one face in permanent day and the other in night. The James Webb Space Telescope is now probing whether any hold an atmosphere. Even if lifeless, the system is a natural laboratory for how rocky planets form and evolve around the galaxy's most common type of star.",
        "category": "Astronomy",
        "source_url": "https://en.wikipedia.org/wiki/TRAPPIST-1",
        "image": "TRAPPIST-1e artist impression 2018.png",
        "author": "eureka",
    },
    # ===================== PHYSICS (7) =====================
    {
        "headline": "A fusion experiment finally produced more energy than it used",
        "l1": "For the first time, a fusion reaction gave back more energy than the lasers poured in.",
        "l2": "In December 2022 the National Ignition Facility focused 192 lasers onto a tiny fuel capsule and achieved ignition: the fusion reactions released more energy than the laser light delivered to the target. It was a landmark step toward clean fusion power.",
        "l3": "Fusion joins light atomic nuclei — here, hydrogen isotopes — into heavier ones, releasing enormous energy, the same process that powers the Sun. At NIF, lasers crush a peppercorn-sized capsule to conditions hotter and denser than the Sun's core for a fraction of a second. The 2022 shot produced about 3.15 megajoules from 2.05 megajoules of laser energy. The catch: powering those lasers took far more energy from the grid than the reaction returned, so this is a scientific milestone, not yet a power plant. Still, proving net energy gain is possible removes a long-standing doubt.",
        "category": "Physics",
        "source_url": "https://en.wikipedia.org/wiki/National_Ignition_Facility",
        "image": "Preamplifier_at_the_National_Ignition_Facility.jpg",
        "author": "quantumleo",
    },
    {
        "headline": "Some materials lose all electrical resistance when cold",
        "l1": "Chill certain materials enough and electricity flows through them with zero loss — forever.",
        "l2": "In a superconductor, electrons pair up and move without any resistance, so a current can circulate endlessly. These materials also expel magnetic fields, which is why a magnet floats above a cold superconductor in the famous levitation demo.",
        "l3": "Below a critical temperature, vibrations in a metal's atomic lattice nudge electrons into 'Cooper pairs' that glide through the material without scattering — the origin of zero resistance, explained by BCS theory in 1957. Superconductors also push out magnetic fields (the Meissner effect), enabling frictionless levitation. Today they power MRI machines, particle accelerators, and experimental maglev trains. The dream is a room-temperature superconductor needing no expensive cooling; researchers have found materials that work under crushing pressures, but a practical version remains unsolved.",
        "category": "Physics",
        "source_url": "https://en.wikipedia.org/wiki/Superconductivity",
        "image": "Meissner_effect_p1390048.jpg",
        "author": "quantumleo",
    },
    {
        "headline": "The Higgs boson explains why matter has mass",
        "l1": "A single particle, found in 2012, reveals why anything has mass at all.",
        "l2": "The Higgs boson is a ripple in the Higgs field, an invisible field filling all of space. Particles gain mass by interacting with this field — the stronger the interaction, the heavier the particle. Its 2012 discovery completed the Standard Model of physics.",
        "l3": "Predicted in 1964, the Higgs field was the missing piece needed to explain why some particles are heavy and others, like the photon, are massless. To find its telltale boson, physicists smashed protons together at nearly light speed inside the Large Hadron Collider, a 27-kilometer ring beneath the France–Switzerland border. The Higgs appears only fleetingly, so teams sifted through trillions of collisions to spot its decay signatures. Confirming it in 2012 earned a Nobel Prize and validated decades of theory — yet deep questions remain about what lies beyond the Standard Model.",
        "category": "Physics",
        "source_url": "https://en.wikipedia.org/wiki/Higgs_boson",
        "image": "CERN_LHC_Tunnel1.jpg",
        "author": "eureka",
    },
    {
        "headline": "Scientists made the coldest matter in the universe",
        "l1": "Chill atoms to a hair above absolute zero and they merge into a single quantum blob.",
        "l2": "A Bose-Einstein condensate forms when a gas of atoms is cooled to billionths of a degree above absolute zero. The atoms lose their individual identity and behave as one coordinated quantum entity — a state of matter predicted by Einstein and Bose in the 1920s.",
        "l3": "At everyday temperatures atoms zip around randomly, but as you remove heat they slow to a crawl. Cool certain atoms cold enough and their quantum wave-natures overlap until they occupy the same lowest energy state, forming a single 'super atom.' First created in 1995 using laser and magnetic trapping, condensates let physicists see quantum effects at a visible scale — including slowing light and creating swirling quantized vortices. They are now tools for testing physics and building ultra-precise sensors. Such temperatures are colder than interstellar space and exist only in the lab.",
        "category": "Physics",
        "source_url": "https://en.wikipedia.org/wiki/Bose%E2%80%93Einstein_condensate",
        "image": "Bose_Einstein_condensate.png",
        "author": "eureka",
    },
    {
        "headline": "Quantum entanglement links particles across any distance",
        "l1": "Measure one entangled particle and its partner responds instantly, even light-years away.",
        "l2": "Two entangled particles share a single quantum state, so measuring one immediately determines the other's result no matter how far apart they are. Einstein called it 'spooky action at a distance,' but experiments have confirmed it again and again.",
        "l3": "Entanglement doesn't let you send messages faster than light — each individual result looks random, and only by comparing notes through a normal channel do the correlations appear. Yet those correlations are stronger than any classical theory allows, as decades of increasingly airtight 'Bell test' experiments have shown, earning a 2022 Nobel Prize. Rather than a loophole in relativity, entanglement is a resource: it underpins quantum computing, cryptography, and teleportation of states. It hints that the universe is 'nonlocal' in a subtle way, where the whole exceeds the sum of its parts.",
        "category": "Physics",
        "source_url": "https://en.wikipedia.org/wiki/Quantum_entanglement",
        "image": "Hubble_ultra_deep_field.jpg",
        "author": "quantumleo",
    },
    {
        "headline": "Light takes eight minutes to travel from the Sun to Earth",
        "l1": "The sunlight warming your face right now left the Sun eight minutes ago.",
        "l2": "Light travels at about 300,000 kilometers per second, and the Sun is roughly 150 million kilometers away. Do the math and it takes light about 8 minutes and 20 seconds to reach us — so we always see the Sun as it was, not as it is.",
        "l3": "The speed of light is the universe's ultimate speed limit, so every view of the sky is a view into the past. The Moon we see is 1.3 seconds old; the nearest star beyond the Sun, over 4 years; distant galaxies, billions of years. Oddly, light born in the Sun's core takes tens of thousands of years to reach the surface, bouncing among dense plasma, before its final 8-minute sprint across space. If the Sun vanished, we'd feel no difference — no darkness, no change in Earth's orbit — until those 8 minutes had passed, because gravity's influence travels at light speed too.",
        "category": "Physics",
        "source_url": "https://en.wikipedia.org/wiki/Speed_of_light",
        "image": "Sun in X-Ray.png",
        "author": "eureka",
    },
    {
        "headline": "Stacking graphene at a 'magic angle' unlocks superconductivity",
        "l1": "Twist two sheets of carbon by 1.1 degrees and they suddenly conduct with zero resistance.",
        "l2": "Graphene is a single layer of carbon atoms. When two sheets are stacked and twisted to a precise 'magic angle' near 1.1 degrees, the material's electrons slow dramatically and can pair up, turning the stack into a tunable superconductor.",
        "l3": "The tiny twist creates a large repeating 'moiré' pattern that traps electrons and flattens their energy bands, making their mutual interactions dominate. In 2018 researchers showed this twisted bilayer graphene can switch between insulating and superconducting behavior just by adjusting an electric field — an unheard-of level of control. It launched the field of 'twistronics,' where the angle between atom-thin layers becomes a design knob. Because the system is simple and adjustable, it's now a playground for studying the same puzzling physics seen in high-temperature superconductors.",
        "category": "Physics",
        "source_url": "https://en.wikipedia.org/wiki/Magic_angle",
        "image": "Graphen.jpg",
        "author": "eureka",
    },
    # ===================== BIOLOGY (6) =====================
    {
        "headline": "Octopuses rewrite their own genetic messages on the fly",
        "l1": "Octopuses edit their RNA so extensively they can rewire their nerves to fit the cold.",
        "l2": "Most animals rarely edit their RNA, the working copies of genes. Octopuses and their relatives do it constantly — recoding the proteins in their nervous systems in response to temperature, which may help explain their surprising intelligence.",
        "l3": "DNA is the master blueprint, but cells transcribe it into RNA to actually build proteins. Cephalopods like octopuses use an enzyme to swap letters in that RNA, changing which proteins get made without altering the underlying genes. In cold water they ramp up edits that tune nerve-signal proteins, keeping their neurons working smoothly. This flexibility comes at a cost: heavy RNA editing seems to slow the evolution of their DNA in those regions. It's a striking example of an animal adjusting its biology in real time, studied for clues about how nervous systems adapt.",
        "category": "Biology",
        "source_url": "https://en.wikipedia.org/wiki/RNA_editing",
        "image": "Octopus_vulgaris_2.jpg",
        "author": "biomaya",
    },
    {
        "headline": "Tardigrades survive being dried out, frozen, and blasted with radiation",
        "l1": "This microscopic animal can survive the vacuum of space — and coming back from total dry-out.",
        "l2": "Tardigrades, or water bears, endure extremes that kill almost everything else. When their environment dries up they curl into a 'tun' state, nearly halting their metabolism, and can revive years later when water returns.",
        "l3": "To survive drying, tardigrades replace lost water with special proteins that vitrify — turning the cell's interior into a stable glass that props up delicate molecules until rehydration. In this suspended state they've withstood temperatures near absolute zero, pressures greater than the deep ocean, and even direct exposure to the vacuum and radiation of space during an orbital experiment. They also make proteins that shield their DNA from radiation. Understanding these tricks could help preserve vaccines and cells without refrigeration, and it stretches our sense of where life can persist.",
        "category": "Biology",
        "source_url": "https://en.wikipedia.org/wiki/Tardigrade",
        "image": "SEM_image_of_Milnesium_tardigradum_in_active_state_-_journal.pone.0045682.g001-2.png",
        "author": "biomaya",
    },
    {
        "headline": "A severed starfish arm can regrow an entire new animal",
        "l1": "Cut a starfish in two and, in some species, each piece can rebuild a whole body.",
        "l2": "Many sea stars can regenerate lost arms, and certain species can regrow a complete individual from a single severed arm, as long as part of the central disc goes with it. This regeneration relies on pools of flexible cells that rebuild lost tissue.",
        "l3": "When a starfish loses an arm to a predator, specialized cells migrate to the wound, multiply, and gradually reconstruct muscle, nerves, gut, and skin. In species capable of whole-body regeneration, a fragment can slowly form a new disc and additional arms — a process that can take months. This isn't just a party trick: studying how starfish regrow complex tissue helps reveal the limits of regeneration in animals, including ourselves, where the ability is largely switched off. Echinoderms are close relatives of vertebrates, so their regenerative genes interest medicine.",
        "category": "Biology",
        "source_url": "https://en.wikipedia.org/wiki/Regeneration_(biology)",
        "image": "Blue_Linckia_Starfish.JPG",
        "author": "biomaya",
    },
    {
        "headline": "Trees share food and warnings through underground fungal networks",
        "l1": "Beneath the forest floor, trees trade sugar and danger signals through fungal threads.",
        "l2": "Tree roots partner with fungi whose fine filaments spread through the soil and connect neighboring trees. Through this network, trees can exchange carbon and nutrients and relay chemical alarm signals — a system nicknamed the 'wood wide web.'",
        "l3": "The partnership is called mycorrhiza: fungi wrap around or enter tree roots, giving the tree water and minerals in exchange for sugars made by photosynthesis. Because a single fungal network can link many trees, experiments using labeled carbon have tracked resources moving between them, sometimes helping shaded seedlings survive. Trees under insect attack can also trigger defensive chemistry in neighbors via these links. How cooperative versus competitive this really is remains debated, but the discovery reframed forests as connected communities rather than solitary individuals.",
        "category": "Biology",
        "source_url": "https://en.wikipedia.org/wiki/Mycorrhizal_network",
        "image": "Fungal mycelium.jpg",
        "author": "eureka",
    },
    {
        "headline": "The bacteria in your gut outnumber your own cells",
        "l1": "You carry trillions of microbes — together they help digest food and shape your health.",
        "l2": "Your gut hosts a vast community of bacteria, roughly comparable in number to your own cells. These microbes break down fibers you can't digest, make certain vitamins, train your immune system, and influence everything from metabolism to mood.",
        "l3": "The gut microbiome is like an extra organ you're not born with but acquire from birth onward. Different diets favor different microbial mixes, and those communities produce molecules that enter your bloodstream and signal to distant organs, including the brain via the 'gut-brain axis.' Disruptions have been linked to obesity, autoimmune conditions, and inflammatory bowel disease, though cause and effect are still being untangled. Fecal transplants already cure stubborn infections. Researchers are now probing whether tuning the microbiome could treat far broader conditions.",
        "category": "Biology",
        "source_url": "https://en.wikipedia.org/wiki/Gut_microbiota",
        "image": "EscherichiaColi_NIAID.jpg",
        "author": "eureka",
    },
    {
        "headline": "Coral reefs are built by animals working with algae inside them",
        "l1": "A coral reef is a living city built by tiny animals farming algae in their own tissue.",
        "l2": "Corals are colonies of small animals called polyps. Inside their cells live photosynthetic algae that feed the coral sugars and give reefs their color. When stressed by heat, corals expel the algae and turn white — a process called bleaching.",
        "l3": "This partnership, or symbiosis, lets corals thrive in nutrient-poor tropical waters: the algae photosynthesize and share energy, while the coral provides shelter and raw materials. Over centuries, polyps lay down limestone skeletons that accumulate into vast reefs supporting a quarter of all marine species. But the relationship is fragile. Even a degree or two of prolonged ocean warming can cause corals to eject their algae, starving and often killing them. Mass bleaching events are now recurring worldwide. Scientists are racing to breed heat-tolerant corals and restore reefs.",
        "category": "Biology",
        "source_url": "https://en.wikipedia.org/wiki/Coral_bleaching",
        "image": "Coral_Outcrop_Flynn_Reef.jpg",
        "author": "eureka",
    },
    # ===================== CHEMISTRY (6) =====================
    {
        "headline": "Diamond and pencil lead are made of the exact same element",
        "l1": "The hardest natural material and soft pencil lead are both just carbon.",
        "l2": "Diamond and graphite are both pure carbon, yet couldn't be more different. The difference is how the atoms bond: diamond's carbon forms a rigid 3D lattice, while graphite stacks flat sheets that slide past each other, making it soft and slippery.",
        "l3": "This is the power of molecular structure. In diamond, each carbon bonds to four others in a strong tetrahedral network, so the whole crystal behaves like one giant molecule — hard, transparent, and an excellent heat conductor. In graphite, each carbon bonds to only three neighbors, forming hexagonal sheets held together by weak forces, so layers flake off (which is how a pencil writes) and loose electrons let it conduct electricity. Same element, wildly different properties — a phenomenon called allotropy. Under extreme heat and pressure, graphite can even be squeezed into diamond.",
        "category": "Chemistry",
        "source_url": "https://en.wikipedia.org/wiki/Allotropes_of_carbon",
        "image": "Diamond_and_graphite.jpg",
        "author": "eureka",
    },
    {
        "headline": "Carbon can form a hollow soccer-ball molecule",
        "l1": "Sixty carbon atoms can lock into a molecule shaped exactly like a soccer ball.",
        "l2": "Buckminsterfullerene, or C60, is a molecule of 60 carbon atoms arranged in pentagons and hexagons — the same pattern as a soccer ball. Its 1985 discovery revealed a whole new family of carbon structures and won a Nobel Prize.",
        "l3": "Before C60, carbon was known mainly as diamond, graphite, and soot. Researchers vaporizing carbon with lasers found a startlingly stable cluster of exactly 60 atoms and realized it must be a closed cage. They named it after architect Buckminster Fuller, whose geodesic domes share the geometry. These 'buckyballs' can trap other atoms inside, act as tiny lubricants, and conduct in surprising ways. Their discovery opened the door to related nanostructures like carbon nanotubes and, ultimately, graphene, seeding the field of nanotechnology.",
        "category": "Chemistry",
        "source_url": "https://en.wikipedia.org/wiki/Buckminsterfullerene",
        "image": "Buckminsterfullerene-perspective-3D-balls.png",
        "author": "eureka",
    },
    {
        "headline": "Caffeine works by impersonating a molecule that makes you sleepy",
        "l1": "Your morning coffee wakes you up by disguising itself as a sleep signal.",
        "l2": "As you stay awake, a molecule called adenosine builds up in your brain and makes you drowsy by fitting into specific receptors. Caffeine has a similar shape, so it plugs into those receptors without activating them — blocking the sleepiness signal.",
        "l3": "Adenosine is a byproduct of your brain's energy use, so its levels rise the longer you're awake, gradually dialing up pressure to sleep. Caffeine is a molecular mimic: it binds adenosine's receptors but doesn't trigger them, so the drowsiness signal can't get through, and alertness-related chemicals flow more freely. That's why coffee perks you up — but the adenosine keeps accumulating behind the blockade. When the caffeine wears off, it floods those newly freed receptors, which is the afternoon crash. Over time the brain grows more receptors, building tolerance.",
        "category": "Chemistry",
        "source_url": "https://en.wikipedia.org/wiki/Caffeine",
        "image": "Caffeine_structure.svg",
        "author": "eureka",
    },
    {
        "headline": "Water is one of the few substances that expands when it freezes",
        "l1": "Ice floats because water does something almost no other liquid does — it expands when it freezes.",
        "l2": "Most substances get denser as they solidify, but water expands by about 9% when it turns to ice, making ice less dense than liquid water. That's why ice floats — and why lakes freeze from the top down instead of the bottom up.",
        "l3": "The quirk comes from water's V-shaped molecules and hydrogen bonds. In liquid water the molecules jostle close together, but as water freezes they lock into an open, hexagonal lattice that holds them slightly farther apart, lowering the density. This seemingly small oddity is crucial for life: a floating ice layer insulates the water below, letting fish and other organisms survive winter beneath the surface. The same expansion cracks pipes and shatters rock through freeze-thaw weathering. It's also why that lattice's hexagonal symmetry gives every snowflake its six-fold shape.",
        "category": "Chemistry",
        "source_url": "https://en.wikipedia.org/wiki/Properties_of_water",
        "image": "Ice_crystals_2.jpg",
        "author": "eureka",
    },
    {
        "headline": "The periodic table's shape reflects the quantum rules of electrons",
        "l1": "The periodic table isn't arbitrary — its shape is dictated by how electrons stack in atoms.",
        "l2": "Elements are arranged by their number of protons, but the table's rows and columns come from how electrons fill shells. Elements in the same column share similar electron arrangements in their outer shell, which is why they behave chemically alike.",
        "l3": "Electrons occupy layers of quantum 'orbitals' with strict capacity rules. As you move across a row, each element adds one electron; when a shell fills, a new row begins. Atoms in the same column have matching outer-electron patterns, so they react in similar ways — the alkali metals are all reactive, the noble gases all inert. Mendeleev arranged the first table in 1869 by chemical behavior and boldly left gaps for undiscovered elements, whose properties he predicted correctly. Only decades later did quantum mechanics explain why his pattern worked.",
        "category": "Chemistry",
        "source_url": "https://en.wikipedia.org/wiki/Periodic_table",
        "image": "Periodic_table_large.svg",
        "author": "eureka",
    },
    {
        "headline": "Fertilizer is made by pulling nitrogen straight out of the air",
        "l1": "Roughly half the people alive are fed by nitrogen yanked from thin air.",
        "l2": "The Haber-Bosch process combines nitrogen from the air with hydrogen to make ammonia, the basis of synthetic fertilizer. By letting farmers enrich soil at industrial scale, it enabled the population boom of the last century — but it's also very energy-hungry.",
        "l3": "Air is 78% nitrogen, yet plants can't use it directly because the nitrogen molecule's triple bond is extraordinarily hard to break. Early last century, chemists Fritz Haber and Carl Bosch found a way to split it using high temperature, crushing pressure, and a metal catalyst, producing ammonia in bulk. That ammonia became fertilizer that dramatically raised crop yields, and today feeds an estimated half of humanity. The downside is steep: the process consumes about 1-2% of the world's energy and emits carbon dioxide, while runoff pollutes rivers and seas.",
        "category": "Chemistry",
        "source_url": "https://en.wikipedia.org/wiki/Haber_process",
        "image": "Ammonia-3D-balls.png",
        "author": "eureka",
    },
    # ===================== MATH (6) =====================
    {
        "headline": "Pi never ends and never repeats",
        "l1": "The digits of pi march on forever with no pattern — and we've computed trillions of them.",
        "l2": "Pi is the ratio of a circle's circumference to its diameter, about 3.14159. It's irrational, meaning its decimal expansion goes on forever without ever settling into a repeating pattern, so it can never be written exactly as a simple fraction.",
        "l3": "Ancient mathematicians approximated pi by squeezing circles between polygons; today, clever formulas and supercomputers have pushed the count past 100 trillion digits. Pi is not just endless but also 'transcendental' — it isn't the solution to any simple algebraic equation, a fact proven in 1882 that finally showed you cannot 'square the circle' with compass and straightedge. Pi appears far beyond circles: in waves, probability, and the equations of quantum mechanics and relativity. Because its digits seem statistically random, almost any string of numbers likely appears in its tail.",
        "category": "Math",
        "source_url": "https://en.wikipedia.org/wiki/Pi",
        "image": "Pi-unrolled-720.gif",
        "author": "eureka",
    },
    {
        "headline": "A simple equation can generate infinitely detailed complexity",
        "l1": "One short formula produces a shape with infinite detail no matter how far you zoom in.",
        "l2": "The Mandelbrot set comes from repeatedly applying a simple rule to complex numbers and asking whether the result stays bounded. Plotting which numbers stay tame yields an intricate, infinitely detailed boundary — the icon of fractal geometry.",
        "l3": "For each point you feed the formula z → z² + c and iterate; if the value never flies off to infinity, the point belongs to the set. The astonishing part is the boundary: zoom in anywhere and you find endless swirls, spirals, and miniature copies of the whole shape, with detail that never smooths out. This is a fractal — a structure with the same roughness at every scale. Fractals aren't just beautiful; they model coastlines, clouds, blood vessels, and mountain ranges. That such boundless complexity springs from one tiny equation reshaped how mathematicians think about simplicity and chaos.",
        "category": "Math",
        "source_url": "https://en.wikipedia.org/wiki/Mandelbrot_set",
        "image": "Mandel_zoom_00_mandelbrot_set.jpg",
        "author": "eureka",
    },
    {
        "headline": "The golden ratio keeps appearing in nature and art",
        "l1": "One special number shows up in sunflowers, seashells, and famous works of art.",
        "l2": "The golden ratio, about 1.618, arises when a line is split so the whole relates to the larger part as the larger part relates to the smaller. It's deeply tied to the Fibonacci sequence and appears in spirals from pinecones to galaxies.",
        "l3": "If you divide each Fibonacci number by the one before it — 1, 2, 3, 5, 8, 13… — the ratios home in on the golden ratio. Plants often arrange leaves and seeds using angles related to it because that spacing packs the most seeds without overlap, as seen in a sunflower's spiraling florets. The proportion turns up in nautilus shells and has been claimed, sometimes over-enthusiastically, in art from the Parthenon to Renaissance paintings. Mathematically it's the 'most irrational' number, hardest to approximate with fractions, which is why nature favors it for efficient growth.",
        "category": "Math",
        "source_url": "https://en.wikipedia.org/wiki/Golden_ratio",
        "image": "Golden_ratio_line.svg",
        "author": "eureka",
    },
    {
        "headline": "There are different sizes of infinity",
        "l1": "Some infinities are genuinely bigger than others — and it can be proven.",
        "l2": "The counting numbers are infinite, but so are the decimals between 0 and 1 — and Cantor proved the decimals form a strictly larger infinity. No matter how you try to list them, you'll always miss some, so they can't be matched one-to-one with the counting numbers.",
        "l3": "Georg Cantor compared infinite sets by pairing their members. The whole numbers, even numbers, and fractions can all be lined up in a list, so they share the same 'countable' infinity — surprising, since it means there are as many even numbers as whole numbers. But Cantor's diagonal argument shows the real numbers can't be listed at all: given any list, you can always construct a number that differs from every entry, so the reals are 'uncountably' infinite, a bigger size. This launched a hierarchy of ever-larger infinities and shook the foundations of mathematics.",
        "category": "Math",
        "source_url": "https://en.wikipedia.org/wiki/Cantor%27s_diagonal_argument",
        "image": "Aleph0.svg",
        "author": "eureka",
    },
    {
        "headline": "A single tile shape can cover a wall without ever repeating",
        "l1": "Mathematicians found a tile that fills a surface forever without the pattern ever repeating.",
        "l2": "Most tilings repeat in a regular grid. In 2023, a decades-long hunt ended with the 'hat' — a single shape that tiles an infinite plane but never produces a repeating pattern, solving the long-standing einstein tile problem.",
        "l3": "A pattern is 'aperiodic' if you can never slide a copy of it onto itself to match perfectly. Earlier, Roger Penrose found aperiodic tilings using two shapes; the open question was whether one shape could do it alone — an 'einstein,' from the German for 'one stone.' In 2023 a hobbyist and a team of mathematicians unveiled the hat, an unassuming 13-sided polygon that fits together in infinitely many non-repeating ways. They soon found a related 'spectre' tile that needs no mirror-image copies. Aperiodic patterns connect to real materials called quasicrystals.",
        "category": "Math",
        "source_url": "https://en.wikipedia.org/wiki/Einstein_problem",
        "image": "Penrose_Tiling_(Rhombi).svg",
        "author": "eureka",
    },
    {
        "headline": "Prime numbers are the atoms of arithmetic",
        "l1": "Every whole number is built from primes in exactly one way — and primes never run out.",
        "l2": "A prime is a number divisible only by 1 and itself. Every whole number breaks down into a unique product of primes, making them the building blocks of arithmetic. Euclid proved over 2,000 years ago that there are infinitely many.",
        "l3": "The fundamental theorem of arithmetic says each number has one and only one prime 'fingerprint' — 60 is always 2×2×3×5. Primes thin out as numbers grow but never stop, and their exact distribution hides deep patterns tied to the famous, still-unsolved Riemann hypothesis. This isn't just abstract: because multiplying two huge primes is easy but factoring the result is fiendishly hard, primes underpin the encryption that secures online banking and messaging. Mathematicians keep hunting ever-larger primes — the biggest known has over 40 million digits.",
        "category": "Math",
        "source_url": "https://en.wikipedia.org/wiki/Prime_number",
        "image": "Primes-vs-composites.svg",
        "author": "eureka",
    },
    # ===================== EARTH SCIENCE (6) =====================
    {
        "headline": "Mount Everest grows a few millimeters taller every year",
        "l1": "Everest is still rising, pushed up as two continents keep colliding.",
        "l2": "The Himalayas formed when the Indian plate crashed into Asia, and that collision hasn't stopped. India keeps pushing north, so Everest and its neighbors rise by a few millimeters a year — even as erosion and gravity try to wear them down.",
        "l3": "Around 50 million years ago the Indian tectonic plate slammed into Eurasia, crumpling the crust upward into the highest mountains on Earth. The plates are still converging by roughly 4-5 centimeters per year, and part of that motion lifts the range. The net height change is a tug-of-war between uplift and erosion by rivers, glaciers, and landslides, plus occasional sudden shifts during earthquakes. Recent studies suggest a nearby river eroding the base may even be letting Everest rebound higher. Precise GPS and satellites now track these tiny yearly changes.",
        "category": "Earth Science",
        "source_url": "https://en.wikipedia.org/wiki/Mount_Everest",
        "image": "Everest_North_Face_toward_Base_Camp_Tibet_Luca_Galuzzi_2006.jpg",
        "author": "geodesam",
    },
    {
        "headline": "Dust from the Sahara fertilizes the Amazon rainforest",
        "l1": "The Amazon is fed by mineral dust blown thousands of miles across the Atlantic from Africa.",
        "l2": "Each year, winds lift enormous amounts of dust from the Sahara and carry it across the ocean. Some settles on the Amazon, delivering phosphorus and other nutrients that the rainforest's rain-leached soils badly need to keep growing.",
        "l3": "Satellites track a near-continuous river of dust rising from the Bodélé Depression in Chad — an ancient dried lakebed rich in nutrients from long-dead microorganisms. Trade winds sweep roughly 180 million tonnes of this dust off Africa annually, and tens of millions of tonnes reach South America. The Amazon's heavy rains constantly wash nutrients out of its soil, so this airborne resupply of phosphorus helps sustain the forest's staggering productivity. It's a reminder that Earth's systems are deeply connected: a barren desert quietly nourishes a distant rainforest.",
        "category": "Earth Science",
        "source_url": "https://en.wikipedia.org/wiki/Bod%C3%A9l%C3%A9_Depression",
        "image": "Sandstorm.jpg",
        "author": "geodesam",
    },
    {
        "headline": "Earth's magnetic field flips every few hundred thousand years",
        "l1": "Compasses would point south during one of Earth's periodic magnetic reversals.",
        "l2": "Earth's magnetic field is generated by churning molten iron in the outer core. Every few hundred thousand years, on average, the field weakens and flips, swapping magnetic north and south. The last full reversal was about 780,000 years ago.",
        "l3": "The 'geodynamo' works like a self-sustaining electromagnet: heat drives convection in the liquid-iron outer core, and the swirling, electrically conductive metal generates the field. This process is chaotic, so reversals happen irregularly and can take hundreds to thousands of years to complete, with the field growing weak and tangled in between. We read this history in rock: as lava cools, iron minerals lock in the field's direction, leaving a striped seafloor record that also confirmed plate tectonics. A prolonged weak field could disrupt satellites and power grids.",
        "category": "Earth Science",
        "source_url": "https://en.wikipedia.org/wiki/Geomagnetic_reversal",
        "image": "Geodynamo_Between_Reversals.gif",
        "author": "eureka",
    },
    {
        "headline": "There may be an ocean's worth of water locked deep inside Earth",
        "l1": "Hundreds of miles down, a mineral holds water bound inside solid rock.",
        "l2": "Deep in Earth's mantle, a blue mineral called ringwoodite can trap water within its crystal structure. Analyzing a rare diamond that formed there suggests the mantle's transition zone may hold as much water as all the oceans combined.",
        "l3": "This isn't water sloshing in caverns — it's hydrogen bound into the mineral's structure, released as water only under the right conditions. In 2014 scientists studied a diamond carried up from about 500 kilometers down and found it encased a speck of ringwoodite that was over 1% water by weight. If that's typical of the transition zone, the rock there could store a volume of water rivaling the surface oceans. This hidden reservoir may buffer Earth's long-term water cycle, feeding volcanoes and helping keep oceans stable for billions of years.",
        "category": "Earth Science",
        "source_url": "https://en.wikipedia.org/wiki/Ringwoodite",
        "image": "BlueRingwoodite.jpg",
        "author": "geodesam",
    },
    {
        "headline": "A single volcano can cool the entire planet for a year",
        "l1": "A big enough eruption can dim the Sun worldwide and drop global temperatures.",
        "l2": "When a large volcano blasts sulfur high into the stratosphere, it forms a haze of tiny droplets that reflect sunlight back to space. After Mount Pinatubo erupted in 1991, global temperatures fell by about half a degree Celsius for over a year.",
        "l3": "The cooling comes not from ash, which falls out quickly, but from sulfur dioxide gas that rises into the stratosphere and converts into a fine sulfuric-acid aerosol. Because there's no rain up there to wash it out, this reflective veil can circle the globe and linger for a year or more, shading the surface. History records the effect: the 1815 eruption of Tambora led to 1816's 'year without a summer,' with crop failures across the Northern Hemisphere. Understanding this natural sun-dimming informs controversial proposals for 'solar geoengineering.'",
        "category": "Earth Science",
        "source_url": "https://en.wikipedia.org/wiki/Mount_Pinatubo",
        "image": "Pinatubo91eruption_clark_air_base.jpg",
        "author": "eureka",
    },
    {
        "headline": "The Atlantic Ocean gets a little wider every year",
        "l1": "North America and Europe drift apart about as fast as your fingernails grow.",
        "l2": "Along the Mid-Atlantic Ridge, molten rock rises and hardens, adding new seafloor and pushing the continents apart. The Atlantic widens by roughly 2-4 centimeters per year — slow, but enough to reshape the globe over millions of years.",
        "l3": "This is seafloor spreading, a core piece of plate tectonics. At the mid-ocean ridge, magma wells up from the mantle, cools into fresh crust, and shoves older crust outward on both sides like a pair of conveyor belts. As the new rock solidifies it records Earth's magnetic field, producing symmetric magnetic stripes that clinched the theory in the 1960s. The same process, running for over 180 million years, split the ancient supercontinent Pangaea and opened the Atlantic from scratch. Iceland sits right on the ridge, which is why it's slowly being torn in two and studded with volcanoes.",
        "category": "Earth Science",
        "source_url": "https://en.wikipedia.org/wiki/Seafloor_spreading",
        "image": "Mid-ocean_ridge_topography.gif",
        "author": "eureka",
    },
    # ===================== TECHNOLOGY (6) =====================
    {
        "headline": "Data can be stored in DNA — the densest memory known",
        "l1": "All the world's data could fit in a few kilograms of DNA.",
        "l2": "DNA stores information in four chemical letters, and scientists can encode digital files into synthetic DNA and read them back. It's astonishingly dense and can last thousands of years, making it a candidate for long-term data archiving.",
        "l3": "Just as computers use 0s and 1s, DNA uses the bases A, C, G, and T, so any file can be translated into a DNA sequence, chemically synthesized, and later sequenced to recover the data. The appeal is density and durability: a gram of DNA could in principle hold hundreds of petabytes, and DNA recovered from ancient bones shows it can survive for millennia if kept cool and dry. Researchers have already stored books, images, and even video this way. The hurdles are cost and speed, but as sequencing gets cheaper, DNA could archive humanity's exploding data in a vanishingly small space.",
        "category": "Technology",
        "source_url": "https://en.wikipedia.org/wiki/DNA_digital_data_storage",
        "image": "DNA_orbit_animated_static_thumb.png",
        "author": "eureka",
    },
    {
        "headline": "Solar panels turn light straight into electricity, no moving parts",
        "l1": "A solar cell makes electricity from sunlight using nothing but a slab of silicon.",
        "l2": "In a solar cell, incoming light knocks electrons loose in a specially treated silicon wafer. A built-in electric field herds those electrons in one direction, creating a current — converting sunlight directly to electricity with no engines, fuel, or moving parts.",
        "l3": "The trick is the photovoltaic effect. Silicon is 'doped' with trace elements to form two layers, one hungry for electrons and one with extras, creating a junction with a built-in electric field. When a photon of sunlight hits, it frees an electron; the field sweeps it across the junction, and wiring lets it flow out as usable current before returning. Because it's solid-state, a panel can run for decades with little maintenance. Efficiency has climbed while costs have plummeted, making solar one of the cheapest sources of new electricity. Perovskites promise even cheaper printable cells.",
        "category": "Technology",
        "source_url": "https://en.wikipedia.org/wiki/Solar_cell",
        "image": "Solar_cell.png",
        "author": "eureka",
    },
    {
        "headline": "The transistors in a modern chip are smaller than a virus",
        "l1": "A single fingernail-sized chip packs tens of billions of switches thinner than a virus.",
        "l2": "Computer chips work by cramming billions of tiny switches called transistors onto a sliver of silicon. Today's smallest features are only a few nanometers across — smaller than most viruses — which is why phones now outmuscle old supercomputers.",
        "l3": "A transistor is just a switch that turns a current on or off, representing the 1s and 0s of computing. Squeezing more of them onto a chip makes it faster and more capable, and for decades their count has roughly doubled every two years — the trend called Moore's law. Manufacturers 'print' these patterns using ultraviolet light in machines of extraordinary precision, building structures a few atoms wide. We're approaching physical limits where quantum effects make electrons leak across barriers, so engineers now stack transistors in 3D and redesign their shapes to keep progress going.",
        "category": "Technology",
        "source_url": "https://en.wikipedia.org/wiki/Transistor_count",
        "image": "Intel_80486DX2_top.jpg",
        "author": "eureka",
    },
    {
        "headline": "Computers are learning to compute with light instead of electrons",
        "l1": "Some new chips do their math with beams of light rather than electric current.",
        "l2": "Photonic processors perform calculations by routing and combining beams of light on a chip. Because light is fast and generates little heat, these devices could handle certain AI computations far more efficiently than conventional electronic chips.",
        "l3": "Modern AI runs on enormous numbers of multiply-and-add operations, and electronics burn a lot of energy moving electrons through resistance-laden wires. Light doesn't have that problem: photons can pass through one another and travel with minimal loss. In a photonic chip, tiny waveguides steer laser light through structures that add and interfere beams, naturally performing the matrix math at the heart of neural networks — at the speed of light with little heat. If the hurdles fall, optical computing could sharply cut the energy appetite of data centers training AI.",
        "category": "Technology",
        "source_url": "https://en.wikipedia.org/wiki/Photonic_integrated_circuit",
        "image": "Optical fiber cable.jpg",
        "author": "eureka",
    },
    {
        "headline": "GPS only works because it accounts for Einstein's relativity",
        "l1": "Your phone's map would drift miles off course without correcting for warped time.",
        "l2": "GPS satellites carry atomic clocks, and Einstein's relativity says those clocks tick at a slightly different rate than clocks on the ground — both from their speed and from weaker gravity in orbit. Without correcting for it, GPS would fail within minutes.",
        "l3": "GPS pinpoints you by timing signals from several satellites, so even nanosecond clock errors translate into position errors. Two relativistic effects apply: special relativity makes the fast-moving satellite clocks run slower, while general relativity makes them run faster because gravity is weaker at their altitude. The gravitational effect wins, leaving satellite clocks gaining about 38 microseconds a day relative to the ground. Uncorrected, that would push positions off by roughly 10 kilometers per day. Engineers build the correction into the satellites.",
        "category": "Technology",
        "source_url": "https://en.wikipedia.org/wiki/Error_analysis_for_the_Global_Positioning_System",
        "image": "GPS_Satellite_NASA_art-iif.jpg",
        "author": "eureka",
    },
    {
        "headline": "Lithium-ion batteries store power by shuttling ions back and forth",
        "l1": "Your phone battery works by sliding lithium ions between two electrodes, over and over.",
        "l2": "In a lithium-ion battery, charging pushes lithium ions into one electrode; using the battery lets them flow back to the other, driving electrons through your device. Because the ions simply move back and forth, the battery can be recharged hundreds of times.",
        "l3": "A lithium-ion cell has two electrodes separated by a liquid that lets ions pass but forces electrons to take the external circuit — which is the useful current. On charge, energy drives lithium ions into the graphite electrode; on discharge, they migrate back to the metal-oxide electrode, releasing that energy. Lithium is ideal because it's light and eagerly gives up an electron, packing lots of energy into little weight. This chemistry, honored with the 2019 Nobel Prize, powers phones, laptops, and electric cars, and is driving research into new alternatives.",
        "category": "Technology",
        "source_url": "https://en.wikipedia.org/wiki/Lithium-ion_battery",
        "image": "18650 and 21700 lithium ion battery cell.jpg",
        "author": "eureka",
    },
    # ===================== MEDICINE (7) =====================
    {
        "headline": "CRISPR gene editing can now cure sickle cell disease",
        "l1": "A one-time gene edit freed patients from the agonizing pain of sickle cell disease.",
        "l2": "CRISPR is a tool that lets scientists edit DNA at precise locations. In 2023 regulators approved the first CRISPR therapy, which edits a patient's own blood stem cells to treat sickle cell disease — in trials, most patients became free of their painful crises.",
        "l3": "Sickle cell disease is caused by a single DNA typo that makes red blood cells warp into rigid crescents, clogging vessels and causing severe pain. The therapy removes a patient's blood stem cells, uses CRISPR to switch a gene back on so the cells produce a healthy fetal form of hemoglobin, then returns the edited cells. CRISPR itself was adapted from a bacterial immune system that snips viral DNA; a guide molecule steers molecular 'scissors' to an exact sequence. The cure proves we can rewrite our own genome to defeat inherited disease, though high cost limits access.",
        "category": "Medicine",
        "source_url": "https://en.wikipedia.org/wiki/Sickle_cell_disease",
        "image": "1911_Sickle_Cells.jpg",
        "author": "neuralnina",
    },
    {
        "headline": "mRNA vaccines teach your cells to make a piece of a virus",
        "l1": "mRNA vaccines don't contain a virus — they hand your cells a recipe to fight one.",
        "l2": "An mRNA vaccine delivers a short genetic instruction telling your cells to build one harmless viral protein. Your immune system learns to recognize that protein, so it can respond fast if the real virus ever shows up. The cells then discard the mRNA.",
        "l3": "Messenger RNA is the everyday molecule cells use to turn genes into proteins. Vaccine mRNA, wrapped in a tiny fat bubble to slip inside cells, carries the recipe for a single viral protein — for COVID-19, the spike. Your cells make that protein, display it, and your immune system trains against it without ever encountering the actual virus. The mRNA is fragile and breaks down within days, and it never enters the cell nucleus or alters your DNA. Decades of quiet research made this possible in record time, and the platform is now aimed at other infections and personalized cancer vaccines.",
        "category": "Medicine",
        "source_url": "https://en.wikipedia.org/wiki/MRNA_vaccine",
        "image": "MRNA-interaction.svg",
        "author": "neuralnina",
    },
    {
        "headline": "Surgeons transplanted a gene-edited pig kidney into a person",
        "l1": "A pig's kidney, tweaked to fool the human immune system, kept a person alive.",
        "l2": "To ease the severe shortage of donor organs, surgeons have transplanted kidneys from genetically modified pigs into human patients. The pigs' genes are edited to remove features that would trigger immediate rejection, and early transplants have produced urine and functioned.",
        "l3": "Thousands of people die waiting for organs, so scientists have long eyed animals as a source — a field called xenotransplantation. Pig organs are a good size match, but the human immune system violently rejects them. Using gene editing, researchers knock out the pig genes that provoke attack and add human genes to calm the immune response and prevent clotting. The first such kidney and heart transplants into living patients, beginning in the 2020s, are closely watched: they've shown the organs can work. If perfected, engineered organs could end waiting lists.",
        "category": "Medicine",
        "source_url": "https://en.wikipedia.org/wiki/Xenotransplantation",
        "image": "2610_The_Kidney.jpg",
        "author": "neuralnina",
    },
    {
        "headline": "Your immune cells can be re-engineered to hunt cancer",
        "l1": "Doctors can reprogram a patient's own immune cells into cancer-seeking assassins.",
        "l2": "CAR-T therapy removes a patient's T cells, genetically arms them with a receptor that recognizes cancer, and infuses them back. These living drugs then multiply and hunt down tumor cells, driving some previously untreatable blood cancers into lasting remission.",
        "l3": "T cells are the immune system's hunters, but cancers often hide from them. In CAR-T therapy, scientists extract a patient's T cells and insert a gene for a 'chimeric antigen receptor' that latches onto a marker on cancer cells. Reinfused, these engineered cells recognize and kill the cancer, and because they're alive, they keep multiplying and patrolling. It has produced dramatic, durable remissions in certain leukemias and lymphomas. The challenges are real: it can unleash dangerous immune overreactions, it's costly, and it works far better on blood cancers than solid tumors.",
        "category": "Medicine",
        "source_url": "https://en.wikipedia.org/wiki/Chimeric_antigen_receptor_T_cell",
        "image": "Red_White_Blood_cells.jpg",
        "author": "neuralnina",
    },
    {
        "headline": "A blood test can spot many cancers before symptoms appear",
        "l1": "A single blood draw may flag dozens of cancers years before you feel sick.",
        "l2": "Tumors shed fragments of DNA into the bloodstream. New 'liquid biopsy' tests read those fragments to detect many cancer types from one blood sample — and can often hint at where in the body the cancer is hiding.",
        "l3": "As tumor cells grow and die, they release bits of their mutated DNA into the blood. Multi-cancer early detection tests sequence this circulating DNA and use chemical tags on it to distinguish cancerous from normal fragments, screening for dozens of cancers at once. Because chemical patterns differ by tissue, the tests can also guess the tumor's origin. The promise is catching cancers early, when they're far more treatable — including cancers with no routine screening today. The caveats matter: the tests still miss early tumors and can raise false alarms, so trials continue.",
        "category": "Medicine",
        "source_url": "https://en.wikipedia.org/wiki/Liquid_biopsy",
        "image": "Blausen_0909_WhiteBloodCells.png",
        "author": "eureka",
    },
    {
        "headline": "Antibiotics work on bacteria but do nothing to viruses",
        "l1": "Taking antibiotics for a cold does nothing — and quietly fuels a global threat.",
        "l2": "Antibiotics kill bacteria by attacking structures bacteria have and human cells don't, like their cell walls. Viruses work completely differently and lack those targets, so antibiotics can't touch a cold or the flu. Misusing them breeds resistant bacteria.",
        "l3": "Bacteria are living cells; many antibiotics exploit features unique to them — building a bacterial cell wall, or running bacterial protein-making machinery — to kill microbes while sparing us. Viruses aren't cells at all: they hijack your own cells to reproduce, offering none of those bacterial targets, which is why they need entirely different antiviral drugs. Every time antibiotics are overused, a few naturally resistant bacteria survive and multiply, so resistance spreads. Antimicrobial resistance already causes over a million deaths a year.",
        "category": "Medicine",
        "source_url": "https://en.wikipedia.org/wiki/Antimicrobial_resistance",
        "image": "Staphylococcus_aureus_VISA_2.jpg",
        "author": "eureka",
    },
    {
        "headline": "New drugs can slow Alzheimer's by clearing sticky brain plaques",
        "l1": "The first drugs that modestly slow Alzheimer's target a sticky protein clogging the brain.",
        "l2": "In Alzheimer's disease, a protein called amyloid-beta clumps into plaques between brain cells. A new class of antibody drugs clears these plaques and, in trials, modestly slowed the decline in memory and thinking for early-stage patients.",
        "l3": "For decades the leading idea has been that amyloid buildup, followed by tangles of another protein called tau, drives the brain-cell damage of Alzheimer's. The new antibodies are engineered to bind amyloid so the immune system removes it, and they clearly clear plaques on brain scans. The clinical benefit is real but modest — a slowing of decline, not a cure — and the drugs carry risks including brain swelling and small bleeds, requiring careful monitoring. They work best when given early. After a long string of failures, they're the first treatments to alter the disease's course.",
        "category": "Medicine",
        "source_url": "https://en.wikipedia.org/wiki/Alzheimer%27s_disease",
        "image": "Alzheimers_brain.jpg",
        "author": "eureka",
    },
]

# Short, realistic comments seed users leave on posts.
SAMPLE_COMMENTS = [
    "Okay this is genuinely mind-blowing. Saving this.",
    "Wait, really? That completely reframes how I thought about this.",
    "Great write-up — the deep dive actually answered my follow-up question.",
    "The source checks out. I looked into this last year for a project.",
    "This is my new favorite fact. Sharing with my study group.",
    "How reproducible is the underlying result? Curious about the sample size.",
    "Science communication done right. The three levels are perfect.",
    "I had no idea the mechanism worked like that. Thanks for explaining.",
    "Been following this field for a while — nice to see it summarized so clearly.",
    "The hook got me, the deep dive kept me. Well done.",
]


def _resolve_target() -> str:
    return os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "mongodb://localhost:27017"


def _mask(uri: str) -> str:
    parts = urlsplit(uri)
    host = parts.hostname or "?"
    port = f":{parts.port}" if parts.port else ""
    netloc = f"***@{host}{port}" if parts.username else f"{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def _filepath_url(filename: str) -> str:
    # quote the filename but keep it readable; Special:FilePath handles the rest.
    return _COMMONS_FILEPATH + quote(filename)


def validate_image(client: httpx.Client, filename: str) -> tuple[bool, str | None, str]:
    """Return (ok, resolved_direct_url, reason). Skips the image if not a real 200 image."""
    url = _filepath_url(filename)
    try:
        resp = client.get(url, follow_redirects=True, timeout=20.0)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"request error: {exc}"
    ctype = resp.headers.get("content-type", "")
    if resp.status_code != 200:
        return False, None, f"HTTP {resp.status_code}"
    if not ctype.startswith("image/"):
        return False, None, f"content-type {ctype or 'unknown'}"
    # resp.url is the final upload.wikimedia.org direct file URL.
    return True, str(resp.url), ctype


def _credibility(source_url: str | None, upvotes: int) -> dict:
    score = max(72, min(97, 80 + upvotes // 15))
    sources = []
    if source_url:
        sources.append({"title": "Reference", "url": source_url, "source_type": "article"})
    return {"score": score, "verified_count": random.randint(0, 40), "sources": sources}


async def _get_or_create_official(db) -> object:
    existing = await db.users.find_one({"username": "eureka"})
    if existing:
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"is_verified": True, "is_official": True, "verified": True}},
        )
        return existing["_id"]
    now = datetime.now(timezone.utc)
    doc = {
        "email": "agent@projecteureka.app",
        "username": "eureka",
        "display_name": "Eureka Official",
        "name": "Eureka Official",
        "password_hash": hash_password(secrets.token_urlsafe(32)),
        "bio": "Official Eureka account sharing the day's most fascinating science.",
        "interests": [
            "Physics", "Astronomy", "Biology", "Chemistry",
            "Math", "Earth Science", "Technology", "Medicine",
        ],
        "avatar_color": "#00E676",
        "avatar_url": None,
        "cover_image": None,
        "link": "https://projecteureka.vercel.app",
        "location": "Everywhere curiosity lives",
        "working_at": "Eureka",
        "is_verified": True,
        "is_official": True,
        "verified": True,
        "pinned_post_id": None,
        "created_at": now - timedelta(days=500),
    }
    result = await db.users.insert_one(doc)
    return result.inserted_id


async def _get_or_create_seed_user(db, spec: dict) -> object:
    existing = await db.users.find_one(
        {"$or": [{"username": spec["username"]}, {"email": spec["email"]}]}
    )
    now = datetime.now(timezone.utc)
    if existing:
        await db.users.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "username": spec["username"],
                    "email": spec["email"],
                    "verified": False,
                    "is_official": False,
                }
            },
        )
        return existing["_id"]
    doc = {
        "email": spec["email"],
        "username": spec["username"],
        "name": spec["name"],
        "display_name": spec["name"],
        "password_hash": hash_password(SEED_PASSWORD),
        "bio": spec["bio"],
        "interests": spec["interests"],
        "avatar_color": spec["avatar_color"],
        "avatar_url": None,
        "cover_image": None,
        "link": None,
        "location": None,
        "working_at": None,
        "verified": False,
        "is_official": False,
        "pinned_post_id": None,
        "created_at": now - timedelta(days=random.randint(120, 400)),
    }
    result = await db.users.insert_one(doc)
    return result.inserted_id


async def main() -> None:
    uri = _resolve_target()
    print(f"[seed] Connecting to {_mask(uri)}")
    await connect_to_mongo()
    db = get_db()
    now = datetime.now(timezone.utc)

    # ---- Accounts ----
    author_ids: dict[str, object] = {"eureka": await _get_or_create_official(db)}
    for spec in SEED_USERS:
        author_ids[spec["username"]] = await _get_or_create_seed_user(db, spec)
    print(f"[seed] Users ready: 1 official + {len(SEED_USERS)} seed users.")

    # ---- Wipe previous seeded posts (and their comments) to avoid duplicates ----
    seed_author_ids = list(author_ids.values())
    old = await db.posts.find(
        {"$or": [{"is_agent_post": True}, {"author_id": {"$in": seed_author_ids}}]},
        {"_id": 1},
    ).to_list(length=5000)
    old_ids = [p["_id"] for p in old]
    if old_ids:
        await db.comments.delete_many({"post_id": {"$in": old_ids}})
        await db.votes.delete_many({"post_id": {"$in": old_ids}})
        await db.bookmarks.delete_many({"post_id": {"$in": old_ids}})
        await db.posts.delete_many({"_id": {"$in": old_ids}})
    print(f"[seed] Deleted {len(old_ids)} previously seeded posts.")

    # ---- Validate images and insert posts ----
    failed_images: list[tuple[str, str]] = []
    length_warnings: list[str] = []
    per_category: dict[str, int] = {}
    images_ok = 0
    inserted_posts: list[tuple[object, object, datetime]] = []

    with httpx.Client(
        headers={
            "User-Agent": "EurekaSeedBot/1.0 (https://eureka.dev; paarthrane09@gmail.com)"
        }
    ) as client:
        for i, post in enumerate(POSTS):
            # Soft length checks so we can review content quality.
            if len(post["l1"]) > 100:
                length_warnings.append(f"[{i}] HOOK {len(post['l1'])} chars: {post['headline']}")
            if not (180 <= len(post["l2"]) <= 320):
                length_warnings.append(f"[{i}] EXPLAIN {len(post['l2'])} chars: {post['headline']}")
            if not (360 <= len(post["l3"]) <= 640):
                length_warnings.append(f"[{i}] DEEP_DIVE {len(post['l3'])} chars: {post['headline']}")

            ok, direct_url, reason = validate_image(client, post["image"])
            images = []
            if ok and direct_url:
                images = [direct_url]
                images_ok += 1
            else:
                failed_images.append((post["image"], reason))

            author_id = author_ids[post["author"]]
            created = now - timedelta(
                days=random.randint(0, 6),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            upvotes = random.randint(5, 200)
            levels = [post["l1"], post["l2"], post["l3"]]
            doc = {
                "headline": post["headline"],
                # body defaults to the hook so any legacy reader shows level 1.
                "body": post["l1"],
                "category": post["category"],
                "source_url": post.get("source_url"),
                "images": images,
                "author_id": author_id,
                "created_at": created,
                "upvotes": upvotes,
                "comment_count": 0,
                "levels": levels,
                "level_1": post["l1"],
                "level_2": post["l2"],
                "level_3": post["l3"],
                "credibility": _credibility(post.get("source_url"), upvotes),
                "is_agent_post": True,
            }
            result = await db.posts.insert_one(doc)
            inserted_posts.append((result.inserted_id, author_id, created))
            per_category[post["category"]] = per_category.get(post["category"], 0) + 1

    # ---- Comments on ~1/3 of posts ----
    all_user_ids = list(author_ids.values())
    comment_total = 0
    commented_posts = random.sample(inserted_posts, k=len(inserted_posts) // 3)
    for post_id, _author_id, created in commented_posts:
        for _ in range(random.randint(1, 4)):
            commenter = random.choice(all_user_ids)
            c_created = created + timedelta(hours=random.randint(1, 60))
            await db.comments.insert_one(
                {
                    "post_id": post_id,
                    "author_id": commenter,
                    "body": random.choice(SAMPLE_COMMENTS),
                    "parent_id": None,
                    "created_at": min(c_created, now),
                }
            )
            comment_total += 1
        await db.posts.update_one(
            {"_id": post_id},
            {"$set": {"comment_count": await db.comments.count_documents({"post_id": post_id})}},
        )

    # ---- Sidebar: questions + circles (shared with seed_sidebar.py) ----
    q_count, c_count = await seed_sidebar(db)

    # ---- Verification summary ----
    print("\n" + "=" * 56)
    print("VERIFICATION SUMMARY")
    print("=" * 56)
    print(f"Posts inserted: {len(inserted_posts)}")
    for cat in sorted(per_category):
        print(f"  - {cat:<14} {per_category[cat]}")
    print(f"Images validated & attached: {images_ok}/{len(POSTS)}")
    print(f"Users: 1 official (@eureka, verified) + {len(SEED_USERS)} seed users")
    print(f"Comments inserted: {comment_total} across {len(commented_posts)} posts")
    print(f"Questions seeded: {q_count}")
    print(f"Study circles seeded: {c_count}")

    if failed_images:
        print("\nImage URLs skipped (failed validation):")
        for name, reason in failed_images:
            print(f"  - {name}  ({reason})")
    else:
        print("\nAll images passed validation.")

    if length_warnings:
        print("\nLevel length warnings (soft):")
        for w in length_warnings:
            print(f"  - {w}")

    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
