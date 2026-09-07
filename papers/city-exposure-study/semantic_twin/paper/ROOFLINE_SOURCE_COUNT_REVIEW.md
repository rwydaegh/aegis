# Review of the roofline source-count model

## Verdict

The current mathematics is valid as a standardized conditional illumination
law. It is not a defensible estimate of how many deployed base stations lie on
the extracted roofline.

The equation

$$
N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}}
$$

gets the count entirely from the area of the 250 m crop. The roofline enters
only after that count has been chosen. Normalizing its element lengths as

$$
p_i=\frac{\ell_i}{\sum_j\ell_j}
$$

then forces all of the crop's source mass onto the route-visible curve. No
roofline observation supplies evidence about the count. The model therefore
means: assume a common expected number of active sources in every equal-area
crop, then condition their locations to be uniform in arc length on the
extracted roofline.

That is a reasonable controlled comparison if stated as a hypothetical source
law. It should not be called a model that determines the number of base
stations along a roofline.

## Exact probabilistic interpretation of the current equation

Let $\Gamma_c$ be the extracted roofline for city $c$, let $ds$ be the selected
arc-length measure, and let

$$
L_c=\int_{\Gamma_c} ds.
$$

A precise generative interpretation consistent with the current calculation is
a Poisson point process on the curve with intensity measure

$$
\Lambda_c(ds)
=\rho_A\frac{A_{\mathrm{crop}}}{L_c}\,ds.
\tag{1}
$$

Consequently,

$$
N_c\sim\operatorname{Poisson}(\rho_A A_{\mathrm{crop}}),
\qquad
S_k\mid N_c=n\overset{\mathrm{iid}}{\sim}
\frac{ds}{L_c}.
\tag{2}
$$

For a linear incoherent endpoint $h(\mathbf{x},s)$ produced at receiver
$\mathbf{x}$ by a unit-EIRP source at $s$, Campbell's theorem gives

$$
\frac{\mathbb{E}[Y_c(\mathbf{x})]}
     {\rho_A P_{\mathrm{EIRP}}}
=\frac{A_{\mathrm{crop}}}{L_c}
 \int_{\Gamma_c} h(\mathbf{x},s)\,ds.
\tag{3}
$$

The paper's quadrature $p_i=\ell_i/L_c$ is the discrete form of (3). The code
evaluates this expectation directly. It does not draw a random count or random
deployments. The Poisson construction is not uniquely implied by the output.
Any count model with the same mean and independent conditional locations has
the same first moment. A count distribution must be declared only if the paper
claims deployment variability.

This interpretation makes the present equations coherent, but it also exposes
their assumptions.

## What is weak in the present physical interpretation

### Area does not imply roofline count

An areal density gives an expected count in an area only for a point process
defined on that area. Equation (1) instead defines a point process on a curve.
The factor $A_{\mathrm{crop}}/L_c$ is an unobserved map from ground area to
roofline length. The paper currently treats that map as physical scaling even
though it is a modeling convention.

### The extracted curve receives all source mass

The route-visible roofline is not the full set of deployable roofs in the crop.
Visibility from the selected route, route length, panorama support, mesh
quality, and the curve-merging algorithm all affect $\Gamma_c$. Equation (1)
nevertheless assigns every expected crop source to this subset.

### The implied linear intensity changes substantially by city

The authenticated campaign identities record the following physical 3D support
lengths:

| Site | $L_c$ (m) | $A_{\mathrm{crop}}/L_c$ (m) |
|---|---:|---:|
| Korenmarkt | 157.545 | 1246.31 |
| Madrid | 79.405 | 2472.77 |
| Mexico City | 63.694 | 3082.69 |
| Prague | 267.152 | 734.97 |
| Tokyo Hachiko | 248.755 | 789.33 |

For a common $\rho_A$, the source intensity per roofline metre is
$\rho_A A_{\mathrm{crop}}/L_c$. It is therefore 4.19 times larger in Mexico
City than in Prague. This difference is introduced to make the total expected
count the same in both equal-area crops. It is not supported by deployment
data.

### The law is not stable under an expanding observation window

If an additional roofline segment is observed, $L_c$ increases and the source
intensity on every previously observed segment decreases. A physical point
process should normally be restriction-consistent: observing a larger window
adds possible sources without changing the local intensity on the old window.
The normalized conditional law intentionally lacks that property.

### A site is not necessarily one active radiator

$P_{\mathrm{EIRP}}$ belongs to a transmitting sector, panel, beam, or another
declared active entity. A base-station site can contain several such entities
with different azimuths, powers, loads, and duty cycles. The manuscript should
use *active transmitter* or *active radiating entity* unless the conversion
from sites to radiators is modeled explicitly.

