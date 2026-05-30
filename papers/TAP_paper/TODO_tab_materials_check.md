# TODO: tab:materials variation column is wrong for all tissues except skin

*Found 2026-05-24 while building the patent concept slides. Verified by direct Fresnel
computation against both the TAP fixed dielectric values and the AEGIS IT'IS Cole-Cole
model. The two agree. Only the skin row of `tab:materials` is correct.*

## The problem

`tab:materials` (paper.tex, around line 590) and its caption state that the variation
column is "the maximum deviation of $\Tavg/T_0$ from unity over $[0^\circ, 75^\circ]$."
Under that exact metric, the table's numbers do not reproduce:

| Tissue | table says | actual max dev. over [0,75] | flux-weighted dev. ($T_0/\bar T - 1$) |
|--------|-----------:|----------------------------:|--------------------------------------:|
| Skin   | 5.6%  | **+5.7%** (correct)  | -1.2% |
| Muscle | 4.8%  | **+12.6%** (wrong)   | -2.9% |
| Fat    | 8.2%  | **-17.4%** (wrong)   | +4.6% |
| Water  | 3.9%  | **+20.3%** (wrong)   | -5.1% |

No single consistent metric reproduces the published column: skin's 5.6% is the raw
pointwise max-deviation, but muscle/fat/water's small numbers match neither the raw
pointwise deviation (10-22%) nor the flux-weighted deviation (skin would then be 1.2%,
not 5.6%). The likely cause is a per-row bug in the table-generating script. The fat
$T_0=0.77$ in the table also does not match its own $\varepsilon_r=4.0,\sigma=2.0$
(which give $T_0=0.876$).

## Why it matters

The paper is near submission and underpins the patent. An examiner or reviewer who
recomputes $\Tavg(75^\circ)$ for water gets +20%, not 3.9%, and the "tissue universality"
claim looks overstated.

## The fix (physically correct framing)

The pointwise $\Tavg(\theta)$ genuinely is **not** flat to 75 deg for the higher-index
tissues, that is true and should be stated. The defensible universality is about
**absorbed power**, not raw transmission: since $\APD \propto T(\theta)\cos\theta$, the
grazing-angle overshoot is suppressed by the $\cos\theta$ projection, and the
flux-weighted (direction-averaged) deviation stays within ~5% for every tissue. This is
exactly what $R(f)=T_0/\bar T$ already shows. Recommended:

1. Either recompute the variation column correctly (raw pointwise) and add a second
   flux-weighted column, or
2. Replace the column with the flux-weighted deviation and adjust the prose so the
   universality claim is about direction-averaged absorbed power, not pointwise $\Tavg$.

Skin's pointwise 5.6%-to-75-deg claim elsewhere in the paper is correct and can stay.

Verification snippet (uses the AEGIS tissue model): see
`presentations/patent_concepts/scripts/skin_depth_plot.py` for the model access pattern;
the deviation computation is a few lines of Fresnel ($r_s,r_p$) over $\theta\in[0,75]$.
