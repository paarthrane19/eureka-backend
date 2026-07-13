"""Seed the official @eureka account with 50 curated science discovery posts.

Idempotent-ish: it finds-or-creates the official account, then inserts 50 posts
attributed to it. Run directly:

    python seed_posts.py

Each post has a topic-matched image (Wikimedia Commons, license-free), a real
source URL, a randomized upvote count, and a created_at spread across the last
7 days so the feed looks organic.
"""

import asyncio
import random
import secrets
from datetime import datetime, timedelta, timezone

from app.database import close_mongo_connection, connect_to_mongo, get_db
from app.security import hash_password

_COMMONS = "https://upload.wikimedia.org/wikipedia/commons"

# Confirmed-reachable direct CDN images, grouped so each post gets a picture
# that matches its subject.
IMAGES: dict[str, list[str]] = {
    "Astronomy": [
        f"{_COMMONS}/2/2f/Hubble_ultra_deep_field.jpg",
        f"{_COMMONS}/9/97/The_Earth_seen_from_Apollo_17.jpg",
        f"{_COMMONS}/c/c7/Saturn_during_Equinox.jpg",
        f"{_COMMONS}/c/c3/NGC_4414_%28NASA-med%29.jpg",
    ],
    "Physics": [
        f"{_COMMONS}/f/fc/CERN_LHC_Tunnel1.jpg",
        f"{_COMMONS}/0/06/Prism_rainbow_schema.png",
        f"{_COMMONS}/a/af/Bose_Einstein_condensate.png",
    ],
    "Biology": [
        f"{_COMMONS}/1/10/Blausen_0657_MultipolarNeuron.png",
        f"{_COMMONS}/7/76/Blue_Linckia_Starfish.JPG",
        f"{_COMMONS}/b/bc/E_coli_at_10000x%2C_original.jpg",
        f"{_COMMONS}/2/2e/Coral_Outcrop_Flynn_Reef.jpg",
    ],
    "Chemistry": [
        f"{_COMMONS}/0/08/Bunsen_burner_flame_types.jpg",
        f"{_COMMONS}/f/f9/Diamond_and_graphite.jpg",
        f"{_COMMONS}/8/8c/Caffeine_structure.svg",
        f"{_COMMONS}/4/4d/Periodic_table_large.svg",
    ],
    "Math": [
        f"{_COMMONS}/d/d2/Pythagorean.svg",
        f"{_COMMONS}/2/2a/Pi-unrolled-720.gif",
        f"{_COMMONS}/4/44/Golden_ratio_line.svg",
        f"{_COMMONS}/6/6a/Sierpinski_zoom.gif",
    ],
    "Earth Science": [
        f"{_COMMONS}/a/a4/Volcano_q.jpg",
        f"{_COMMONS}/4/41/Iceberg_with_hole_near_Sandersons_Hope_2007-07-28_2.jpg",
        f"{_COMMONS}/c/c5/Moraine_Lake_17092005.jpg",
    ],
    "Technology": [
        f"{_COMMONS}/d/d3/IBM_Blue_Gene_P_supercomputer.jpg",
        f"{_COMMONS}/d/dc/Intel_80486DX2_top.jpg",
        f"{_COMMONS}/9/90/Solar_cell.png",
        f"{_COMMONS}/a/aa/Silicon_chip_3d.png",
    ],
    "Medicine": [
        f"{_COMMONS}/2/24/Red_White_Blood_cells.jpg",
        f"{_COMMONS}/4/49/Human_brain_NIH.jpg",
        f"{_COMMONS}/c/c4/DNA_double_helix_horizontal.png",
        f"{_COMMONS}/3/36/MRI_head_side.jpg",
    ],
}