### Physical 3D length is not the natural default for an areal law

If source opportunities are tied to map-plane building frontage or rooftop
footprint, horizontal projected arc length $ds_{xy}$ is the natural measure.
Physical 3D length gives additional source weight to slopes and vertical
reconstruction variation. It is appropriate only if placement opportunity is
truly proportional to distance along the sloped parapet or ridge.

### Only the mean deployment is represented

The 16 replicas measure numerical first-diffuse estimator variation. They do
not represent uncertainty in source count, source location, activity, EIRP, or
antenna orientation. Equation (3) is an ensemble mean. It is not the
distribution of exposure across possible deployments.

## Recommended mathematics for this paper

The cleanest choice, given that no deployment data are used, is not to infer a
source count. Separate the conditional roofline response from an external
network multiplier.

Choose a nonnegative opportunity weight $q_c(s)$ and define the probability
measure

$$
\pi_c(ds)
=\frac{q_c(s)\,ds}
       {\int_{\Gamma_c}q_c(u)\,du}.
\tag{4}
$$

The per-active-transmitter response is

$$
R_c(\mathbf{x})
=\int_{\Gamma_c}h(\mathbf{x},s)\,\pi_c(ds).
\tag{5}
$$

For an externally supplied expected active-transmitter count $\mu_c$ and a
common EIRP,

$$
\mathbb{E}[Y_c(\mathbf{x})]
=\mu_c P_{\mathrm{EIRP}}R_c(\mathbf{x}).
\tag{6}
$$

The geometry study should report $R_c$, or the body endpoint derived from it,
per unit $\mu_cP_{\mathrm{EIRP}}$. It should state that $\mu_c$ is not estimated
here. A later deployment study can supply it.

With $q_c(s)=1$, the archived output is related to this response by

$$
\frac{\mathbb{E}[Y_c]}{\rho_A P_{\mathrm{EIRP}}}
=A_{\mathrm{crop}}R_c.
\tag{7}
$$

All five sites use the same $A_{\mathrm{crop}}$. Dividing the existing linear
endpoints by $A_{\mathrm{crop}}$ would therefore change their displayed scale
but preserve every between-site ratio, dB contrast, component share, and route
ordering. No transport rerun is needed for this reframing.

This is the strongest formulation that the present evidence supports. It says
what the solver measures without attaching an unvalidated count to it.

## Better mathematics for a physical deployment model

If the goal changes to deployment prediction, use a marked inhomogeneous point
process on eligible rooflines:

$$
\Phi_c\sim\operatorname{PPP}(\Lambda_c),
\qquad
\Lambda_c(ds,dm)=\lambda_c(s)\,ds\,F_c(dm\mid s).
\tag{8}
$$

The mark $m$ contains at least active EIRP, antenna orientation, activity, and
sector or beam identity. The aggregate endpoint and its first two moments are

$$
Y_c(\mathbf{x})
=\sum_{(s,m)\in\Phi_c}h(\mathbf{x},s,m),
\tag{9}
$$

$$
\mathbb{E}[Y_c]
=\int h(\mathbf{x},s,m)\,\Lambda_c(ds,dm),
\qquad
\operatorname{Var}(Y_c)
=\int h(\mathbf{x},s,m)^2\,\Lambda_c(ds,dm),
\tag{10}
$$

where the variance expression is for a Poisson process. A clustered or
repulsive process can replace the PPP if deployment data support it.

Two useful intensity models are available.

### Line-intensity model

For a common active-transmitter density $\rho_L$ per metre of eligible
plan-view roofline,

$$
\lambda_c(s)=\rho_L q_c(s),
\qquad
\mathbb{E}[N_c]
=\rho_L\int_{\Gamma_c}q_c(s)\,ds_{xy}.
\tag{11}
$$

This model lets a city with more eligible roofline contain more sources. It is
locally defined and restriction-consistent. It requires calibration of
$\rho_L$ and $q_c$.

For uniform $q_c$, the existing city results can be converted from the current
per-$\rho_A P_{\mathrm{EIRP}}$ scale to a per-$\rho_L P_{\mathrm{EIRP}}$ scale
by multiplying each city's linear endpoints by $L_c/A_{\mathrm{crop}}$. This
will change between-city results because the current law deliberately removes
the effect of total roofline length.

### Building-catchment model

A more credible bridge from an areal density to roofline placement associates
each eligible building $b$ with an opportunity area $A_b$, an eligibility or
availability factor $\eta_b$, and an eligible curve $\Gamma_b$. Define

