"""Hand-written depth levels for batch 07.

Covers the run of @eureka agent posts that landed between the batch 06
verification pass and the discovery that the in-house content agent (now
retired, see app/agent_scheduler.py) never wrote explanation/deep-dive
levels at all. All 19 headlines here are grounded in the source_url each
post already carries.

Safety behaviour lives in backfill_runner.py: length check before the db
connection, dry run by default, flagged headlines excluded.

    MONGODB_URI='<connection string>' DRY_RUN=true  python backfill_batch_07.py
    MONGODB_URI='<connection string>' DRY_RUN=false python backfill_batch_07.py
"""

from __future__ import annotations

import asyncio
import sys

from backfill_runner import run

# headline -> (level 2 "explain", level 3 "deep dive")
CONTENT: dict[str, tuple[str, str]] = {
    "The Voyager 1 probe is the most distant human-made object": (
        "Launched in 1977 to tour the outer planets, Voyager 1 kept going "
        "after its flybys ended. It crossed the heliopause, the boundary "
        "where the Sun's influence gives way to interstellar space, in 2012 "
        "and has been travelling through it ever since.",
        "At over 24 billion kilometres away, a radio signal takes more than "
        "22 hours to reach it one way, so commands and replies happen on a "
        "nearly two-day round trip. Its plutonium power source loses output "
        "every year, and NASA has been switching off instruments one by one "
        "to keep the rest running. Some onboard systems are expected to stay "
        "alive into the early 2030s, after which it will drift silently, "
        "carrying the Golden Record, for billions of years.",
    ),
    "The body has enough iron to make a small nail": (
        "Iron sits at the centre of haemoglobin, the molecule in red blood "
        "cells that grabs oxygen in the lungs and releases it in tissue. An "
        "adult carries roughly three to four grams of iron in total, most of "
        "it locked inside those cells.",
        "Most of that iron is recycled rather than replaced: when old red "
        "blood cells break down after about four months, the body salvages "
        "the iron and reuses it, so daily dietary needs are small relative "
        "to the total stored. Too little iron limits oxygen delivery and "
        "causes the fatigue of anaemia; too much is toxic, since the body "
        "has no active way to excrete excess iron, only to control how much "
        "it absorbs from food.",
    ),
    "Light takes 100,000 years to escape the Sun's core": (
        "Photons made by fusion in the Sun's core do not travel in a "
        "straight line outward. The core is so dense that a photon collides "
        "with a charged particle almost immediately, scatters in a random "
        "direction, and repeats that billions of times before it drifts "
        "outward at all.",
        "This random walk means a photon's net progress toward the surface "
        "is far slower than light speed in open space, and estimates for the "
        "crossing time span tens of thousands to over a hundred thousand "
        "years depending on the model of the Sun's interior used. Once the "
        "photon reaches the transparent outer layers it escapes freely, and "
        "the 150 million kilometre trip to Earth then takes about eight "
        "minutes. The light hitting your eyes right now started its journey "
        "long before humans existed.",
    ),
    "The Sun makes up 99.86 percent of the mass of the solar system": (
        "The Sun's gravity is what holds the solar system together, and "
        "mass is why: it contains almost all of the material orbiting it. "
        "Everything else combined, eight planets, their moons, asteroids "
        "and comets, adds up to a small fraction of one percent.",
        "Jupiter alone accounts for roughly two thirds of whatever mass is "
        "left over after the Sun, more than all the other planets combined. "
        "This lopsided distribution is a direct consequence of how the "
        "solar system formed: almost all the material in the original "
        "collapsing cloud fell inward to ignite the Sun, while only the "
        "leftover disc of gas and dust farther out coalesced into planets. "
        "It is also why the Sun's gravity dominates the orbits of everything "
        "from Mercury to distant comets.",
    ),
    "A spinning figure skater speeds up by pulling in their arms": (
        "Angular momentum, a measure of how much an object is spinning "
        "combined with how its mass is spread out, stays constant if "
        "nothing pushes or twists the skater from outside. Pulling the arms "
        "in concentrates that same mass closer to the axis of rotation.",
        "Since the momentum can't change, the spin rate must increase to "
        "compensate for the mass moving inward, the same trade-off skaters "
        "feel in their arms works at cosmic scale. A collapsing star's core "
        "shrinks from roughly the size of Earth down to a city-sized sphere, "
        "and by the same conservation law it can end up spinning hundreds of "
        "times per second, becoming a pulsar. The skater and the dying star "
        "are obeying the exact same physical law.",
    ),
    "A hummingbird's heart can beat over 1,200 times a minute": (
        "Hovering flight burns energy faster than almost any other form of "
        "animal locomotion, so hummingbirds run correspondingly extreme "
        "metabolisms. Their hearts can beat well over a thousand times a "
        "minute during activity, among the fastest of any animal.",
        "To fuel that, hummingbirds eat roughly their own body weight in "
        "nectar each day and their wings can flap dozens of times per "
        "second, fast enough to produce the audible hum they're named for. "
        "The trade-off is that this pace is unsustainable overnight: many "
        "species drop into torpor, a controlled hibernation-like state where "
        "heart rate and body temperature fall dramatically, to avoid "
        "starving before dawn.",
    ),
    "Your stomach lining is replaced every few days to avoid digesting itself": (
        "Stomach acid is strong enough to break down the same proteins and "
        "tissue that make up the stomach wall itself. To survive its own "
        "acid, the stomach constantly secretes a thick layer of protective "
        "mucus and replaces its lining cells every few days.",
        "The mucus layer combines with bicarbonate to neutralise acid right "
        "at the tissue surface, creating a thin buffer zone even though the "
        "stomach's interior stays intensely acidic, often below pH 2. When "
        "this defence fails, for instance due to certain bacterial "
        "infections or long-term use of some anti-inflammatory drugs, the "
        "acid can erode the lining faster than it regenerates, which is how "
        "painful peptic ulcers form.",
    ),
    "Olympus Mons on Mars is nearly three times taller than Everest": (
        "Olympus Mons is a shield volcano built from countless slow lava "
        "flows, the same way Hawaii's volcanoes form on Earth. It rises "
        "about 22 kilometres above the surrounding plains, compared to "
        "Everest's 8.8 kilometres above sea level.",
        "Mars can grow volcanoes this large partly because it has no moving "
        "tectonic plates: on Earth, a plate drifts over a stationary hot "
        "spot, spreading eruptions into a chain of smaller volcanoes like "
        "the Hawaiian islands, but on Mars the crust stays put over the same "
        "hot spot for hundreds of millions of years, letting lava pile up in "
        "one place indefinitely. Weaker Martian gravity also lets volcanoes "
        "grow taller before their own weight would cause them to collapse.",
    ),
    "The number graham once held the record for largest used in a proof": (
        "Graham's number came from a proof in combinatorics, the branch of "
        "math dealing with counting and arrangements, where it served as an "
        "upper bound for a hard-to-pin-down quantity. For years it was cited "
        "as the largest number ever used in a serious mathematical proof.",
        "The number is built using a fast-growing notation stacked on "
        "itself repeatedly, producing a value so large that writing it in "
        "ordinary digits is physically impossible: there is not enough room "
        "in the observable universe to record them, even at one digit per "
        "Planck volume, the smallest length physics considers meaningful. "
        "The actual answer to the combinatorics problem it bounds is now "
        "known to be vastly smaller, and other proofs have since used even "
        "larger numbers, but Graham's number remains the popular icon of the "
        "idea because of how it was first popularised.",
    ),
    "Helium was discovered on the Sun before it was found on Earth": (
        "During a solar eclipse in 1868, astronomers examined sunlight "
        "passing through the Sun's outer atmosphere and found a yellow "
        "spectral line that matched no known element. They named the new "
        "element helium, after Helios, the Greek word for the Sun.",
        "Spectral lines work because every element absorbs and emits light "
        "at wavelengths unique to it, like a fingerprint, so a mismatch "
        "against every known element was strong evidence of something new. "
        "It took until 1895 for chemists to isolate helium on Earth, "
        "extracting it from a uranium mineral, confirming what astronomers "
        "had inferred purely from starlight nearly three decades earlier. It "
        "remains one of the few elements discovered in space before it was "
        "found at home.",
    ),
    "Comets grow tails only when they near the Sun": (
        "Far from the Sun, a comet is an inert mix of ice, rock and dust, "
        "often compared to a dirty snowball. As its orbit carries it closer, "
        "solar heat turns the surface ice directly into gas, releasing dust "
        "trapped inside and streaming both outward into a tail.",
        "A comet actually grows two tails: a straight ion tail of charged "
        "gas pushed directly away by the solar wind, and a curved dust tail "
        "that lags behind along the comet's orbital path. Both always point "
        "generally away from the Sun regardless of which direction the comet "
        "is travelling, so outbound comets appear to fly tail-first. As it "
        "moves away again the heating stops, the tail fades, and the nucleus "
        "returns to its inert state until the next close pass.",
    ),
    "A teaspoon of neutronium would not fit in normal chemistry at all": (
        "Ordinary matter is mostly empty space held up by electron shells "
        "around atomic nuclei, which is what gives chemistry its rules. "
        "Inside a neutron star, gravity is strong enough to crush those "
        "shells away entirely, packing matter into a state chemistry has no "
        "category for.",
        "\"Neutronium\" is not a recognised element but a popular shorthand "
        "for this crushed state, where protons and electrons are forced "
        "together into neutrons, leaving matter as dense as an atomic "
        "nucleus throughout. A teaspoon of it would weigh on the order of a "
        "billion tonnes on Earth, though it could not actually exist here: "
        "without the star's immense gravity holding it together, it would "
        "instantly blow apart back into ordinary particles. Its properties "
        "are inferred from physics models and neutron star observations "
        "rather than direct sampling, since none has ever been retrieved.",
    ),
    "Your liver can regenerate even after losing most of its mass": (
        "Most organs cannot regrow lost tissue, but the liver is a "
        "prominent exception. Removing up to about two thirds of it "
        "surgically still leaves enough surviving cells to rebuild the "
        "organ back toward its original size over the following weeks.",
        "Regeneration here means the liver's own cells rapidly multiply to "
        "restore mass and function, rather than the remaining tissue simply "
        "growing larger, and the regrown liver does not perfectly recreate "
        "its original shape. This capacity is what makes living-donor liver "
        "transplants possible: a portion from a healthy donor can be "
        "removed and transplanted, and both the donor's remaining liver and "
        "the transplanted section regrow independently in their new hosts. "
        "The exact biological trigger that tells the liver when to stop "
        "regrowing is still an active area of research.",
    ),
    "There is a planet made largely of a diamond-like carbon": (
        "55 Cancri e is a super-Earth about 40 light-years away, orbiting "
        "so close to its star that its surface is likely molten. Early "
        "models of its density suggested an interior unusually rich in "
        "carbon, which under enough heat and pressure could form "
        "diamond-like crystalline structures.",
        "The idea comes from indirect evidence: astronomers cannot sample "
        "the planet directly, so composition is inferred from its mass, "
        "radius and the carbon-to-oxygen ratio measured in its star's light, "
        "on the assumption that a star and its planets tend to share similar "
        "starting chemistry. More recent studies using updated data have "
        "pushed back on the original carbon-rich picture, suggesting the "
        "planet may be less exotic than first proposed, so its exact "
        "interior remains a genuinely open and actively debated question "
        "rather than a settled fact.",
    ),
    "Prime numbers thin out but never run out": (
        "Primes are the numbers divisible only by themselves and one, and "
        "they become noticeably rarer as numbers get larger, since there "
        "are simply more possible smaller factors around to rule a number "
        "out. Despite that thinning, the supply never actually ends.",
        "Euclid proved this over two thousand years ago with an elegantly "
        "simple argument: assume there were only finitely many primes, "
        "multiply them all together and add one, and the result must either "
        "be prime itself or divisible by some prime missing from the "
        "original list, a contradiction either way. That guarantees "
        "infinitely many primes exist. Modern research has moved on to "
        "subtler questions this proof doesn't touch, like exactly how "
        "primes are spaced, including the still-unproven twin prime "
        "conjecture about pairs of primes just two apart.",
    ),
    "GPS satellites must correct for Einstein's relativity to work": (
        "GPS satellites orbit fast and sit in weaker gravity than clocks on "
        "the ground, and Einstein's relativity says both of those change "
        "how quickly time passes. Left uncorrected, the satellites' atomic "
        "clocks would drift out of sync with ground clocks.",
        "Special relativity says the satellites' high orbital speed slows "
        "their clocks slightly, while general relativity says the weaker "
        "gravity at orbital altitude speeds them up by a larger amount, and "
        "the two effects don't cancel. The net result is that uncorrected "
        "clocks would gain about 38 microseconds a day, which sounds tiny "
        "but would translate into kilometres of position error daily, since "
        "GPS distance comes from the travel time of light-speed signals. "
        "Engineers correct for this by running the clocks slightly slow "
        "before launch.",
    ),
    "The at symbol in email was chosen almost by accident": (
        "In 1971, engineer Ray Tomlinson needed a character to separate a "
        "person's name from the computer they used, for the first system "
        "that could send messages between different machines. He picked the "
        "@ symbol mainly because it was on the keyboard and rarely used "
        "elsewhere.",
        "The @ sign had existed on typewriters and keyboards for decades "
        "before that, mostly for commercial pricing notation like \"3 "
        "widgets @ $5\", but had no real use in computing text. Tomlinson "
        "chose it specifically because it could not appear in a person's "
        "name and would not be confused with other characters, and the "
        "message format he devised, name@host, became the template every "
        "email address has followed since. He reportedly considered the "
        "choice unremarkable at the time and didn't expect it to matter "
        "much.",
    ),
    "Rust is just iron slowly returning to the ore it came from": (
        "Iron ore is mostly iron oxide, and refining it into metal takes "
        "energy to strip the oxygen away. Left exposed to oxygen and water, "
        "iron slowly reacts to reform iron oxide, chemically similar to the "
        "ore it started as.",
        "This happens because the metallic form of iron is a higher-energy "
        "state than the oxide, so smelting effectively stores energy in the "
        "metal that rusting slowly releases back, an example of the metal "
        "reverting toward its more stable, lower-energy natural form. "
        "Unlike some other metals whose oxide layer forms a protective "
        "seal, iron oxide is porous and flakes away, constantly exposing "
        "fresh metal underneath, which is why rust keeps eating into iron "
        "rather than stopping at a thin surface layer.",
    ),
}


if __name__ == "__main__":
    sys.exit(asyncio.run(run("batch 07", CONTENT)))
