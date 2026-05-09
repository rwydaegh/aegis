# Opus prose pass — TAP paper

Aggressive prose-level pass executed by Opus in-session, on top of the
22-agent swarm work captured in `MEGA_REPORT.md`. The swarm fixed
anti-patterns; this pass mimics positive Wydaeghe style.

Round 1 squash-merged as PR #793 (commit `16c058c`). Round 2 is
uncommitted in the working tree (12 ins / 12 del).

## Tally

| Class | Count | Where |
|-------|------:|-------|
| `approx.\` flowing prose → "approximately" | 12 | §I, §V, §VI, §IX, throughout |
| `$X\,$GHz` math-mode → `$X$~GHz` | ~100 | body-wide unit normalization |
| `IEC/IEEE\,62704` → `IEC/IEEE~62704` | 2 | §VII.C |
| Sub-section title `5\,GHz` → `5~GHz` | 1 | §V.C |
| `10\,g cube` → `10~g cube` | 1 | §VII.B title |
| Penetration-depth list `$X\,$cm` etc. → `$X$~cm` | 7 | §IX.A |
| GELU/GeLU casing → GELU | 1 | §VII.B |
| British "totalling" → "totaling" | 1 | §I |
| Explicit First/Second/Third cadence introduced | 3 | §I gap statement, §III Setup, §III.D conditions |
| Paragraph splits | 1 | §X conclusion (1 → 3 paragraphs) |
| Passive → active in claims | 2 | §III opener, §VI opener |
| "closed forms ... closed-form" echo removed | 1 | §VII opener |
| Topic-first opener restructured | 2 | §III, §VI |

## Per-section edits

### §I Introduction
- Cell-count sentence tightened (lost weak `that grows to` clause).
- Literature paragraph: lead changed from "Several partial closed
  forms exist in the literature" to **"Five partial closed forms
  exist in the literature, each fitting one empirical scalar to
  numerical or experimental data"** — committal lead.
- Three-gap statement restructured to explicit **"Three gaps
  remain. First, … Second, … Third, …"** parallel form (was a
  single "However" sentence with three dashed conjuncts).
- "This paper derives" preamble re-cast as **"This work closes the
  three gaps with a single closed form"** + First/Second/Third
  paragraph addressing each gap in order.
- Long literature-recap paragraph split into two: (1) the closed-form
  pair definition, (2) the empirical-scalar mapping (Kodera $T_0$,
  Flintoft $\gamma_s$, Bamba $\Tbar$, $3$~GHz Fabry–Pérot).
- "totalling" → "totaling".

### §III Local absorption law
- Section opener: passive `The configuration is shown in
  Fig.~\ref{fig:configuration}` → **`\Cref{fig:configuration}
  shows the configuration`** (figure-as-subject).
- Setup paragraph re-cast as **"Three working assumptions hold
  throughout. First, … Second, … Third, …"** (was a flat list of
  four flat declaratives).
- Polarization-cancellation passage re-cast as **"under any of
  three conditions. First, … Second, … Third, …"** with explicit
  `D_B ≤ 16%` / `N ≥ 20` numeric anchors at the end of the third
  bullet.

### §V Pseudo-Brewster
- Subsection title `Layered transmission below 5\,GHz` →
  `5~GHz` (consistency with body convention).

### §VI Whole-body absorbed power
- Validation opener: passive `are tested against` → **`We test`**.

### §VII Higher-order corrections
- Curvature subsection table cells kept with `approx.\` (tight
  technical context, override allows it).
- GELU acronym normalized (was inconsistent GELU/GeLU after swarm).
- Compliance-section opener: **`The closed forms reduce regulatory
  compliance to closed-form functions`** (echo) → **`Regulatory
  compliance reduces to a function of three precomputed scalars`**.

### §IX Discussion
- Penetration-depth list and torso/limb radius math-mode units
  normalized.
- High-frequency-boundary paragraph: 4 `approx.\` → "approximately"
  + cleaner "and" / "and" connectives instead of "to … to … to".

### §X Conclusion
- **Third paragraph split into three**:
  1. compliance threshold reduces to three scalars + five empirical
     scalars collapse into one;
  2. GPU primitive framing — *"the same GPU primitives that drive
     real-time rendering apply directly to real-time exposure
     assessment"*;
  3. breakdown limits + future work + **closing numeric headline +
     condition + implication**.
- Closing sentence rewritten to loop back to the introduction:
  *"every published ground truth is matched within the ±7% envelope
  on T₀ propagated from the ±20% dielectric input uncertainty, and a
  regulatory campaign that takes weeks of FDTD reduces to one
  ambient-occlusion pass and one Fresnel quadrature."* The "weeks
  of FDTD" callback echoes "weeks on GPU clusters" in para 1 of
  the introduction — Wydaeghe-style ring closure.

## Style targets that the swarm did vs. this pass did

| Target | Swarm | Opus pass |
|--------|:-----:|:---------:|
| Title case → sentence case | done | — |
| Equation-end `\, .` / `\, ,` inside env | done | — |
| `\gls{}` removed entirely | done | — |
| Em dashes removed | done | — |
| British → American spellings | done | "totalling" caught |
| `siunitx` removed | done | — |
| `to`-ranges → `--` ranges (text) | done | — |
| `$X\,$GHz` → `$X$~GHz` (math) | missed | done (~100) |
| `approx.\` flowing → "approximately" | done in SI, partial in body | done in body (12 more) |
| First/Second/Third explicit cadence | not attempted | done (3 places) |
| Active voice in claims | not attempted | done (3 places) |
| Result-then-reason restructuring | not attempted | done (intro gap + closing) |
| Paragraph splits for one-idea | not attempted | done (conclusion) |
| Ring closure (intro ↔ conclusion) | not attempted | done |
| GELU/GeLU casing reconciled | flagged | resolved |
| "closed forms … closed-form" echo | flagged | resolved |

## Compile state

- `paper.tex`: compiles clean. 1 standard `Underfull \hbox` (line
  1628), 1 standard `Overfull \hbox` (line 1616, 5.76 pt). Both are
  the band-stratification table — pre-existing.
- `paper_SI.tex`: compiles clean (no warnings from this pass).

## Known leftovers (cross-cutting decisions deferred)

These are still unresolved from the swarm pass — Opus did not touch
them on judgment grounds:

- FWO / ERC absent from Acknowledgment (paper has Methusalem +
  GOLIAT only; original npj/IEEE Access papers had a different
  funding stack).
- Bamba2014 cite-key/year mismatch (entry is 2013, key reads 2014;
  rename + 6 body refs).
- DOIs identified but not inserted (Tier-B list in MEGA_REPORT).
- Table column header style: `[mm]` vs `(mm)` vs `\,[mm]` — three
  forms coexist.
- Title `from 1 to 100\,GHz` retains the prose form; not converted
  to en-dash.

## How to read this against MEGA_REPORT.md

`MEGA_REPORT.md` covers the swarm's anti-pattern cleanup (22 agents,
~270 edits across 11 ranges × 2 waves). This file covers the
Opus prose-mimicry pass that runs on top. Total state of the paper
is the union: anti-patterns out (swarm) + Wydaeghe positive style in
(Opus). Round-1 of Opus is in master via #793; round-2 is the
12/12 diff currently uncommitted.
