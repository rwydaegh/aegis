# Military angle

Can AEGIS be sold into high-power military RF safety? Big shipboard radars, electronic-warfare
jammers, and the new counter-drone microwave weapons all put out enough power to hurt the crew, and
the current practice is to compute the field in empty air, compare it to a limit, and paint a
keep-out zone on the deck. Nobody models the human body. That is the opening.

Split out of `../before-tom-meeting/` on 2026-07-09 because it grew past a side note.

| File | What it is |
|---|---|
| `military_rf_hazard.md` | **Start here.** The assessment, in plain language. Verdict: conditional, near the top of the band. |
| `gemini_deep_research_prompt.md` | The prompt used to survey the landscape. |
| `gemini_deep_research_answer.md` | Raw Gemini deep-research output. Jargon-heavy. Confirms the two load-bearing claims, corrects me on three things. |

Related, elsewhere:

- `../before-tom-meeting/feasibility_synthesis.md` sets the rule this domain is graded against
  (design a controllable excitation, do not certify a passive signature).
- `../before-tom-meeting/survivor_topics/installed_antenna_cosite.md` is the same customer and the
  same shipboard toolchain.

## The one-paragraph state of play

Two claims hold up under independent research: in 99% of ship topside projects the human body is
never modeled, and no fielded military system does exposure-constrained beamforming. The near-term
play is not the beamformer, it is the boring one. Above 6 GHz the regulated quantity is absorbed
power density on skin over 4 cm² for 6 minutes, which is exactly what AEGIS computes natively, so a
single figure comparing an industry keep-out zone against a real-body one either kills the idea or
makes it. Against that: personnel safety is a small budget line next to ordnance safety, the safety
boards prefer the conservative static method because it cannot fail, and the ship geometry you would
need is classified even though the software is not. Route in through a European Defence Fund call
with a prime as partner, not by selling a navy anything. And rename the product for this market,
because AEGIS is the US Navy's combat system.
