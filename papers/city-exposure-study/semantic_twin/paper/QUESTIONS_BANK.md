# Questions bank

These questions do not block a complete scientific draft. Provisional text is
used where needed and is marked here rather than scattered through the paper.

1. What is the final author list, order, IEEE membership status, affiliation,
   email address, and ORCID for each author?
2. What funding statement and grant numbers belong in the first-page footnote?
3. Which biography text and headshot should be used for each author?
4. Is the working title, "Image-informed urban propagation and route-level body
   exposure at 15 GHz," the preferred final title?
5. What public code and data archive should the availability statement name?
   A versioned DOI is preferable before submission.
6. Please approve the required IEEE AI-use disclosure. The draft says that
   OpenAI Codex was used for manuscript drafting, editing, plotting code, and
   manuscript checks, and that the authors verified the claims, numbers,
   references, and final text.
7. Confirm that the production tissue database version is IT'IS 4.2 and that
   the final paper should retain this version instead of updating the inputs.
8. Confirm whether the graphical abstract should use the configuration figure
   alone or a simplified panorama-to-route-result strip.
9. The AEGIS v0.39.1 repository is currently private. Which public archive or
   DOI should replace the software citation before submission?
10. Should the final submission use the current regular IEEE Access route, or
    should it still be redirected to a named Special Section if one opens?
11. The acknowledgment currently credits only OpenAI Codex. This rewrite was
    done with Anthropic Claude. Should the acknowledgment cite both, or replace
    the Codex reference?
12. Fig. 1a: the bottom 30% of the image appears to be dead space. Crop it?
13. Fig. 5a: the raw CDF looks irregular because line-of-sight dominance
    compresses most points into a narrow band while the six shadowed points
    create a long lower tail. Would a multipath-surplus CDF be a better primary
    figure, with the raw CDF kept as supplementary or secondary?
14. Fig. 5b (route-mean component bar chart): is this panel worth keeping in the
    main paper, or should the component shares move to the supplementary
    material? The paper narrative is stronger around route-level exposure
    variation than around internal transport decomposition.
15. NUMBER INCONSISTENCY between abstract and conclusion. Both numbers are
    real (per RESULTS_INVENTORY): 0.0344 dB = adjoint vs Sionna for TOTAL
    transport, 0.0621 dB = adjoint vs Sionna for the REFLECTED term only.
    The abstract reports 0.0616 (vs quadrature, reflected) and 0.0344
    (vs Sionna, total). The conclusion reports 0.0616 (vs quadrature,
    reflected) and 0.0621 (vs Sionna, reflected). Pick one pair and use it
    consistently. The 0.0344 total-transport number is the more conservative
    claim.
16. The ten-location geometric fixed-grid screening is now complete (64 points,
    16 seeds, geometry-based materials, all ten cities authenticated). The
    discussion mentions it as a supplementary diagnostic. Should the main paper
    cite any headline number from it (e.g., the roughly twofold location-to-location
    span), or should it remain supplement-only?
