"""Populate the Eureka database with seed accounts and science posts.

Run from the backend directory (with your virtualenv active and MongoDB running):

    python seed.py

This DROPS and rebuilds the posts/users/comments/votes collections so the feed
feels alive from first launch. Existing accounts you created will be removed.
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings
from app.security import hash_password

settings = get_settings()

SEED_PASSWORD = "eureka123"

AVATAR_COLORS = ["#D97757", "#6A8D73", "#7C6BAA", "#C48B3F", "#4F7CAC", "#B0654E"]

ACCOUNTS = [
    {
        "email": "mira@eureka.dev",
        "name": "Dr. Mira Chandra",
        "bio": "Astrophysicist chasing exoplanet atmospheres. Occasional stargazer.",
        "interests": ["Astronomy", "Physics", "Math"],
    },
    {
        "email": "leo@eureka.dev",
        "name": "Leo Whitfield",
        "bio": "Molecular biologist. I think about proteins folding while I sleep.",
        "interests": ["Biology", "Chemistry", "Medicine"],
    },
    {
        "email": "sana@eureka.dev",
        "name": "Sana Okonkwo",
        "bio": "Climate scientist reading the story written in ice cores.",
        "interests": ["Earth Science", "Chemistry", "Biology"],
    },
    {
        "email": "raj@eureka.dev",
        "name": "Raj Patel",
        "bio": "Computer scientist tinkering at the edge of quantum and AI.",
        "interests": ["Technology", "Physics", "Math"],
    },
    {
        "email": "elena@eureka.dev",
        "name": "Dr. Elena Vasquez",
        "bio": "Neuroscientist mapping how memory takes root in the brain.",
        "interests": ["Medicine", "Biology", "Technology"],
    },
    {
        "email": "tom@eureka.dev",
        "name": "Tomasz Nowak",
        "bio": "Science writer. I collect facts that make people say 'wait, really?'",
        "interests": ["Physics", "Astronomy", "Earth Science"],
    },
]

# 25 genuinely interesting science posts across all eight categories.
# Each post carries three depth levels (TL;DR → detailed → technical deep-dive)
# and a credibility sub-doc with a realistic score and 1-3 sources.
POSTS = [
    {
        "author": "mira@eureka.dev",
        "category": "Astronomy",
        "headline": "A planet where it rains molten glass, sideways",
        "body": "HD 189733b is a deep cobalt-blue gas giant 64 light-years away. Its blue comes not from oceans but from silicate clouds, and 5,400 mph winds whip glass rain horizontally across the sky.",
        "source_url": "https://science.nasa.gov/exoplanets",
        "levels": [
            "HD 189733b is a deep cobalt-blue gas giant 64 light-years away. Its blue comes not from oceans but from silicate clouds, and 5,400 mph winds whip glass rain horizontally across the sky.",
            "HD 189733b is a 'hot Jupiter' orbiting its star every 2.2 days, so close that its dayside reaches roughly 1,000 C. Hubble measured its color by watching the light dip as the planet slipped behind its star: the reflected blue vanished, revealing an intrinsic azure. That blue is scattered light from a haze of silicate particles high in the atmosphere. Because the planet is tidally locked, a fierce temperature gradient drives supersonic winds from the hot dayside to the cooler nightside.\n\nThose winds are estimated at up to 8,700 km/h (about 5,400 mph), seven times the speed of sound in Earth's air. Silicate condensates in that flow behave like wind-driven glass, so any 'rain' is blasted sideways rather than falling.",
            "The color detection relied on transmission and reflection spectroscopy: measuring the planet's albedo across wavelengths during secondary eclipse. Rayleigh scattering by sub-micron magnesium-silicate (enstatite/forsterite) grains preferentially scatters shorter wavelengths, producing the blue geometric albedo (~0.4 in blue, near zero in red). Wind speeds are inferred from Doppler shifts of atmospheric absorption lines (e.g. sodium) across the terminator, comparing the blueshifted evening limb to the redshifted morning limb. Caveats: retrieved cloud properties are model-dependent, particle size and composition are degenerate with altitude, and the extreme winds come from general circulation models constrained by sparse phase-curve data rather than direct imaging.",
        ],
        "credibility": {
            "score": 94,
            "verified_count": 212,
            "sources": [
                {"title": "NASA Exoplanet Exploration: HD 189733 b", "url": "https://science.nasa.gov/exoplanets", "source_type": "university"},
                {"title": "Evans et al., 'The deep blue color of HD 189733b', ApJ Letters", "url": "https://iopscience.iop.org/article/10.1088/2041-8205/772/2/L16", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "mira@eureka.dev",
        "category": "Astronomy",
        "headline": "There is a giant cloud of alcohol in space",
        "body": "Near the constellation Aquila sits a cloud of methanol and ethanol 1,000 times the diameter of our solar system. It won't get you tipsy, but it's a nursery where stars are being born.",
        "source_url": None,
        "levels": [
            "Near the constellation Aquila sits a cloud of methanol and ethanol 1,000 times the diameter of our solar system. It won't get you tipsy, but it's a nursery where stars are being born.",
            "Star-forming regions like G34.3 and Sagittarius B2 are cold, dense molecular clouds where complex organic molecules accumulate on icy dust grains and are released into the gas phase as young stars warm their surroundings. Radio telescopes have detected methanol (CH3OH) and even ethanol (C2H5OH) spanning enormous volumes. The 'alcohol' is real but astronomically dilute, and mixed with far more abundant hydrogen.\n\nThese molecules are tracers: their emission lines let astronomers map density, temperature, and the chemistry that eventually seeds planet-forming disks with organics.",
            "Detection uses rotational spectroscopy at millimeter and centimeter wavelengths: each molecule emits at characteristic frequencies set by its moment of inertia and quantum rotational transitions. Methanol in particular hosts numerous maser transitions (e.g. 6.7 GHz Class II masers) that are collisionally or radiatively pumped, producing intensely amplified, non-thermal emission that pinpoints massive-star formation. Column densities are derived from rotational-diagram or LTE modeling assuming an excitation temperature; abundances relative to H2 are typically 10^-9 to 10^-6. Caveats: beam dilution, optical-depth effects, and non-LTE excitation make absolute quantities uncertain, and the 'size' quoted depends on the emission threshold chosen.",
        ],
        "credibility": {
            "score": 88,
            "verified_count": 140,
            "sources": [
                {"title": "Jodrell Bank Observatory press release on interstellar methanol", "url": "https://www.jodrellbank.manchester.ac.uk/", "source_type": "university"},
                {"title": "Astrophysical maser surveys of methanol, MNRAS", "url": "https://academic.oup.com/mnras", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "tom@eureka.dev",
        "category": "Astronomy",
        "headline": "A day on Venus is longer than its year",
        "body": "Venus rotates so slowly that one full spin takes 243 Earth days, while it orbits the Sun in just 225. It also spins backwards, so the Sun there rises in the west.",
        "source_url": None,
        "levels": [
            "Venus rotates so slowly that one full spin takes 243 Earth days, while it orbits the Sun in just 225. It also spins backwards, so the Sun there rises in the west.",
            "Venus has a sidereal rotation period of about 243 Earth days but orbits the Sun in roughly 225 days, so a single rotation outlasts its year. Its rotation is retrograde (clockwise viewed from the north), the opposite of nearly every other planet. Combined with its orbital motion, the solar day (noon to noon) works out to about 117 Earth days, and the Sun appears to rise in the west and set in the east.\n\nThe leading explanation blends a possible ancient giant impact with strong tidal torques from the Sun acting on Venus's massive, super-rotating atmosphere.",
            "The retrograde, slow spin is thought to arise from atmospheric thermal tides: solar heating creates a bulge in the dense (92 bar) atmosphere that the Sun's gravity tugs on, producing a torque that can drive the solid planet toward its current state. Core-mantle friction and possible past chaotic obliquity variations also contribute. Modeling shows multiple stable end-states (including retrograde) are dynamically accessible, so Venus's configuration may be one attractor among several. Caveats: rotation-period measurements from Magellan, Venus Express, and radar differ by minutes to a day, hinting the solid body's spin fluctuates as angular momentum is exchanged with the atmosphere, and the impact-versus-tide contributions remain debated.",
        ],
        "credibility": {
            "score": 96,
            "verified_count": 305,
            "sources": [
                {"title": "NASA Solar System Exploration: Venus facts", "url": "https://solarsystem.nasa.gov/planets/venus/", "source_type": "university"},
                {"title": "Correia & Laskar, 'Long-term evolution of the spin of Venus', Nature", "url": "https://www.nature.com/", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "raj@eureka.dev",
        "category": "Physics",
        "headline": "Quantum computers just held a state for 1,000 seconds",
        "body": "A trapped-ion qubit maintained coherence for over 1,000 seconds this year, up from milliseconds a decade ago. Stable qubits are the bottleneck between us and useful quantum machines.",
        "source_url": None,
        "levels": [
            "A trapped-ion qubit maintained coherence for over 1,000 seconds this year, up from milliseconds a decade ago. Stable qubits are the bottleneck between us and useful quantum machines.",
            "A qubit's coherence time measures how long it holds fragile quantum superposition before noise scrambles it. Trapped-ion qubits, single charged atoms held in electromagnetic traps and manipulated with lasers, have reached single-qubit memory coherence exceeding 1,000 seconds, and in some experiments far longer, by encoding information in magnetically insensitive 'clock' states.\n\nLonger coherence means more operations fit inside a computation before errors dominate, which is why it is a headline metric on the road to fault-tolerant quantum computing.",
            "The relevant timescales are T1 (energy relaxation) and T2 (dephasing). Using hyperfine clock transitions with near-zero first-order magnetic-field sensitivity suppresses dephasing from ambient field noise, and dynamical decoupling pulse sequences further extend T2 toward the T1 limit. What matters for computation is coherence relative to gate time: the ratio (coherence/gate duration) sets the number of operations before decoherence, and error-correction thresholds require this to be large (roughly >10^4). Caveats: record coherence is for idle memory qubits, not during two-qubit entangling gates, where crosstalk, motional heating, and laser phase noise dominate; scaling many such qubits while preserving these figures is the unsolved engineering problem.",
        ],
        "credibility": {
            "score": 82,
            "verified_count": 97,
            "sources": [
                {"title": "Wang et al., 'Single-qubit coherence beyond 10 minutes', Nature Photonics", "url": "https://www.nature.com/nphoton/", "source_type": "journal"},
                {"title": "NIST Ion Storage Group", "url": "https://www.nist.gov/pml/time-and-frequency-division/ion-storage", "source_type": "university"},
            ],
        },
    },
    {
        "author": "tom@eureka.dev",
        "category": "Physics",
        "headline": "Nothing is not empty: the vacuum is boiling",
        "body": "Empty space constantly froths with particle-antiparticle pairs that pop into existence and annihilate. This 'quantum foam' isn't a theory quirk; it nudges atoms in a measurable way called the Lamb shift.",
        "source_url": None,
        "levels": [
            "Empty space constantly froths with particle-antiparticle pairs that pop into existence and annihilate. This 'quantum foam' isn't a theory quirk; it nudges atoms in a measurable way called the Lamb shift.",
            "In quantum field theory, the vacuum is the lowest-energy state of every field, but it is not truly still. The uncertainty principle guarantees fields fluctuate, allowing virtual particle-antiparticle pairs to briefly borrow energy and vanish again. These fluctuations have real, measured consequences: they shift atomic energy levels (the Lamb shift), nudge the electron's magnetic moment, and produce an attractive force between close metal plates (the Casimir effect).\n\nSo 'empty' space is a seething medium whose fingerprints appear in precision experiments.",
            "The Lamb shift is the ~1057 MHz splitting between the 2S1/2 and 2P1/2 hydrogen levels, degenerate in Dirac theory. It arises from the electron's interaction with vacuum fluctuations of the electromagnetic field: self-energy corrections, vacuum polarization, and electron mass renormalization computed to one loop in QED. The same formalism yields the electron anomalous magnetic moment a_e = (g-2)/2, predicted and measured to better than one part in 10^12, the most precise agreement between theory and experiment in physics. Caveats: 'virtual particles' are calculational terms in a perturbative expansion, not literally observable objects, and the absolute vacuum energy density predicted this way famously disagrees with cosmological observations by many orders of magnitude, the cosmological constant problem.",
        ],
        "credibility": {
            "score": 91,
            "verified_count": 176,
            "sources": [
                {"title": "Feynman, QED: The Strange Theory of Light and Matter", "url": "https://press.princeton.edu/books/paperback/9780691164090/qed", "source_type": "article"},
                {"title": "Hanneke et al., 'New measurement of the electron magnetic moment', PRL", "url": "https://journals.aps.org/prl/", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "raj@eureka.dev",
        "category": "Physics",
        "headline": "Superconductors can now levitate on a track indefinitely",
        "body": "Quantum locking pins a superconductor in a magnetic field so firmly it can hang upside down under a rail. Cool it below its critical temperature and it remembers exactly where it was placed.",
        "source_url": None,
        "levels": [
            "Quantum locking pins a superconductor in a magnetic field so firmly it can hang upside down under a rail. Cool it below its critical temperature and it remembers exactly where it was placed.",
            "Type-II superconductors don't simply repel magnetic fields; they trap thin filaments of field, called flux vortices, in tiny defects. This 'flux pinning' locks the superconductor in three dimensions relative to a magnet, so it can float above, beside, or even beneath a magnetic track and stay there. Cool a suitable ceramic below its critical temperature over a magnetic rail and it holds that exact position and orientation.\n\nThis 'quantum locking' is what makes stable maglev demos and frictionless bearings possible.",
            "Below Tc, superconductors expel magnetic field via the Meissner effect (perfect diamagnetism). Type-II materials have two critical fields: below Hc1 they fully exclude flux, but between Hc1 and Hc2 field penetrates as quantized vortices each carrying one flux quantum Phi0 = h/2e. Crystal defects pin these vortices, creating an energy landscape that resists both vertical and lateral displacement, hence stable levitation and suspension. The restoring force per vortex depends on the pinning potential and critical current density Jc. Caveats: pinning strength falls with temperature and applied field; flux creep slowly relaxes the trapped configuration; and the effect requires cryogenic cooling (liquid nitrogen for YBCO at 77 K), so 'indefinitely' really means 'as long as it stays cold'.",
        ],
        "credibility": {
            "score": 89,
            "verified_count": 133,
            "sources": [
                {"title": "Tel Aviv University superconductivity group: quantum levitation", "url": "https://www.quantumlevitation.com/", "source_type": "university"},
                {"title": "Tinkham, Introduction to Superconductivity", "url": "https://store.doverpublications.com/", "source_type": "article"},
            ],
        },
    },
    {
        "author": "leo@eureka.dev",
        "category": "Biology",
        "headline": "Your body replaces 330 billion cells every single day",
        "body": "That's about 1% of you, renewed daily. Over roughly three months, you rebuild an entirely fresh set of red blood cells. You are less a fixed object than a standing wave.",
        "source_url": None,
        "levels": [
            "That's about 1% of you, renewed daily. Over roughly three months, you rebuild an entirely fresh set of red blood cells. You are less a fixed object than a standing wave.",
            "Cell turnover varies wildly by tissue. Gut-lining epithelium is replaced every few days, skin over weeks, red blood cells over about four months, while neurons and lens cells last a lifetime. Summing across tissues, researchers estimate the body produces on the order of hundreds of billions of new cells daily, dominated by blood cells and gut epithelium. The steady replacement is balanced by programmed cell death, keeping total cell number roughly constant.\n\nSo the atoms and cells composing you are constantly cycling even as the overall pattern persists.",
            "A 2021 quantitative analysis (Sender & Milo) combined tissue masses, cell-size data, and measured turnover rates to estimate ~330 billion cells replaced per day, with erythrocytes (~86%) and gastrointestinal epithelial cells (~12%) dominating by number, while adipocytes and muscle dominate by mass. Turnover is quantified via methods like carbon-14 birth-dating (leveraging the atmospheric bomb-pulse), Ki-67 proliferation markers, and isotope-labeling of DNA. Caveats: rates differ across individuals, age, and disease; long-lived post-mitotic cells (cardiomyocytes, neurons) turn over slowly or negligibly; and 'replacing your whole body' is a simplification since many structural cells and their extracellular matrix persist for decades.",
        ],
        "credibility": {
            "score": 90,
            "verified_count": 188,
            "sources": [
                {"title": "Sender & Milo, 'The distribution of cellular turnover in the human body', Nature Medicine", "url": "https://www.nature.com/nm/", "source_type": "journal"},
                {"title": "Weizmann Institute BioNumbers database", "url": "https://bionumbers.hms.harvard.edu/", "source_type": "dataset"},
            ],
        },
    },
    {
        "author": "leo@eureka.dev",
        "category": "Biology",
        "headline": "Tardigrades survived the raw vacuum of space",
        "body": "In a 2007 orbital experiment, these water bears endured hard vacuum and cosmic radiation for 10 days, then rehydrated and laid healthy eggs back on Earth. Almost nothing kills them.",
        "source_url": None,
        "levels": [
            "In a 2007 orbital experiment, these water bears endured hard vacuum and cosmic radiation for 10 days, then rehydrated and laid healthy eggs back on Earth. Almost nothing kills them.",
            "Tardigrades survive extremes by entering cryptobiosis: they expel most body water, curl into a desiccated 'tun', and drop metabolism to near zero. In the 2007 TARDIS experiment aboard the FOTON-M3 mission, tuns exposed to open space (vacuum plus intense UV) for 10 days had survivors that rehydrated and reproduced. Vacuum alone barely fazed them; the harshest damage came from solar UV radiation.\n\nTheir toolkit includes protective sugars and specialized proteins that shield cellular machinery when water is gone.",
            "Cryptobiotic tolerance relies on tardigrade-unique intrinsically disordered proteins (TDPs) that vitrify the cytoplasm on drying, forming a glassy matrix that immobilizes and protects biomolecules, plus the damage-suppressor protein Dsup, which binds DNA and shields it from hydroxyl-radical and radiation-induced strand breaks. In the TARDIS results, survival after vacuum-only exposure was high, whereas full-spectrum solar UV drastically reduced it, implicating photochemical DNA damage as the limiting factor. Caveats: survival rates varied by species and were far from 100%; 'surviving space' means desiccated tuns, not active animals; and long-term genomic integrity of survivors was assessed by reproduction, not full sequencing, so sublethal mutational load is not fully characterized.",
        ],
        "credibility": {
            "score": 87,
            "verified_count": 154,
            "sources": [
                {"title": "Jonsson et al., 'Tardigrades survive exposure to space in low Earth orbit', Current Biology", "url": "https://www.cell.com/current-biology/", "source_type": "journal"},
                {"title": "Hashimoto et al., 'Dsup protects DNA from radiation', Nature Communications", "url": "https://www.nature.com/ncomms/", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "sana@eureka.dev",
        "category": "Biology",
        "headline": "A single aspen grove in Utah is one 80,000-year-old organism",
        "body": "Pando is 47,000 genetically identical trunks sharing one root system, weighing ~6,000 tonnes. It may be the heaviest and among the oldest living things on Earth, and it's slowly declining.",
        "source_url": None,
        "levels": [
            "Pando is 47,000 genetically identical trunks sharing one root system, weighing ~6,000 tonnes. It may be the heaviest and among the oldest living things on Earth, and it's slowly declining.",
            "Pando ('I spread' in Latin) is a clonal colony of quaking aspen (Populus tremuloides) in Utah. Every trunk is a genetically identical stem (ramet) sprouting from one shared, interconnected root system, so the whole 43-hectare grove is a single organism. Its estimated mass of ~6,000 tonnes makes it possibly the heaviest known living thing, and root-system age estimates run into the tens of thousands of years.\n\nToday it is failing to regenerate, largely because deer and elk eat young shoots before they can mature.",
            "Clonality is confirmed by genetic markers (microsatellites, SNPs) showing uniform genotype across ramets, and by the shared vegetative root network from which new stems arise via suckering. Age is not measured by tree rings (individual trunks live only ~100-130 years) but inferred from clone size, spread rate, and paleoclimate constraints, giving highly uncertain figures often cited as ~14,000 up to 80,000 years. Decline is documented via aerial imagery and stem-age structure showing a missing cohort of young stems. Caveats: root-age estimates carry large error bars and some researchers argue for far younger ages; mass figures are extrapolations from stem counts and allometry; and herbivory, drought, and disease jointly drive the decline rather than a single cause.",
        ],
        "credibility": {
            "score": 72,
            "verified_count": 61,
            "sources": [
                {"title": "Rogers & McAvoy, 'Mule deer impede Pando's recovery', PLOS ONE", "url": "https://journals.plos.org/plosone/", "source_type": "journal"},
                {"title": "US Forest Service: Pando clone", "url": "https://www.fs.usda.gov/", "source_type": "university"},
            ],
        },
    },
    {
        "author": "elena@eureka.dev",
        "category": "Biology",
        "headline": "Octopuses edit their own RNA to survive the cold",
        "body": "Rather than waiting for evolution, octopuses rewrite their RNA on the fly to tune nerve proteins to water temperature. It's a rare case of an animal editing its genetic messages in real time.",
        "source_url": None,
        "levels": [
            "Rather than waiting for evolution, octopuses rewrite their RNA on the fly to tune nerve proteins to water temperature. It's a rare case of an animal editing its genetic messages in real time.",
            "Coleoid cephalopods (octopus, squid, cuttlefish) recode their messenger RNA extensively through A-to-I editing, chemically converting adenosine bases so the protein produced differs from what the DNA encodes. Much of this editing targets neural proteins, and studies show octopuses ramp up editing at ion-channel genes when water temperature drops, tuning nerve signaling to the cold within hours to days.\n\nThis gives them a fast, reversible way to acclimate that ordinary DNA mutation could never match.",
            "A-to-I editing is catalyzed by ADAR enzymes acting on double-stranded RNA; inosine is read as guanosine by the ribosome, so an A-to-I edit can change a codon and thus an amino acid (recoding). Cephalopods have vastly more recoding sites than other animals, many conserved and enriched in the nervous system. Temperature-dependent editing of the potassium channel Kv1.1 and other targets shifts channel kinetics to compensate for cold, a form of physiological plasticity. Caveats: high editing appears to constrain genome evolution (surrounding sequence must preserve the dsRNA structure ADAR needs), the functional impact of most edits is unverified, and whether editing changes are truly adaptive versus incidental is still being tested experimentally.",
        ],
        "credibility": {
            "score": 85,
            "verified_count": 118,
            "sources": [
                {"title": "Birk et al., 'Temperature-dependent RNA editing in octopus', Cell", "url": "https://www.cell.com/", "source_type": "journal"},
                {"title": "Liscovitch-Brauer et al., 'Trade-off between transcriptome plasticity and genome evolution in cephalopods', Cell", "url": "https://www.cell.com/", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "leo@eureka.dev",
        "category": "Chemistry",
        "headline": "Glass is not a slow-moving liquid after all",
        "body": "The old myth that medieval cathedral windows are thicker at the bottom because glass flows is false. Glass is an amorphous solid; the panes were just made unevenly. It would take longer than the universe's age to flow.",
        "source_url": None,
        "levels": [
            "The old myth that medieval cathedral windows are thicker at the bottom because glass flows is false. Glass is an amorphous solid; the panes were just made unevenly. It would take longer than the universe's age to flow.",
            "Glass is an amorphous solid: its atoms are frozen in a disordered, liquid-like arrangement but lack the mobility to flow on human timescales. Old cathedral windows are thicker at the bottom because medieval crown-glass panes were uneven, and glaziers usually set the heavier edge down, not because the glass sagged over centuries. Measured viscosity of room-temperature glass is so astronomically high that any flow would take vastly longer than the age of the universe.\n\nGlass is best described as a material stuck between liquid and crystal.",
            "Glass forms when a melt is cooled through its glass-transition temperature Tg fast enough to avoid crystallization; molecular relaxation times diverge (super-Arrhenius behavior, often fit by Vogel-Fulcher-Tammann) so the structure kinetically arrests. Room-temperature viscosity estimates for silica glass exceed 10^40 poise, implying flow distances of atomic dimensions over cosmological times. Studies of centuries-old panes find no measurable, uniform gravitational sag. Caveats: 'is glass a liquid or solid?' is partly semantic, the nature of the glass transition (thermodynamic vs purely kinetic) remains an open problem in condensed-matter physics, and thin-film or nanoscale glasses can show measurable relaxation and even ultrastable states via vapor deposition, so 'never flows' applies to bulk glass on ordinary timescales.",
        ],
        "credibility": {
            "score": 93,
            "verified_count": 201,
            "sources": [
                {"title": "Zanotto, 'Do cathedral glasses flow?', American Journal of Physics", "url": "https://pubs.aip.org/aapt/ajp", "source_type": "journal"},
                {"title": "Corning Museum of Glass: is glass a liquid?", "url": "https://www.cmog.org/", "source_type": "article"},
            ],
        },
    },
    {
        "author": "sana@eureka.dev",
        "category": "Chemistry",
        "headline": "Water can boil and freeze at the same time",
        "body": "At its triple point, ~0.01 C and very low pressure, water exists as solid, liquid, and gas simultaneously. You can watch it bubble and ice over in the same beaker. Physics at a knife's edge.",
        "source_url": None,
        "levels": [
            "At its triple point, ~0.01 C and very low pressure, water exists as solid, liquid, and gas simultaneously. You can watch it bubble and ice over in the same beaker. Physics at a knife's edge.",
            "Every substance has a triple point: the single combination of temperature and pressure where its solid, liquid, and gas phases coexist in equilibrium. For water that is 0.01 C (273.16 K) and 611.657 pascals, far below normal atmospheric pressure. In a sealed chamber pumped to that pressure, water simultaneously boils and freezes, producing the striking sight of ice forming while bubbles rise.\n\nThis point was so fundamental it defined the kelvin temperature scale for decades.",
            "On a pressure-temperature phase diagram, the triple point is where the sublimation, vaporization, and melting curves intersect, a zero-degree-of-freedom state by the Gibbs phase rule (F = C - P + 2 = 1 - 3 + 2 = 0), meaning it is fixed and cannot be varied. From 1954 to 2019 the kelvin was defined by setting water's triple point to exactly 273.16 K, before the 2019 SI redefinition anchored temperature to the Boltzmann constant. Caveats: reaching it requires very pure water and precise control since dissolved gases and isotopic composition shift the exact values (VSMOW is specified); the 'boiling' is low-pressure vaporization, not 100 C boiling; and water's phase diagram is unusually rich, with many high-pressure ice polymorphs beyond this ordinary triple point.",
        ],
        "credibility": {
            "score": 95,
            "verified_count": 240,
            "sources": [
                {"title": "NIST reference on the triple point of water", "url": "https://www.nist.gov/", "source_type": "university"},
                {"title": "IUPAC/BIPM SI definition of the kelvin", "url": "https://www.bipm.org/en/si-base-units/kelvin", "source_type": "article"},
            ],
        },
    },
    {
        "author": "leo@eureka.dev",
        "category": "Chemistry",
        "headline": "There's enough gold in the ocean to give everyone 9 pounds",
        "body": "Seawater holds around 20 million tonnes of dissolved gold. The catch: it's so dilute, roughly one gram per 100 million tonnes of water, that extracting it costs vastly more than it's worth.",
        "source_url": None,
        "levels": [
            "Seawater holds around 20 million tonnes of dissolved gold. The catch: it's so dilute, roughly one gram per 100 million tonnes of water, that extracting it costs vastly more than it's worth.",
            "Gold is present in seawater as trace dissolved ions and colloids at concentrations of parts per trillion. Multiplied by the ocean's ~1.3 billion cubic kilometers, the total sums to millions of tonnes, dwarfing all gold ever mined. But the concentration is so low that any extraction method must process staggering volumes of water for a tiny yield, so the energy and chemistry costs vastly exceed the gold's value.\n\nFritz Haber famously tried to fund Germany's WWI debts this way and failed once he measured the true, far lower concentration.",
            "Modern analyses put open-ocean dissolved gold near 10-30 parts per quadrillion (roughly 0.00001-0.00003 micrograms per liter), far below Haber's overestimates. At these levels, selective recovery would require adsorbents or biosorbents with extreme affinity and enormous throughput; the thermodynamic and pumping energy to move billions of tonnes of water swamps the recoverable value. Total-mass estimates carry large uncertainty because concentrations vary with depth, location, and whether colloidal and particulate gold are included. Caveats: 'enough for everyone' figures depend on which concentration estimate is used and can be off by an order of magnitude; no economically viable seawater-gold extraction exists, and past claims of success were measurement errors.",
        ],
        "credibility": {
            "score": 68,
            "verified_count": 52,
            "sources": [
                {"title": "NOAA Ocean Facts: gold in the ocean", "url": "https://oceanservice.noaa.gov/facts/gold.html", "source_type": "university"},
                {"title": "Falkner & Edmond, 'Gold in seawater', Earth and Planetary Science Letters", "url": "https://www.sciencedirect.com/journal/earth-and-planetary-science-letters", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "raj@eureka.dev",
        "category": "Math",
        "headline": "A deck of cards you shuffle has likely never existed before",
        "body": "52! orderings is about 8 x 10^67, far more than atoms in our galaxy. Shuffle a deck properly and you almost certainly created an arrangement no human has ever seen or will see again.",
        "source_url": None,
        "levels": [
            "52! orderings is about 8 x 10^67, far more than atoms in our galaxy. Shuffle a deck properly and you almost certainly created an arrangement no human has ever seen or will see again.",
            "The number of ways to order 52 distinct cards is 52 factorial (52!), which equals about 8.07 x 10^67. That is a number so vast it exceeds the estimated count of atoms in the Milky Way and even rough estimates of all card shuffles ever performed in history. So a genuinely random shuffle almost certainly produces a sequence that has never occurred before and never will again.\n\nThe key requirement is randomness: a poor shuffle can revisit familiar patterns.",
            "52! grows via the factorial's rapid combinatorial explosion; Stirling's approximation n! ~ sqrt(2 pi n)(n/e)^n captures the scale. Even bounding total historical shuffles generously (say 10^10 people x 10^9 shuffles each) gives ~10^19, an infinitesimal fraction of 10^67, so by the pigeonhole/probability argument, collision is astronomically unlikely under uniform sampling. The catch is achieving uniformity: mathematical analysis (Bayer & Diaconis) shows about 7 riffle shuffles are needed for a standard deck to approach uniform randomness; fewer leaves detectable structure, and mechanical or one-handed shuffles can be far from random. Caveats: 'never existed' assumes true uniform shuffling, and factory-ordered new decks all start identically, so early shuffles of fresh decks share correlated states.",
        ],
        "credibility": {
            "score": 97,
            "verified_count": 289,
            "sources": [
                {"title": "Bayer & Diaconis, 'Trailing the dovetail shuffle to its lair', Annals of Applied Probability", "url": "https://projecteuclid.org/journals/annals-of-applied-probability", "source_type": "journal"},
                {"title": "Diaconis, 'Mathematical developments from the analysis of riffle shuffling'", "url": "https://statweb.stanford.edu/~cgates/PERSI/", "source_type": "university"},
            ],
        },
    },
    {
        "author": "mira@eureka.dev",
        "category": "Math",
        "headline": "The number that describes chaos hides in dripping faucets",
        "body": "Feigenbaum's constant, 4.669, shows up whenever orderly systems tip into chaos, from dripping taps to heartbeats. Wildly different systems bifurcate into disorder at the exact same rhythm.",
        "source_url": None,
        "levels": [
            "Feigenbaum's constant, 4.669, shows up whenever orderly systems tip into chaos, from dripping taps to heartbeats. Wildly different systems bifurcate into disorder at the exact same rhythm.",
            "Many systems transition to chaos through a cascade of 'period-doublings': a steady behavior splits into a two-cycle, then a four-cycle, eight, and so on, faster and faster, until it becomes chaotic. Mitchell Feigenbaum discovered that the ratio of successive doubling intervals approaches a universal constant, about 4.6692, regardless of the specific system. The same number governs dripping faucets, electronic oscillators, convecting fluids, and population models.\n\nThat universality is why chaos theory says diverse systems share deep mathematical structure.",
            "For a smooth one-dimensional map with a single quadratic (parabolic) maximum, like the logistic map x_{n+1} = r x_n (1 - x_n), the parameter values r_n where the 2^n-cycle appears satisfy (r_n - r_{n-1})/(r_{n+1} - r_n) -> delta = 4.669201..., and successive branch scalings converge to a second constant alpha = 2.5029. Feigenbaum explained this via renormalization-group analysis: the constants are eigenvalues of a fixed-point functional equation, universal across all maps in the same (quadratic-maximum) universality class. Experiments in Rayleigh-Bénard convection and nonlinear circuits confirmed delta. Caveats: universality holds only for that class; maps with different local behavior (e.g. quartic maxima) have different constants, and real systems show clean doubling cascades only over limited parameter ranges before noise or higher-dimensional effects intrude.",
        ],
        "credibility": {
            "score": 90,
            "verified_count": 121,
            "sources": [
                {"title": "Feigenbaum, 'Quantitative universality for a class of nonlinear transformations', J. Stat. Phys.", "url": "https://link.springer.com/journal/10955", "source_type": "journal"},
                {"title": "Strogatz, Nonlinear Dynamics and Chaos", "url": "https://www.stevenstrogatz.com/books/nonlinear-dynamics-and-chaos", "source_type": "article"},
            ],
        },
    },
    {
        "author": "raj@eureka.dev",
        "category": "Math",
        "headline": "You only need 23 people for a coin-flip chance of a shared birthday",
        "body": "The birthday paradox: with just 23 people, there's a 50% chance two share a birthday; with 70, it's 99.9%. Our intuition fails because we count pairs, not people.",
        "source_url": None,
        "levels": [
            "The birthday paradox: with just 23 people, there's a 50% chance two share a birthday; with 70, it's 99.9%. Our intuition fails because we count pairs, not people.",
            "The 'paradox' is that a surprisingly small group is likely to contain a shared birthday. With 23 people the probability exceeds 50%, and with 70 it climbs above 99.9%. The intuition trap is that we imagine matching our own birthday against others (22 comparisons), when what actually matters is every possible pair. In a group of 23 there are 253 pairs, and each is a chance for a match, which adds up fast.\n\nIt is not a true paradox, just a counterintuitive counting result.",
            "Assuming 365 equally likely birthdays and independence, it is easiest to compute the complement: P(no shared birthday) = 365/365 x 364/365 x ... x (365 - n + 1)/365 = 365! / ((365 - n)! x 365^n). For n = 23 this gives about 0.4927, so P(at least one match) ~ 0.5073. The number of pairs is C(n,2) = n(n-1)/2, which grows quadratically, explaining the rapid rise. Caveats: real birthdays are not uniformly distributed (seasonal clustering, fewer on Feb 29), which slightly increases collision probability; leap years, twins, and cultural birth-timing effects are ignored in the classic model; and the related 'birthday attack' uses the same sqrt(N)-scaling to find hash collisions in cryptography.",
        ],
        "credibility": {
            "score": 97,
            "verified_count": 264,
            "sources": [
                {"title": "Mosteller, Fifty Challenging Problems in Probability", "url": "https://store.doverpublications.com/", "source_type": "article"},
                {"title": "Wolfram MathWorld: Birthday Problem", "url": "https://mathworld.wolfram.com/BirthdayProblem.html", "source_type": "university"},
            ],
        },
    },
    {
        "author": "sana@eureka.dev",
        "category": "Earth Science",
        "headline": "The Sahara fertilizes the Amazon from across an ocean",
        "body": "Each year, ~27 million tonnes of Saharan dust cross the Atlantic. The phosphorus in it replenishes the Amazon's nutrient-poor soils. One desert quietly keeps a rainforest alive.",
        "source_url": None,
        "levels": [
            "Each year, ~27 million tonnes of Saharan dust cross the Atlantic. The phosphorus in it replenishes the Amazon's nutrient-poor soils. One desert quietly keeps a rainforest alive.",
            "Winds lift enormous quantities of mineral dust from the Sahara, especially the Bodélé Depression, and carry it thousands of kilometers across the Atlantic. Satellites and models estimate that around 27 million tonnes settle over the Amazon basin each year. Crucially, the dust carries phosphorus, a nutrient that heavy tropical rainfall constantly leaches from Amazon soils. This trans-oceanic delivery roughly balances the phosphorus the rainforest loses, linking two ecosystems an ocean apart.\n\nIt is a striking example of Earth's systems coupling across continents.",
            "The estimate comes from NASA's CALIPSO lidar, which profiles the vertical distribution of the Saharan Air Layer, combined with transport modeling to convert optical depth to mass flux. Yu et al. (2015) derived a multi-year mean of ~182 Tg of dust leaving Africa, with ~27.7 Tg deposited in the Amazon basin, delivering an estimated ~22,000 tonnes of phosphorus per year, comparable to hydrological phosphorus losses. Dust also affects radiation, cloud microphysics, and hurricane suppression. Caveats: year-to-year variability is large (factor of ~2-3) and correlates with Sahel rainfall; phosphorus bioavailability depends on mineralogy and solubility; and satellite-to-mass conversions carry substantial uncertainty, so the 'balance' is approximate rather than exact.",
        ],
        "credibility": {
            "score": 86,
            "verified_count": 109,
            "sources": [
                {"title": "Yu et al., 'The fertilizing role of African dust in the Amazon', Geophysical Research Letters", "url": "https://agupubs.onlinelibrary.wiley.com/journal/19448007", "source_type": "journal"},
                {"title": "NASA Earth Observatory: Saharan dust and the Amazon", "url": "https://earthobservatory.nasa.gov/", "source_type": "university"},
            ],
        },
    },
    {
        "author": "sana@eureka.dev",
        "category": "Earth Science",
        "headline": "Earth's inner core may spin at its own pace",
        "body": "Seismic data suggests the solid iron inner core rotates slightly differently from the mantle above it, and recently may have paused and reversed relative to the surface. The planet has a heartbeat we're only starting to read.",
        "source_url": None,
        "levels": [
            "Seismic data suggests the solid iron inner core rotates slightly differently from the mantle above it, and recently may have paused and reversed relative to the surface. The planet has a heartbeat we're only starting to read.",
            "Earth's solid iron inner core floats within the liquid outer core, mechanically decoupled from the rocky mantle, so it can rotate at a slightly different rate, called differential rotation or super/sub-rotation. Seismologists track this by comparing repeating earthquakes whose waves pass through the core over decades; tiny changes in travel time hint at the core's motion. A 2023 analysis suggested the inner core's rotation relative to the surface recently slowed, paused, and may be reversing on a multi-decadal cycle.\n\nThe interpretation is debated but points to a dynamic, oscillating core.",
            "The method uses 'doublets', pairs of near-identical earthquakes years apart, and compares differential travel times of core-traversing phases (e.g. PKIKP) against surface reference paths; systematic drifts imply the sampled inner-core structure has moved. Yang & Song (2023) reported that inner-core rotation relative to the mantle appears to have stalled around 2009 and may oscillate on a ~70-year period, consistent with gravitational coupling to the mantle and electromagnetic torques from the geodynamo. Caveats: the signal is small and could reflect changing inner-core surface topography or localized structure rather than bulk rotation; independent groups infer different rates or even the opposite sense; and data coverage is sparse, so conclusions remain provisional and actively contested.",
        ],
        "credibility": {
            "score": 65,
            "verified_count": 44,
            "sources": [
                {"title": "Yang & Song, 'Multidecadal variation of the Earth's inner-core rotation', Nature Geoscience", "url": "https://www.nature.com/ngeo/", "source_type": "journal"},
                {"title": "Vidale et al., inner-core rotation reanalysis, PNAS", "url": "https://www.pnas.org/", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "tom@eureka.dev",
        "category": "Earth Science",
        "headline": "There are more trees on Earth than stars in the Milky Way",
        "body": "Roughly 3 trillion trees to the galaxy's 100-400 billion stars. Sadly we cut down about 15 billion trees a year, a number worth sitting with.",
        "source_url": None,
        "levels": [
            "Roughly 3 trillion trees to the galaxy's 100-400 billion stars. Sadly we cut down about 15 billion trees a year, a number worth sitting with.",
            "A 2015 global study combined satellite imagery with hundreds of thousands of ground plot measurements to estimate about 3.04 trillion trees on Earth, roughly eight times earlier estimates. The Milky Way is thought to hold on the order of 100-400 billion stars, so trees outnumber our galaxy's stars by roughly ten to one. The same study estimated humans remove around 15 billion trees per year and that tree numbers have fallen by nearly half since the start of civilization.\n\nBoth figures come with wide uncertainty but the comparison holds.",
            "The tree estimate (Crowther et al., Nature 2015) used ~429,000 ground-truth plot density measurements to calibrate relationships between tree density and biome-level predictors (climate, topography, human activity), then scaled globally via remote sensing, yielding 3.04 trillion with substantial confidence intervals. The Milky Way's stellar count is inferred from its estimated mass and stellar mass function, itself uncertain by a factor of a few. Caveats: 'tree' requires a stem-diameter threshold (here >=10 cm DBH), so definitions affect the count; both numbers are order-of-magnitude estimates with large error bars; and the 15 billion/year loss and 46% historical decline are modeled figures sensitive to assumptions, not direct tallies.",
        ],
        "credibility": {
            "score": 84,
            "verified_count": 132,
            "sources": [
                {"title": "Crowther et al., 'Mapping tree density at a global scale', Nature", "url": "https://www.nature.com/articles/nature14967", "source_type": "journal"},
                {"title": "NASA: how many stars in the Milky Way?", "url": "https://asd.gsfc.nasa.gov/blueshift/index.php/2015/07/22/how-many-stars-in-the-milky-way/", "source_type": "university"},
            ],
        },
    },
    {
        "author": "raj@eureka.dev",
        "category": "Technology",
        "headline": "An AI designed a chip layout humans couldn't beat",
        "body": "Reinforcement learning now arranges chip components in hours, producing floorplans that match or exceed expert engineers who need weeks. The tools that design our computers are learning to design themselves.",
        "source_url": None,
        "levels": [
            "Reinforcement learning now arranges chip components in hours, producing floorplans that match or exceed expert engineers who need weeks. The tools that design our computers are learning to design themselves.",
            "Chip floorplanning, deciding where to place large functional blocks (macros) on silicon, has long been a slow, expert-driven bottleneck. Researchers reframed it as a reinforcement-learning problem: an agent places components one by one and is rewarded for minimizing wire length, congestion, and timing violations. Trained this way, the system generated layouts in hours that met or beat human-expert designs on those metrics, and versions of the approach were reportedly used in real Google TPU designs.\n\nIt is a concrete case of AI participating in the design of its own hardware.",
            "The method (Mirhoseini et al., Nature 2021) treats placement as a sequential decision process, using a graph neural network to encode the netlist and a policy trained via proximal policy optimization; the reward proxies final metrics (approximate wirelength and routing congestion) to stay tractable. Transfer learning across chip blocks lets the agent improve with experience. Caveats: the results were contested, a later independent study and internal disputes questioned the strength of the baselines and reproducibility, and comparisons depend heavily on which commercial EDA tools and settings define the human/automated baseline. The reward is a proxy, so downstream timing/power sign-off still requires conventional tools, and 'beating humans' claims remain an active, contentious area rather than settled fact.",
        ],
        "credibility": {
            "score": 62,
            "verified_count": 38,
            "sources": [
                {"title": "Mirhoseini et al., 'A graph placement methodology for fast chip design', Nature", "url": "https://www.nature.com/articles/s41586-021-03544-w", "source_type": "journal"},
                {"title": "Cheng et al., 'Assessing the state of ML-based chip placement' (critique)", "url": "https://arxiv.org/abs/2302.11014", "source_type": "preprint"},
            ],
        },
    },
    {
        "author": "elena@eureka.dev",
        "category": "Technology",
        "headline": "A paralyzed man typed with his brain at 90 characters a minute",
        "body": "A brain-computer interface decoded his imagined handwriting directly from motor cortex signals, hitting speeds close to able-bodied phone typing. Thought is quietly becoming an input device.",
        "source_url": None,
        "levels": [
            "A brain-computer interface decoded his imagined handwriting directly from motor cortex signals, hitting speeds close to able-bodied phone typing. Thought is quietly becoming an input device.",
            "In a 2021 study, a man paralyzed from the neck down imagined the hand movements of writing letters while implanted electrode arrays recorded activity in his motor cortex. A neural network decoded those attempted-handwriting signals into text, reaching about 90 characters per minute with high accuracy, roughly the speed of typing on a smartphone. Imagined handwriting proved easier to decode than imagined straight-line 'point and click' movements because each letter has a distinctive, temporally rich neural signature.\n\nIt showed thought-to-text can approach practical, everyday speeds.",
            "The system (Willett et al., Nature 2021) used two 96-channel intracortical microelectrode (Utah) arrays in the hand 'knob' of precentral gyrus. Neural firing patterns during attempted handwriting were fed to a recurrent neural network (RNN) trained to output character probabilities, followed by a language model for error correction, achieving ~90 cpm with ~94% raw accuracy (>99% with autocorrect). Performance depended on daily recalibration to handle signal nonstationarity. Caveats: this is a single-participant proof of concept requiring invasive surgery and tethered lab equipment; long-term electrode stability, generalization across users, and untethered clinical use remain unsolved; and decoded 'writing' is attempted movement of a paralyzed limb, not abstract mind-reading.",
        ],
        "credibility": {
            "score": 88,
            "verified_count": 147,
            "sources": [
                {"title": "Willett et al., 'High-performance brain-to-text via handwriting', Nature", "url": "https://www.nature.com/articles/s41586-021-03506-2", "source_type": "journal"},
                {"title": "Stanford Neural Prosthetics Translational Laboratory", "url": "https://nptl.stanford.edu/", "source_type": "university"},
            ],
        },
    },
    {
        "author": "raj@eureka.dev",
        "category": "Technology",
        "headline": "The first webcam was invented to watch a coffee pot",
        "body": "In 1991, Cambridge researchers pointed a camera at their lab's coffee machine so they'd know when it was full. It became the world's first live webcam feed, and streamed until 2001.",
        "source_url": None,
        "levels": [
            "In 1991, Cambridge researchers pointed a camera at their lab's coffee machine so they'd know when it was full. It became the world's first live webcam feed, and streamed until 2001.",
            "At the University of Cambridge Computer Laboratory, researchers were tired of walking to a shared coffee pot only to find it empty. In 1991 they aimed a camera at it and wrote software to serve a small, frequently updated grayscale image to their internal network, so anyone could check the pot from their desk. When it was connected to the early web in 1993, the Trojan Room coffee pot became the world's first webcam, watched by millions until it was switched off in 2001.\n\nA mundane annoyance produced a landmark of internet history.",
            "The original system captured frames via a video-capture card and distributed them using a custom client-server protocol (XCoffee) over the lab network; the 1993 web version served periodically refreshed 128x128 grayscale images through HTTP as browsers gained inline-image support. It predated streaming video, so 'live' meant a still image updated roughly every few seconds. The pot was auctioned in 2001 (bought by Der Spiegel) after the lab moved buildings. Caveats: it was not video in the modern sense but a refreshing still; 'first webcam' is a widely accepted claim but hinges on definitions of webcam versus networked camera; and details of frame rate and resolution vary slightly across retellings by the original researchers.",
        ],
        "credibility": {
            "score": 80,
            "verified_count": 88,
            "sources": [
                {"title": "University of Cambridge: the Trojan Room coffee pot", "url": "https://www.cl.cam.ac.uk/coffee/coffee.html", "source_type": "university"},
                {"title": "Stafford-Fraser, 'The life and times of the first web cam'", "url": "https://www.cl.cam.ac.uk/coffee/qsf/coffee.html", "source_type": "article"},
            ],
        },
    },
    {
        "author": "elena@eureka.dev",
        "category": "Medicine",
        "headline": "We can now grow tiny functioning brains in a dish",
        "body": "Brain organoids grown from stem cells self-organize into layered tissue and even fire coordinated electrical waves resembling a preterm infant's. They're transforming how we study autism, Zika, and Alzheimer's.",
        "source_url": None,
        "levels": [
            "Brain organoids grown from stem cells self-organize into layered tissue and even fire coordinated electrical waves resembling a preterm infant's. They're transforming how we study autism, Zika, and Alzheimer's.",
            "Brain organoids are millimeter-scale 3D tissues grown from human pluripotent stem cells. Given the right chemical cues, the cells self-organize into structures resembling regions of the developing brain, complete with layered cortical-like architecture and diverse neuron types. Some develop networks that produce coordinated electrical activity, with one study reporting oscillation patterns statistically similar to EEGs of premature infants. Because they are human and developmental, organoids let researchers model conditions like microcephaly, Zika infection, autism, and neurodegeneration in ways animal models cannot.\n\nThey are powerful but still crude approximations of a real brain.",
            "Organoids derive from induced pluripotent or embryonic stem cells guided through neural induction; 'unguided' protocols allow intrinsic self-patterning while 'guided' ones use morphogen gradients (e.g. SHH, WNT modulation) to bias toward specific regions, and region-specific organoids can be fused into 'assembloids' to study circuit formation and interneuron migration. Trujillo et al. (2019) reported nested, increasingly complex oscillatory activity on multi-electrode arrays, with a machine-learning comparison to preterm-infant EEG. Caveats: organoids lack vasculature (limiting size and causing necrotic cores), lack sensory input and a body, show batch-to-batch variability, and do not model later maturation or higher cognition; claims about 'brain-like' activity raise interpretive and ethical questions rather than implying sentience.",
        ],
        "credibility": {
            "score": 78,
            "verified_count": 96,
            "sources": [
                {"title": "Trujillo et al., 'Complex oscillatory waves in brain organoids', Cell Stem Cell", "url": "https://www.cell.com/cell-stem-cell/", "source_type": "journal"},
                {"title": "Lancaster & Knoblich, 'Cerebral organoids model human brain development', Science", "url": "https://www.science.org/", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "elena@eureka.dev",
        "category": "Medicine",
        "headline": "A gene-editing infusion lowered cholesterol in a one-time shot",
        "body": "In early trials, a single CRISPR base-editing dose switched off a liver gene and cut harmful LDL cholesterol durably. It hints at a future where some chronic conditions are edited away, not managed daily.",
        "source_url": None,
        "levels": [
            "In early trials, a single CRISPR base-editing dose switched off a liver gene and cut harmful LDL cholesterol durably. It hints at a future where some chronic conditions are edited away, not managed daily.",
            "A therapy called VERVE-101 uses CRISPR base editing to make a precise, one-time change in liver cells that switches off the PCSK9 gene. PCSK9 normally reduces the liver's ability to clear LDL ('bad') cholesterol from the blood, so silencing it lowers LDL. In an early-phase human trial, a single intravenous infusion produced substantial, durable LDL reductions in patients with an inherited high-cholesterol disorder. Unlike daily pills, the edit is meant to be permanent.\n\nIt is an early but striking demonstration of in-vivo genome editing to treat a chronic disease.",
            "Base editing uses a catalytically impaired Cas9 fused to a deaminase to convert a single DNA base (here an A-to-G change that disrupts PCSK9) without making a double-strand break, reducing indel and translocation risk versus conventional CRISPR nucleases. The editor is delivered as mRNA plus guide RNA inside lipid nanoparticles that home to hepatocytes via ApoE/LDL-receptor uptake. The Phase 1b heart-1 trial reported dose-dependent LDL lowering, some patients exceeding 50%, from a single dose. Caveats: this is small, early-phase safety data with reported serious cardiovascular events under investigation; long-term durability, off-target edits, immunogenicity, and germline-safety must be established; and because the change is permanent, adverse effects cannot be reversed by stopping treatment.",
        ],
        "credibility": {
            "score": 74,
            "verified_count": 71,
            "sources": [
                {"title": "Verve Therapeutics heart-1 Phase 1b results (AHA presentation)", "url": "https://www.vervetx.com/", "source_type": "article"},
                {"title": "Musunuru et al., 'In vivo CRISPR base editing of PCSK9', Nature", "url": "https://www.nature.com/articles/s41586-021-03534-y", "source_type": "journal"},
            ],
        },
    },
    {
        "author": "leo@eureka.dev",
        "category": "Medicine",
        "headline": "Your gut bacteria outnumber your own cells",
        "body": "You carry roughly 38 trillion bacteria, slightly more than your ~30 trillion human cells. They help train your immune system and even influence your mood through the gut-brain axis.",
        "source_url": None,
        "levels": [
            "You carry roughly 38 trillion bacteria, slightly more than your ~30 trillion human cells. They help train your immune system and even influence your mood through the gut-brain axis.",
            "For decades a '10-to-1 bacteria-to-human-cell' ratio was repeated, but a careful 2016 reestimate revised it to roughly 1.3-to-1: about 38 trillion bacteria to 30 trillion human cells (most of which are small red blood cells). The gut microbiome helps digest fiber, synthesizes vitamins, trains and regulates the immune system, and communicates with the brain via the 'gut-brain axis' through nerves, hormones, and metabolites, with links to mood and behavior.\n\nSo you are, cell for cell, roughly half microbial, and those microbes are metabolically active partners.",
            "The updated figures (Sender, Fuchs & Milo, 2016) come from summing organ-level human cell counts (dominated by ~26 trillion erythrocytes) and estimating colonic bacterial density (~10^11 per gram of content) times gut volume, yielding ~3.8 x 10^13 bacteria. Gut-brain signaling involves vagal afferents, microbial metabolites like short-chain fatty acids, tryptophan/serotonin pathways, and immune mediators; germ-free and fecal-transplant animal studies show behavioral effects, and human associations exist for mood and neurological conditions. Caveats: counts vary substantially between individuals and after each bowel movement; by mass bacteria are only ~0.2 kg, so 'outnumber' is about count, not dominance; and most gut-brain causal evidence is from animals or correlational human data, so mechanistic claims in people remain tentative.",
        ],
        "credibility": {
            "score": 83,
            "verified_count": 129,
            "sources": [
                {"title": "Sender, Fuchs & Milo, 'Revised estimates for the number of human and bacteria cells in the body', PLOS Biology", "url": "https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1002533", "source_type": "journal"},
                {"title": "NIH Human Microbiome Project", "url": "https://www.hmpdacc.org/", "source_type": "dataset"},
            ],
        },
    },
]


# Category → accent hex, shared by collections/discovery seeding.
CATEGORY_COLORS = {
    "Physics": "#3B82F6",
    "Astronomy": "#8B5CF6",
    "Biology": "#10B981",
    "Chemistry": "#F59E0B",
    "Math": "#EF4444",
    "Earth Science": "#14B8A6",
    "Technology": "#0EA5E9",
    "Medicine": "#EC4899",
}

# Mutual-follow pairs — both directions inserted so DMs are allowed.
FOLLOW_PAIRS = [
    ("mira@eureka.dev", "raj@eureka.dev"),
    ("mira@eureka.dev", "tom@eureka.dev"),
    ("leo@eureka.dev", "elena@eureka.dev"),
    ("sana@eureka.dev", "leo@eureka.dev"),
    ("raj@eureka.dev", "elena@eureka.dev"),
]

# Topic rooms; members are auto-added from users whose interests include category.
CHAT_ROOMS = [
    {
        "name": "Physics Chat",
        "category": "Physics",
        "description": "Fields, forces, and the occasional thought experiment.",
    },
    {
        "name": "Astronomy Chat",
        "category": "Astronomy",
        "description": "Telescopes, exoplanets, and late-night sky watching.",
    },
    {
        "name": "Biology Chat",
        "category": "Biology",
        "description": "Cells, evolution, and the machinery of life.",
    },
    {
        "name": "Chemistry Chat",
        "category": "Chemistry",
        "description": "Reactions, elements, and beautiful crystals.",
    },
    {
        "name": "Technology Chat",
        "category": "Technology",
        "description": "AI, chips, and the tools building the future.",
    },
]

# Realistic message text per room category (used ascending over the last day).
ROOM_MESSAGES = {
    "Physics": [
        "Anyone else following the new muon g-2 results? The tension with the Standard Model is holding.",
        "I keep coming back to how the Lamb shift is basically the vacuum poking at atoms.",
        "Superconducting qubit coherence times have jumped so fast this decade it's dizzying.",
        "Reminder that entropy isn't disorder, it's just counting microstates. Fight me.",
        "Teaching Noether's theorem today. Symmetry → conservation law never stops being magic.",
        "Ran a double-slit demo for undergrads. The gasp when the pattern appears is worth it.",
    ],
    "Astronomy": [
        "JWST dropped new spectra of a hot Jupiter — water and CO2 features are crisp.",
        "That methanol cloud near Aquila is 1000x our solar system. Space is absurd.",
        "Venus having a day longer than its year still breaks my brain a little.",
        "Anyone imaging tonight? Clear skies here and Saturn is well placed.",
        "The inner-core rotation story is wild — a planet with its own rhythm.",
        "Reminder: HD 189733b rains molten glass sideways at 5,400 mph. Cobalt blue too.",
    ],
    "Biology": [
        "330 billion cells replaced daily still feels made up, but here we are.",
        "Octopus RNA editing is the closest thing to real-time adaptation I know of.",
        "Pando being one 80,000-year-old organism reframes what 'an individual' means.",
        "Working on protein folding sims this week — AlphaFold changed everything.",
        "Tardigrades surviving raw vacuum should be impossible and yet.",
        "Gut microbiome talk today: 38 trillion bacteria steering our mood. Humbling.",
    ],
    "Chemistry": [
        "The 'glass is a slow liquid' myth needs to finally die. It's an amorphous solid.",
        "Triple point demos never get old — boiling and freezing at once.",
        "There's ~20 million tonnes of gold dissolved in the ocean. Just too dilute to grab.",
        "Running a crystallization today, fingers crossed for clean single crystals.",
        "Catalysis is basically chemistry's cheat code and I love it.",
        "Anyone have a good source on green ammonia synthesis routes?",
    ],
    "Technology": [
        "RL-designed chip floorplans matching expert engineers in hours is nuts.",
        "BCIs decoding imagined handwriting at 90 cpm — thought as an input device.",
        "First webcam watched a coffee pot in 1991. Peak engineering motivation.",
        "Playing with on-device inference this week; quantization is doing heavy lifting.",
        "Quantum error correction milestones are stacking up faster than I expected.",
        "Reminder that the tools designing our chips are learning to design themselves.",
    ],
}

# DM conversation scripts (sender is index % 2: 0 = first participant email).
DM_SCRIPTS = [
    {
        "pair": ("mira@eureka.dev", "raj@eureka.dev"),
        "messages": [
            ("mira@eureka.dev", "Did you see the trapped-ion coherence paper? 1000 seconds!"),
            ("raj@eureka.dev", "Yes! That's the number I've been waiting years for."),
            ("mira@eureka.dev", "Want to co-write a short explainer post on it?"),
            ("raj@eureka.dev", "Absolutely. I'll sketch the qubit basics tonight."),
            ("mira@eureka.dev", "Perfect, I'll cover why coherence time is the bottleneck."),
        ],
    },
    {
        "pair": ("leo@eureka.dev", "elena@eureka.dev"),
        "messages": [
            ("elena@eureka.dev", "The brain organoid firing patterns are keeping me up at night."),
            ("leo@eureka.dev", "In a good way I hope? The self-organization is remarkable."),
            ("elena@eureka.dev", "Both. Ethically it's a minefield but scientifically gorgeous."),
            ("leo@eureka.dev", "Let's grab a call this week and map out the open questions."),
        ],
    },
    {
        "pair": ("sana@eureka.dev", "leo@eureka.dev"),
        "messages": [
            ("sana@eureka.dev", "Saharan dust feeding the Amazon — I can't stop thinking about it."),
            ("leo@eureka.dev", "One desert keeping a rainforest alive. Systems thinking at planetary scale."),
            ("sana@eureka.dev", "Exactly. I'm pulling the phosphorus flux numbers now."),
            ("leo@eureka.dev", "Send them over when ready, I'd love to see the balance."),
        ],
    },
]

# Curated collections + their content items.
COLLECTIONS = [
    {
        "title": "Black Holes 101",
        "subtitle": "Everything that falls in, and the physics that bends around it.",
        "category": "Astronomy",
        "emoji": "🕳️",
        "items": [
            {
                "title": "What actually is a black hole?",
                "body": "A black hole is a region where gravity is so strong that not even light can escape past its boundary, the event horizon. It forms when a massive star collapses at the end of its life.",
                "source_url": "https://science.nasa.gov/universe/black-holes/",
            },
            {
                "title": "The event horizon is a point of no return",
                "body": "Cross the event horizon and every possible path leads inward. Nothing you do — not even moving at light speed — can bring you back out.",
                "source_url": None,
            },
            {
                "title": "Supermassive black holes anchor galaxies",
                "body": "At the heart of most large galaxies, including our Milky Way, sits a black hole millions to billions of times the Sun's mass. Ours is called Sagittarius A*.",
                "source_url": None,
            },
            {
                "title": "We photographed one in 2019",
                "body": "The Event Horizon Telescope linked observatories worldwide into an Earth-sized dish, capturing the glowing ring around M87's black hole — the first image of its kind.",
                "source_url": None,
            },
            {
                "title": "They slowly evaporate",
                "body": "Stephen Hawking showed black holes emit faint radiation and shrink over unimaginable timescales. A stellar black hole would take far longer than the age of the universe to vanish.",
                "source_url": None,
            },
        ],
    },
    {
        "title": "The Physics of Everyday Life",
        "subtitle": "The hidden mechanics behind ordinary moments.",
        "category": "Physics",
        "emoji": "⚛️",
        "items": [
            {
                "title": "Why the sky is blue",
                "body": "Air molecules scatter shorter blue wavelengths of sunlight more than red ones. That scattered blue light reaches your eyes from every direction, painting the sky.",
                "source_url": None,
            },
            {
                "title": "Why ice is slippery",
                "body": "A thin layer of liquid-like water always coats ice, even below freezing. This mobile surface layer, not just pressure, is what makes ice so slick.",
                "source_url": None,
            },
            {
                "title": "How microwaves heat your food",
                "body": "Microwaves make water molecules flip back and forth billions of times per second. That molecular jiggling is heat — which is why dry, water-free items barely warm up.",
                "source_url": None,
            },
            {
                "title": "Why a spinning bike stays upright",
                "body": "A moving bicycle resists tipping thanks to a mix of gyroscopic effects and steering geometry that automatically steers into a fall, keeping you balanced.",
                "source_url": None,
            },
        ],
    },
    {
        "title": "Mind-Bending Space Facts",
        "subtitle": "The cosmos is stranger than any fiction.",
        "category": "Astronomy",
        "emoji": "🌌",
        "items": [
            {
                "title": "A day on Venus is longer than its year",
                "body": "Venus takes 243 Earth days to spin once but only 225 to orbit the Sun. It also rotates backwards, so there the Sun rises in the west.",
                "source_url": None,
            },
            {
                "title": "There are more stars than grains of sand on Earth",
                "body": "Estimates put the observable universe at 10^22 to 10^24 stars — comfortably more than every grain of sand on every beach on our planet.",
                "source_url": None,
            },
            {
                "title": "Neutron stars are impossibly dense",
                "body": "A sugar-cube-sized piece of neutron star would weigh about a billion tonnes. They pack more than the Sun's mass into a sphere the size of a city.",
                "source_url": None,
            },
            {
                "title": "Space is completely silent",
                "body": "Sound needs a medium to travel through. In the near-vacuum of space there's nothing to carry the vibrations, so no sound can propagate.",
                "source_url": None,
            },
        ],
    },
    {
        "title": "How Your Body Works",
        "subtitle": "A guided tour of the machine you live inside.",
        "category": "Biology",
        "emoji": "🧬",
        "items": [
            {
                "title": "You replace billions of cells daily",
                "body": "Your body renews about 330 billion cells every day — roughly 1% of you. Over three months you rebuild an entirely fresh set of red blood cells.",
                "source_url": None,
            },
            {
                "title": "Your gut bacteria outnumber your cells",
                "body": "You host around 38 trillion bacteria, slightly more than your ~30 trillion human cells. They train your immune system and even sway your mood.",
                "source_url": None,
            },
            {
                "title": "Bones are stronger than steel by weight",
                "body": "Gram for gram, bone can withstand more stress than steel while staying light. It's a living composite that constantly rebuilds itself.",
                "source_url": None,
            },
            {
                "title": "Your brain runs on about 20 watts",
                "body": "Despite doing more than any supercomputer, the brain sips only around 20 watts of power — roughly a dim light bulb's worth of energy.",
                "source_url": None,
            },
        ],
    },
    {
        "title": "The Elements Around Us",
        "subtitle": "The periodic table, hiding in plain sight.",
        "category": "Chemistry",
        "emoji": "⚗️",
        "items": [
            {
                "title": "Most of you is made of stardust",
                "body": "The carbon, oxygen, and iron in your body were forged inside stars that died before the Sun formed. You are quite literally recycled star material.",
                "source_url": None,
            },
            {
                "title": "Helium can escape Earth entirely",
                "body": "Helium is so light that once released it drifts to the top of the atmosphere and leaks into space. It's a genuinely finite resource we can't easily replace.",
                "source_url": None,
            },
            {
                "title": "There's gold dissolved in the ocean",
                "body": "Seawater holds roughly 20 million tonnes of gold — but at about one gram per 100 million tonnes of water, it's far too dilute to extract profitably.",
                "source_url": None,
            },
            {
                "title": "Water's triple point balances three states",
                "body": "At about 0.01°C and low pressure, water can be solid, liquid, and gas at once. You can watch it boil and freeze in the same beaker.",
                "source_url": None,
            },
        ],
    },
]

# Daily discovery entries — today plus a few past days for the fallback path.
DISCOVERIES = [
    {
        "offset_days": 0,
        "title": "Honey never spoils",
        "body": "Archaeologists have found 3,000-year-old honey in Egyptian tombs still perfectly edible. Its low moisture and natural acidity make it nearly impossible for bacteria to survive.",
        "category": "Chemistry",
        "emoji": "🍯",
        "source_url": None,
    },
    {
        "offset_days": 1,
        "title": "A teaspoon of neutron star weighs a billion tonnes",
        "body": "Neutron stars pack more than the Sun's entire mass into a sphere the size of a city, making them the densest objects we can directly observe.",
        "category": "Astronomy",
        "emoji": "⭐",
        "source_url": None,
    },
    {
        "offset_days": 2,
        "title": "Your body glows in the dark",
        "body": "Humans emit a faint visible bioluminescence from metabolic reactions — about 1,000 times too weak for our eyes to see, but real and measurable.",
        "category": "Biology",
        "emoji": "✨",
        "source_url": None,
    },
    {
        "offset_days": 3,
        "title": "Lightning is hotter than the Sun's surface",
        "body": "A bolt of lightning can reach 30,000 kelvin — roughly five times hotter than the surface of the Sun — for a fraction of a second.",
        "category": "Physics",
        "emoji": "⚡",
        "source_url": None,
    },
]


# Followable questions across the science categories.
QUESTIONS = [
    {
        "text": "Could a Dyson sphere ever be built, and what would it take?",
        "category": "Astronomy",
        "follower_count": 342,
        "answer_count": 18,
    },
    {
        "text": "Why does quantum entanglement not allow faster-than-light communication?",
        "category": "Physics",
        "follower_count": 511,
        "answer_count": 27,
    },
    {
        "text": "How close are we to a universal cancer vaccine?",
        "category": "Medicine",
        "follower_count": 803,
        "answer_count": 41,
    },
    {
        "text": "Is there a largest prime gap, or do they grow without bound?",
        "category": "Math",
        "follower_count": 129,
        "answer_count": 9,
    },
    {
        "text": "What actually happens to a protein when it misfolds?",
        "category": "Biology",
        "follower_count": 256,
        "answer_count": 14,
    },
    {
        "text": "Can we realistically pull enough CO2 from the air to matter?",
        "category": "Earth Science",
        "follower_count": 467,
        "answer_count": 33,
    },
    {
        "text": "Why is room-temperature superconductivity so hard to achieve?",
        "category": "Chemistry",
        "follower_count": 388,
        "answer_count": 22,
    },
    {
        "text": "Will large language models ever truly understand, or just predict?",
        "category": "Technology",
        "follower_count": 921,
        "answer_count": 58,
    },
    {
        "text": "How do we know the age of the universe so precisely?",
        "category": "Astronomy",
        "follower_count": 274,
        "answer_count": 16,
    },
    {
        "text": "Could we ever reverse aging at the cellular level?",
        "category": "Medicine",
        "follower_count": 655,
        "answer_count": 37,
    },
]

# Study circles (capacity always 20). member_count is the target size the seeder
# fills toward using the seeded accounts (topped up with synthetic member ids).
STUDY_CIRCLES = [
    {
        "name": "Exoplanet Hunters",
        "topic": "Detecting and characterizing worlds beyond the solar system",
        "category": "Astronomy",
        "description": "We read transit and radial-velocity papers together and swap JWST spectra. Beginners welcome.",
        "member_count": 12,
    },
    {
        "name": "Quantum Reading Group",
        "topic": "Foundations and applications of quantum information",
        "category": "Physics",
        "description": "Working through qubits, error correction, and the occasional Bell-inequality argument.",
        "member_count": 20,  # intentionally full to test the capacity cap
    },
    {
        "name": "Protein Folding Club",
        "topic": "Structure prediction from AlphaFold to the wet lab",
        "category": "Biology",
        "description": "Half computational, half biochemistry. We pick one structure a week and dissect it.",
        "member_count": 8,
    },
    {
        "name": "Climate Data Circle",
        "topic": "Reading the planet through ice cores and satellite records",
        "category": "Earth Science",
        "description": "Hands-on with real datasets. Bring questions about carbon, dust, and ocean cycles.",
        "member_count": 15,
    },
    {
        "name": "Proof Workshop",
        "topic": "Number theory and combinatorics problem solving",
        "category": "Math",
        "description": "We tackle a hard problem each session and present partial proofs. Chalk optional.",
        "member_count": 5,
    },
    {
        "name": "ML Systems Study",
        "topic": "How large models are trained, served, and made efficient",
        "category": "Technology",
        "description": "From attention internals to quantization and on-device inference. Practical and paper-driven.",
        "member_count": 18,
    },
]


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db]

    print(f"Seeding database '{settings.mongo_db}' at {settings.mongo_uri} ...")

    for coll in [
        "users",
        "posts",
        "comments",
        "votes",
        "bookmarks",
        "notifications",
        "chat_rooms",
        "room_members",
        "messages",
        "follows",
        "dm_threads",
        "direct_messages",
        "collections",
        "curated_content",
        "daily_discovery",
        "questions",
        "study_circles",
    ]:
        await db[coll].drop()

    # Indexes (mirrors app.database so a fresh seed works standalone).
    await db.users.create_index("email", unique=True)
    await db.posts.create_index([("created_at", -1)])
    await db.votes.create_index([("post_id", 1), ("user_id", 1)], unique=True)
    await db.bookmarks.create_index([("user_id", 1), ("post_id", 1)], unique=True)
    await db.messages.create_index([("room_id", 1), ("created_at", 1)])
    await db.room_members.create_index([("room_id", 1), ("user_id", 1)], unique=True)
    await db.direct_messages.create_index([("thread_id", 1), ("created_at", 1)])
    await db.dm_threads.create_index("participants")
    await db.follows.create_index(
        [("follower_id", 1), ("following_id", 1)], unique=True
    )
    await db.curated_content.create_index([("collection_id", 1), ("order", 1)])
    await db.daily_discovery.create_index("date")
    await db.questions.create_index([("created_at", -1)])
    await db.study_circles.create_index([("created_at", -1)])

    now = datetime.now(timezone.utc)
    email_to_id: dict[str, object] = {}
    password_hash = hash_password(SEED_PASSWORD)

    for i, acc in enumerate(ACCOUNTS):
        doc = {
            "email": acc["email"],
            "name": acc["name"],
            "password_hash": password_hash,
            "bio": acc["bio"],
            "interests": acc["interests"],
            "avatar_color": AVATAR_COLORS[i % len(AVATAR_COLORS)],
            "created_at": now - timedelta(days=random.randint(120, 400)),
        }
        result = await db.users.insert_one(doc)
        email_to_id[acc["email"]] = result.inserted_id
    print(f"  Inserted {len(ACCOUNTS)} accounts (password for all: '{SEED_PASSWORD}').")

    post_ids = []
    for i, post in enumerate(POSTS):
        author_id = email_to_id[post["author"]]
        # Spread timestamps over the last ~10 days so the feed looks organic.
        created = now - timedelta(
            hours=i * 9 + random.randint(0, 6), minutes=random.randint(0, 59)
        )
        doc = {
            "headline": post["headline"],
            "body": post["body"],
            "category": post["category"],
            "source_url": post.get("source_url"),
            "author_id": author_id,
            "created_at": created,
            "upvotes": random.randint(3, 240),
            "comment_count": 0,
            "levels": post["levels"],
            "credibility": post["credibility"],
        }
        result = await db.posts.insert_one(doc)
        post_ids.append((result.inserted_id, author_id, created))
    print(f"  Inserted {len(POSTS)} posts.")

    # Sprinkle a few comments so detail views aren't empty.
    sample_comments = [
        "This is wild. Do we know the mechanism yet?",
        "Saved. I'm going to be thinking about this all day.",
        "Wait, really? That reframes so much for me.",
        "Source is solid. I looked into this last year.",
        "Okay this is my new favourite fact.",
        "How reproducible is the result?",
        "Beautifully put. Science communication done right.",
    ]
    comment_total = 0
    all_ids = list(email_to_id.values())
    for post_id, author_id, created in post_ids:
        for _ in range(random.randint(0, 3)):
            commenter = random.choice(all_ids)
            c_created = created + timedelta(hours=random.randint(1, 40))
            await db.comments.insert_one(
                {
                    "post_id": post_id,
                    "author_id": commenter,
                    "body": random.choice(sample_comments),
                    "parent_id": None,
                    "created_at": min(c_created, now),
                }
            )
            comment_total += 1
        await db.posts.update_one(
            {"_id": post_id},
            {"$set": {"comment_count": await db.comments.count_documents({"post_id": post_id})}},
        )
    print(f"  Inserted {comment_total} comments.")

    # ---------- Follows (mutual graph so DMs work) ----------
    follow_total = 0
    for a_email, b_email in FOLLOW_PAIRS:
        a_id, b_id = email_to_id[a_email], email_to_id[b_email]
        for follower, following in [(a_id, b_id), (b_id, a_id)]:
            await db.follows.insert_one(
                {
                    "follower_id": follower,
                    "following_id": following,
                    "created_at": now - timedelta(days=random.randint(10, 90)),
                }
            )
            follow_total += 1
    print(f"  Inserted {follow_total} follow edges ({len(FOLLOW_PAIRS)} mutual pairs).")

    # ---------- Chat rooms + members + messages ----------
    interests_by_id = {email_to_id[a["email"]]: a["interests"] for a in ACCOUNTS}
    room_total = 0
    member_total = 0
    room_msg_total = 0
    for room in CHAT_ROOMS:
        room_doc = {
            "name": room["name"],
            "category": room["category"],
            "description": room["description"],
            "created_at": now - timedelta(days=random.randint(20, 60)),
        }
        room_result = await db.chat_rooms.insert_one(room_doc)
        room_id = room_result.inserted_id
        room_total += 1

        members = [
            uid
            for uid, interests in interests_by_id.items()
            if room["category"] in interests
        ]
        # Ensure the room has at least a couple of members even if interests miss.
        if len(members) < 2:
            members = list(email_to_id.values())[:3]
        for uid in members:
            # last_read a bit in the past so some unread shows up.
            await db.room_members.insert_one(
                {
                    "room_id": room_id,
                    "user_id": uid,
                    "joined_at": now - timedelta(days=random.randint(5, 20)),
                    "last_read_at": now - timedelta(hours=random.randint(3, 30)),
                }
            )
            member_total += 1

        # 4-6 sample messages spread ascending over the last day.
        texts = ROOM_MESSAGES[room["category"]]
        count = random.randint(4, min(6, len(texts)))
        chosen = texts[:count]
        base = now - timedelta(hours=24)
        for j, text in enumerate(chosen):
            author = members[j % len(members)]
            created = base + timedelta(
                minutes=int(j * (24 * 60 / max(count, 1))) + random.randint(0, 30)
            )
            await db.messages.insert_one(
                {
                    "room_id": room_id,
                    "author_id": author,
                    "body": text,
                    "created_at": min(created, now),
                }
            )
            room_msg_total += 1
    print(
        f"  Inserted {room_total} chat rooms, {member_total} memberships, "
        f"{room_msg_total} room messages."
    )

    # ---------- DM threads + direct messages ----------
    thread_total = 0
    dm_total = 0
    for script in DM_SCRIPTS:
        a_email, b_email = script["pair"]
        a_id, b_id = email_to_id[a_email], email_to_id[b_email]
        participants = sorted([a_id, b_id], key=lambda x: str(x))

        thread_doc = {
            "participants": participants,
            "created_at": now - timedelta(days=random.randint(2, 10)),
            "last_message": None,
            "last_message_at": None,
        }
        thread_result = await db.dm_threads.insert_one(thread_doc)
        thread_id = thread_result.inserted_id
        thread_total += 1

        msgs = script["messages"]
        base = now - timedelta(hours=random.randint(6, 20))
        last_body = None
        last_at = None
        for k, (sender_email, body) in enumerate(msgs):
            created = base + timedelta(minutes=k * random.randint(3, 12))
            created = min(created, now)
            # Leave the latest 1-2 incoming (not from first author) unread.
            is_incoming = sender_email != msgs[-1][0]
            read = True
            if k >= len(msgs) - 2 and is_incoming:
                read = False
            await db.direct_messages.insert_one(
                {
                    "thread_id": thread_id,
                    "sender_id": email_to_id[sender_email],
                    "body": body,
                    "created_at": created,
                    "read": read,
                }
            )
            dm_total += 1
            last_body, last_at = body, created
        await db.dm_threads.update_one(
            {"_id": thread_id},
            {"$set": {"last_message": last_body, "last_message_at": last_at}},
        )
    print(f"  Inserted {thread_total} DM threads, {dm_total} direct messages.")

    # ---------- Collections + curated content ----------
    coll_total = 0
    content_total = 0
    for coll in COLLECTIONS:
        coll_doc = {
            "title": coll["title"],
            "subtitle": coll["subtitle"],
            "category": coll["category"],
            "accent": CATEGORY_COLORS[coll["category"]],
            "emoji": coll["emoji"],
            "created_at": now - timedelta(days=random.randint(1, 30)),
        }
        coll_result = await db.collections.insert_one(coll_doc)
        coll_id = coll_result.inserted_id
        coll_total += 1
        for order, item in enumerate(coll["items"]):
            await db.curated_content.insert_one(
                {
                    "collection_id": coll_id,
                    "title": item["title"],
                    "body": item["body"],
                    "source_url": item.get("source_url"),
                    "order": order,
                    "category": coll["category"],
                }
            )
            content_total += 1
    print(f"  Inserted {coll_total} collections, {content_total} curated items.")

    # ---------- Daily discoveries ----------
    disc_total = 0
    for disc in DISCOVERIES:
        date_str = (now - timedelta(days=disc["offset_days"])).strftime("%Y-%m-%d")
        await db.daily_discovery.insert_one(
            {
                "date": date_str,
                "title": disc["title"],
                "body": disc["body"],
                "category": disc["category"],
                "source_url": disc.get("source_url"),
                "emoji": disc["emoji"],
            }
        )
        disc_total += 1
    print(f"  Inserted {disc_total} daily discoveries.")

    # ---------- Followable questions ----------
    first_user_id = email_to_id[ACCOUNTS[0]["email"]]
    other_ids = [uid for uid in email_to_id.values() if uid != first_user_id]
    question_total = 0
    followed_by_first = 0
    # Have the first user follow ~3 questions (indices chosen deterministically).
    first_follows = {0, 2, 7}
    for i, q in enumerate(QUESTIONS):
        target = q["follower_count"]
        # Build a followers list of the requested size: real seeded users first,
        # then synthetic ObjectIds so follower_count reflects the desired number.
        followers: list[object] = []
        if i in first_follows:
            followers.append(first_user_id)
            followed_by_first += 1
        for uid in random.sample(other_ids, k=min(len(other_ids), 2)):
            if uid not in followers:
                followers.append(uid)
        while len(followers) < target:
            from bson import ObjectId

            followers.append(ObjectId())
        await db.questions.insert_one(
            {
                "text": q["text"],
                "category": q["category"],
                "followers": followers,
                "answer_count": q["answer_count"],
                "created_at": now - timedelta(days=i, hours=random.randint(0, 20)),
            }
        )
        question_total += 1
    print(
        f"  Inserted {question_total} questions "
        f"(first user follows {followed_by_first})."
    )

    # ---------- Study circles ----------
    circle_total = 0
    joined_by_first = 0
    # First user is a member of ~2 circles (deterministic indices).
    first_member_of = {0, 4}
    for i, c in enumerate(STUDY_CIRCLES):
        target = c["member_count"]
        members: list[object] = []
        if i in first_member_of:
            members.append(first_user_id)
            joined_by_first += 1
        for uid in random.sample(other_ids, k=min(len(other_ids), target - len(members))):
            if uid not in members:
                members.append(uid)
        while len(members) < target:
            from bson import ObjectId

            members.append(ObjectId())
        members = members[:20]  # never exceed capacity
        await db.study_circles.insert_one(
            {
                "name": c["name"],
                "topic": c["topic"],
                "category": c["category"],
                "description": c["description"],
                "members": members,
                "capacity": 20,
                "created_at": now - timedelta(days=i * 2, hours=random.randint(0, 20)),
            }
        )
        circle_total += 1
    print(
        f"  Inserted {circle_total} study circles "
        f"(first user is a member of {joined_by_first})."
    )

    client.close()
    print("Done. The feed is alive.")


if __name__ == "__main__":
    asyncio.run(main())
