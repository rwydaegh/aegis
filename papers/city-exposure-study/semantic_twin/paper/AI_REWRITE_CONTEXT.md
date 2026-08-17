# Context for a future paper rewrite

This is standing context for another AI that will work on this paper. It is not
a line-by-line prompt, a replacement for the scientific sources, or an
instruction to begin work merely because this file was opened. The concrete
assignment will be given separately.

## What Robin wants

The paper should be clear, confident, technically serious, and pleasant to
read. Robin is open to a fairly strong rewrite of both sentences and content.
The writer does not need to preserve awkward wording, inherited paragraph
shapes, or repository jargon. Meaning must be preserved, however. Numerical
claims, scientific scope, qualifications, provenance, and distinctions between
different experiments must not drift in the pursuit of smoother prose.

This is more freedom than the earlier request to make only minimal edits while
sliding new results into an existing draft. That earlier warning was mainly
against replacing the paper, deleting useful results, or recasting a modest
update as an entirely different study. It was not a request to protect bad
sentences forever. A future writer may substantially improve the exposition and
organization, but should understand the existing argument before changing it
and should retain material that still earns its place.

The finished paper must read as one coherent study written for a new reader. It
must not read as a changelog, a conversation with the author, or a story about
how one version became another. Present the final method and evidence directly,
as if they had been designed correctly from the start.

## The desired voice

Robin strongly prefers concrete writing. Use ordinary nouns and simple verbs.
Choose the phrase a technically literate reader will understand on first
reading, even when an internal report or codebase uses a more specialized term.
Professional does not mean stiff. Simplicity does not mean writing for a child.

Repository vocabulary should always be treated with suspicion. A term may be
precise inside the software and still be a poor choice in the paper. Words such
as *atlas*, *standpoint*, *support*, *sealed record*, *scene evidence*, and
*body yaw* are examples of the broader problem: they hide a concrete object or
action behind an unfamiliar label. Either name the object plainly or define the
technical term where it is genuinely needed. The same principle applies to
heavy grammar. Prefer a direct sentence over a sentence that a reader has to
unpack twice.

The prose should have some character and rhythm. It should not become a sequence
of clipped textbook statements. A restrained broad opening sentence in the
Introduction is welcome when it helps place the problem, but avoid generic
throat-clearing and inflated importance claims. Do not force every paragraph to
begin with a summary sentence. Let the logic of the argument determine the
paragraph shape.

The PaperMaker9000 anti-AI guidance matters in particular. Avoid formulaic
transitions, canned contrasts, empty signposting, grand claims, invented
jargon, needless abstraction, and language that makes methods, results, or
figures behave like people. Robin's own scientific voice may override a minor
house preference when the two genuinely conflict, but it does not override the
anti-AI standard. The aim is not to mechanically remove a list of forbidden
words. The aim is prose that sounds focused because the writer understands the
science.

## Story and explanation

Begin with the paper's spine: what problem is being solved, why the chosen
comparison answers it, what evidence supports the method, and what the results
allow the reader to conclude. The section structure and individual paragraphs
should serve that story. Do not preserve a weak structure merely because it is
already present, but do not reorganize for novelty alone.

Explain the core idea in physical, visual terms before relying on formal names.
For this paper, a reader should quickly understand that street-level imagery is
projected onto three-dimensional city geometry, that transmitters are placed
along rooflines for a reason, that rays are traced in the computationally useful
direction, and that the arriving power is converted into exposure on a human
body model. Equations should sharpen that picture rather than substitute for
it. Check notation against the actual model and conventional mathematical use.

Keep the scope unusually clear. Distinguish route-based production results from
fixed observation-point diagnostics, geometric materials from image-derived
materials, and normalized comparisons from claims about deployed networks or
populations. Do not pool or rank results that answer different questions. State
important design restrictions where a first reader needs them, including in a
caption when that is where confusion is most likely.

Results should lead with the quantities that carry the argument. Strong or
memorable numbers are useful when they are honestly representative of the
declared analysis. Do not bury an interesting effect simply because it is
dramatic, but do not cherry-pick beyond the experiment's scope. Preserve the
less glamorous evidence needed to make the headline result credible.

## Figures and tables

