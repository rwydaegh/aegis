# Keeping people safe near big military radars: is there a business here?

Written 2026-07-06, revised 2026-07-09 after a Gemini deep-research pass
(`gemini_deep_research_answer.md`, in this directory). Companion to
`../before-tom-meeting/feasibility_synthesis.md`. Written in plain language on purpose, because I am
not a defense person and neither is anyone I will hand this to.

## Read this first (the whole thing in six sentences)

Warships and military bases carry enormous radio transmitters: radars, jammers, and now
microwave weapons that fry drones. These transmitters are powerful enough to cook the crew, so the
military paints "do not stand here" zones on the deck and switches transmitters off when people are
around. Those zones are computed by simulating the radio field **in empty space, with no human body
in the picture at all**, and then comparing the field to a safety number. Because nobody models the
person, the zones are drawn far too conservatively, and the operational cost is real: ships have to
shut down their air-defense radar during flight-deck operations. AEGIS models the person better than
anyone. That is the entire opportunity, and it is the one corner of defense that is not secret.

The catch: personnel safety is a small budget line, the safety regulators actively prefer the dumb
conservative method because it cannot fail, and the ship geometry you would need to run a real
simulation is classified.

**Verdict: CONDITIONAL.** Excellent physics fit and a confirmed gap, real business friction.

## The ten words you need

| Term | What it actually means |
|---|---|
| **RADHAZ** | Radiation hazard. Umbrella term for "the transmitters might hurt something." |
| **HERP** | Hazards of EM Radiation to **Personnel**. The transmitters might hurt *people*. This is my target. |
| **HERO** | Same, to **Ordnance**. The transmitters might set off a missile. |
| **HERF** | Same, to **Fuel**. The transmitters might ignite fuel vapor. |
| **MIL-STD-464D** | The military standard that requires you to handle all three. Public document. |
| **DoDI 6055.11** | The US Defense Department rule that sets the actual human exposure limits. |
| **STANAG 2345** | The NATO version of that rule. What binds a Belgian or Dutch navy ship. |
| **Phased array** | A radar made of many small antennas whose signals are combined in software. You can steer and shape the beam electronically, with no moving parts. |
| **Sidelobe** | A phased array points a strong beam at its target, but it also leaks energy in other directions. Those leaks are sidelobes. The crew stands in the sidelobes. |
| **Keep-out zone** | The painted area on deck where people are not allowed while a transmitter is running. |
| **Unperturbed field** | Industry jargon for "the radio field computed as if no human were standing there." This phrase is the whole story. |

## What the idea is

Three candidate customers, one physical problem:

1. **Warships.** Big search and tracking radars, plus electronic-warfare jammers. Crew works on deck.
2. **Counter-drone microwave weapons.** New, being fielded now (Epirus Leonidas, US Air Force THOR).
   Deployed at bases and borders, with friendly troops and civilians nearby by design.
3. **Ground air-defense radars.** Same problem, fixed installation.

And one non-candidate: **lasers.** See section 6. Your instinct grouped lasers with jammers. The
physics says do not.

## What the deep-research pass confirmed (this is why the idea is real)

Three findings, and they are the load-bearing ones.

**1. Nobody models the human body. At all.**

> "In 99% of ship topside integration and platform design projects, the human body is not physically
> modeled. The platform's electromagnetic environment is simulated in an empty space [...] the human
> is treated as a point that must not enter that volume."

The industry computes the field in empty air and compares it to a threshold. This is exactly what my
whole method exists to improve on. The one partial exception is Dassault CST, which can drop in a
Virtual Population phantom (including Duke, which AEGIS also ships). So CST *can* do body dosimetry.
It is not fast, not differentiable, and it is not how the operational workflow is actually run.

**2. There is no exposure-aware beam control anywhere in service.**

> "In currently fielded military radar and electronic warfare systems, there are no active,
> software-driven exposure-constrained beamforming or dynamic beam-scheduling loops in operation."