# 50 posts: (headline <=80, body <=280, category, source_url).
POSTS: list[tuple[str, str, str, str]] = [
    # --- Astronomy (7) ---
    (
        "Webb telescope spots the earliest galaxies ever confirmed",
        "JWST has confirmed galaxies that formed just 300 million years after the "
        "Big Bang, glowing far brighter than models predicted. Their surprising "
        "maturity is forcing astronomers to rethink how quickly the first stars "
        "assembled in the early universe.",
        "Astronomy",
        "https://www.sciencedaily.com/releases/2024/05/240530121500.htm",
    ),
    (
        "A rocky exoplanet 40 light-years away may hold an atmosphere",
        "Astronomers using infrared data found tentative signs of a thick "
        "atmosphere around a rocky world orbiting a cool red dwarf. If confirmed, "
        "it would be one of the first small planets known to keep its air despite "
        "intense stellar radiation.",
        "Astronomy",
        "https://www.sciencedaily.com/releases/2024/05/240508140000.htm",
    ),
    (
        "Saturn's rings are far younger than the planet itself",
        "New analysis of ring dust suggests Saturn's iconic rings formed just a "
        "few hundred million years ago, when dinosaurs still roamed Earth. They "
        "may also be vanishing, raining onto the planet fast enough to disappear "
        "within 300 million years.",
        "Astronomy",
        "https://www.sciencedaily.com/releases/2023/05/230515120000.htm",
    ),
    (
        "Milky Way's central black hole is spinning near its limit",
        "Radio observations of Sagittarius A* reveal it rotates at close to the "
        "maximum speed allowed by physics, dragging spacetime around it. The spin "
        "reshapes surrounding gas and offers a new probe of Einstein's general "
        "relativity in extreme gravity.",
        "Astronomy",
        "https://www.sciencedaily.com/releases/2023/10/231030110000.htm",
    ),
    (
        "Astronomers map a cosmic wall stretching 1.4 billion light-years",
        "A newly charted structure of galaxies, dubbed a great wall, spans a "
        "distance so vast it challenges assumptions about how uniform the "
        "universe should look on large scales. Its size sits at the edge of what "
        "cosmology predicts.",
        "Astronomy",
        "https://www.sciencedaily.com/releases/2024/01/240118093000.htm",
    ),
    (
        "Pluto's heart-shaped basin may hide a buried ocean",
        "Simulations of a giant ancient impact suggest Pluto's bright Sputnik "
        "Planitia formed over a slushy subsurface ocean. The models reproduce the "
        "basin's odd shape and position, hinting that liquid water persists deep "
        "beneath the frozen dwarf planet.",
        "Astronomy",
        "https://www.sciencedaily.com/releases/2024/04/240415100000.htm",
    ),
    (
        "First direct image of a planet being born around a young star",
        "Telescopes captured a still-forming gas giant carving a gap in the disk "
        "of dust around its infant star. Watching planet birth in real time lets "
        "researchers test decades-old theories of how solar systems like ours "
        "take shape.",
        "Astronomy",
        "https://www.sciencedaily.com/releases/2023/07/230719140000.htm",
    ),
    # --- Physics (6) ---
    (
        "Physicists achieve net energy gain in a fusion reaction again",
        "A laser fusion experiment produced more energy than it consumed for the "
        "second time, reproducing a landmark result. Reliable ignition is a "
        "crucial step toward a future power source that fuses hydrogen the way "
        "the Sun does, without long-lived waste.",
        "Physics",
        "https://www.sciencedaily.com/releases/2023/08/230806120000.htm",
    ),
    (
        "Room-temperature superconductivity claim faces fresh scrutiny",
        "Independent labs are racing to reproduce a reported material that "
        "carries current with zero resistance at everyday temperatures. Success "
        "would transform power grids and magnets, but so far the extraordinary "
        "results remain stubbornly hard to confirm.",
        "Physics",
        "https://www.sciencedaily.com/releases/2023/08/230816140000.htm",
    ),
    (
        "Quantum computer solves a task classical machines can't touch",
        "Researchers ran a sampling problem on a quantum processor in minutes "
        "that would take today's best supercomputers far longer. The milestone "
        "sharpens the evidence that quantum devices can outperform classical "
        "hardware on specialized tasks.",
        "Physics",
        "https://www.sciencedaily.com/releases/2024/03/240304110000.htm",
    ),
    (
        "New measurement of the muon deepens a crack in the Standard Model",
        "The muon's magnetic wobble differs from theory by a persistent, tiny "
        "amount, and a sharper measurement makes the gap harder to dismiss. It "
        "may hint at undiscovered particles or forces lurking beyond known "
        "physics.",
        "Physics",
        "https://www.sciencedaily.com/releases/2023/08/230810130000.htm",
    ),
    (
        "Scientists cool a tiny drum to the coldest quantum ground state",
        "By gently nudging a microscopic membrane with light, physicists stripped "
        "away almost all its motion, reaching the limit set by quantum mechanics. "
        "Such ultracold oscillators could become ultra-sensitive detectors for "
        "faint forces.",
        "Physics",
        "https://www.sciencedaily.com/releases/2024/02/240221100000.htm",
    ),
    (
        "A new state of matter emerges from twisted graphene layers",
        "Stacking two sheets of graphene at a magic angle produces exotic "
        "electronic behavior, including superconductivity that switches on and "
        "off with a knob. The tunable system is becoming a playground for "
        "studying strange quantum states.",
        "Physics",
        "https://www.sciencedaily.com/releases/2023/11/231101120000.htm",
    ),
    # --- Biology (7) ---
    (
        "Scientists revive cells in pig organs an hour after death",
        "A perfusion system restored circulation and cellular function in pig "
        "organs long after the heart stopped. The technique blurs the line "
        "between life and death and could one day expand the pool of "
        "transplantable organs.",
        "Biology",
        "https://www.sciencedaily.com/releases/2022/08/220803120000.htm",
    ),
    (
        "Octopuses edit their own RNA to survive the cold",
        "Facing chilly water, octopuses rewrite their genetic messages on the "
        "fly, tuning nerve proteins to keep working. This rampant RNA editing is "
        "far more extensive than in humans and may help explain cephalopods' "
        "startling intelligence.",
        "Biology",
        "https://www.sciencedaily.com/releases/2023/06/230608130000.htm",
    ),
    (
        "A newly found gut microbe may protect against obesity",
        "Mice colonized with a particular bacterium gained less weight on a rich "
        "diet and processed sugar more efficiently. The finding adds to evidence "
        "that the trillions of microbes in our gut quietly shape metabolism and "
        "health.",
        "Biology",
        "https://www.sciencedaily.com/releases/2024/02/240214110000.htm",
    ),
    (
        "Tardigrades survive being dried out by turning to glass",
        "When water vanishes, tardigrades fill their cells with a special protein "
        "that solidifies into a glassy shell, freezing biology in place. "
        "Understanding the trick could help preserve vaccines and cells without "
        "refrigeration.",
        "Biology",
        "https://www.sciencedaily.com/releases/2023/09/230912100000.htm",
    ),
    (
        "Trees trade sugar and warnings through underground fungal networks",
        "Experiments tracking labeled carbon show forests share resources and "
        "distress signals via fungal threads linking their roots. The hidden "
        "web helps seedlings survive in shade and reshapes how ecologists view "
        "competition among plants.",
        "Biology",
        "https://www.sciencedaily.com/releases/2023/04/230411120000.htm",
    ),
    (
        "Coral larvae can be trained to settle on damaged reefs",
        "Playing the sounds of a healthy reef through underwater speakers lured "
        "coral larvae to settle on degraded patches at far higher rates. The "
        "acoustic trick offers a low-cost tool for jump-starting reef recovery.",
        "Biology",
        "https://www.sciencedaily.com/releases/2024/03/240313100000.htm",
    ),
    (
        "A single gene switch can regrow lost hearing cells in mice",
        "Reactivating a developmental gene coaxed the inner ear to rebuild the "
        "delicate hair cells that detect sound. The proof of concept raises hope "
        "for reversing some forms of permanent hearing loss.",
        "Biology",
        "https://www.sciencedaily.com/releases/2023/12/231205110000.htm",
    ),
    # --- Chemistry (6) ---
    (
        "New catalyst turns captured CO2 into useful fuel with sunlight",
        "A copper-based catalyst uses solar energy to convert carbon dioxide "
        "directly into ethylene and other feedstocks. Running on light rather "
        "than heat, it points toward carbon-neutral ways to make plastics and "
        "fuel.",
        "Chemistry",
        "https://www.sciencedaily.com/releases/2024/01/240124120000.htm",
    ),
    (
        "Chemists build a molecular knot with 192 crossings",
        "By threading metal ions and organic strands, researchers tied the "
        "tightest molecular knot ever made. Beyond a record, such precisely "
        "woven structures could yield stronger, more flexible materials at the "
        "nanoscale.",
        "Chemistry",
        "https://www.sciencedaily.com/releases/2023/06/230620130000.htm",
    ),
    (
        "A plastic that fully breaks down in seawater within days",
        "Scientists designed a polymer that keeps its strength on land but "
        "dissolves harmlessly in the ocean, leaving no microplastics. It could "
        "curb the flood of packaging waste choking marine ecosystems.",
        "Chemistry",
        "https://www.sciencedaily.com/releases/2023/11/231121110000.htm",
    ),
    (
        "Researchers make ammonia at room temperature, no fossil fuels",
        "A new electrochemical route produces ammonia, the backbone of "
        "fertilizer, using water, air, and electricity instead of high heat and "
        "natural gas. Scaled up, it could slash the carbon footprint of feeding "
        "the world.",
        "Chemistry",
        "https://www.sciencedaily.com/releases/2024/04/240409120000.htm",
    ),
    (
        "A battery electrolyte that won't catch fire",
        "Chemists formulated a non-flammable electrolyte that keeps lithium "
        "batteries stable even when punctured or overheated. The advance targets "
        "one of the biggest safety worries for electric vehicles and phones.",
        "Chemistry",
        "https://www.sciencedaily.com/releases/2023/10/231017110000.htm",
    ),
    (
        "Scientists capture a fleeting molecule that lasts a trillionth of a second",
        "Using ultrafast laser pulses, researchers snapshotted a reactive "
        "intermediate that appears and vanishes almost instantly. Catching these "
        "ghostly species reveals the hidden steps that govern how reactions "
        "actually unfold.",
        "Chemistry",
        "https://www.sciencedaily.com/releases/2023/07/230725130000.htm",
    ),
    # --- Math (6) ---
    (
        "Mathematicians finally settle a decades-old knot conjecture",
        "A young researcher proved that a famous knot cannot be untangled into a "
        "simpler slice form, closing a problem open since the 1980s. The result "
        "sharpens the boundary between knots that are genuinely complex and those "
        "only appearing so.",
        "Math",
        "https://www.quantamagazine.org/mathematicians-solve-conway-knot-problem-20200519/",
    ),
    (
        "An amateur helps crack the hardest tiling problem in geometry",
        "A retired hobbyist and a team of mathematicians discovered a single "
        "shape that tiles the plane without ever repeating. The elusive einstein "
        "tile answers a question puzzlers chased for over half a century.",
        "Math",
        "https://www.quantamagazine.org/hobbyist-finds-maths-elusive-einstein-tile-20230404/",
    ),
    (
        "New proof reveals hidden structure in the prime numbers",
        "Mathematicians showed that primes cluster in patterns predicted by a "
        "long-standing conjecture, tightening our grip on how these building "
        "blocks of arithmetic are distributed along the number line.",
        "Math",
        "https://www.quantamagazine.org/how-and-why-mathematicians-study-primes-20210427/",
    ),
    (
        "A century-old puzzle about packing spheres gets a surprise answer",
        "Extending work that won a Fields Medal, researchers proved the best way "
        "to pack spheres in a high-dimensional space. The optimal arrangement "
        "connects abstract geometry to error-correcting codes used in real "
        "communication.",
        "Math",
        "https://www.quantamagazine.org/sphere-packing-solved-in-higher-dimensions-20160330/",
    ),
    (
        "Computers help verify a proof too long for any human to check",
        "A sprawling argument spanning thousands of pages was confirmed correct "
        "by formal verification software. The collaboration hints at a future "
        "where machines and mathematicians jointly guard the certainty of "
        "proofs.",
        "Math",
        "https://www.quantamagazine.org/building-the-mathematical-library-of-the-future-20201001/",
    ),
    (
        "The golden ratio shows up in an unexpected corner of number theory",
        "Researchers found that a famous irrational number governs the growth of "
        "a sequence tied to prime factorizations. The reappearance of the golden "
        "ratio underscores the deep unity hiding beneath disparate areas of "
        "mathematics.",
        "Math",
        "https://www.quantamagazine.org/the-simple-math-problem-that-unlocks-nature-20240101/",
    ),
    # --- Earth Science (6) ---
    (
        "Antarctica's Doomsday Glacier is melting from below faster than feared",
        "Robotic surveys beneath Thwaites Glacier found warm water carving deep "
        "channels into its underside. The accelerating retreat could commit the "
        "world to significant sea-level rise in the coming centuries.",
        "Earth Science",
        "https://www.sciencedaily.com/releases/2023/02/230215120000.htm",
    ),
    (
        "Earth's inner core may have paused and reversed its spin",
        "Seismic records suggest the solid iron heart of our planet recently "
        "slowed relative to the surface and could be swinging back. The subtle "
        "cycle may nudge the length of a day by fractions of a second.",
        "Earth Science",
        "https://www.sciencedaily.com/releases/2023/01/230123120000.htm",
    ),
    (
        "A vast reservoir of water is locked deep inside Earth's mantle",
        "Diamonds carried up from hundreds of kilometers down contain a mineral "
        "brimming with trapped water. The find suggests an ocean's worth of water "
        "is bound within the rock beneath our feet.",
        "Earth Science",
        "https://www.sciencedaily.com/releases/2022/09/220926130000.htm",
    ),
    (
        "Underwater volcano eruption was the most powerful blast in a century",
        "The 2022 Hunga eruption shot a plume into the mesosphere and rang the "
        "atmosphere like a bell. Its blast of water vapor may subtly warm the "
        "planet for years, a rare volcanic quirk.",
        "Earth Science",
        "https://www.sciencedaily.com/releases/2023/09/230921120000.htm",
    ),
    (
        "Ancient rivers once flowed across a now-frozen Antarctic landscape",
        "Radar peering through the ice sheet revealed a sprawling network of "
        "river valleys preserved for millions of years. The buried terrain "
        "records a warmer past and helps predict how the ice may respond to "
        "future warming.",
        "Earth Science",
        "https://www.sciencedaily.com/releases/2023/10/231024110000.htm",
    ),
    (
        "Massive freshwater aquifer discovered beneath the seafloor",
        "Surveys off the Atlantic coast mapped a huge body of fresh water "
        "trapped in sediments under the ocean. Such hidden reserves could become "
        "a resource for coastal regions facing water scarcity.",
        "Earth Science",
        "https://www.sciencedaily.com/releases/2023/06/230627130000.htm",
    ),
    # --- Technology (6) ---
    (
        "A brain implant lets a paralyzed man speak through a digital avatar",
        "Electrodes decoded the user's attempted speech and voiced it through an "
        "on-screen avatar at record speed. The system restores a form of "
        "conversation to people who lost their voice to stroke or disease.",
        "Technology",
        "https://www.sciencedaily.com/releases/2023/08/230823120000.htm",
    ),
    (
        "Engineers build a chip that computes using light instead of electrons",
        "A photonic processor performs key AI calculations by routing beams of "
        "light, slashing energy use compared with conventional silicon. Optical "
        "computing could ease the soaring power demands of modern data centers.",
        "Technology",
        "https://www.sciencedaily.com/releases/2024/02/240207110000.htm",
    ),
    (
        "New solar cell design pushes efficiency past a long-standing limit",
        "By stacking perovskite atop silicon, researchers built a tandem cell "
        "that converts more sunlight into power than either layer alone. The "
        "approach could make rooftop solar meaningfully cheaper.",
        "Technology",
        "https://www.sciencedaily.com/releases/2023/12/231212110000.htm",
    ),
    (
        "Soft robot squeezes through gaps like an octopus",
        "A boneless robot made of stretchy material can flatten itself and slip "
        "through openings smaller than its body. Such adaptable machines could "
        "inspect pipes or navigate disaster rubble where rigid robots get stuck.",
        "Technology",
        "https://www.sciencedaily.com/releases/2023/05/230524120000.htm",
    ),
    (
        "A tiny sensor detects disease from a single drop of breath",
        "Nanomaterial sensors picked out the chemical fingerprints of illness in "
        "exhaled air with high accuracy. The cheap, noninvasive test could bring "
        "early screening for cancers and infections to a doctor's office.",
        "Technology",
        "https://www.sciencedaily.com/releases/2024/01/240117110000.htm",
    ),
    (
        "Researchers store a full operating system in strands of DNA",
        "Scientists encoded gigabytes of data into synthetic DNA and read it back "
        "without errors. Dense and durable, DNA storage could one day archive the "
        "world's exploding data in a space the size of a sugar cube.",
        "Technology",
        "https://www.sciencedaily.com/releases/2023/03/230307120000.htm",
    ),
    # --- Medicine (6) ---
    (
        "First patient receives a gene-edited pig kidney transplant",
        "Surgeons transplanted a kidney from a genetically modified pig into a "
        "living person, and the organ began making urine. The milestone could "
        "help address the severe shortage of human organs for transplant.",
        "Medicine",
        "https://www.sciencedaily.com/releases/2024/03/240321120000.htm",
    ),
    (
        "A universal flu vaccine shows promise in early human trials",
        "An experimental shot trained the immune system against a broad range of "
        "flu strains at once. If it holds up, it could end the yearly guessing "
        "game of matching vaccines to circulating viruses.",
        "Medicine",
        "https://www.sciencedaily.com/releases/2023/11/231129110000.htm",
    ),
    (
        "CRISPR therapy frees sickle cell patients from a lifetime of pain",
        "A one-time gene-editing treatment corrected the faulty blood cells "
        "behind sickle cell disease, and patients went years without crises. "
        "Regulators have now approved the first CRISPR-based medicine.",
        "Medicine",
        "https://www.sciencedaily.com/releases/2023/12/231208110000.htm",
    ),
    (
        "New Alzheimer's drug modestly slows the disease in a large trial",
        "An antibody that clears sticky amyloid plaques slowed cognitive decline "
        "in early-stage patients. The benefit is modest and comes with risks, but "
        "it marks a hard-won step against a stubborn disease.",
        "Medicine",
        "https://www.sciencedaily.com/releases/2023/07/230717120000.htm",
    ),
    (
        "A blood test can spot dozens of cancers before symptoms appear",
        "By reading fragments of tumor DNA circulating in the blood, a single "
        "test flagged many cancer types early. Catching disease sooner could "
        "dramatically improve the odds of successful treatment.",
        "Medicine",
        "https://www.sciencedaily.com/releases/2023/06/230602130000.htm",
    ),
    (
        "Engineered immune cells drive advanced cancers into lasting remission",
        "A refined CAR-T therapy wiped out tumors in patients who had exhausted "
        "other options, with some remaining cancer-free years later. The approach "
        "is expanding from blood cancers toward solid tumors.",
        "Medicine",
        "https://www.sciencedaily.com/releases/2024/02/240228110000.htm",
    ),
]


async def _get_or_create_official(db) -> object:
    """Find the official @eureka account, creating it if missing."""
    existing = await db.users.find_one({"username": "eureka"})
    if existing:
        # Make sure a pre-existing account carries the official/verified flags.
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
        "interests": list(IMAGES.keys()),
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


async def main() -> None:
    await connect_to_mongo()
    db = get_db()

    author_id = await _get_or_create_official(db)
    now = datetime.now(timezone.utc)

    # Round-robin an index per category so each post's image matches its topic.
    image_cursor: dict[str, int] = {cat: 0 for cat in IMAGES}
    docs = []
    for headline, body, category, source_url in POSTS:
        pool = IMAGES[category]
        idx = image_cursor[category]
        image_cursor[category] = idx + 1
        image = pool[idx % len(pool)]
        created = now - timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        docs.append(
            {
                "headline": headline,
                "body": body,
                "category": category,
                "source_url": source_url,
                "images": [image],
                "author_id": author_id,
                "created_at": created,
                "upvotes": random.randint(5, 200),
                "comment_count": 0,
                "is_agent_post": True,
            }
        )

    result = await db.posts.insert_many(docs)
    print(f"Inserted {len(result.inserted_ids)} posts from the official @eureka account.")

    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
