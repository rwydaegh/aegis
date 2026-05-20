# Wout Joseph Review Workplan

This file is the operating plan for applying `transcription.md` to the
PaperMaker `main/` tree. The monolithic `v1_to_coauthors/paper.tex` is now a
migration reference, not the edit target.

## Canonical Target

- Edit: `main/`
- Assemble/check: `make pm-roundtrip`
- Generated artifact: `build/papermaker/assembled.tex`
- Review source of truth: `reviews/2026-05-11_wout_joseph/transcription.md`
- Action queue: `reviews/2026-05-11_wout_joseph/actions.md`

The round-trip check is expected to pass before substantive edits. After edits,
the old monolith will intentionally differ; use the assembled artifact for
compile and final export.

## Interactive Protocol

For each packet, Codex should present:

1. transcript rows being addressed
2. proposed exact edit or rewrite
3. why the edit is likely right
4. risks or scientific judgment points
5. choices: `apply`, `revise`, `skip`, `defer`

After applying a packet:

1. run `make pm-assemble` as a cheap structural sanity check
2. do not run the legacy round-trip diff after substantive edits; the old
   monolithic TeX is only a migration reference
3. compile only for fragile packets: floats, tables, equations, labels,
   references, bibliography, or section moves
4. run the full check stack only after the Wout pass is complete
5. update `actions.md` statuses for rows fully handled

## Rule Discipline

Wout's transcription is trusted as a record of what he marked, not as an
automatic rewrite of the paper. Every packet should keep literal
transcription, interpretation, and final paper edit separate.

Do not run a whole-document style sweep until the Wout packets are applied.
Global AI-prose, Wout-pet-peeve, IEEE-style, reference, and abstract/conclusion
consistency sweeps happen at the end.

## Packet 0: Migration Gate

Goal: Keep `main/` canonical and prevent accidental drift from the migrated
paper.

Likely action:
- Run `make pm-roundtrip`.
- Confirm the only legacy difference is blank-line placement.
- Do not edit `v1_to_coauthors/paper.tex`.

Choice default: `apply`.

## Packet 1: Mechanical Frontmatter And Intro

Rows:
- abstract shortening and struck sentences
- `simulation` -> `simulations`
- add/clarify `AEGIS`
- spell out `Finite-Difference Time-Domain` first use
- `regulatory campaign` -> `simulation campaign`
- `become infeasible` -> `become difficult`

Likely action:
- Apply exact wording fixes first.
- Propose a compact abstract rewrite separately before committing it.

Risk:
- Abstract validation claims need scientific wording, not just copy-editing.

Choice default: `mechanical first`.

## Packet 2: Introduction To Method Boundary

Rows:
- move `The empirical scalars...` material out of Introduction
- Fig. 1 should be referenced and treated as method/process material
- define `psSAR`, `SARwb`, `APD`
- Section II should become method-oriented, not just `Local absorption law`

Likely action:
- Move method-heavy paragraphs into the method section before rewriting.
- Keep a short introduction promise instead of detailed derivation text.

Risk:
- Structural move can disturb narrative and references.

Choice default: `move first, polish later`.

## Packet 3: Local Law And Fig. 1

Rows:
- clarify `The derivation below is exact...`
- remove `monochromatic`
- `Figure 2 shows the configuration` / add considered configuration
- insert explicit Fig. 1 references
- insert `\eta` after `exposure fraction`

Likely action:
- Clean section opening and setup definitions.
- Keep equations stable unless Wout explicitly marked them.

Risk:
- `exact` wording may need a conservative mathematical statement.

Choice default: `apply with conservative wording`.

## Packet 4: Pseudo-Brewster, Fig. 3, Table I

Rows:
- `upper/lower panel` -> `Fig. 3(a)/(b)`
- `shows the normalized absorbed power`
- `The maximum deviation is`
- `T_0` definition and normal-incidence meaning
- move Table I to bottom of column
- SI/Transactions note

Likely action:
- Apply mechanical wording.
- Defer float placement if it requires layout iteration.

Risk:
- Table placement is LaTeX-layout-sensitive.

Choice default: `wording now, layout after compile`.

## Packet 5: Fig. 5 And Geometric Law

Rows:
- `Fig 5 shows`
- explain Fig. 5(b)
- remove pseudo-Brewster sentence
- `conservative` / `underestimates` wording
- `of the exact law in (5)` style correction
- make Fig. 5(a) smaller

Likely action:
- Rewrite Fig. 5 discussion so both panels are explicitly explained.
- Adjust figure sizing only after checking compiled layout.

Risk:
- Some notes are style pet peeves rather than technical changes.

Choice default: `rewrite discussion first`.

## Packet 6: Theorems, Corollaries, Whole-Body Section

Rows:
- theorem numbering/name concerns
- avoid awkward `Corollary` framing
- refs near Flintoft/Zhang
- below 6 GHz wording
- possible deletion of `Total power remains valid...`

Likely action:
- Rename theorem-like material into plain propositions/claims if IEEE style is
  smoother.
- Add requested refs before deeper structural surgery.

Risk:
- Mathematical labels may be referenced later.

Choice default: `rename carefully`.

## Packet 7: Validation And Literature References

Rows:
- validation section should enumerate `(i) ...`
- `Setup` -> `Configuration`
- define `mmWave`
- replace vague `sub-mmWave` with explicit GHz range
- add Bamba/Diao/Kodera refs
- `Table V lists`
- remove stray vertical spacing near Kodera

Likely action:
- Reframe validation as a clean numbered evidence stack.
- Add references in one focused pass.

Risk:
- Reference additions need source verification.

Choice default: `structure first, references verified separately`.

## Packet 8: Higher-Order Corrections And Fig. 8

Rows:
- Fig. 8 is good but caption is too long for IEEE style
- `mmWave`/`frequencies?`
- inter-body section accepted

Likely action:
- Shorten caption without changing plotted content.
- Resolve frequency wording locally.

Risk:
- Caption shortening can remove necessary interpretive detail.

Choice default: `short caption + move detail to text`.

## Packet 9: Compliance, Discussion, Validity

Rows:
- merge Section VII into VIII
- `Discussion and Compliance`
- replace `network` with `method`
- Table VII `returns` -> `lists`
- Table VIII `Band stratification` AI-language note
- validity section should start with Table VIII summary

Likely action:
- Merge compliance into discussion and reduce section count.
- Use Table VIII as the opening validity map.

Risk:
- This is a major structural edit.

Choice default: `outline before applying`.

## Packet 10: Future Work, Conclusion, Acknowledgment

Rows:
- future work max two sentences in conclusion
- conclusion starts with 2-3 clean sentences
- no equations in conclusion
- remove worst-case paragraph
- acknowledgment struck through

Likely action:
- Collapse future work into a short final-conclusion paragraph.
- Remove or sharply shorten acknowledgment.

Risk:
- Funding acknowledgment may be administratively required.

Choice default: `ask before deleting acknowledgment`.