Today, if a radar beam would sweep across a walkway, the system just turns the power down or blanks
the sector. It is an on/off lookup table. Meanwhile the mathematics for doing this properly is well
developed in the *civilian* literature (exposure-aware precoding in 5G, thermal-budget optimization
for millimeter-wave uplinks, human-avoidance null-steering in wireless power transfer). **Nobody has
carried that mathematics across into the military domain.** That translation is the gap.

**3. The conservatism has a documented operational cost.**

Because keep-out zones ignore the body's own shadowing and absorption, they are drawn too big. The
consequence, in Gemini's words: during flight-deck launch and recovery, ships must put their
high-power tracking radars into standby or blank whole sectors, which "degrades the ship's
hemispherical air defense capabilities, leaving the platform vulnerable to low-altitude threats
during flight operations."

That is the pain. A ship becomes partially blind precisely when it is most exposed, because the
safety model does not know what a human body does to a radio wave.

## Where I was wrong, and it matters

In my first draft I assumed the counter-drone microwave weapons ran at high frequency, so my
surface-absorption speed trick would apply. **That is wrong.**

- Epirus Leonidas is **L-band**, roughly 1.1 GHz.
- Air Force THOR is **S-band**, roughly 2 to 4 GHz.

Below about 6 GHz, radio energy penetrates *deep into the body*, so this is a whole-body volumetric
absorption problem, not a skin-surface one. My fast surface method does not apply. The
constrained-beamforming planner still transfers (it only needs the field to be linear in the array
weights, which it is), but the millisecond speed does not. Same honest split as hyperthermia and
sub-6 GHz wireless power.

Gemini adds a genuinely unsettling detail I did not know: because these weapons sit in the
deep-penetration band, and because humans have **no heat-sensing nerves deep inside the body**, a
person in the sidelobes can take serious internal organ heating with no pain reflex to warn them.
The 95 GHz Active Denial System is the opposite case, pure skin absorption, which is exactly why it
hurts instantly and is used as a non-lethal deterrent.

## Where Gemini is wrong, and you would have caught it

Gemini's comparison table sets the **military controlled** limits against the **civilian general
public** limits and concludes the military allows a "5x higher threshold [...] assuming a trained,
physically fit population under medical surveillance."

That is an apples-to-oranges comparison. The correct comparison is military-controlled against
**civilian occupational**, and when you do that:

| Quantity | IEEE C95.1-2345 (military, controlled) | ICNIRP 2020 **occupational** |
|---|---|---|
| Whole-body average SAR | 0.4 W/kg | 0.4 W/kg |
| Local SAR, head and torso (10 g) | 10 W/kg | 10 W/kg |
| Local SAR, limbs (10 g) | 20 W/kg | 20 W/kg |
| Absorbed power density above 6 GHz (4 cm², 6 min) | 100 W/m² | 100 W/m² |

They are **the same numbers**. The military "controlled" tier is the ordinary occupational tier. The
5x factor Gemini describes is just the standard occupational-versus-public safety factor, not
anything military-specific.

This is good news and it changes a to-do item. I previously wrote that adding the military limit sets
is "small, concrete engineering." It is smaller than that: **the occupational tier AEGIS already
implements is numerically the military tier.**

What genuinely *is* military-specific is the **pulsed regime**. Leonidas is quoted at 450 MW peak
power, 20 ns pulses, 50 Hz repetition. Civilian standards handle brief high-peak pulses poorly, and
the military standard adds fluence (energy-per-pulse) rules that civilian guidance lacks. **That, not
the limit values, is the real technical work AEGIS would have to do.** Worth knowing before a meeting.

## The physics, and the one calculation that decides it

Two assumptions matter.

**The field is linear in the array weights.** This is the only thing my operator method truly needs,
and it is unconditionally true here. So the constrained-optimization machinery transfers whole.

**The surface-absorption shortcut only works above about 6 GHz.** Below that, energy goes into the
whole body volume. So:

