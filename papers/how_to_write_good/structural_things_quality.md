# Structural Conventions for IEEE Journal Papers (TAP, TWC, JSAC, TCOM, etc.)

These are conventions and tendencies for serious flagship IEEE journals, not hard rules — but deviating without reason will read as inexperience to the editorial board.

## Length and scope

1. **Abstract:** 150–250 words, single paragraph. No citations, no equations, no undefined acronyms. Often the only thing read at editor desk-screen and reviewer-assignment stage, so it carries disproportionate weight. Should state problem, approach, key technical novelty, headline quantitative result, and significance.
2. **Total length:** journal regular papers typically 10–14 pages in two-column IEEE format; some journals (TAP, TWC) accept up to ~30 pages but charge overlength fees beyond ~8–10 printed pages. Letters/communications are 4–5 pages and a different beast.
3. **References:** flagship journal papers commonly carry 30–60+ references. A TAP/TWC paper with under 20 references will look under-grounded unless the topic is genuinely narrow.
4. **Self-citation calibration:** citing your own prior work is expected and good (establishes the research arc), but more than ~20% of references being self-cites starts to look insular.

## The four niches: abstract, introduction, conclusion, and (often) discussion

In a serious journal paper these need to be cleanly distinguished. The failure mode of saying the same thing four times is more visible at this length.

5. **Abstract** is the elevator pitch. Compressed, outcome-focused. No narrative.
6. **Introduction** tells the story: motivation, prior art landscape, gap, contribution, organization. Builds the case for why this paper exists.
7. **Discussion / Results interpretation** (sometimes its own section, sometimes folded into Results) is where you reflect on what the numbers mean, edge cases, comparison to prior art quantitatively, and limitations.
8. **Conclusion** is short and forward-looking. Reflects on implications now that the reader has seen everything, points to genuine open problems. Not a re-summary.

If sentences are interchangeable across these four, restructure.

## Introduction structure (the "five-paragraph intro" pattern, loosely)

A flagship journal intro is typically 1.5–2.5 pages and follows a recognizable arc:

9. **Paragraph 1: Context and motivation.** Why this problem matters in the broader field. Often opens with the application driver (5G/6G, mmWave deployment, EMF compliance, etc.).
10. **Paragraph 2–3: State of the art.** A structured tour of prior work, often grouped thematically rather than chronologically. Each group cited densely. This is where most of the references appear.
11. **Paragraph 4: The gap.** Explicit identification of what existing work does not address. Phrased as limitations of the prior art, not as criticism. "However, [11]–[15] do not consider..." or "To the best of the authors' knowledge, no prior work has..."
12. **Paragraph 5: Our contribution.** What this paper does. Often ends with an explicit numbered or bulleted contribution list (3–5 items, each verifiable).
13. **Paragraph 6: Organization.** "The remainder of this paper is organized as follows..." One sentence per section. Some reviewers consider this dated but the majority of journal papers still include it.

A teaser figure (system model, scenario illustration, headline result) on page 1 or 2 is common and helps reviewers orient.

## Related work as its own section vs. folded

14. **Folded into intro** works for narrower topics with ~20–30 references.
15. **Separate Section II "Related Work" or "Background"** is more common when there are 40+ references or multiple distinct prior-art threads to contrast. Don't do both — either the intro covers it or a separate section does.

## System model / problem formulation

16. **Notation block** at the start of the methods, often as a paragraph or a small notation table. Define vector/matrix conventions, sets, operators, before any equation uses them. Reviewers will flag inconsistent notation hard.
17. **Assumptions stated explicitly,** ideally numbered or in a clearly demarcated subsection. Channel models, statistical assumptions, hardware constraints. A reviewer asking "is this assuming X?" because the assumption was implicit is a guaranteed revision request.
18. **Reuse standard notation** from the subfield where possible (TAP papers use the EM conventions; TWC papers use the comms conventions). Inventing new notation for things that have established symbols is a red flag.

## Methods / proposed approach

19. **Build up incrementally.** Subsection per logical block (channel model → signal model → exposure model → optimization formulation, for example). Each subsection self-contained.
20. **Theorems, lemmas, propositions** numbered globally or per-section. Proofs either inline (if short) or in an appendix (if long enough to break flow). A flagship journal paper often has at least one formally stated result.
21. **Algorithms** in `algorithm` environments with line numbers and a caption. Complexity analysis usually follows.

## Results section

22. **Simulation/measurement setup subsection first.** Reproducibility-grade detail: parameters, software (with versions), hardware, geometry, tolerances. A TAP reviewer will check whether you specified mesh size, solver, boundary conditions; a TWC reviewer will check SNR ranges, channel realizations, Monte Carlo counts.
23. **Validation / benchmark comparison early in the section.** Show your method matches a known case before showing new results.
24. **Headline result figure(s)** prominent, often on page boundaries.
25. **Sensitivity / parameter sweeps** to show robustness. Single-point results in a flagship paper read as preliminary.
26. **Quantitative comparison to prior art** — a table benchmarking against [N], [M], [K] is often expected. Saying "our method is better" without numbers is insufficient at this tier.
27. **Negative or surprising results acknowledged** rather than hidden. Increases credibility with reviewers.

## Discussion (when separate)

