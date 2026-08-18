# Current supplementary-information source

This directory contains the PaperMaker paragraph tree for the current ten-site
result and the separate geometric diagnostic. The root is `si_new.md`. Its LaTeX body is designed for inclusion after
the main paper or assembly as a separate supplement with the main paper's
preamble and bibliography.

The source uses only the current `first_material_interaction_v1` campaigns. It
does not use the superseded 11-site, three-bounce, masonry, RCWA, or hybrid
results.

Build the standalone supplement from `semantic_twin/paper`:

```bash
uv run --project /home/user/PaperMaker9000 papermaker assemble si_new \
  --out build/supplement_body.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error \
  -output-directory=build si_new/supplement_wrapper.tex
```

Authoritative numerical sources are:

- `semantic_twin/docs/CURRENT_PRODUCTION_CONTRACT.md`
- `semantic_twin/docs/RESULTS_INVENTORY.md`
- `semantic_twin/docs/MATERIAL_EVIDENCE_ABLATION.md`
- `semantic_twin/outputs/roofline_campaign/current_five_city_first_material_interaction/`
- `semantic_twin/outputs/roofline_campaign/material_evidence_ablation/`
- `semantic_twin/outputs/experiments/ray_reached_evidence_coverage_v1/`
- `semantic_twin/outputs/experiments/current_topology_convergence64_v1/`
- `semantic_twin/outputs/experiments/ten_city_route_extension64_v1/report/`
- `semantic_twin/outputs/experiments/roofline_budget_sensitivity_v1/`
