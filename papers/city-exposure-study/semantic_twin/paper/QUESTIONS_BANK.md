# Questions bank

These questions do not block a complete scientific draft. Provisional text is
used where needed and is marked here rather than scattered through the paper.

1. Resolved on 2026-08-27. The author order is Robin Wydaeghe, G\"unter
   Vermeeren, Emmeric Tanghe, and Wout Joseph. The byline contains the confirmed
   IEEE membership grades and ORCIDs. All authors use the Ghent University/IMEC
   affiliation, and Robin Wydaeghe is the corresponding author at
   `robin.wydaeghe@ugent.be`.
2. What funding statement and grant numbers belong in the first-page footnote?
None
3. Resolved on 2026-08-27. The biographies use `figures/rw.png`,
   `figures/gv.png`, `figures/et.png`, and `figures/wj.png` for Robin Wydaeghe,
   G\"unter Vermeeren, Emmeric Tanghe, and Wout Joseph, respectively.
4. Is the working title, "Image-informed urban propagation and route-level body
   exposure at 15 GHz," the preferred final title?
Prolly not, feel free to think of a good one. I tend on the longer side. Has to contain the word exposure and 10 cities.
5. What public code and data archive should the availability statement name?
   A versioned DOI is preferable before submission.
\hl{TODO}
6. Please approve the required IEEE AI-use disclosure. The draft says that
   OpenAI Codex was used for manuscript drafting, editing, plotting code, and
   manuscript checks, and that the authors verified the claims, numbers,
   references, and final text.
Just write less specifically about codex (it's complicated). KISS. AI was used.
7. Confirm that the production tissue database version is IT'IS 4.2 and that
   the final paper should retain this version instead of updating the inputs.
What? how is this relevant?
8. Confirm whether the graphical abstract should use the configuration figure
   alone or a simplified panorama-to-route-result strip.
Stop caring on this
9. The AEGIS v0.39.1 repository is currently private. Which public archive or
   DOI should replace the software citation before submission?
\hl{TODO}. Tbh I wouldnt really lean too much on AEGIS here. I think something like "it is just Absorption Cross Section (ACS)" is sufficient. Esp dont go saying level-2 dosimetry that is not a real thing that anybody understands. Perhaps using ACS is a bit awkward in the formulas. If so, just keep it chill. Very chill. Say we approximate it by T0 for incoherent unpolarized EMF and boom.
10. Should the final submission use the current regular IEEE Access route, or
    should it still be redirected to a named Special Section if one opens?
IEEE ACcess
11. The acknowledgment currently credits only OpenAI Codex. This rewrite was
    done with Anthropic Claude. Should the acknowledgment cite both, or replace
    the Codex reference?
AI use is enough lmao. Dont acknowledge anything there.
12. Fig. 1a: the bottom 30% of the image appears to be dead space. Crop it?
Yes, but didnt u already? 
13. Fig. 5a: the raw CDF looks irregular because line-of-sight dominance
    compresses most points into a narrow band while the six shadowed points
    create a long lower tail. Would a multipath-surplus CDF be a better primary
    figure, with the raw CDF kept as supplementary or secondary?
Yes but not primary. I think both should be shown close to each other.
14. Fig. 5b (route-mean component bar chart): is this panel worth keeping in the
    main paper, or should the component shares move to the supplementary
    material? The paper narrative is stronger around route-level exposure
    variation than around internal transport decomposition.
Probably in SI, I think. If it isnt too big of an issue. If you do include it: 0 to 100 in log scale and dont do those funky stripped patterns etc. KISS on the colors.
15. NUMBER INCONSISTENCY between abstract and conclusion. Both numbers are
    real (per RESULTS_INVENTORY): 0.0344 dB = adjoint vs Sionna for TOTAL
    transport, 0.0621 dB = adjoint vs Sionna for the REFLECTED term only.
    The abstract reports 0.0616 (vs quadrature, reflected) and 0.0344
    (vs Sionna, total). The conclusion reports 0.0616 (vs quadrature,
    reflected) and 0.0621 (vs Sionna, reflected). Pick one pair and use it
    consistently. The 0.0344 total-transport number is the more conservative
    claim.
Uhhh whatever u think is best. We are adding new cities anyways.
16. The ten-location geometric fixed-grid screening is now complete (64 points,
    16 seeds, geometry-based materials, all ten cities authenticated). The
    discussion mentions it as a supplementary diagnostic. Should the main paper
    cite any headline number from it (e.g., the roughly twofold location-to-location
    span), or should it remain supplement-only?
It turns out this was with a 'shortcut' to compute them faster. They are now running the normal way. We will slide in those new results some day. But for now pretend like the new results are just like the old results, to be slotted in. And dont mention this in the text

## OJ-COMS revision, 2026-08-27

17. Resolved on 2026-08-27. Robin confirmed that the production surface-label
    stage uses the SAM~3 Agent variant. The paper now identifies SAM~3 Agent as
    the agentic AI stage. Historical planning documents that describe this
    stage as future work are superseded for the manuscript.

18. The stable public code and data archive is still missing. The draft can be
    completed with a factual availability statement, but the DOI and final
    repository URL must be supplied before submission.

19. Resolved on 2026-08-27. The byline links Robin Wydaeghe to
    `0000-0002-1374-0118`, G\"unter Vermeeren to `0000-0002-5309-3808`,
    Emmeric Tanghe to `0000-0003-0020-6466`, and Wout Joseph to
    `0000-0002-8807-0673`.

20. The official OJ-COMS template prints received, revised, accepted,
    publication, and current-version dates. The draft keeps the official
    `XX Month, XXXX` placeholders. Replace them only when the journal supplies
    the dates.

21. Resolved on 2026-08-27. Retain the requested "in Ten Cities" title. The
    methods and results identify the selected route and observation points in
    each city directly.

22. The special-issue page links to ScholarOne, while the general OJ-COMS page
    points to the newer IEEE submission portal. Confirm the active portal when
    the submission package is uploaded.

23. IEEE asks authors to identify the system, affected sections, and level of
    use when generative AI produced substantive article content. The current
    acknowledgment follows the requested short generic wording. Confirm whether
    a more specific disclosure is required for this submission.

24. Resolved on 2026-08-27. `claude --model claude-opus-4-6` completed the
    requested independent review. Its report is preserved in
    `versions_and_feedback/claude_opus_flow_review.md`.
