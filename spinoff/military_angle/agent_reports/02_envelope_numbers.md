# The certifiable exposure envelope, computed. It ties the incumbent zone, it does not beat it.

Agent report 02 for the military-angle study. Answers Finding A, claim (ii): is a
worst-case-over-all-beams absorbed-power envelope, computed with a real body, *tighter*
than the incumbent unperturbed-field keep-out zone. This is a numbers job. I ran it.

Reproducible code and data: `spinoff/military_angle/agent_reports/envelope_calc/`
(`run_envelope.py`, `analyze.py`, `envelope_lib.py`, `results.json`, `fig_zone_comparison.png`).

## 1. Verdict

At X-band, the range where AEGIS's surface method is valid, the certifiable envelope
reproduces the incumbent keep-out zone to within about 2 percent (361 m vs 369 m for a
fielded-scale emitter), it does not shrink it, because ICNIRP's reference level already
embeds the absorbed-to-incident coupling that is AEGIS's only physical differentiator and
the supremum over all beams throws away the body-orientation margin that is its only other
edge. Claim (ii), the whole business case, does not hold for shipboard X-band HERP.

## 2. The three things that most changed my view

1. **The absorbed-vs-incident advantage is already in the standard, and it cancels exactly.**
   My worst-case 4 cm^2 absorbed power density divided by the industry unperturbed incident
   density is 0.52 at every range from 5 to 100 m (fig right panel). The ICNIRP occupational
   limit ratio, basic restriction over reference level, is 100 / 185 = 0.54. Normal-incidence
   skin power transmission at 9.4 GHz is T0 = 0.489. These three numbers are the same number.
   The reference level was constructed so that at the reference level the absorbed basic
   restriction is just met under worst-case coupling, and worst-case coupling is normal
   incidence into skin, which is exactly what the worst-case-over-all-beams supremum selects.
   So AEGIS computing S_ab explicitly and comparing to the basic restriction lands on the same
   zone as the dumb method comparing S_inc to the reference level. Source: my calc plus
   `aegis/compliance/__init__.py` (the RL and BR formulae) plus `aegis/tissue/fresnel.py`.

2. **The sub-resolution hazard of Finding C(a) is a millimetre-wave phenomenon and vanishes
   at X-band.** At 9.4 GHz the worst-case coherent footprint on the body is 35 cm across
   (979 cm^2 at half-peak), not sub-centimetre. The 4 cm^2 averaging window (2.26 cm diameter)
   sits entirely inside it, so spatial dilution is 1.01, not the ~4 the 28 GHz data-mining
   found. The cross-range focal size is set by diffraction, lambda*r/D = 0.032 * 10 / 0.64 =
   0.5 m for a 0.64 m aperture at 10 m. A steerable lambda-sized hotspot needs lambda small,
   which needs >= ~28 GHz and the 1 cm^2 window. The band where the surface method is valid
   (>= 6 GHz) and the band where the sub-resolution story is real (>= ~30 GHz) barely overlap,
   and shipboard fire-control at 9.4 GHz is on the wrong side of the gap.

3. **The only lever that actually shrinks the zone is antenna scan-sector geometry, which is
   not AEGIS physics.** Confining the main beam to >= 15 degrees above the horizon, so it
   cannot point down at the deck, suppresses the worst on-body deposit by 184x (23 dB). That
   is a real and large zone reduction, but it comes entirely from where the array is allowed
   to point, which FEKO, a measured antenna pattern, or a NAVSEA sidelobe envelope already
   captures. The body-surface absorption model adds nothing to it.

## 3. What I verified, inferred, could not check

**Verified (my own computation, calibrated against a closed form):**
- The whole pipeline is calibrated. A single element on a flat skin slab at normal incidence
  gives S_ab / S_inc = 0.4889, matching the analytic power transmission 1 - |Gamma|^2 = 0.4889
  to four digits. Oblique 45 deg gives 0.268. The physics builder is correct.
- The zone-ratio result (B ties A within 2 percent) across two array sizes, five ranges,
  three body orientations. This is a ratio driven by T0 versus the limit ratio, so it is
  insensitive to my modelling choices.
- Focal spot 35 cm at 9.4 GHz, spatial dilution 1.01, near-field enhancement 1.09 to 1.12.
- Breach power and zone radius scaling.

