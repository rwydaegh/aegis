# Questions bank

These questions do not block a complete scientific draft. Provisional text is
used where needed and is marked here rather than scattered through the paper.

1. What is the final author list, order, IEEE membership status, affiliation,
   email address, and ORCID for each author?
   Robin Wydaeghe, G\"unter Vermeeren, Emmeric Tanghe, Wout Joseph. U can take a look at semantic_twin/paper/IEEE_Access_paper_submit.zip it has literally all u could ever need (go hard on stealing stuff from it)
2. What funding statement and grant numbers belong in the first-page footnote?
None
3. Which biography text and headshot should be used for each author?
See above
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