| Band | Example | Regime |
|---|---|---|
| 2 to 30 MHz | ship HF comms | **not my physics.** Hazard is induced body currents and contact burns off rigging. Exclude. |
| 1 to 4 GHz | Leonidas, THOR, air-search radar | whole-body volumetric. Planner transfers, speed does not. |
| ~10 GHz (X-band) | fire-control, navigation radar | skin regime returning |
| 30 GHz and up (Ka, mmWave) | seekers, jammers, 95 GHz Active Denial | **home turf.** Sub-millimetre skin depth. |

Now the number. Take a representative shipboard array: 50 kW average power, main-beam gain 40 dB
(a factor of 10,000). The power density at distance `r` is `S = P·G / (4πr²)`.

Pointing straight at you, the field only drops below the public safety limit of 10 W/m² at about
**2 kilometres**. A destroyer is 150 m long, so the entire ship sits inside its own hazard distance.
That is why keep-out zones and emission-control doctrine exist.

But the crew is never in the main beam. They stand in the sidelobes. Take a sidelobe 30 dB down
(a factor of 1000 weaker, so effective gain 10) and a sailor 50 m away:

```
S = (50,000 × 10) / (4π × 50²) = 15.9 W/m²
```

Compare: 10 W/m² is the public limit, 50 W/m² is the occupational limit. **The sailor sits right
between them.** Two things follow, and they are the report:

1. **The safety constraint genuinely binds.** It is not a formality. (Contrast wireless power
   transfer, where I had to strain to show the constraint binds at all.)
2. **It binds in the sidelobes**, and sidelobes are precisely what a phased array controls in
   software.

So the product is not "draw the hazard zone." It is **steer a null onto the crew and keep the main
beam on the target**:

> maximise radar performance toward the track,
> subject to: absorbed power on every crew position stays under the limit,
> subject to: total array power.

That is my existing exposure-constrained beamformer (`src/aegis/coherent/ecbf.py`), structurally
unchanged, with the constraint region assembled over the deck instead of over a bystander phantom.
`theory/exposure_null_precoding.tex` is already the null-steering form of it. Gemini independently
writes down the same optimisation problem, which is a good sign for the framing and a warning that it
is not a secret.

## The strongest position, in one sentence

Everyone in that room can model the antenna and the ship. Nobody brought a body.

Altair FEKO, Ansys HFSS, and Remcom model the *ship* far better than I ever will. The industry's own
description of its method is "unperturbed fields," meaning it deliberately leaves the human out. The
human body is the one cell in the topside-design matrix where I am the world expert and the
incumbents are not even trying. That is a position that does not require me to beat FEKO at
electromagnetics.

Better still, this rides the **same workflow and the same customer** as the installed-antenna and
co-site wedge in `../before-tom-meeting/survivor_topics/installed_antenna_cosite.md`. Shipboard "topside design" bundles
antenna placement, coupling, RADHAZ, and radar signature into one job. This thickens that strategy
rather than splitting it.

## Two plays, and I now prefer the boring one

**Play A, the near-free one. Above 6 GHz, replace the empty-space threshold with real body dosimetry.**
Above 6 GHz the regulated quantity stops being "field strength in the air" and becomes **absorbed
power density on skin**, averaged over 4 cm² for 6 minutes. That is *literally the quantity AEGIS was
built to compute*, natively, in milliseconds. Gemini notes the military community is only slowly
adapting to this shift, and says plainly that moving to skin-surface dosimetry means that "instead of
demanding wide spatial keep-out zones on ship decks, software models can evaluate the actual physical
heating of the skin surface." Smaller keep-out zones, more operational tempo, and it is the thing I
already do. X-band and Ka-band shipboard emitters are the target.

**Play B, the moonshot. Exposure-constrained beam scheduling.** Bigger prize, confirmed empty gap,
and a certification wall (below).

Play A is what I would lead with. It requires almost no new physics, it attacks a documented pain,
and it lands squarely on my home turf. Play B is the story, but Play A is the sale.

## The walls, sharpened by the research

- **Personnel safety is the poor cousin.** This is the finding that hurt most. Ordnance safety (HERO)
  commands a far larger budget than personnel safety (HERP), because a missile cooking off destroys a
  carrier while overexposing a sailor is treated as a chronic, administrative, non-catastrophic
  occupational matter managed with paint and signage. I am selling into the small budget line.