Figures should be improved as part of the rewrite, not treated as fixed
decoration. Each figure should make the method or result easier to understand
at the scale at which it appears in the assembled paper. Prefer a clean visual
explanation over dense panels whose meaning exists only in the caption.

For this study, useful visual language includes recognizable buildings,
attractive map-like ground plans, clear routes or observation points, roofline
transmitters, the image-to-geometry step, and a legible explanation of adjoint
ray tracing. Existing historical figures may provide good ideas, but they are
not scientific authority and should be reused only when they fit the current
study. Improve an existing figure by adding a well-chosen line, panel, or entry
when that genuinely adds information. Redesign it when incremental additions
would make it crowded.

Plots should look deliberate and consistent with the paper. Use SciencePlots
where appropriate. Labels, legends, notation, colors, and captions should use
reader-facing language rather than pipeline terminology. Captions should stand
on their own and make the comparison and its limits clear. Always judge figures
inside the built paper, not only as large source images. Iterate until text is
readable and there are no overlaps, clipped elements, confusing backgrounds, or
badly balanced panels. Keep figure generation reproducible and tied to
authenticated data.

Tables should earn their density. A large table can work well when it keeps a
major comparison in one clean block and makes its scope obvious. Avoid mixing
secondary variants into that block merely because the data exist. Smaller
follow-up analyses can form a second logical block if that reads more clearly.

## Scientific integrity

Writing quality cannot repair an unsupported claim. Read the current scientific
authority files and executable claims before revising a result. If a report or
the manuscript contains a physics mistake, correct it directly for the reader
and flag the underlying issue to Robin. Never write from the point of view of
the internal debugging history.

Preserve uncertainty, limitations, and the exact population to which a claim
applies. Be especially careful with language that turns a conditional or
site-specific result into a general city claim. Keep enough provenance that
figures and tables can be regenerated and audited. If a proposed simplification
would change the scientific meaning rather than merely clarify it, stop and
make that choice explicit.

## How to use the local guidance

PaperMaker9000 is the detailed working framework, but it is a general ruleset,
not scripture. Apply its meaning with judgment. Story and scientific honesty
come first; its style and anti-AI guidance should then be used aggressively to
improve the execution. Where rules conflict, use Robin's current instruction
and demonstrated voice, while retaining the strict anti-AI standard.

The main references are:

- `/home/user/PaperMaker9000/corpus/INDEX.md`, the entry point to the rule
  corpus, its precedence, structural guidance, style rules, and figure rules.
- `/home/user/PaperMaker9000/corpus/examples/wydaeghe_style_analysis.md`, a
  useful analysis of Robin's preferred research-group voice.
- `semantic_twin/docs/instructions_pm9k.md`, Robin's project-specific
  interpretation of PaperMaker9000 and the IEEE Access target.
- `semantic_twin/paper/comments_for_new_paper.md`, concrete first-reader
  reactions to this manuscript. The examples are local, but the underlying
  preference for clear words and visible explanations applies throughout.
- `semantic_twin/paper/READ_THIS_FIRST.md` and `semantic_twin/paper/spine.md`,
  for the canonical manuscript, present scope, and argument.
- `semantic_twin/docs/RESULTS_INVENTORY.md` and
  `semantic_twin/docs/CURRENT_PRODUCTION_CONTRACT.md`, for numerical and method
  authority.
- `semantic_twin/paper/paper.tex` and `semantic_twin/paper/paper.pdf`, only as
  historical sources of potentially useful visual ideas, not as authorities for
  current claims.

The canonical main manuscript is the paragraph tree under
`semantic_twin/paper/main/`; the supplement is under
`semantic_twin/paper/si_new/`. Work through those sources and regenerate their
assembled parents rather than editing build products as if they were canonical.

## Standard of completion

A rewrite is not complete when the prose merely sounds smoother. Read the whole
paper again as a skeptical first-time reader. Check that the basic idea is
visible early, terms are understandable on first use, each section advances the
same story, claims retain their exact scope, and figures genuinely explain what
the text asks the reader to imagine.

Then use the relevant PaperMaker lint, style, lens, claim, assembly, citation,
and build checks. Inspect the actual diff so that useful material has not
vanished unnoticed. Render every page and review it visually at publication
scale, including fonts, labels, float order, references, clipping, and figure
balance. The final test is whether a careful reader can understand the work
without access to the repository, the development history, or the conversation
that produced it.
