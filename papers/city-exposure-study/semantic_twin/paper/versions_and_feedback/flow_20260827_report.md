# Final flow and synchronization report

## Introduction and meso-scale flow

The opening paragraph now states the complete causal chain. Urban geometry and
materials change the power and directions that reach the pedestrian. Body
orientation then changes how those arrivals couple into the body. This makes
the need to retain arrival direction a consequence of the physical argument,
not a detached rule.

The prior-work sequence moves from route propagation and source normalization
to the missing surface information, then to the combined method. One repeated
`However` was removed. Connectors remain only where the relationship is causal
or sequential.

## Figures, tables, and workflow

Figure and table introductions now say what role each item plays before it
appears. The route-results introduction also states that the distributions and
component shares cover all 163 observation points.

The flowchart is referenced five times in the paper and five times in Chapter
6. The discussion returns to it when explaining the 14.31-fold route contrast.
The arrows were checked from the TikZ source and from the rendered PNG at full
resolution. They encode these dependencies:

1. Street images feed AI object and material labels.
2. Labels, 3-D geometry, route and body setup, and possible roofline
   transmitters feed the human-centric digital twin.
3. The twin feeds direct and reflected directional arrivals.
4. The arrivals are applied to the body to obtain whole-body SAR.

The two central labels were shortened to `AI assigns object and material
labels` and `Compute direct and reflected radio arrivals`. Paper and thesis use
identical flowchart source, PDF, and PNG files.

## Agentic AI and scope

The abstract, introduction, method, and conclusion identify SAM~3 Agent as the
agentic AI stage. The method explains its contribution through prompt-guided
material concepts that extend fixed object classes with material evidence.

Scope statements were phrased as descriptions of the modeled routes, source
model, frequency, body model, and surface labels. The title decision in the
question bank is resolved in favor of the requested title.

## Paper and thesis synchronization

The prose changes were mirrored where the paper and Chapter 6 share the same
argument. Chapter 6 retains its thesis-specific validation, convergence,
budget-sensitivity, and cross-chapter synthesis.

The independent reviews found two stale lower-decile values. The current
generated route-results record gives Mexico City
$q_{10}=1.0052271467418079\times10^{-6}$~m$^2$~kg$^{-1}$ and Tokyo Hachiko
$q_{10}=3.634582286181274\times10^{-5}$~m$^2$~kg$^{-1}$. The paper table now
matches Chapter 6 at the rounded values $1.01\times10^{-6}$ and
$3.63\times10^{-5}$, respectively.

## Layout and QA

Chapter 6 keeps the convergence, route figure, route table, material analysis,
and budget-sensitivity items in source order. The full thesis remains 230
pages, and the final route-results spread was inspected page by page. The paper
remains eight pages with all four author biographies on page 8.

Final automated checks:

- PaperMaker lint: 0 flags.
- PaperMaker style scan: 0 hits after allowlisting.
- PaperMaker claim checks: 13 run, 0 failed.
- PaperMaker test suite: passed.
- Paper and thesis builds: passed.
- Final source diff checks: passed.
- Final logs: no undefined references or citations.
- Paper and Chapter 6 prose: no em dashes or semicolons.

The completed Claude Opus 4.6 review reported no must-fix scientific or
structural issue. Its accepted and rejected suggestions are recorded in
`claude_opus_flow_review.md`.
