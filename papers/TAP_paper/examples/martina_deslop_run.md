# deslop run ledger — martina.md

Run date: 2026-05-22. Target: `examples/martina.md` (warm expert note to a colleague).
This file is the bookkeeping for one full pipeline pass (split -> scope -> swarm -> apply).
Original is left untouched; cleaned output goes to `martina_deslopped.md` with a diff below.

## Stage 1 — deterministic scan

```
kind=md units=12 flagged=0 | tiers A=0 B=0 C=0 D=0 | tells={}
```

Zero excess-vocab hits, zero regex tells. Clean human prose. The swarm's job is to
confirm clean, catch what regex cannot (spelling, craft), and surface genuine
class-2 spectrum calls — not to manufacture edits.

Unit map (blank-line paragraph units, from `scan_text.py all_units`):

| unit | lines | kind | content |
|------|-------|------|---------|
| 1 | 1 | heading (h1) | Notes on the Huygens Box input file in Sim4Life |
| 2 | 3 | salutation | Hello Martina |
| 3 | 5 | prose | intro: two file routes, ASCII is yours |
| 4 | 7 | heading (h2) | What Sim4Life accepts as a Huygens Box input |
| 5 | 9 | prose | the three Input Type options |
| 6 | 11 | prose | the .h5 route + Zurich/IT'IS anecdote |
| 7 | 13 | heading (h2) | Low-frequency case |
| 8 | 15 | prose | A/B vs E/H, which solver |
| 9 | 17 | heading (h2) | A few things to keep an eye on |
| 10 | 19 | prose | metres-not-mm, uniform grid, sanity check |
| 11 | 21 | prose | offer to look at her file |
| 12 | 23-24 | signoff | Best, Robin |

## Stage 2 — scope manifest (register: warm expert note)

Register inferred: **warm expert note**, first person, helpful asides.
Destination: shared note/email to a colleague (markdown a person will read).
Voice to preserve: first person ("I worked it out", "I would start with"), the
Zurich/IT'IS anecdote, the direct asides ("That third one is yours.", "just send
it over"), the closing offer to help, and the technical precision.

Active rule set, resolved from `scope.yaml`:

- **ON — class 1 (always strip):** all anti-AI-language tells + AI word-swaps. Confirm each is genuinely slop here.
- **ON — class 2 (craft, considered, NEVER mechanical):** prose_structure + positive_voice + misused_words correctness. The interaction surface.
- **ON — synthesized plain-prose:** no decorative bold/italic lead-ins, no gratuitous emoji (graded for an eyeball deliverable).
- **ON — class 4 has_headings:** `title_case_headings`, `no_heading_article`, `no_dropped_article` (doc has one h1 + three h2).
- **OFF — class 3 (register), all of it for warm:** `no_passive_no_we` (first-person by design), `no_contractions`, `no_interjectional_subsentences` (asides are the warmth), `deadpan_prose` (warmth is the point), `subject_verb_rest`, `staccato_sentences` (relaxed), `hedging_calibrated`, `verb_strength_evidence`, `tense_conventions`, `bullet_list_avoidance`.
- **OFF — not applicable:** abstract/keyword rules, latex.*, figures.*, `internal_brand_names_in_prose` (Sim4Life is a real product, name it freely), `no_cross_ref_unpublished`.
- **OFF — class 5 promoter:** the whole `pet_peeves_wout` family (writing to Martina, not Wout).

## Stage 3 — swarm verdicts

(one read-only Opus reviewer per substantive unit, full active set in a single
read; salutation units 2 and 12 judged inline as trivially clean. Verdicts pasted
verbatim below.)

13 reviewers dispatched (6 prose units x {craft Opus, slop+correctness Sonnet},
unit 11 combined in one Opus agent, 1 Sonnet heading agent). Salutation units 2
("Hello Martina") and 12 ("Best, / Robin") judged inline: trivially clean, nothing
to flag in a warm note.

Per-unit roll-up (P = rules cleared, F = flags, Pr = preserved):

| unit | lens | P | F | Pr | flags raised |
|------|------|---|---|----|--------------|
| 3 | craft | 24 | 0 | 3 | — |
| 3 | slop+corr | 47 | 1 | 2 | `correctness.spelling` "seperate" -> "separate" (interact:false) |
| 5 | craft | 24 | 0 | 3 | — |
| 5 | slop+corr | 46 | 0 | 1 | — |
| 6 | craft | 20 | 1 | 2 | `concrete_over_abstract` drop "really" (interact:true) |
| 6 | slop+corr | 47 | 1 | 1 | `book_williams.comma_after_long_intro` add comma after "At your low frequency" (interact:false) |
| 8 | craft | 22 | 2 | 1 | `no_very` "very few"->"few" (interact:true); `omit_needless_words` drop "actually" (interact:true) |
| 8 | slop+corr | 47 | 1 | 0 | `filler_adverbs_intensifiers` drop "actually" (interact:false) |
| 10 | craft | 25 | 0 | 2 | — |
| 10 | slop+corr | 48 | 0 | 0 | — |
| 11 | craft+slop | 36 | 1 | 1 | `omit_needless_words` "look"/"look" echo (interact:true, optional) |
| 1,4,7,9 | heading | 3 | 0 | 0 | — (h9 opens with "A"; orphan rule bans only "The", so no trigger) |