**Verified (public sources):**
- AN/SPG-62, a fielded US Navy X-band illuminator, is CW, 10 kW average, 2.29 m dish, which
  gives ~45 dBi. This is my realistic anchor. Source: radartutorial.eu naval file 047 and
  Wikipedia AN/SPG-62.
- CEROS 200 is Ku-band (15.5 to 17.5 GHz), 1.5 kW peak TWT, 1 m Cassegrain. Source: Wikipedia,
  Saab product sheet. Confirms naval trackers cluster at X and Ku with 1 to 2.3 m apertures and
  kW-class power.

**Inferred (defensible assumptions, all stated in section 4):**
- Element directivity g_elem = pi (a filled lambda/2 aperture, 4.97 dBi element) applied
  uniformly. Isotropic array elements otherwise. First-bounce only, no inter-body occlusion,
  which slightly over-predicts absorption and therefore cannot rescue the negative result.
- The incumbent uses peak main-beam gain toward the person. If instead the incumbent already
  credits the real antenna pattern toward the deck, AEGIS ties it even harder.

**Could not check:**
- No SDP solver in this environment (no cvxpy). My per-element-modulus number is a lower bound
  on the constrained supremum via coordinate ascent, so the looseness of lambda_max is an
  upper bound (at most ~2x near field), not a proven value. See section 5.
- Real element patterns, mutual coupling, true ship deck multipath. Out of scope for a zone
  ratio, in scope for an absolute certificate.

## 4. Scenario and assumptions

| Item | Value | Justification |
|---|---|---|
| Carrier | 9.4 GHz | Shipboard X-band fire-control / nav band. AEGIS surface method valid (skin depth < 1 mm). |
| Skin dielectric | eps_r 31.29, sigma 8.01 S/m, n_tilde 5.73 - 1.26j | IT'IS v5 at 10 GHz (`SKIN_BY_GHZ`, nearest tabulated). |
| Phantom | duke, 72 kg, 56024 triangles, 1.87 m^2, standing on deck | AEGIS `data/duke.stl`. Median triangle 0.22 cm^2, fine enough for 4 cm^2 averaging. |
| Array "tracker" | 16x16 = 256 el, lambda/2, D = 0.255 m, 29.1 dBi, far field 4 m | Small X-band tracker sub-aperture. |
| Array "illuminator" | 40x40 = 1600 el, lambda/2, D = 0.638 m, 37.0 dBi, far field 26 m | Larger aperture so the body is in the near field out to 26 m, where coherent focusing is live. |
| Real anchor | AN/SPG-62: 45 dBi, 10 kW CW | Fielded US Navy X-band illuminator (verified). I scale the 37 dBi model up by 8 dB for absolute numbers. |
| Ranges | 5, 10, 20, 50, 100 m | Deck standoff. Brackets near field and far field for both arrays. |
| Orientations | yaw 0 (facing array), 90 (side), 180 (back) | Tests whether body orientation buys margin. It does not, for the worst case. |
| Occupational limits | S_ab 100 W/m^2 (4 cm^2 basic restriction), S_inc 185 W/m^2 (local reference level), SAR_wb 0.4 W/kg | ICNIRP 2020 occupational = military-controlled (brief correction). `aegis.compliance` at 9.4 GHz. |
| Power calibration | psi = peak E-field, S_inc = abs(psi)^2 / (2 Z0), element field amplitude sqrt(2 Z0 P / 4pi)/d | AEGIS `paths.py`, `differt.py`. Results built per 1 W total radiated, scaled linearly. |

Method for (B): I build the coherent body-surface channel G_tilde of shape (T, 3, M) with
true near-field spherical-wave phase and amplitude per element per triangle, reusing AEGIS
Fresnel and depth-coupling primitives. This is the honest model because at 10 to 100 m a
0.64 m aperture puts the body in the Fresnel region (far field 26 m), so the plane-wave
`compute_body_channel` path is not valid. Q = sum_t area_t G_t^H G_t. Worst-case whole body
= lambda_max(Q). Worst-case local 4 cm^2 APD = max over hot windows of lambda_max(Q_window),
which is the true supremum over all beams of the 4 cm^2-averaged absorbed density.