28. **Interpretation, not restatement.** What do the numbers mean physically, operationally, regulatorily?
29. **Limitations explicit.** Range of validity, computational cost, scenarios not covered. Pre-empts reviewer concerns.
30. **Practical implications** — for TAP, what does it mean for antenna design or measurement; for TWC, what does it mean for system deployment or standardization.

## Conclusion

31. **Short:** half a column to one column for a long paper. Disproportionately short conclusions are normal in flagship journals; bloated conclusions look padded.
32. **Three beats:** what was shown (one paragraph, in past tense, distinct from the contribution list in the intro), what it means (implications), what's next (real open problems, not wishlist items).
33. **No new results, no new figures, no new equations** in the conclusion.

## Acknowledgments and back matter

34. **Acknowledgments** before references. Funding agencies with grant numbers (often required by funders), people who helped but aren't authors. Keep brief and factual.
35. **Appendices** for long proofs, derivations, parameter tables, supplementary measurements. Each appendix self-contained with an opening sentence stating its purpose. Lettered (Appendix A, B, ...).
36. **Biographies** at the end of the paper, with photo, for journals that require them (TAP, TWC do). 100–150 words each, third person, covering education, current affiliation, research interests, IEEE membership grade, awards. Check the journal's exact format.

## Tone and voice for flagship journals

37. **First-person plural** is standard. "We propose," "we show," "we derive."
38. **Hedging calibrated tightly.** Flagship-journal reviewers are sensitive to oversell. "Optimal" means provably optimal; "novel" needs justification; "significant" needs a number. Replace marketing language with technical language.
39. **Tense:** present for the paper itself ("Section III presents..."), past for what was done ("we conducted simulations..."), present for general truths and stable findings.
40. **Avoid colloquialisms, contractions, and first-person singular.** "Don't" → "do not." "I" almost never appears.

## Things that signal a paper not yet ready for a flagship

41. Conclusion paraphrasing the abstract.
42. Fewer than ~25 references on a topic that has substantial prior literature.
43. No quantitative comparison to prior art.
44. Single-point results without sensitivity analysis.
45. Notation introduced inconsistently across sections.
46. Assumptions implicit rather than stated.
47. Limitations section absent or one sentence.
48. Future work as a wishlist rather than rooted in identified limitations of the present work.
49. Figures referenced out of order in the text.
50. Acronyms redefined multiple times in the body, or used before definition.
51. Reproducibility detail thin enough that a competent reader could not re-implement.

## The flagship-journal meta-questions

52. **Would a reviewer in this subfield learn something they didn't know?** Below this bar, the paper goes to a less selective venue.
53. **Could a competent graduate student in the subfield reproduce the central result from the paper alone?** If not, the methods or results sections need more detail.
54. **Does the contribution list in the intro match what the paper actually delivers?** Reviewers check this explicitly. Overclaiming is the fastest path to a major revision or rejection.
55. **Is each figure load-bearing?** In a 12-page paper, every figure should earn its space. Decorative figures get cut.

## Process: plan, write, listen, re-spine

56. **Plan before you write.** Before producing any tex, read the source material (monograph, prior published work, related literature). Write a short, non-styled spine in markdown listing each section, the load-bearing equations, the load-bearing figures, the validation that backs each claim. Run an adversarial self-review: how would a reviewer attack the spine? Where is content that doesn't pay its way? Iterate the spine until defensible. *Only then* start producing tex. A draft that "didn't go all the way to the finality" is not a submission, even if it compiles cleanly.

57. **Re-spining is allowed and often correct.** Polished drafts are not a reason to defend a spine. A single external input (a promotor's "three papers is too many", a reviewer's "I don't see the contribution") can warrant tearing down the structure mid-project. Sunk cost on wordsmithing is not a defense. When asked for an honest opinion on whether the spine works, give it ("total yes", "total no", "maybe" are all valid answers); don't deflect with "all options have merit".

58. **Listening across edits is itself a deliverable.** A long writing session involves dozens of small directives. Common failure modes: applying a fix near the cursor but missing the ten other instances; applying it in one sister paper and forgetting the others; "fixing" without re-rendering and verifying. After every edit pass, recompile, convert to PNG (figures and whole pages), grep before/after (prose patterns) and count occurrences. Equal counts mean the edit didn't land. Lazy partial application is a flagged failure.

59. **IMRaD is not mandatory in flagship IEEE journals.** Custom top-level section titles ("System and notation", "Geometric absorption law", "Path-space factorisation", "Exposure-constrained beamforming") are accepted by TAP, TWC, and JSAC when they fit the content better than Introduction–Methods–Results–Discussion–Conclusion. When IMRaD fits, use it; when it doesn't, don't force it. Bigger sins than non-IMRaD structure: duplicate section/subsection titles ("Coherent absorption law" inside "Coherent absorption law"), "The"-prefixed headings, clever poetic titles ("Frequency landscape"), subsections that preview rather than contain ("Setup. The next subsection derives...").

60. **No subsections in the introduction.** The intro is one unified narrative arc: context, prior art, gap, contribution, organization, all flowing paragraphs. The roadmap paragraph at the end can list sections via `\Cref`, but it stays a paragraph. Cutting the intro into subsections is unusual and reads as inexperience.