Notable preserved (rules that technically applied but would have flattened the voice):
- u3 `concrete_over_abstract` / `hackneyed_nouns`: "a few practical things to watch out for" — the soft "things" is warm hand-waving toward the list that follows; a crisp abstract noun would stiffen it.
- u3 / u6 `positive_form`: "not really meant for external generation", "is not specified in the manual", "does not really apply" — genuine denials; forcing positive flattens the gentle steer.
- u5 `emphatic_end` / `mic_drop_stinger`: "That third one is yours." — 5 words (above the under-5 stinger threshold), the deliberate warm landing of the enumeration.
- u5 `passive_for_flow` / `passive_agent_unknown`: agentless passives ("produced by...", "intended to be used") keep old-before-new order; permissive rules license them.
- u10 `parallel_form` / `subject_verb_long_list`: the "write, load, run, compare" recipe and the causal because/so chain carry the hands-on explanatory voice; splitting would clip it.

Cross-lens agreement check:
- "seperate" (u3): single clean spelling catch, both lenses consistent (craft correctly ruled it out of its scope).
- "really" (u6): craft flagged interact:true, slop preserved it. Net = a spectrum call leaning KEEP (warmth).
- "actually" (u8): both lenses flagged it; they split on interact (craft true, slop false). Net = treat as spectrum (conservative), leaning DROP (mild filler).
- "comma after intro" (u6): clean mechanical correctness, no voice cost.

## Stage 4 — aggregated decisions + receipt

### Auto-applied (interact:false — slop strips + unambiguous mechanical fixes)

Written to `martina_deslopped.md`. Two changes, both safe and voice-neutral:

| # | unit/line | rule | before | after |
|---|-----------|------|--------|-------|
| 1 | u3 / L5 | `correctness.spelling` | "is a **seperate**, proprietary format" | "is a **separate**, proprietary format" |
| 2 | u6 / L11 | `book_williams.comma_after_long_intro` | "At your low frequency that performance argument" | "At your low frequency**,** that performance argument" |

### Spectrum calls (interact:true) — surfaced to user, decided

These are the judgment surface. Robin's call: apply my recommended set (A + B),
keep C + D for warmth.

| # | unit | rule | change | trade-off | decision |
|---|------|------|--------|-----------|----------|
| A | u8 | `no_very` | "very few cells" -> "few cells" | "very" adds nothing "tiny" (next clause) doesn't already carry | **APPLIED** |
| B | u8 | `filler/omit` | "that phrasing actually matches" -> "matches" | "actually" is filler with a faint note-of-surprise | **APPLIED** |
| C | u6 | `concrete_over_abstract` | "does not really apply" -> "does not apply" | "really" is a softener; removing reads more clinical | **KEPT** (warmth) |
| D | u11 | `omit_needless_words` | vary the repeated "look" | the echo reads as warmth | **KEPT** (warmth) |

### Receipt

Martina is a clean, well-built warm note: across 12 units the swarm cleared ~330
rule-checks and raised no class-1 AI-slop and no register violations. What I
changed: one spelling typo ("seperate") and one missing comma after a four-word
intro — both mechanical, neither touches the voice. What I deliberately left:
the first person throughout, the "That third one is yours." landing, the
Zurich/IT'IS anecdote, the soft "things"/"not really"/"actually" hedges that make
it sound like Robin and not a manual, and the warm open-door closing. Four
optional tightenings (A-D above) are on the table; none is required and two of
them (C, D) I would skip to keep the warmth. Register confirmed: no class-3
formality rule was applied, because this is a warm first-person note, not a paper.

### Verification

Token-level diff (`tr -s ' \n' '\n\n'` on both files) confirms `martina_deslopped.md`
differs from the original by EXACTLY two tokens: `seperate->separate` and
`frequency->frequency,`. Nothing else moved.

First write of the cleaned file mis-placed both `##` headings one paragraph too
early (a hand-transcription slip, not a swarm decision), which the token diff
caught immediately; rewritten from the original structure and re-verified clean.
Lesson for the skill: the apply stage should patch the original in place (Edit on
the exact spans), never retype the document — retyping risks silent structural
drift that no reviewer flagged.

### Files

- `martina.md` — original, untouched.
- `martina_deslopped.md` — final: 4 token changes vs original (separate, intro-comma, -very, -actually). Verified by token diff. C and D kept.