$$
Q_b=\int_{\Gamma_b}q_b(u)\,du
$$

and

$$
\lambda_c(s)
=\rho_A\eta_b A_b\frac{q_b(s)}{Q_b},
\qquad s\in\Gamma_b.
\tag{12}
$$

Then

$$
\mathbb{E}[N_c]
=\rho_A\sum_b\eta_b A_b.
\tag{13}
$$

This model states the missing area-to-roofline map instead of hiding it in
$A_{\mathrm{crop}}/L_c$. Roof footprint, parcel area, or another audited
opportunity area can define $A_b$. Deployment records should calibrate
$\eta_b$, $q_b$, the mark law, and any exclusion or clustering behavior.

The current model is the special case of (12) in which the whole crop is one
pseudo-building, $A_b=A_{\mathrm{crop}}$, $\eta_b=1$, and every metre of the
extracted route-visible curve is equally eligible. Written this way, the
strength of that assumption is clear.

## Manuscript-safe replacement that preserves the current results

The following text can replace the current source-count paragraph without
changing the calculation or any reported number.

```tex
The calculation uses a standardized conditional source process, not an
observed deployment. Let $\Gamma_c$ be the route-visible roofline in city $c$,
with physical arc length $L_c$, and let $\rho_A$ denote a hypothetical mean
density of active transmitters in the crop. We define a Poisson process on
$\Gamma_c$ with intensity measure
\begin{equation}
  \Lambda_c(ds)
  =\rho_A\frac{A_{\mathrm{crop}}}{L_c}\,ds,
  \qquad
  \mathbb{E}[N_c]=\rho_A A_{\mathrm{crop}}.
  \label{eq:source-process}
\end{equation}
Conditional on $N_c$, source positions are independent and uniform in physical
arc length. For numerical element $i$ with endpoints $\mathbf{p}_i$ and
$\mathbf{p}_{i+1}$, the corresponding probability is
\begin{equation}
  p_i=\frac{\ell_i}{L_c},
  \qquad
  \ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2,
  \qquad
  L_c=\sum_j\ell_j.
  \label{eq:source-quadrature}
\end{equation}
The solver evaluates the ensemble mean under this process directly. It does not
draw a base-station count or a deployment. The numerical roofline elements are
quadrature elements, not transmitters. This law holds the expected active
transmitter count fixed across equal-area crops and redistributes it over each
city's observed roofline. It is a common hypothetical illumination law, not an
estimate of a deployed network.
```

The abstract should then replace

```tex
A common source measure sets the expected source count from areal density and
weights the observed route-aligned roofline by physical arc length.
```

with

```tex
A common hypothetical source process conditions transmitter locations on the
observed route-aligned roofline and weights that curve by physical arc length.
```

The limitation section should add:

```tex
The areal factor fixes the mean count of the standardized source process. It is
not inferred from the extracted roofline or calibrated to a deployment. The
reported results are ensemble means under this conditional law and do not
include source-count or source-placement variation.
```

## Preferred replacement if the paper drops the count claim

This version is scientifically cleaner and also preserves every relative
result. It changes the reported normalization from per unit
$\rho_AP_{\mathrm{EIRP}}$ to per unit
$\mu_cP_{\mathrm{EIRP}}$.

```tex
The source support is a probability measure on the observed roofline, not an
estimate of a deployment. Let $\Gamma_c$ have physical arc length $L_c$. Its
conditional source measure and numerical weights are
\begin{equation}
  \pi_c(ds)=\frac{ds}{L_c},
  \qquad
  p_i=\frac{\ell_i}{L_c},
  \qquad
  L_c=\sum_j\ell_j.
  \label{eq:conditional-source-measure}
\end{equation}
The calculation reports the route response per unit expected active-transmitter
count and per unit EIRP. The expected count is an external deployment parameter
and is not estimated in this study. The numerical roofline elements are
quadrature elements, not transmitters.
```

## Recommendation

For the present five-route paper, use the result-preserving rewrite and call the
model a *standardized conditional source process*. Replace *site* with *active
transmitter* wherever it is multiplied by a single EIRP. State explicitly that
the solver evaluates an ensemble mean and that the areal count is hypothetical.

If the central claim is intended to concern real deployment exposure, the
current model is not enough. Use the building-catchment marked point process in
(8) and (12), calibrate it from deployment data, and propagate deployment
variation. Without that calibration, the clean scientific endpoint is the
conditional per-transmitter roofline response in (5), not a base-station count.
