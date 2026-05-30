# Meta-lessons for AI-assisted IEEE paper writing

A distilled report on how Robin wants AI agents to write IEEE papers,
drawn from session `7dc0a8d1` (which produced `papers/TAP_paper/paper.tex`
and `paper_SI.tex` over 123 user messages and several agent swarms). The
content is generalised: TAP examples are used illustratively, but every
rule below is meant to apply to any IEEE submission, including JSAC.

This document is **complementary** to the other files in
`papers/how_to_write_good/`. Each section ends with cross-references to
existing files that cover the same ground. Read those first. The value
here is in patterns that surface only because a writing session is long
and instructions had to be repeated.

---

## 1. Plan before you write

> "Writing will actually be relatively easy. The difficult part is planning
> IMO."

The first hours of work on a paper are not "start writing." They are:

1. **Read the source.** Monograph, theory drafts, prior published papers,
   related work in `papers/key_literature/`. For PDFs, convert to PNG and
   read the figures, especially comparison-of-literature figures that
   already do the meta-analysis you would otherwise have to redo.
2. **Write a short, non-styled spine** in markdown. List each section,
   the load-bearing equations, the load-bearing figures, the validation
   that backs each claim.
3. **Adversarial self-review.** How would a reviewer attack the spine?
   What's missing? Where is overlap with prior work that doesn't pay its
   way? What's the weakest link?
4. **Re-spine.** Iterate the markdown until the structure is defensible
   on its own merits.

Only after the spine is stable do you start producing tex. A draft that
"didn't go all the way to the finality" is not a submission, even if it
compiles cleanly.

When the project has a spec and the work is multi-step, this is what
`brainstorming`, `writing-plans`, and the `Plan` agent are for. Use them.

**Cross-refs:** `structural_things_quality.md`, `Summary_Index.md`.

---

## 2. The figure loop is mandatory and physical

The single rule Robin repeated most:

> "Do a big write now, compile, convert to png, read the png files,
> critique visual issues, iterate until satisfied. Especially when latex
> is unusual."

> "actually convert pdf to png and read that png... in the paper it doesnt
> look changed"

The pattern is **not optional and not a one-shot**:

```
write tex → pdflatex → pdftoppm/convert to PNG → Read the PNG → critique
→ edit script or tex → recompile → convert again → re-read → repeat
```

Six iterations on one multi-panel figure was typical, not excessive.
Verification habits Robin uses *himself* and expects from agents:

- Open the rendered PDF, screenshot a problem area, sometimes highlight
  it with markers, paste it back to the agent if needed.
- After every claim of "fixed", **re-render and re-read the PDF**.
  Intermediate state lies. "did u recompile?" is the ambient question.

**Implication for agents:** never claim a fix landed without converting
the *current* PDF to PNG and reading it. Trust the pixels, not the diff.
This applies to whole-paper layout passes too, not just to individual
figures — the only way to spot float-pressure issues, orphaned widows,
or page-eight-mostly-empty problems is to look at every page as a PNG.

**Cross-refs:** `figures_extreme_quality.md` (the 22-rule checklist).

---

## 3. High-level figure thinking, not patching

> "really think high level here about figures. what should we do. not
> just patching here. it could be you even want a brand new figure, or
> a combination of things... let's think what we really need, and what
> we might miss that's important."

Before any figure-edit pass, ask:

1. **Is each panel earning its space, or duplicating?** A panel that
   differs from its neighbour only by a confidence band is not two
   panels. A panel that shows the same trend as another panel with the
   x-axis reversed is not two panels.
