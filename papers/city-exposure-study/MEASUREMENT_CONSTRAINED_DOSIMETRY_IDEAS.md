# Paper ideas from the GOLIAT microenvironment measurements

## Honest assessment

There is a genuinely good paper here, but the obvious version is already partly
occupied.

The straightforward paper, "multiply the measured band powers by
phantom-specific SAR coefficients," overlaps substantially with the existing
GOLIAT dose model and the four-phantom far-field simulations. The GOLIAT dose
model already combines measured power density, device output power, normalized
SAR lookup tables, and Monte Carlo uncertainty. The far-field study already
covers four phantoms from 450 MHz to 26 GHz.

- [GOLIAT dose model](https://biblio.ugent.be/publication/01KM5R78YWT0K68CHZ4RQTP8QB)
- [Far-field phantom study](https://biblio.ugent.be/publication/01KM5MFMCXZEVADPGNK7ZYBDP9)

The interesting unanswered question is not simply "what is the dose?" It is:

> What can a scalar, body-worn, frequency-selective probe actually tell us about
> absorbed dose when arrival direction is unobserved?

## Preferred paper

### What can an isotropic exposimeter identify about human absorbed dose?

For each frequency band and phantom, AEGIS gives a directional dose-response
kernel:

$$
K_{f,h}(\Omega)
=
\frac{\operatorname{wbSAR}}{S_{\mathrm{inc}}}.
$$

Here, $f$ is frequency, $h$ identifies the phantom, and $\Omega$ is the arrival
direction. A corresponding kernel can be constructed for the surface absorbed
power field or its peak value.

Adriana's probe supplies one measured band power $y_f$, but not its angular
distribution. Instead of inventing transmitters, calculate the minimum and
maximum dose over every nonnegative angular spectrum compatible with that
measurement:

$$
D_{\min}(y_f)
\leq
D(y_f)
\leq
D_{\max}(y_f).
$$

If the directional response of the probe is $R_f(\Omega)$, the measurement
constraint is

$$
y_f
=
\int R_f(\Omega)\,S_f(\mathrm{d}\Omega),
$$

while the corresponding dose is

$$
D_f
=
\int K_{f,h}(\Omega)\,S_f(\mathrm{d}\Omega).
$$

After discretizing direction and polarization, finding the lower and upper dose
bounds becomes a small linear optimization problem. This bypasses the impossible
step of reconstructing the complete RF environment.

The Adriana dataset could then answer several empirical questions:

- Are the urban, rural, and country comparisons preserved after converting
  measured power flux density to dose?
- How often do two microenvironments reverse order because their frequency
  spectra differ?
- Is whole-body SAR tightly identified even when local surface absorption is
  not?
- Does directional uncertainty matter more or less than phantom morphology,
  frequency composition, probe uncertainty, or temporal sampling?
- Is one average 11.6% body-shielding correction adequate for dose, even if it
  is adequate for mean field strength?

The final question is especially promising. Existing work generally corrects a
probe reading toward an estimated unperturbed field and then performs dosimetry.
This method would estimate dose directly from the probe observation without
pretending that the unperturbed scalar field is identifiable.

Possible titles:

- **Sharp bounds on absorbed dose from body-worn multiband RF exposimetry**
- **From measured field strength to absorbed dose: what can an isotropic
  exposimeter tell us?**

## How the semantic twin fits

The current semantic twin should not predict the absolute power for this paper.
Its present study uses five routes at 15 GHz, while the Adriana measurements end
at 6 GHz. The routes and frequencies do not align directly.

Its conceptual separation is nevertheless ideal:

1. The measurement determines total power in each frequency band.
2. Scene geometry supplies plausible arrival directions.
3. AEGIS supplies direction-aware body coupling.

The semantic twin can therefore tighten the direction-free interval without
controlling the absolute amplitude. A hierarchy of directional assumptions
could be compared:

1. No directional information, giving full-sphere bounds.
2. A generic outdoor model, using horizontal and rooftop elevation support.
3. A panorama-derived model, using visible sky, roofline, street-canyon, and
   facade directions.
4. A full normalized semantic-twin angular spectrum for a small matched subset.

Every angular model would be normalized back to the measured power in that
frequency band. Errors in transmitter power, traffic load, antenna EIRP, and
propagation loss would therefore not corrupt the absolute scale.

The paper-level question becomes:

> How much scene information is needed after the field has already been
> measured?

A plausible and interesting outcome is that whole-body SAR is relatively robust
because integration over the body suppresses directional variability, while the
surface hotspot remains strongly direction dependent. That result would connect
AEGIS's whole-body theory to real field surveys particularly well.

The semantic twin should initially be applied to perhaps 5 to 20 exact outdoor
routes, not all 800 microenvironments. It would be a bound-tightening and
value-of-information experiment, not the exposure predictor.

## Other viable papers

### 1. Exposure rankings versus dose rankings

Use all 35 bands to ask whether total power flux density in mW/m2 is a faithful
ranking variable for absorbed dose.

The Adriana study has very different spectra in the non-user, maximum-downlink,
and maximum-uplink scenarios. One mW/m2 at 700 MHz is not dosimetrically
interchangeable with one mW/m2 at 3.5 or 5 GHz. The result would be a
cross-country and microenvironmental rank-stability analysis.

This is feasible, but conversion alone is probably not a sufficiently strong
contribution. The identified-interval method supplies the stronger hook.

### 2. The downlink-uplink exposure trade-off in dose units

Adriana finds lower environmental exposure but higher handset uplink exposure
in rural areas and in countries with precautionary limits. A dose paper could
ask whether network conditions shift absorbed dose from far-field
infrastructure to the user's own handset.

This is interesting but difficult:

- The 3.5 GHz TDD probe measurement cannot distinguish handset uplink from
  base-station downlink.
- Maximum-uplink exposure is a near-field problem.
- Policy comparisons are strongly confounded across countries.
- The existing GOLIAT dose model already enters this territory.

This should be framed as partial identification of the near-field and far-field
mixture, not as a causal paper about regulation.

### 3. Design the next measurement protocol

Use the Adriana data distribution and AEGIS to quantify the value of additional
measurements:

- one versus two exposimeters,
- coarse front-back discrimination,
- coarse elevation bins,
- placing the phone 30 cm versus 1.5 m from the probe,
- slot-resolved TDD sensing,
- synchronized handset transmit-power logging,
- 5 versus 15 minutes per microenvironment.

The endpoint would be the reduction in absorbed-dose uncertainty rather than
the reduction in field-strength variance. This could be a strong final section
of the first paper or a separate protocol paper.

## Important scope decisions

The first paper should concentrate primarily on outdoor non-user measurements.

The maximum-downlink and maximum-uplink scenarios place a phone approximately
30 cm from the ExpoM-RF 4. This creates a different observation problem. At
3.5 GHz, the measured TDD signal combines handset uplink and base-station
downlink. The nearby phone may also not be adequately represented as a
far-field plane wave. Applying the same conversion law to all three scenarios
would invite a justified reviewer criticism.

Peak absorbed power density should be a secondary physical endpoint. The
Adriana dataset ends at 6 GHz, where SAR and peak spatial-average SAR are the
relevant regulatory quantities. AEGIS surface APD remains informative, but it
should not be presented as the primary compliance endpoint.

There is also a frequency-domain boundary. The present AEGIS theory is validated
from approximately 1 to 100 GHz, whereas the ExpoM-RF 4 measurements begin at
87.5 MHz. Body resonance matters below 1 GHz. A clean hybrid solution is:

- use AEGIS for dense angular and morphological sweeps above 1 GHz,
- use existing GOLIAT or Sim4Life transfer tables below 1 GHz,
- perform a deliberate overlap comparison near 1 to 2 GHz.

## Recommended pilot

### What the supplement now makes possible

The supplementary DOCX contains substantially more usable data than the main
paper suggests. Seven native Word tables provide exact country, study-area,
scenario, band, probe, and crosstalk summaries. Figures A6 to A10 additionally
provide the missing country by individual-study-area by scenario by band
interaction as stacked bars.

Those five figures have now been digitized with a one-pixel resolution of
0.0458 mW/m2 for the urban panels and 0.0802 mW/m2 for the rural panels. The
digitized urban totals agree with 54 of 56 Table A6 totals to within two pixels.
The two exceptions are Poland maximum-uplink bars whose plotted stacks and
tabulated totals appear internally inconsistent.

This enables an immediate aggregate pilot without waiting for the raw dataset:

1. Convert the exact Table A7 country spectra to phantom-specific whole-body
   SAR transfer estimates.
2. Use the digitized Figures A6 to A10 to resolve the same analysis by large
   city, secondary city, and each of the three rural areas.
3. Compare rankings by total measured power with rankings by absorbed dose.
4. Quantify how much of each ranking change comes from spectral composition,
   phantom choice, and the treatment of unknown direction.

The strongest simple result is no longer merely a conversion table. It is a
rank-stability result with a controlled evidence ladder: exact country spectra,
digitized study-area spectra, yaw-marginalized body coupling, and directional
bounds. The supplement can support this pilot now. Raw data are still needed
for time-series endpoints and exact microenvironment-level spectra.

Start with Belgian outdoor non-user data, ideally including one route with exact
GPS coordinates and panorama access.

1. Compute directional whole-body SAR and surface-response libraries for Duke,
   Ella, Thelonious, and Eartha.
2. Begin with an ideal isotropic probe response.
3. Calculate the full directional bounds and the isotropic estimate.
4. Measure rank reversals and interval widths.
5. Restrict direction using a simple panorama and roofline support.
6. Add the measured backpack and probe response when it becomes available.

The decisive figure would show, for every measured microenvironment:

- measured total power flux density,
- the isotropic dose estimate,
- the direction-free dose interval,
- the panorama-constrained dose interval.

If the whole-body SAR intervals are narrow but the hotspot intervals are wide,
that is already a strong result. If panorama information materially tightens
both intervals, that justifies the semantic-twin layer. If neither happens, the
pilot will have shown cheaply that a large deterministic reconstruction is not
needed.

The published article's data statement still only says that a data and code
link will be made available. The supplement is sufficient for an aggregate
pilot. A microenvironment-level or time-series paper will probably require a
direct raw-data handoff from Adriana's team.

- [Published Adriana paper](https://www.sciencedirect.com/science/article/pii/S0160412025002910)

## Recommendation

Do not build another absolute city propagation study. Build an inverse-dosimetry
paper about what measured multiband exposimetry does and does not identify. Use
the semantic twin only to provide additional directional information.

This direction is new, mathematically clean, faithful to the measurements, and
well matched to what AEGIS can compute quickly.