- **The regulator prefers the dumb method.** Safety boards require deterministic verification. A
  phased array that continuously reshapes its sidelobes based on live human positions is hard to
  certify against sensor dropout and software failure. They would rather have a painted line that
  cannot crash. This is a real, structural objection to Play B, and it is not solved by better physics.
- **The classified-geometry bottleneck.** The good news: general electromagnetic solvers are
  commercial dual-use, not arms-controlled, whereas radar-signature and stealth tooling *is* strictly
  arms-controlled. So my safety thesis about openness holds. The bad news: the detailed ship CAD,
  antenna phase centres, and radar waveform tables you need to run a *real* simulation are classified.
  The tool is open, its inputs are not.
- **The software slice is modest.** The military electromagnetic-effects market is roughly $1.5B to
  $2B a year, but only about $300M to $400M of that is software licensing. The rest is physical test
  and engineering services. I would be competing for a slice of the smaller half.
- **The name.** AEGIS is the name of the US Navy's flagship combat system (Lockheed Martin, with the
  SPY-1 radar). Lockheed also builds the HELIOS laser. Walking into naval RF safety with a product
  called AEGIS is at best a distraction and at worst a trademark problem in that exact vertical. If
  this is ever pursued seriously, it needs another name in this market.
- **The ethics.** Making a microwave weapon legally operable closer to humans protects bystanders and
  simultaneously raises the weapon's permitted duty cycle. Decide where you stand before someone else
  asks. Not a footnote.

## The laser half is dead, and here is why

A 60 kW shipboard laser (HELIOS, Lockheed, on Arleigh Burke destroyers) is a genuine human hazard. It
is not *my* hazard.

Laser safety is governed by ANSI Z136, and the binding limit is **ocular**, not skin. The quantity
that matters is the distance at which the beam can still damage a retina, set by beam divergence,
atmospheric propagation, and glint off surfaces. There is no interesting transmission-into-tissue
surface integral, no body-geometry shadowing problem worth solving, and crucially **no controllable
array of emitters whose weights you optimise**. A high-energy laser is *pointed*, not synthesised from
a constrained aperture.

Do not let the phrase "directed energy" glue the microwave and optical halves together in a pitch.
Different physics, different regulator, different buyer.

## Verdict

**CONDITIONAL, near the top of the band.** The physics fit is among the best in the whole
generalisation study, the gap is now confirmed by independent research rather than assumed, the
constraint provably binds, the receptor is a human body (the one thing I own), and the domain is
unclassified at the software level.

It does not reach PURSUE because the buyer for personnel safety specifically has a small budget, the
certifying authority structurally prefers the conservative method I would be displacing, and the
input data is classified.

Ranked against the survivor set: this sits **above** wireless power transfer (same "stay on while a
person is present" story, but the buyer has money and a mandate rather than a market that has
under-delivered for a decade) and **beside** RIS constrained synthesis on physics quality.

## What I would actually do next

Do not try to sell a navy anything. Get someone to pay for the research instead.

1. **Target a European Defence Fund call.** The non-thematic SME calls are reportedly 100% funded, and
   there are 2026 calls around disruptive SME technology and radio-frequency sensing. Verify the exact
   call codes and deadlines directly, do not trust a language model on grant identifiers.
2. **Find a European prime as partner**, because they hold the classified geometry problem, not you.
   Thales Netherlands (naval air-defense radars), Damen, Naval Group, Saab, Hensoldt, Leonardo.
3. **Join a NATO Science and Technology Organization panel** in this area to build defense credibility
   without needing a product.
4. **Do the pulsed-exposure work**, since that is the one genuine technical gap between what AEGIS
   computes today and what a military system needs.
5. **Build the Play A demo:** one X-band shipboard scene, keep-out zone computed the industry way
   (empty space, threshold) versus the AEGIS way (real body, absorbed power density on skin). If the
   zone shrinks meaningfully, that single figure is the entire pitch.

Item 5 is a week of work and it either kills the idea or makes it.
