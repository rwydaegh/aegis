# Current paper figures

These figures use the current five-city `first_material_interaction_v1` result
or a current-compatible controlled validation. They replace the stale
eleven-city figure set for the IEEE Access paper.

Every scientific plot has a PNG review copy, a PDF publication copy, a source
script, and a JSON audit or authenticated asset manifest. The flowchart uses a
standalone TikZ source. The figure scripts fail when the expected data contract
or source hash changes.

## Figure 1. Configuration

Files:

- `configuration/configuration.py`
- `configuration/configuration.tex`
- `configuration/configuration.pdf`
- `configuration/configuration.png`
- `configuration/configuration_assets.json`

Draft introduction: “The study configuration is shown in Fig. 1.”

Draft caption: “Configuration of the image-informed fixed-route study in
Prague. A registered panorama supplies surface evidence to the traced support
and material field. The current simulation uses a 250 m-radius support mesh, a
502-element roofline source curve, 22 fixed route standpoints, and a 56,024-
element anatomical surface with route-tangent orientation.”

The panorama and campaign assets are separately authenticated. They share the
same Prague geometry, but the figure does not imply that one panorama observes
the complete current route.

## Figure 2. Flowchart

Files:

- `flowchart/flowchart.tex`
- `flowchart/flowchart.pdf`
- `flowchart/flowchart.png`

Draft introduction: “The processing flowchart is shown in Fig. 2.”

Draft caption: “Flowchart of the proposed method. A registered panorama and the
support mesh define a fused material surface. The roofline source curve and the
fixed pedestrian route define the simulation configuration. Exact direct,
exact order-1 specular, and first-diffuse transport are coupled to the body and
summarized as fixed-route distributions.”

## Figure 3. Controlled validation

Files:

- `validation/make_validation.py`
- `validation/validation.pdf`
- `validation/validation.png`
- `validation/validation.audit.json`

Draft introduction: “The controlled first-diffuse validation is shown in Fig.
3.”

Draft caption: “Controlled depth-1 validation for six receivers, 27 sources,
and eight triangles at 15 GHz. The adjoint first-diffuse estimate and an
independent Sionna RT forward calculation are compared with deterministic surface quadrature.
The bars show seed variation. This test validates first-diffuse normalization
and geometry terms. It does not validate the complete city material and
specular stack.”

## Figure 4. Fixed-route results and components

Files:

- `route_results/make_route_results.py`
- `route_results/route_results.pdf`
- `route_results/route_results.png`
- `route_results/route_results.json`

Draft introduction: “The five fixed-route distributions are shown in Fig. 4.”

Draft caption: “Normalized whole-body SAR on the five fixed routes. The
empirical CDFs include all 73 standpoints and mark the six zero-direct and
zero-specular points. The second panel gives additive route-mean whole-body SAR
shares. The routes are fixed case studies, not city or population samples.”

The older `results/` and `components/` figures remain as authenticated detailed
diagnostics. They are not used in the main manuscript.

## Supplementary figure. Convergence

Files:

- `convergence/make_convergence.py`
- `convergence/convergence.pdf`
- `convergence/convergence.png`
- `convergence/convergence.audit.json`

Draft caption: “Absolute 12-to-16-replica change in normalized whole-body SAR.
Circles show the fixed-route median. Triangles show the largest change among
standpoints in the final lower decile. Every route median changes by at most
\(5.91\times10^{-5}\) dB, while the Mexico City and Tokyo lower tails remain
less stable.”

## Supplementary figures. Material-evidence control

Files:

- `../../outputs/roofline_campaign/material_evidence_ablation/madrid_plazamayor/`
- `../../outputs/roofline_campaign/material_evidence_ablation/mexico_zocalo/`

Draft caption: “Paired atlas-evidence versus geometric-fallback control with
geometry, route, source, seeds, transport, and body model fixed. The route
median normalized whole-body SAR changes by +0.249 dB in Madrid and -0.158 dB
in Mexico City. The large Mexico City lower-tail change occurs at three
shadowed points where first-diffuse transport is the only nonzero modeled contribution.”

The Mexico City panel uses a wide vertical scale because the paired values at
the shadowed points are both near zero. It belongs in the supplementary
material. The main text should report the visible and shadowed strata
separately.

## Regeneration

Run Python figures from the semantic-twin root with the shared plotting
environment:

```bash
uv run --extra paper python paper/figures/route_results/make_route_results.py
uv run --extra paper python paper/figures/convergence/make_convergence.py
uv run --extra paper python paper/figures/validation/make_validation.py
uv run --extra paper python paper/figures/configuration/configuration.py
```

Compile the standalone TikZ flowchart from its directory:

```bash
pdflatex -interaction=nonstopmode -halt-on-error flowchart.tex
pdftoppm -png -r 300 -singlefile flowchart.pdf flowchart
```

After every change, inspect the PNG at full size and at approximate two-column
print size. Before manuscript submission, render the complete paper to PNG and
inspect every page.