## 5. The four questions, answered

### Q1. Does the envelope beat the incumbent zone? No, it ties it.

Compliance ratios per unit radiated power, and the implied zone-boundary radius B / A
(both metrics scale as 1/r^2 in the far field, so the zone-radius ratio is sqrt(C_B / C_A)):

| range (m) | tracker C_B/C_A | tracker zone B/A | illuminator C_B/C_A | illuminator zone B/A |
|---|---|---|---|---|
| 5 | 1.052 | 1.025 | 1.055 | 1.027 |
| 10 | 1.005 | 1.003 | 0.998 | 0.999 |
| 20 | 0.979 | 0.990 | 0.957 | 0.978 |
| 50 | 0.964 | 0.982 | 0.965 | 0.982 |
| 100 | 0.959 | 0.979 | 0.962 | 0.981 |

The AEGIS worst-case zone is 2 to 4 percent *smaller* in radius than the incumbent zone, and
at short range (5 m) it is actually 2 to 3 percent *larger*. Scaled to a real AN/SPG-62-class
emitter (45 dBi, 10 kW), the AEGIS envelope keep-out is 361 m against the industry incident
zone of 369 m. That 8 m out of 369 m is inside the noise of the assumptions. It does not buy
operational tempo. Orientation does not help: yaw 0, 90, 180 all give the same worst-case
local APD to two digits, because the supremum finds the best-coupled lit patch whatever the
pose. This is the crux the brief flagged, and it goes the wrong way for the business.

The tie is not a coincidence, it is structural. `wc_local_4cm2 / sinc_ff = 0.52` at every
range equals the limit ratio `100/185 = 0.54` equals `T0 = 0.489` (fig right panel).

### Q2. Is lambda_max over all unit-norm x hopelessly loose? In the near field, loose by at most ~2x, not 10x.

For a phased array the physical constraint is per-element modulus |x_i| = 1/sqrt(M), phase
only. I maximised x^H Q x under that constraint by coordinate ascent seeded from both the
steering vector and the top eigenvector phases (illuminator, 10 m, near field):

| quantity | value (absorbed W per W radiated) | fraction of lambda_max |
|---|---|---|
| lambda_max (all unit-norm x) | 0.297 | 100 percent |
| best phase-only equal-power beam achievable | 0.141 | 48 percent |
| steer-to-body in-phase beam (= industry full-gain assumption) | 0.107 | 36 percent |

So lambda_max over-states the realizable phase-only worst case by at most 2.1x (3 dB) in the
near field. In the far field Q collapses to rank 1 (top mode 89 to 100 percent of trace) and
lambda_max is tight, since the only thing an unresolved body permits is to point the beam at
it. Two honest caveats. First, 0.141 is a lower bound on the constrained supremum, so 2.1x is
an upper bound on the looseness, the true looseness is less, and I could not compute the SDR
upper bound without a solver. Second, and this is the point that kills the constrained-envelope
angle too, the phase-only max (0.141) is still above the industry full-gain-on-person beam
(0.107), so tightening the excitation set does not push the envelope below the incumbent
assumption. It cannot, because pointing the beam at the person is itself a valid phase-only
beam and that is essentially what the incumbent already assumes.

### Q3. The three blindnesses at X-band multiply to about 1.1, not 200. The scanning term is the only large one and AEGIS cannot model it.

| blindness | 28 GHz (data-mining) | 9.4 GHz (this work) | note |
|---|---|---|---|
| (i) 4 cm^2 spatial dilution | ~4x | 1.01x | Focal spot is 35 cm at X-band, dwarfs the 2.26 cm window. |
| (ii) 6-min time average, scanning | not quantified | 1x staring, up to ~450x rotating | See below. |
| (iii) coherent buildup / near-field focus vs far-field estimate | claimed large | 1.09 to 1.12x | Array gain M caps concentration, focusing cannot beat boresight gain. |

