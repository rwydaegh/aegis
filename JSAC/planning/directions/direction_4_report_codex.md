# Direction 4 report codex

## scope

This report compiles the direction 4 theory into a code-backed AEGIS case study.
The theory note is in `JSAC/direction_4_problem_codex.tex`.
The reproducible simulation code is in `JSAC/direction_4_sim_codex/real_phantom_case_study_codex.py`.
The generated output is in `JSAC/direction_4_sim_codex/real_phantom_case_study_codex.json`.

The question is simple:

- when does the ICNIRP `4 cm^2` local APD constraint become tighter than whole-body `SARwb`
- can coherent MIMO produce that crossover at modest array sizes

## theory in one page

For coherent dosimetry, the monograph gives

$$
S_{\mathrm{ab}}(\mathbf{r};\mathbf{x}) = \|\widetilde{\mathbf{G}}(\mathbf{r})\mathbf{x}\|^2
$$

and the whole-body exposure operator

$$
\mathbf{Q} = \int_{\Sigma} \widetilde{\mathbf{G}}(\mathbf{r})^H \widetilde{\mathbf{G}}(\mathbf{r})\,\mathrm{d}A,
\qquad
P_{\mathrm{abs}}(\mathbf{x}) = \mathbf{x}^H \mathbf{Q} \mathbf{x}.
$$

Whole-body SAR is then

$$
\mathrm{SAR}_{\mathrm{wb}}(\mathbf{x}) = \frac{P_{\mathrm{abs}}(\mathbf{x})}{m}.
$$

The spatial-compliance object is not one matrix but a family of local matrices:

$$
\mathbf{Q}_A(\mathbf{r}_0)
=
\int_{\Sigma}\omega_A(\mathbf{r}_0,\mathbf{r})
\widetilde{\mathbf{G}}(\mathbf{r})^H\widetilde{\mathbf{G}}(\mathbf{r})\,\mathrm{d}A,
$$

so that the `A`-patch averaged APD is

$$
S_{\mathrm{ab},A}(\mathbf{r}_0;\mathbf{x}) = \mathbf{x}^H \mathbf{Q}_A(\mathbf{r}_0)\mathbf{x}.
$$

This gives the downlink problem

$$
\max_{\mathbf{x}} |\mathbf{h}^T\mathbf{x}|^2
$$

subject to

$$
\mathbf{x}^H\mathbf{Q}\mathbf{x} \le m\,\mathrm{SAR}_{\mathrm{wb}}^{\max},
\qquad
\max_{\mathbf{r}_0\in\Sigma}\mathbf{x}^H\mathbf{Q}_A(\mathbf{r}_0)\mathbf{x}
\le S_{\mathrm{ab},A}^{\max},
\qquad
\|\mathbf{x}\|^2 \le P.
$$

Define the hotspot concentration factor

$$
\eta_A(\mathbf{x})
=
\frac{\max_{\mathbf{r}_0} S_{\mathrm{ab},A}(\mathbf{r}_0;\mathbf{x})}
{P_{\mathrm{abs}}(\mathbf{x})/A_\Sigma}.
$$

Then APD binds before `SARwb` if and only if

$$
\eta_A(\mathbf{x})
>
\eta_A^{\mathrm{th}}
=
\frac{S_{\mathrm{ab},A}^{\max}A_\Sigma}{m\,\mathrm{SAR}_{\mathrm{wb}}^{\max}}.
$$

For ICNIRP public mmWave limits,

$$
S_{\mathrm{ab},4\mathrm{cm}^2}^{\max} = 20~\mathrm{W/m^2},
\qquad
\mathrm{SAR}_{\mathrm{wb}}^{\max} = 0.08~\mathrm{W/kg},
$$

so

$$
\eta_{4\mathrm{cm}^2}^{\mathrm{th}} = 250\,A_\Sigma/m.
$$

Representative thresholds from the monograph:

| body type | mass `m` (kg) | surface area `A_\Sigma` (m²) | `eta_th` |
| --- | ---: | ---: | ---: |
| adult | 70 | 1.8 | 6.43 |
| child | 20 | 0.8 | 10.0 |
| infant | 8 | 0.4 | 12.5 |

The coherent-hotspot argument from the monograph says local peaks can scale like `N^2` while total absorbed power stays `O(N)`. That means `eta` can grow roughly linearly with the number of coherently aligned paths. For adults, the local constraint can already overtake `SARwb` once the hotspot is only about `6.4x` above the whole-body mean APD.

## code path

The report uses existing AEGIS primitives rather than a new physics model.

- `src/aegis/coherent/body_channel.py`
  `compute_body_channel()` builds the coherent body-surface channel `\widetilde{G}`.
- `src/aegis/coherent/exposure_operator.py`
  `compute_exposure_operator()` builds the global exposure matrix `Q` as the area-weighted Gram integral.