2. **Does every label, curve, regime annotation appear in the paper
   text?** Curves named "Level 2", "L3", "L_all" only make sense if the
   levels are defined in-paper. Either rename to descriptive features
   ("Fresnel only", "+ polarisation", "+ curvature & diffraction", "Full
   kernel") or define the levels.
3. **Are there brand names that shouldn't be in a figure?** Internal
   codebase names (e.g. "AEGIS") belong to the implementation, not the
   science. Use generic identifiers in legends and axis labels.
4. **Are there figures that were drafted as internal QA?** Some plots
   are made for the author to track progress. They don't earn a paper
   slot. Each figure has to justify itself against the story.
5. **Is there a figure that is missing?** Configuration / scenario
   figure early on? Phantom-with-colour visualisation for any quantity
   that varies across the body? Flowchart of the computational pipeline?

Only after these questions are answered should you touch font sizes,
legend boxes, or label collisions.

**Cross-refs:** `wout_specific_pet_peeves.md` (#1 flowchart, #2
configuration figure), `figures_extreme_quality.md` rules 1, 2, 22.

---

## 4. Figure plumbing: SciencePlots + LaTeX, IEEE widths

The setup that worked across all the papers in the session:

- All figures use `theory/scripts/_plot_style.py::apply_monograph_style(mode="pdf")`.
  This activates `text.usetex=True` with the monograph's Latin Modern +
  amsmath + bm preamble, rendered through pdflatex+dvipng. SciencePlots
  installed in the venv; dvipng installed system-wide.
- Use `fig_size_ieee(columns, aspect)` returning `(3.5, 3.5*aspect)` for
  single-column and `(7.16, 7.16*aspect)` for two-column-wide
  (`figure*`). Existing `fig_size_textwidth` API kept intact.
- **Output PDF**, save PNG companion alongside for the iteration loop.
- **Colour-blind-safe palettes.** Wong palette
  (`#0072B2 #009E73 #E69F00 #CC79A7 #D55E00 #56B4E9`) plus dash patterns
  for line-shape redundancy.
- **Unfilled markers** with `markerfacecolor="none"`,
  `markeredgewidth=0.9`.
- **Square legend frame**, 1pt black edge, no rounded corners
  (`fancybox=False`, set boxstyle "Square"). Tight padding
  (`borderpad=0.25`, `handlelength=1.2`, `framealpha=0.92`).
- **Subpanel labels**: minimal `(a)`/`(b)` in upper-left of axes, not
  verbose titles. Main caption carries the explanation.
- **Linear-readable tick labels** even on log axes (e.g. `0.5, 1, 2, 5`
  not `10^0`).
- **Body fontsize is the reference**, but legend fontsize may go below
  10pt if density requires (6.0pt is acceptable as a tradeoff).
- **Don't compromise the data area** to fit labels. If the graph isn't
  3.5″ wide it's a layout bug, not an excuse: "We dont need any kind
  of removing of labels or compromises. it's a coding bug."
- **Captions start with a one-sentence high-level summary of what we
  see**, before any formula or list.

**Cross-refs:** `figures_extreme_quality.md` rules 4, 6, 8, 11, 12, 16,
17, 18.

---

## 5. The Wout archetypes: flowchart and configuration figure

Two figure archetypes are non-negotiable in a Wout-style paper:

1. **Flowchart, early.** Black non-rounded rectangles, same fontsize as
   body text, plain arrows, dashed boxes to group blocks. 3.5″ wide,
   variable height. Inputs box, Formula / pipeline box (dashed, label
   *on* the top dashed edge as `-- Formula -----`), Outputs box.
   Side-paths (limits, special cases) live inside the formula box, not
   branching out. Corrections / extensions sit in a small dashed box
   connected by a curved arrow.

   The flowchart for the TAP paper went through five distinct iterations
   (E, E5, E5_io, v2, v3) before landing — that is the expected order
   of magnitude, not an outlier.

2. **Configuration figure as Fig. 1 or Fig. 2.** Whatever the paper is
   simulating, this figure shows it in a nutshell. Place it early. For
   a body-on-radio-channel paper this means: phantom in a known pose,
   excitation symbol on the left, scenario-defining geometry on the
   right, pointer arrows to landmarks ("Thelonious phantom") *placed
   so they don't overlap the phantom*. Privacy boxes on faces /
   sensitive regions placed precisely (re-render and look at the PNG
   until they sit right).

**Both figures live in their own `.tex` file**, are compiled and
rendered to PNG repeatedly until clean, then `\include`d in the main
paper. Don't develop them inline.

If you can do the flowchart and the configuration figure, do them. If
the paper has neither, expect Wout to flag it.

**Cross-refs:** `wout_specific_pet_peeves.md` items 1 and 2.

---

## 6. Mic-drop sentences are the single most-flagged AI tell

Robin called these out three different times:

> "You have a lot of 'mic drop' moments. Like. You are describing
> something, clearly holding yourself in to not splurge, and then say a
> 3 word sentence like 'The physics does not'. No need."

Worked examples that were folded:

- "The activation is exact, not a fit." → folded into the surrounding
  sentence.
- "The error is conservative. The framework underestimates absorption."
  → one combined clause.
- "No fitted parameters." → removed.
- "Five notations, five fits, one underlying ratio." → removed.
- "This paper closes the gap." → removed.
- "Smaller body sizes carry lower thresholds." → folded with preceding
  clause.
- "Both values are moderate." → folded.
- "No FDTD step is in the loop." → folded into preceding sentence.

**Heuristic:** if a sentence is under five words and follows a longer
one that already conveys the point, fold it. **One** deliberate
short-sentence landmark per paper is the maximum (and even that is
optional). The pattern of "long-prose → short-punchline" reads as AI
showmanship.

**Cross-refs:** `style_guide.md` Part A; `ai_writing.md`.

---

## 7. Verb and word substitutions

A representative subset of the substitutions Robin and the cleanup
agents applied. **All went one direction**, and the direction is
shorter / more elementary / more boring:

| Replace                                  | With                          |
|------------------------------------------|-------------------------------|
| yields                                   | gives                         |
| executes (at frame rate)                 | runs                          |
| identifies, characterises (the mech.)    | names, describes              |
| provides a much faster path              | is much faster                |
| obtains, to obtain                       | gets, to get                  |
| demonstrates                             | shows                         |
| utilise                                  | use                           |
| elucidate                                | explain                       |
| in order to                              | to                            |
| significantly, notably, particularly     | (delete)                      |
| very, highly, extremely, fundamentally   | (delete)                      |
| respectively                             | **(allowed freely)**          |
| co-workers                               | **et al.**                    |
| The framework / our framework            | the law / the prediction / the closed form / the construction / (the concrete object) |
| chain, chaining                          | (delete; just state)          |
| converged (the literature has —)         | (delete; just cite)           |
| communities (five — ...)                 | "independent research approaches" or just cite |
| the regulator wants/cares about          | concrete description of the standard / rule |
| ‘exposes’ the anthropometric scaling      | "depends on body shape alone", or similar plain form |
| richly multipath                         | multipath                     |
| fundamentally inapplicable                | does not apply                |
| canonical (X model)                      | (delete)                      |
| captures the dominant physics            | (delete; just describe what the model is) |
| frequency landscape                      | frequency dependence / frequency window of validity |
| fail honestly                            | break down                    |
| The mechanism is general:                | (delete; just continue)       |

The pattern: **shorter, more boring, more elementary verbs.** "Is",
"has", "are", "gives", "shows", "uses". When in doubt, downgrade.

But don't over-do it. Legitimate technical uses survive:

- "carries", "admits", "retains" in operator language stay.
- "dominates" in the literal mathematical sense stays.
- "Three consequences follow" / "Three assumptions apply throughout"
  stay when they actually introduce three items.

**Cross-refs:** `Robin_writing_style.md`; `style_guide.md` Part A.

---

## 8. The introduction is where promotional drift hides

The single most useful message about introductions:

> "for the introduction beginning i really hate this angle of 'the
> regulator wants X'. 'It wants'. Nobody 'wants' something. ... 'The
> dosimetry literature has converged' why the use of the word converge?
> It....hasn't. It just did things. ... 'Five communities' Again I hate
> the angle. They arent communities. ... The contribution chains five
> known results from five fields ... yeah I hate this. ... Even the word
> 'chaining' is... unnecessary throughout the paper. ... In the abstract,
> don't just write 'Azzam's' since nobody has any idea who this guy is."

Distilled rules, applicable to any IEEE paper:

- **No anthropomorphism** of standards bodies, literature, fields, or
  algorithms. They don't "want", "care about", "converge on", or
  "demand" anything. Just say what they specify or report.
- **No grand-narrative framing.** "Five communities", "the literature
  has converged", "we chain five results into one closed form" — drop
  it. Cite the work and state the result.
- **No name-dropping in the abstract.** "Azzam's identity" /
  "Smith's bound" / "the Foschini limit" is fine in the body once the
  result has been introduced. In the abstract, the reader hasn't met
  these names. Reframe to plain prose ("a published identity for...",
  or just describe it).
- **Precision over generality** for technical claims. If APD applies
  above 6 GHz and psSAR10g for basis restrictions, say so. The fear of
  being pinned down is what drives vague phrasing — and Robin will pin
  it. "specify either or both, depending on frequency and scenario" is
  the kind of sentence that gets called out.
- **Quantitative numbers** in the abstract. "10^12 cells" is not the
  same as "**up to** 10^12 cells at 100 GHz on an adult phantom". Say
  the regime where the number applies. An error is not "an error" — it
  is precise to its third or fourth significant figure.

**Cross-refs:** `wydaeghe_introduction_anatomy.md`; `style_analysis.md`;
`wout_specific_pet_peeves.md` item 5 (abstract).

---

## 9. No subsections in the introduction

> "Dont cut up an intro into subsections (i think this is unusual)."

The IEEE intro is one unified narrative arc: literature, gap,
contributions, roadmap, all as flowing paragraphs. The roadmap paragraph
at the end of the intro can list sections via `\Cref`, but it stays a
paragraph.

**Cross-refs:** `wydaeghe_introduction_anatomy.md`.

---

## 10. IMRaD is not mandatory in IEEE flagship journals

> "I've looked at several papers and many appear to stick with main
> section titles that are NOT introduction methods results discussion
> conclusion. ... I was under the belief that literally every IEEE
> paper needs IMRAD kinda and that you only get freedom to name
> subsections."

IMRaD is one common structure, not a hard rule. IEEE TAP, TWC, and
JSAC all accept custom top-level section titles when they fit the
content better.

When the structure does fit IMRaD, fine. When it doesn't, **don't force
it**. The bigger sins are:

- Duplicate section/subsection titles ("Coherent absorption law" inside
  "Coherent absorption law" — rename the subsection to something like
  "Reduction to a squared norm" or "Statement and proof").
- `The`-prefixed headings.
- Clever poetic titles ("Quantitative landscape", "Frequency
  landscape").
- Subsections that preview rather than say what they contain
  ("Setup. The next subsection derives...").

**Cross-refs:** `structural_things_quality.md`.

---

## 11. Section titles are plain noun phrases

> "the subtitles should be deadsimple and clear (not 'What this paper
> is' lol....)"

Examples of renamings from the session:

- "Mechanism" (parent + child) → "Physical mechanism" for the child.
- "The geometric absorption law" → "Geometric absorption law".
- "Quantitative landscape" → "Quantitative behaviour across angle and
  polarisation".
- "Frequency landscape" → "Frequency dependence" or "Frequency window
  of validity".
- "Generalised Cauchy formula" inside "Generalised Cauchy formula" →
  "Statement and proof".

**Sentence case throughout.** Never title case.

---

## 12. Standalone is non-negotiable; overlap is fine

> "A big blunder too is for them to be referencing 'as in paper A'. We
> can't have that. It's standalone. But overlap is okay you know."

Both subtle and overt forms get removed:

- All "in companion Paper~B/C" prose phrases.
- All `\cite{...}` placeholders for unpublished sister papers, unless
  there is a clear plan that they will be on arXiv before submission.
  "fake-cite it if you want but the best would be not to, for now"
  applies to anything you don't actually have on arXiv.
- Roadmap paragraphs that reference undefined section labels
  (`sec:branches`, `sec:Q`, etc.).

If the JSAC paper's content also appears in a TAP paper, the JSAC paper
must derive what it needs from first principles for its own readers.
Cross-citing a sister paper as a *prior published* work (with a real
DOI / arXiv ID) is fine. Cross-citing a sister paper as "in
preparation" is not.

The exception: explicit short letter formats (e.g. AWPL) where you
cite sister papers as if published. Don't generalise that licence.

---

## 13. Abstracts are dense, precise, and name-free

Reinforcing rules from `wout_specific_pet_peeves.md` item 5:

- Don't name-drop authors in the abstract. The reader hasn't met them.
- If you say "10^12 cells", say "**up to** 10^12 at 100 GHz on an adult
  phantom" or similar.
- "shows a 4 to 5 reduction" → "shows a **factor of** 4 to 5 reduction"
  (unambiguous units).
- Numbers in the abstract should match the body to the third or fourth
  significant figure. The abstract is not the place to round freely.

---

## 14. Front matter: copy the TAP paper

For author block, ORCID placement, `\IEEEmembership`, `\thanks`,
acknowledgments, biographies, manuscript-date placeholders,
`\bibitem` style, and so on, **use `papers/TAP_paper/paper.tex` as the
template.** That paper resolved every front-matter decision through a
long audit cycle and is the canonical reference for this group.

A few decisions that came out of that cycle and propagate as defaults:

- **American spelling** (polarization, behavior, modeling, color, gray,
  meter, center, program). British is a common project habit, but
  IEEE house style is American.
- **No-space percent**: `5.6%`, not `5.6\,\%`.
- **Manual `\bibitem`** rather than BibTeX, for full control.
- **Funding in the Acknowledgment section**, not in `\thanks`.
- **Corresponding-author email in `\thanks`**; ORCID **not** in
  `\thanks` (use the inline-byline style from
  `papers/example_papers/main_iopjournal.tex` and `oldest_paper.tex`).
- **Co-author bios** copied as single paragraphs from
  `papers/example_papers/oldest_paper.tex`.
- **Acronym capitalisation** in body text matches the acronym:
  "Transverse Electric (TE)", not "transverse electric (TE)".
- **No `\gls{}` in keywords.** Just write the acronym. Keywords are
  short and generic.
- **Units in `[ ]`**, not `( )`.
- **`et al.`** always over "co-workers".
- **Nothing about AI** in front-matter unless the venue requires it.

For LaTeX micro-rules (`\,` between number and unit, `\cite{}` ties,
math-text spacing for units, etc.), see
`latex_rules_extreme_quality.md` and read the TAP paper's preamble.

For "approx." in text, **write the word "approx."**, not `\approx`.

**Cross-refs:** `journal_front_matter.md`,
`latex_rules_extreme_quality.md`, `papers/TAP_paper/paper.tex`.

---

## 15. Paragraphing and prose rhythm

1. **Mimic literature paragraph blocks.** Large blocks of contiguous
   text, not a new paragraph every other sentence. Justified text. Use
   real paragraph breaks for real paragraph transitions.
2. **Subject–verb–rest** in the present tense by default. Calm,
   neutral. "The experiment shows a higher X value."
3. **Long subject–verb–[list-tail] sentences are welcome**, not the
   failure mode. After the subject-verb stem the reader handles the
   cognitive load every time, no matter how many list items follow.
   The long-sentence failure mode is *subordinate-clause-heavy*
   construction, not *list-tail* construction. (`Robin_writing_style.md`
   3a; `style_guide.md` C12.)
4. **"respectively" / `resp.` carries no cognitive-load penalty.** Use
   freely whenever a parallel construction is clearer than splitting
   into two sentences. (`Robin_writing_style.md` 3b; `style_guide.md`
   C13.)
5. **No semicolons** in body prose. Split into sentences. ";" survives
   only in the preamble's `\Crefname` declarations.
6. **No em dashes** in body prose. Hyphens in compounds and `--` in
   bibliography part-separators are fine.

**Cross-refs:** `Robin_writing_style.md`; `style_guide.md` Part B
(Strunk + Cargill); `wydaeghe_style_analysis.md`.

---

## 16. Listening, persistence, and not being lazy

> "Most of it has been done, but sometimes you just dont listen.
> Instruct agents to be precise and persistent and not lazy."

When Robin gives an instruction and a follow-up review shows it wasn't
applied, that's a serious signal. Common failure modes:

- The agent claimed it was fixed without re-rendering and verifying.
- The agent applied it in one of three sister papers and forgot the
  others.
- The agent fixed the mention closest to the cursor but missed the ten
  other instances.
- The agent followed the instruction once at the start of a long task
  and didn't carry it forward.

When you claim a fix:

- After every edit pass, recompile, convert to PNG (for figures), or
  grep (for prose patterns), and verify.
- For prose patterns, **count occurrences before and after**: if the
  before/after grep counts are equal, the edit didn't apply or didn't
  apply globally.
- For figure changes, the only acceptable evidence is the rendered PNG
  read directly.

Worth adopting: when reviewing your own work before declaring it done,
run an **AI-tells audit** as a separate pass with a fresh agent and a
clean grep sweep. The session showed that even after multiple rounds
of editing, a dedicated audit still finds things — and the edits *do*
land when applied via a dedicated "scrub" pass.

**Cross-refs:** the `verification-before-completion` skill;
`STYLE_REVIEW_STATUS.md` and `REVISION_NOTES.md` in the TAP paper
directory are good audit-log templates.

---

## 17. Honest reflection on the spine, willingness to pivot

> "We planned the 3 papers to have these 3 topics, but are they good
> topics? ... it's not just yes/no im asking you here, im asking in
> general, what if we rethink a bit the spines of these paper(s) big
> picture? ... reflect on the papers in their finality. Is this truly
> something that lands on their own? why yes or not? be balanced honest
> (that means it CAN be a total yes, or a total no, or a maybe, idk)
> based on real funded opinion"

After hours of agent work producing polished drafts, a single
external input (the promotor's "three is too many") can — and
should — cause a re-spining. The agent must be willing to mark its own
work as ill-conceived if a reframing serves the project better. Sunk
cost on tex wordsmithing is not a reason to defend a structure that's
wrong.

When asked for an honest opinion, give the honest opinion. Robin
explicitly allows "total yes, total no, or maybe, idk". A bland "all
options have merit" answer is an actively bad answer. Pick a
direction, defend it, flag the trade-off, offer one alternative if
there is a real one.

Avoid: "Here are five considerations, you decide."
Prefer: "Option B, because of X. The cost is Y. If you weight Z higher,
switch to Option C."

For a JSAC paper this means: before locking in a structure, ask
whether the natural framing is information-theoretic, system-level,
geometry-first, or measurement-first, and pick. Be willing to
reconsider mid-draft if the spine isn't working.

**Cross-refs:** `feedback_brainstorm_voice.md` in user memory.

---

## 18. Use the existing rule files (and pass them to subagents)

When Robin tells you to read style files, he expects you to read all of
them, not pick and choose:

> "read papers/how_to_write_good/style_guide.md
>      papers/how_to_write_good/style_analysis.md
>      papers/how_to_write_good/elos.md
>      papers/how_to_write_good/ai_writing.md"

> "If you'd have ambitiously and precisely followed
> papers/how_to_write_good/figures_extreme_quality.md it would have
> been better. and also dont forget
> papers/how_to_write_good/journal_front_matter.md
> papers/how_to_write_good/latex_rules_extreme_quality.md
> papers/how_to_write_good/structural_things_quality.md"

The rule-file ecosystem is treated as canon. If your output violates
one of them, you've failed. **Read them again at the start of each
writing session,** not just at the start of a project.

Spawn a subagent to audit the draft against each file, line by line,
with grep counts. **Always pass the rule-file paths in the prompt** so
the subagent reads them too.

The current set, briefly:

- `Robin_writing_style.md` — short KISS rules.
- `ai_writing.md` — AI-tells, exhaustive.
- `style_guide.md` — three-part guide (AI-tells, Strunk/Cargill, voice).
- `style_analysis.md` — monograph patterns analysed.
- `figures_extreme_quality.md` — figure checklist.
- `journal_front_matter.md` — author block, ORCID, etc.
- `latex_rules_extreme_quality.md` — LaTeX micro-rules.
- `structural_things_quality.md` — paper structure conventions.
- `wout_specific_pet_peeves.md` — the project-specific non-negotiables.
- `wydaeghe_introduction_anatomy.md` — intro structure template.
- `wydaeghe_style_analysis.md` — wider style audit.

**Two files are book-sized and not for the main thread:**

- `Writing_Scientific_Research_Articles.md` — Cargill & O'Connor,
  ~1440 lines.
- `elos.md` — Strunk's *Elements of Style*, ~1045 lines.

These are reference books, not house style. Only spawn subagents to
read them (and only when a specific question warrants it — e.g.
"Cargill on how to handle the discussion section", "Strunk on
participial phrases"). Do not load them into the main conversation
context. Their voice is also not particularly close to the project's
style, so apply with judgement: they inform craft, they don't dictate
it. The project-specific files above override them where they
disagree.

---

## 19. Open-ended questions get committed answers

A few stylistic notes about how Robin asks questions:

- "Be balanced honest" / "Give honest opinion" / "Be ambitious. Go." /
  "Impress me." — these are standing orders, not platitudes.
- "I am giving a vague prompt but also expect a generalist answer.
  Like, 'what would you do'."
- "you can TOTALLY tell me yes if you believe so" — when asked for
  an opinion that contradicts your default.
- "give honest opinion" + "if it CAN be a total yes, total no, or
  maybe, idk".

Robin **wants** dissent and pushback when the work warrants it. Pick a
direction, defend it, flag the trade-off you're making, and offer one
alternative if there is a real one.

**Cross-refs:** `feedback_brainstorm_voice.md` in user memory.

---

## 20. The conversation log is the source of truth

When agents disagreed about whether a thing had been requested, the
answer was always to go back to the conversation log and check.

For any long writing project, treat the conversation as a reference
document:

- Save the conversation log as you go (or extract it later via the
  jsonl in `~/.claude/projects/`).
- When in doubt about whether an instruction landed, grep the log for
  the relevant phrase.
- When delegating audit work to subagents, hand them the log file (or
  the relevant slice) so they can self-resolve disputes.

This file is itself such an artifact — distilled from the TAP-paper log
so the JSAC session doesn't have to re-derive these lessons.

---

## 21. Where each nugget lives in the canonical files

Most of the portable nuggets from this session have been promoted into
the existing rule files as additions (not edits). This document remains
the long-form context and process record; the canonical home of each
rule is one of:

- **Figures:** `figures_extreme_quality.md` rules 24-28 (PNG iteration
  loop, high-level questions precede patching, no brand names in
  figures, whole-paper PNG reading, "wide enough is a coding bug").
- **Wout pet peeves:** `wout_specific_pet_peeves.md` items 7-11 (no
  brand names, standalone is non-negotiable, no abstract
  name-drops, no anthropomorphism, abstract precision).
- **Structural process:** `structural_things_quality.md` rules 56-60
  (plan-before-write, re-spining, listening across edits, IMRaD not
  mandatory, no intro subsections).
- **Style — AI tells:** `style_guide.md` Part A rules A21-A24 (mic-drop
  stingers, internal-codebase brand names, anthropomorphism,
  grand-narrative framing).
- **Style — voice:** `style_guide.md` Part C rules C12-C14
  (subject-verb-[list] is welcome, "respectively" carries no penalty,
  no cross-references to unpublished sister papers).
- **LaTeX micro-rules:** `latex_rules_extreme_quality.md` rules 66-78
  ("et al." globally, "approx." in text, no `\gls{}` in keywords,
  acronym capitalisation, units in `[]`, American spelling, no-space
  percent, `\Cref` over `\cref`, math-text unit consistency, bold
  convention, abstract precision).

If you find a rule that's missing from those files, add it there (not
here). This document is the process and rationale store; the rule files
are the authoritative reference.

---

*Source: `session_7dc0a8d1_user_messages.txt`, the extracted
user-message stream of the TAP-paper writing session. Numbered
references in earlier drafts pointed to messages in that file.*