Product of the AEGIS-modelable terms (i)x(iii) = 1.1 to 1.15. The standard is not blind at
X-band. The one large factor is (ii): a rotating search radar with a 0.8 degree beam dwells
on a fixed point for a fraction theta/2pi = 0.0022 of each scan, so the 6-minute average is
~450x below the peak. But this is a genuine and physically correct steady-state average, not
a regulatory blind spot, unless the concern is transient thermal damage from the peak, and
transient thermal is exactly the pulsed / fluence regime the brief lists as an AEGIS gap. A
staring illuminator such as AN/SPG-62 has dwell fraction 1 on the tracked target line and does
not scan, so (ii) = 1 there. Net: at 9.4 GHz the fundable "compliant on paper, non-compliant
in reality" gap of Finding C(a) is about 1.1x. It is real and worth a slide at 28 GHz and
above with a 1 cm^2 window, and it is essentially absent at shipboard X-band.

### Q4. Breach power is realistic and the hazard is real, but you do not need coherence for it.

Total radiated power to breach the occupational 4 cm^2 APD (100 W/m^2) at 20 m, worst-case beam:

| emitter | gain | breach power at 20 m |
|---|---|---|
| tracker model | 29 dBi | 1180 W |
| illuminator model | 37 dBi | 193 W |
| AN/SPG-62-scaled | 45 dBi | 31 W |

AN/SPG-62 radiates 10 kW, which is 326x over the 20 m breach threshold. Its genuine keep-out
zone is ~360 m. So the hazard at fielded X-band power is large and real, and it is caused by
plain array gain on a beam pointed the wrong way, not by any coherent cleverness. This matches
Finding C: at military power a pencil beam hurts trivially, the coherent-hotspot novelty adds
nothing to the injury story. It also means AEGIS, which reproduces that 360 m zone within 2
percent, is a correct but not a differentiated way to draw it.

## 6. What this means for the thesis

The certifiable envelope is real, it is closed form, it is computed with a body, and it is
regulator-shaped (the VOP precedent in Finding B stands). But at the one naval band where the
surface-speed trick is valid, it produces the same keep-out zone the Navy already paints with a
far cheaper calculation. The three reasons, in order of how load-bearing they are:

1. ICNIRP's reference level already discounts incident by the absorbed coupling factor (~0.5),
   so re-deriving that factor from a body mesh recovers the same zone.
2. The supremum over all beams selects the best-coupled normal-incidence patch, so body shape
   and orientation, AEGIS's information advantage, give zero relief on the worst case.
3. At 9.4 GHz the coherent hotspot is 35 cm wide, so none of the sub-resolution averaging
   blindnesses fire.

Where the thesis could still live, honestly: at Ku and Ka (16 to 35 GHz naval trackers, seekers,
95 GHz systems) the spot shrinks below the 1 cm^2 window and blindnesses (i) and (iii) revive
while the surface method stays valid. That is the band the brief already calls home turf. This
report is a negative result specifically for the *X-band shipboard fire-control HERP* framing,
and it should redirect the pitch up the band, not kill AEGIS.

## 7. What would kill this (a one-week falsifiable test)

Take one real, unclassified antenna pattern for a naval X-band tracker (a measured or published
principal-plane cut with its sidelobe envelope). Compute the incumbent NAVSEA/OP-3565-style
keep-out zone two ways: (a) the way a safety board actually does it today, and (b) the AEGIS
envelope with the same pattern and a duke phantom. If (b) is more than ~20 percent tighter in
standoff for a realistic scan sector, my structural-tie result is wrong and the business case is
alive. If (b) is within a few percent of (a), as my synthetic model predicts, the X-band case is
dead and the pitch must move to Ku/Ka. The single number that decides it is whether the incumbent
already credits the antenna pattern toward the deck (then AEGIS ties) or assumes peak gain
everywhere (then the win is the pattern, not the body, and any antenna tool delivers it).

## 8. The single highest-value next action

Rerun this exact pipeline at 28 GHz and 35 GHz with the 1 cm^2 window and a 1 to 2 m aperture,
to measure how much the zone-ratio and the blindness product move once the spot goes
sub-centimetre. That is a half-day of compute on the code already written here, it needs no new
data, and it directly tests whether the sweet spot exists one band up. Robin, or an agent, can
run it. Only after that number is in hand is it worth Wout spending standards-body capital on the
Finding C(a) sub-resolution paper, because that paper's entire force is the blindness product,
which is 1.1 at X-band and unknown but plausibly large at Ka.