- `src/aegis/geometry/averaging.py`
  `precompute_averaging_matrix()` builds the sparse row-stochastic `4 cm^2` averaging matrix `G_A`.

The `_codex` script combines them as follows:

1. Load `data/thelonious.stl`.
2. Build the existing AEGIS `4 cm^2` averaging matrix.
3. Generate one equal-power path per antenna element on a `20°` cone around `-\hat{x}`.
4. Build `\widetilde{G}` with `compute_body_channel()`.
5. Build the global operator `Q`.
6. Build the local family
   `Q_local[m] = sum_i G_A[m,i] G_i^H G_i`.
7. For each path count `N`, find the worst patch `m*` by maximizing `lambda_max(Q_local[m])`.
8. Use the dominant eigenvector of that worst local operator as the precoder.
9. Compare worst local APD to the whole-body mean absorbed power density.

This is not a full communications design loop. It is a clean stress test for the geometry of the constraint itself.

## reproducible case study

Run:

```bash
python3 JSAC/direction_4_sim_codex/real_phantom_case_study_codex.py
```

The script is repo-local and bootstraps `src/` onto `sys.path`, so it runs from a checkout without requiring `pip install -e .`.

### phantom and tissue

- phantom: `thelonious`
- triangles: `23,826`
- surface area: `0.78658 m^2`
- height: `1.18205 m`
- tissue model: `SKIN_28GHZ`
- frequency: `28 GHz`
- patch area: `4e-4 m^2`

### results

The JSON output gives:

| paths `N` | worst `4 cm^2` APD | `P_abs` | whole-body mean APD | `eta_4cm2` | adult binds first | child binds first | infant binds first |
| ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: |
| 1  | 0.5386 | 0.1047 | 0.1331 | 4.0467 | no | no | no |
| 2  | 0.9296 | 0.1397 | 0.1776 | 5.2344 | no | no | no |
| 4  | 0.9296 | 0.1397 | 0.1776 | 5.2345 | no | no | no |
| 8  | 1.8859 | 0.1210 | 0.1539 | 12.2557 | yes | yes | no |
| 16 | 3.7559 | 0.1257 | 0.1598 | 23.5104 | yes | yes | yes |

Two patterns matter.

- `P_abs` stays almost flat across the sweep. It moves between `0.1047` and `0.1397` in these normalized units.
- The worst `4 cm^2` local APD does not stay flat. It rises from `0.5386` at `N=1` to `3.7559` at `N=16`.

That is exactly the structure direction 4 needs. The global absorbed-power budget barely moves, but the local hotspot factor moves a lot.

## interpretation

The fixed-geometry conclusion from this run is:

- with `N=1,2,4`, the hotspot factor is below every threshold, so whole-body SAR would remain the tighter limit
- with `N=8`, `eta_4cm2 = 12.26`, which is already above the adult and child thresholds
- with `N=16`, `eta_4cm2 = 23.51`, which is above adult, child, and infant thresholds

So the answer is yes. Even in a simple coherent cone model on a real phantom, local APD can overtake whole-body `SARwb` well before anything dramatic happens to total absorbed power.

Another useful detail is that the worst patch index stayed fixed at `14654` across the sweep. In this setup the hotspot location is geometrically stable while its severity grows with coherent path count. That suggests a reduced-patch formulation may be practical once a likely hotspot region is known.

## what this does and does not show

What it shows:

- the local-operator formulation is already implementable in AEGIS
- the crossover criterion is numerically modest
- a real phantom can exceed that criterion under coherent buildup

What it does not show:

- it is not a scene-traced ray-tracing study
- it does not optimize the communications objective `|h^T x|^2`
- it does not solve the full multi-constraint ECBF problem yet
- it does not include temporal thermal averaging of the Zhou type

## next steps

The next useful steps are straightforward.

1. Replace the single global `Q` in ECBF with a finite active set of local operators `Q_{A,m}`.
2. Compare three precoders on the same scene: MRT, global-`Q` ECBF, and local-operator ECBF.
3. Repeat the case study on a ray-traced channel rather than the synthetic cone model.
4. If the Zhou thermal framing is needed, drive the thermal state with worst-patch APD rather than total absorbed power alone.

## bottom line

Direction 4 is no longer just a vague idea. The right object is a mesh-indexed local operator family, and the right summary statistic is

$$
\eta_{4\mathrm{cm}^2}
=
\frac{\max_m \mathbf{x}^H \mathbf{Q}_{4\mathrm{cm}^2,m}\mathbf{x}}
{(\mathbf{x}^H\mathbf{Q}\mathbf{x})/A_\Sigma}.
$$

Once

$$
\eta_{4\mathrm{cm}^2} > 250\,A_\Sigma/m,
$$

the `4 cm^2` local APD limit binds before whole-body `SARwb`. The `thelonious` run in this report crosses that threshold at `N=8` for adults and children, and by `N=16` for infants too.
