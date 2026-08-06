# Absorbed and incident power density above 6 GHz: definitions, the Poynting-reduction ambiguity, the Sim4Life extraction, and where AEGIS stands

**A master reference assembled from a deep investigation (2026-06-08).**

Scope: the two regulated power-density quantities above 6 GHz (absorbed `S_ab` and incident `S_inc`); their exact definition from Maxwell's equations; the three/four scalar reductions of the Poynting vector and how each maps to the standards and to Sim4Life's evaluator; the factor-of-½ (peak-vs-RMS) convention; what the GOLIAT/Sim4Life FDTD pipeline actually extracted and the still-open question of whether the published PMB absorbed-power-density values are the correct reduction; and a verification that the AEGIS closed-form law and monograph define and validate the **correct** quantity. Builds on, corrects, and extends `power_density_definitions_report.md` with code-level and on-disk evidence that the earlier report (internet + manuals only, no code) could not see.

A note on provenance and confidence: parts of this rest on primary sources read directly (the vendored Sim4Life 8.2 Python API reference; the AEGIS monograph and TAP paper LaTeX; the GOLIAT extraction code; on-disk result files). Other parts rest on a prior AI-written report whose standards quotes are secondary (IEC/IEEE 63195 is paywalled). Where a claim is inference rather than a read fact, it is marked. The one genuinely unresolved question is flagged repeatedly and has a one-line experiment that settles it.

---

## 0. Executive conclusions (read this first)

1. **There are two distinct regulated quantities above 6 GHz, and they are *not* interchangeable.** The basic restriction is **absorbed power density `S_ab`** (the power flowing *into* the body); the reference level is **incident power density `S_inc`** (a property of the unperturbed wave). They differ by the air-tissue transmittance: `S_ab = (1-|Gamma|^2) S_inc` at a planar interface, so `S_ab` is roughly half of `S_inc` on skin in the low-mmWave band (`T_0 ~ 0.4-0.55`).

2. **The factor-of-½ (peak vs RMS) fear is resolved and is NOT a bug.** Sim4Life stores peak-amplitude phasors and writes `S = ½ Re(E x H*)`; ICNIRP uses RMS fields and writes `S = Re(E x H*)` with no ½. Same watts per square metre. The GOLIAT renormalisation `754 = 2*eta_0` is the correct peak-convention factor (`E_peak = sqrt(2*eta_0) = 27.46 V/m` gives `S_inc = 1 W/m^2`). A real 2x error only appears if peak fields are fed into ICNIRP's no-½ formula, which GOLIAT does not do.

3. **The genuinely physical ambiguity is *which scalar* you reduce the (complex, vector) Poynting field to.** Four options: `n.Re{S}`, `|Re{S}|`, `n.S`, `|S|`. The true absorbed power density `S_ab` is `n.Re{S}` (inward normal real part). The incident-side reference proxy `S_inc` is `|S|` (modulus). These coincide for a single normally incident plane wave and diverge at a reflecting tissue surface and in the reactive near field.

4. **AEGIS's closed-form law and monograph define and validate the CORRECT quantity.** `S_ab = S_inc * T_0 * ReLU(n.(-k))` is the inward normal transmitted flux = `n.Re{S}` = ICNIRP eq.16. The monograph's validation observable is explicitly "the time-averaged Poynting flux flowing inward through the body surface," checked against exact Mie and Bessel-Hankel cylinder oracles (Mie canary at 0.7%), not against the FDTD pipeline. AEGIS does **not** fit any coefficient to FDTD. **There is no analogous reduction bug in AEGIS theory or code.**

5. **The open question is confined to the GOLIAT/Sim4Life FDTD extraction.** Its `GenericSAPDEvaluator` was run with `SetAPD=False` (the "Absorbed Power Density" property defaults off) and `AveragedQuantity` never set. Whether the resulting "SAPD" the PMB paper reports is the absorbed `n.Re{S}` or the larger modulus `|S|` is **not settled** by desk analysis. Two readings survive; the stronger evidence (an exact-Mie-certified AEGIS absorbed-PD calculation matching the report port at the peak) favours "it is the absorbed quantity, the paper is fine, and the side-channel field dump is the buggy one." One Sim4Life seat-minute settles it definitively.

---

## 1. The two quantities

ICNIRP 2020 (Health Phys. 118(5):483-524) and IEEE C95.1-2019 split the spectrum at 6 GHz. Below, the dosimetric quantity is SAR (mass-averaged, tracks deep heating). Above, absorption is superficial (penetration depth ~8 mm at 6 GHz, ~0.2 mm at 300 GHz) and the quantity becomes a *surface* power density.

### 1.1 Incident power density `S_inc` (the reference level)

`S_inc` is a property of the **unperturbed incident wave** - what an EMF probe reads in free space with no body present. For a plane wave,

```
S_inc = |E_pk|^2 / (2 eta_0) = |E_rms|^2 / eta_0 ,   eta_0 = 376.73 ohm.
```

It is the **reference level** (ICNIRP) / **exposure reference level** (IEEE): the easily-measured proxy you check first. ICNIRP defines it (eq.18) as the **modulus of the complex Poynting vector**, `|S| = |E x H*|`, because near a source up to ~50% of incident power can reflect and you want the proxy to *over*-predict, not under-predict, the actual deposition. It is the most conservative of the reductions (Section 4).

In AEGIS, `S_inc` is the driver: the code runs at `power = 1.0 W/m^2` and every output scales linearly with it. In GOLIAT/Sim4Life the plane wave is excited at `E = 1 V/m` (peak), so its native `S_inc = 1/(2*eta_0) = 1.327 mW/m^2`, and outputs are renormalised by `2*eta_0 = 754` to express everything per `S_inc = 1 W/m^2`.

### 1.2 Absorbed power density `S_ab` (the basic restriction)

`S_ab` is the power that actually **crosses the body surface and is deposited** in tissue, spatially averaged over a 4 cm^2 square (plus a 1 cm^2 constraint above 30 GHz). From the complex Poynting theorem, with the inward normal `n` and averaging area `A`,

```
S_ab = (1/A) * integral_A  Re{ ½ E x H* } . n  dA       (evaluated with TOTAL fields at the surface)
     = (1/A) * integral_A integral_0^Zmax rho * SAR dz  dA   (equivalent depth-integrated dissipation).
```

The two forms are the entire content of Poynting's theorem: net inward surface flux = ohmic dissipation inside. This is ICNIRP eq.16 (Poynting form) = eq.15 (volumetric form). The local limits are 100 W/m^2 (occupational) and 20 W/m^2 (general public) over 4 cm^2, derived thermally (operational 5 C / 2 C rise thresholds, ~200 W/m^2 to reach 5 C, then safety factors 2 and 10).

### 1.3 The link

At a planar interface, ICNIRP eq.20:

```
S_ab = (1 - |Gamma|^2) * S_inc = T_0 * S_inc ,
```

with `Gamma` the (complex, polarisation- and angle-dependent) Fresnel reflection coefficient and `T_0` the power transmittance. For skin, `T_0 ~ 0.4-0.55` across 7-28 GHz, so **`S_ab` is roughly half of `S_inc`.** Conflating the two is therefore a ~2x error, in the conservative (over-reporting) direction if `S_inc` is reported as `S_ab`.

---

## 2. The three (four) Poynting reductions - the genuinely physical ambiguity

A complex vector Poynting field reduces to a scalar surface power density in several ways. Christ et al. (2020, Bioelectromagnetics 41(5)) named and compared them; ISED RSS-102.IPD.MEAS codifies them; Sim4Life's `GenericSAPDEvaluator.AveragedQuantity` property exposes exactly these (read directly from the vendored 8.2 API reference):

| Sim4Life `AveragedQuantity` | definition | standards name | maps to |
|---|---|---|---|
| `n.Re{S}` | normal component of the real part (positive values only) | sPD_n+ | **`S_ab`, ICNIRP eq.16 - basic restriction** |
| `\|Re{S}\|` | magnitude of the real part | sPD_tot+ | "active flux" |
| `n.S` | normal component of the complex vector | - | (includes reactive normal flux) |
| `\|S\|` | magnitude of the complex vector | sPD_mod+ | **`S_inc`, ICNIRP eq.18 - reference level** |

Exact ordering (from `|S|^2 = |Re S|^2 + |Im S|^2` and `|Re{S_n}| <= |Re S| <= |S|`):

```
sPD_n+  <=  sPD_tot+  <=  sPD_mod+
n.Re{S} <=  |Re{S}|   <=  |S|
```

**The absorbed quantity is the smallest; the incident/modulus proxy is the largest.**

`AveragingMethod` (also in the API) is a separate property: "Rotating Cube" (averages over 5-degree rotations of a cube-surface intersection, the IEEE 63195 procedure) vs "Sphere." `Threshold` is documented as "Surface Discretization" - **not** a depth threshold (the GOLIAT code comment calling it a "10 mm depth threshold" is a misreading of that knob).

### 2.1 When the reductions coincide, and the surface-reflection correction

For a **single, normally incident plane wave in free space**, `E ⊥ H`, in phase, flow purely along `n`, so `Im S = 0` and all reductions equal `|E|^2/2eta_0`. This is why the distinction was invisible until mmWave near-field device exposure. They diverge:

- in the **reactive near field** (`d < lambda/2pi ~ 1.7 mm at 28 GHz`), where `E,H` acquire a phase difference; and
- at **large oblique incidence**, where tangential flow appears.

**Correction to the earlier report (a place where the internet-only analysis was incomplete):** the SAPD evaluator reduces the **total field at the reflecting skin surface**, not a free-space plane wave. There, even at normal far-field incidence, the air-tissue Fresnel reflection is **complex** (lossy tissue), so `Im{S} != 0` and the reductions diverge by the reflection. For normal incidence on a half-space,

```
n.Re{S} = (1 - |Gamma|^2) S_i        (the absorbed/transmitted flux)
|S|      = S_i * sqrt[ (1+|Gamma|^2)^2 - 4 (Re Gamma)^2 ]   (the surface modulus)
```

With a complex `Gamma` (`|Gamma|^2 ~ 0.45` on skin), `|S| / n.Re{S} ~ 1.5`. So for the GOLIAT far-field plane-wave case the `|S|`-vs-`n.Re{S}` gap is **~1.5x driven by reflection**, NOT a small reactive-near-field-only effect. This matters for interpreting the on-disk data in Section 4.

---

## 3. The factor-of-½ / peak-vs-RMS question - resolved, not a bug

| source | complex Poynting vector | field convention |
|---|---|---|
| ICNIRP 2020 | `S = E x H*` (eq.16, no ½) | **RMS** |
| Sim4Life 7.2 / 8.2 | `S = ½ E x H*` | **peak amplitude** |

Proof ICNIRP is RMS: its plane-wave eq.19 reads `S_inc = |E|^2/Z_0` with no ½; the unambiguous time-averaged intensity is `|E_pk|^2/2Z_0 = |E_rms|^2/Z_0`, so ICNIRP's `E` must be RMS. Sim4Life defines `|H|_RMS = (1/sqrt2)|H|`, i.e. the stored phasor is peak; hence the ½. The two are identical time-averaged W/m^2 because

```
Re(E_rms x H_rms*)  =  ½ Re(E_pk x H_pk*) ,   since  E_rms = E_pk / sqrt2 .
```

**Consequence for GOLIAT.** Excitation at `E_pk = 1 V/m` gives `S_inc = 1/(2*eta_0) = 1.327 mW/m^2`. To renormalise to `S_inc = 1 W/m^2`, multiply power-like outputs by `2*eta_0 = 753.46 ~ 754` (equivalently `E_ref = sqrt(2*eta_0) = 27.46 V/m`, and power scales as `E^2`, giving `27.46^2 = 754`). The GOLIAT comment `# (27.5)^2` is the correct derivation, not a fudge. This is internally consistent across the normalization doc, the SAR extractor, the field-dump (`753.46`), and the Table-4 builder (`754`).

**The only way a real 2x sneaks in** is mixing conventions: dropping Sim4Life's peak fields into ICNIRP's no-½ formula (or vice-versa). GOLIAT uses Sim4Life's own evaluators end-to-end, which carry the ½ internally, so this error is not present. The original "is there a factor of half" worry is therefore **closed: not a bug.** The real axis of risk is the *reduction* (Section 2), not the ½.

---

## 4. What the GOLIAT/Sim4Life pipeline actually extracted

### 4.1 `GenericSAPDEvaluator.SetAPD` - what the API says

From the vendored `PythonAPIReference_8_2.zip` (`s4l_v1.analysis.em_evaluators`):

```
GenericSAPDEvaluator  -- "Generic Surface Averaged Density Evaluator"
  property SetAPD : bool   -- "Value of: Absorbed Power Density"   (default False)
  property Threshold : float -- "Value of: Surface Discretization"
  property AveragedQuantity  -- {n.Re{S}, |Re{S}|, n.S, |S|}   (Section 2)
  property AveragingMethod   -- {Rotating Cube (IEEE 63195, 5 deg), Sphere}
```

So `SetAPD` is literally the evaluator's "Absorbed Power Density" toggle, defaulting **off**. The 5G post-processing module (`PostProRec5G.EmGenericSAPDEvaluator`) is titled "Generic **Power Density** Evaluator" and carries the same `AveragedQuantity` enumeration.

### 4.2 The two ports in `goliat/extraction/sapd_extractor.py`

- **Report port** (`SetAPD=False`): `Outputs["Spatial-Averaged Power Density Report"]` -> scalar `peak_sapd_W_m2`. **This is what the paper uses.** Stored raw; renormalised by 754 downstream.
- **Field port** (`SetAPD=True`, only when `extraction.sapd_field`): `Outputs["APD(x,y,z,f0)"]` -> per-vertex field, written to `skin_apd.npz` with `* 753.46` applied. Feeds the AEGIS surface-map (Tier-2) validation only. `SetAPD=True` *swaps the report port out* and exposes the field port instead.

Crucially the code sets only `AveragingArea`, `Threshold`, `SetAPD` - it **never sets `AveragedQuantity` or `AveragingMethod`**, so both default. The IEC-63195 "Rotating Cube + n.Re{S}" configuration was left implicit.

### 4.3 On-disk evidence (report vs field, matched sims)

For the seven sims that have both `sapd_results.json` (report) and `skin_apd.npz` (field), comparing `report_raw * 754` against the field-port peak (already x754):

| sim (real APD regime) | report x754 | field peak (SetAPD=True) | field / report |
|---|---|---|---|
| thelonious 7000 x_neg | 0.565 | 0.500 | 0.88 |
| thelonious 7000 x_pos | 0.641 | 0.236 | 0.37 |
| thelonious 7000 y_neg | 0.805 | 0.631 | 0.78 |
| thelonious⅓ 10000 | 0.310 | 0.158 | 0.51 |

The report is **systematically larger** than the field, by a scattered 0.37-0.88. Two facts about this:

- If they were the same quantity differently aggregated (report = 4 cm^2-averaged peak; field = per-vertex peak), the per-vertex peak would be **>=** the averaged peak. It is smaller. So either the ports are different quantities, **or the field dump is under-reading.**
- The field mesh is fine (0.4-0.9 mm edges, V = 9.5k-25k, `kNode`), so naive under-sampling is not the explanation. But the field npz is independently flagged in `tier1_findings.md` as "a 100-mm box around the peak-SAR location... not informative as full-body metrics," and the Tier-2 surface map built from it is garbage (NRMSE 52, **negative** spatial correlation). So a real field-dump extraction bug is on the table.

### 4.4 The normalisation chain (consistent)

`extract_apd_table_data.py` applies `* 754` and its outputs verify against the published Table 4 (e.g. Thelonious 7 GHz = 2.05). The SAR path normalises consistently. So the 754 is applied once, downstream, and is not double-counted. (A double application would give a ~1/754 absurdity, not observed.)

---

## 5. The central question: which reduction did the PMB paper report?

This is the one thing desk analysis cannot close. Two readings survive.

### 5.1 Reading A - report port = `|S|` (sPD_mod+), over-reports

Evidence:
- `SetAPD` ("Absorbed Power Density") defaults **off**; `AveragedQuantity` never set, so the default reduction applies, and a "Power Density Evaluator" default is plausibly the conservative `|S|`.
- `report > field` on a shared mesh, with `|S| >= n.Re{S}`.
- The earlier report's mapping: ICNIRP's default incident proxy is the modulus.

Implication: the paper's "absorbed power density" would actually be the incident-side modulus `|S| ~ S_inc`, over-reporting true `S_ab` by `~1/(1-|Gamma|^2) ~ 1.5x` (range 1.1-2.7x by direction/frequency). Conservative direction, but the **wrong basic-restriction quantity** (it is the reference-level reduction).

### 5.2 Reading B - report port = `n.Re{S}` (absorbed), field dump buggy

Evidence:
- AEGIS's `S_ab` is **Mie-certified to 0.7%** and *slightly under-estimates* true absorbed PD (it misses diffraction into shadow). It applies the transmittance `T_0` in the peak metric (verified in `engine.py`/`result.py`), so AEGIS-peak is the absorbed quantity (`~0.54*S_inc`), not incident-side.
- AEGIS-peak matched the report port at the peak: direction-averaged **1.027** (per-direction 1.06, 1.20, 0.83).
- If the report were `|S|` (~1.5-2x the absorbed), a certified-and-slightly-low absorbed-PD oracle would read **~0.5-0.65** against it, not 0.83-1.20. The observed ratios are inconsistent with Reading A's 1.5-2x gap.
- `report > field` is fully explained by the known-broken field dump (head-box around the wrong peak; Tier-2 garbage). `SetAPD=True` may simply switch the *output* to the per-vertex APD field, while the report's default reduction is already the absorbed normal flux.

### 5.3 Weighing

Reading B is favoured, because the AEGIS cross-check uses an **independently exact-validated** absorbed-PD oracle and its per-direction agreement (0.83-1.20) is quantitatively incompatible with the report being 1.5-2x too large. The API naming keeps Reading A alive, but the `field<report` datum - the main on-disk support for A - is equally consistent with a buggy field dump, which we have independent reason to believe is broken. **Net: the PMB / Table-4 numbers are probably the correct absorbed quantity; not certain.**

### 5.4 The decisive experiment (one Sim4Life seat-minute)

On a single existing sim, run the evaluator twice with the reduction set **explicitly**:

```python
ev.AveragingArea    = 4.0 cm^2
ev.AveragingMethod  = "Rotating Cube"      # IEEE 63195
ev.AveragedQuantity = "n.Re{S}"   # absorbed  -> S_ab
# ... and again with:
ev.AveragedQuantity = "|S|"       # modulus   -> S_inc-side
```

Then compare both to the published value.
- published == the `n.Re{S}` run -> **Reading B, paper fine.**
- published == the `|S|` run, ~1.5x the `n.Re{S}` run -> **Reading A, erratum** (over-reports `S_ab` by the transmittance).

This simultaneously diagnoses the field-dump bug and removes all remaining ambiguity. Until it is run, neither reading should be asserted as settled.

---

## 6. AEGIS theory and code - is the closed-form law the right quantity?

**Yes, unambiguously.** This part is not a hedge.

### 6.1 The law

```
S_ab(r) = S_inc * T_0 * ReLU[ n(r) . (-k) ]
```

`S_inc * ReLU(n.(-k))` is the incident flux projected onto the tilted surface element (the cosine of incidence); `* T_0` transmits it into tissue. The product is the **inward transmitted normal flux = the absorbed power density = `n.Re{S}` = sPD_n+ = ICNIRP eq.16.** The transmittance `T_0` is present and applied in code (`engine.py: fresnel_T0`; `result.peak_sab_averaged = max(sab_averaged)` with `sab` carrying `T_0`). At 28 GHz skin `T_0 = 0.536`; AEGIS therefore predicts ~half of `S_inc`, the absorbed quantity, not the modulus.

### 6.2 The monograph's observable

`theory/unified/sec_13_validation.tex` defines the validation observable as **"the time-averaged Poynting flux flowing inward through the body surface, evaluated from the exact exterior total field"**, explicitly `S_ab = -½ Re(E_theta H_phi* - E_phi H_theta*)` (the inward radial real Poynting component). `sec_03_fresnel.tex`: "The physically meaningful quantity is the **normal component** of the Poynting vector." This is `n.Re{S}` - the correct reduction, stated outright.

### 6.3 Validation against exact oracles

AEGIS is validated against analytic ground truths, not against the suspect FDTD:
- **Mie lossy sphere** (the CI canary): the surface integral of the inward radial Poynting recovers exact `Q_abs` to 0.7%, certifying the observable. The law underestimates exact Mie by 3-14% for torso/head at 28-60 GHz (diffraction into shadow it omits) - i.e. AEGIS errs *low*, not high.
- **Bessel-Hankel cylinder** (limb / shadow-edge diffraction), with the documented `Im(n) > 0` sign-convention fix.
- Phantom self-consistency: the law matches full angle-dependent Fresnel integration to 0.35% (total power), 0.0% (peak `S_ab`), 28 GHz skin.

### 6.4 The TAP paper

`papers/TAP_paper/paper.tex` defines APD correctly in the abstract: "Absorbed Power Density (APD) is Incident Power Density multiplied by normal-incidence transmission, an ambient-occlusion factor, and the positive incidence cosine." It validates **four independent ways** (Mie exact = primary; full Fresnel; Sim4Life FDTD = 3rd/supplementary; reverberation-chamber + FDTD literature across 108 volunteers and 5 phantoms). The Sim4Life FDTD ratios it cites are `1.027` (peak 4 cm^2 APD, 7 GHz) and `1.012` (Cauchy whole-body, 5.8 GHz).

Two reassurances against circularity:
- **AEGIS does not fit to FDTD.** The "single fitted coefficient... fitted separately for each phantom and frequency from an FDTD sweep" passage describes **prior literature** (Bamba, Flintoft, Zhang, Kodera, Diao). AEGIS *derives the closed form behind* those coefficients; it has no free coefficient tuned to GOLIAT.
- The whole-body `1.012` validation uses FDTD **`DielLoss`** (total ohmic dissipation), which is **reduction-independent** - the true absorbed power regardless of any surface-reduction choice. So the core whole-body validation is immune to the Section-5 question entirely.

### 6.5 Verdict

The AEGIS law, code, monograph, and TAP paper define and validate the **absorbed** power density (`n.Re{S}`), against exact oracles, without fitting to FDTD. **The GOLIAT reduction question does not propagate into AEGIS.** The worst case (Reading A) would only mean the TAP paper's *supplementary* FDTD figure compared AEGIS-absorbed against a `|S|` FDTD column and would need a caption caveat or a re-extraction - it would not touch the law, the Mie/cylinder validation, the whole-body `DielLoss` agreement, or the literature comparison.

---

## 7. How a factor-of-2 could still sneak in (failure-mode checklist)

1. **Reduction conflation** (Section 5): report `|S|` (`S_inc`-side) as `S_ab`. ~1.5-2x, conservative. *Status: unresolved, leaning "not present."*
2. **Peak/RMS mixing** (Section 3): peak fields into a no-½ formula. *Status: not present in GOLIAT.*
3. **Incident-vs-absorbed in the validation metric**: comparing an `S_inc`-side number on one side to an `S_ab` number on the other. AEGIS applies `T_0` (verified), so AEGIS is absorbed-side; the cross-check is only clean if the FDTD side is also absorbed-side (Section 5).
4. **Field-dump extraction bug**: the `skin_apd.npz` under-reads (head-box, sampling). *Status: present; affects AEGIS Tier-2 surface validation only, not the paper.*
5. **Double or missing 754 normalisation**: checked, applied once, verifies against Table 4. *Status: not present.*

---

## 8. Recommendations / action items

1. **Run the Section 5.4 dual-`AveragedQuantity` re-extraction** on 2-3 published frequencies. This is the single highest-value action; it converts "probably fine" into certainty and decides erratum vs methods-note.
2. **Fix the `skin_apd.npz` field dump** (center the box on the peak *SAPD*, not peak *SAR*; verify `kNode` vs cell handling; confirm the per-vertex max >= the report's 4 cm^2-averaged peak). This restores the AEGIS Tier-2 surface validation.
3. **Set the reduction explicitly** in `sapd_extractor.py` going forward: `AveragedQuantity = n.Re{S}`, `AveragingMethod = Rotating Cube`, and correct the `Threshold` comment ("Surface Discretization," not depth). Configuration-by-default for a regulatory quantity is a latent hazard regardless of how this case resolves.
4. **In any paper that reports both**, state the reduction used and report `S_ab` (sPD_n+) for the basic restriction and `S_inc` (sPD_mod+) for the reference-level check, and quote the spread across reductions as the near-field definitional uncertainty (small beyond `lambda/2pi`, growing in the reactive zone and at oblique incidence; ~1.5x at the reflecting skin surface from complex `Gamma`).
5. **AEGIS papers need no change on the law**; at most add a one-line caveat to the supplementary FDTD figure pending item 1.

---

## 9. Quantity reference

| symbol | name | reduction | role | rough size on skin |
|---|---|---|---|---|
| `S_inc` | incident power density | `\|S\|` (sPD_mod+) | reference level | the driver; 1 W/m^2 by normalisation |
| `S_ab` | absorbed power density | `n.Re{S}` (sPD_n+) | basic restriction | `~T_0 * S_inc ~ 0.4-0.55 * S_inc` |
| `T_0`, `T = 1-\|Gamma\|^2` | transmittance | - | links the two | 0.536 at 28 GHz skin |
| `U_ab` | absorbed energy density | - | brief-exposure (<6 min) restriction | J/m^2, sqrt(t) |
| `eta_0` | free-space impedance | - | - | 376.73 ohm; `2*eta_0 = 754` |
| `E_ref` | field for 1 W/m^2 | - | - | 27.46 V/m peak / 19.4 V/m RMS |
| `lambda/2pi` | reactive near-field boundary | - | reduction divergence | ~1.7 mm at 28 GHz |

---

## 10. Sources and provenance

**Read directly (primary, this investigation):**
- Sim4Life 8.2 Python API reference (`goliat/PythonAPIReference_8_2.zip`, `s4l_v1.analysis.em_evaluators`, `PostProRec5G`, `EmPostPro`) - `SetAPD`, `AveragedQuantity`, `AveragingMethod`, `Threshold` semantics.
- GOLIAT extraction code: `sapd_extractor.py`, `sar_extractor.py`, `power_extractor.py`, `extract_apd_table_data.py`, `docs/technical/power_normalization_philosophy.md`.
- On-disk results: `results/far_field/.../sapd_results.json`, `skin_apd.npz`, `tier0_findings.md`, `tier1_findings.md`, `tier2_*_metrics.txt`.
- AEGIS: `theory/unified/sec_13_validation.tex`, `sec_03_fresnel.tex`, `theory/summary_paper.tex`, `papers/TAP_paper/paper.tex`, `src/aegis/engine.py`, `result.py`.

**Secondary (AI-assembled, sources not all verifiable here):**
- `power_density_definitions_report.md` (ICNIRP 2020 and Sim4Life 7.2 manual read directly by that author; standards quotes secondary). Corrected here on the reflecting-surface divergence (Section 2.1).
- Web summaries of IEC/IEEE 63195-1/-2 (2022/2023), C95.1-2019, Christ et al. 2020 - paywalled standards **not** read directly; treat the eq.16/18/20 attributions as "consistent with, not verified against" the primary text.

**Provenance caveat on this report:** assembled by an AI agent from the above during a single investigation. The factual reads (code, API ref, LaTeX, on-disk numbers) are reliable; the standards attributions are second-hand; the Section-5 verdict is a weighing of evidence, not a measurement. The Section-5.4 experiment is the authority that supersedes this document.

---

## Appendix A. Epistemic log (honest record of the reasoning, including the wrong turns)

This investigation reversed itself twice; recording it so the next reader does not repeat the swings.

1. **First pass: "factor of ½ - is the paper doubled?"** Concluded *no* (peak/RMS, 754 = 2*eta_0 correct). Stable; never overturned.
2. **Second pass: "SetAPD defaults off, so the paper used `|S|` and over-reports ~1.5x."** Asserted too confidently from the API naming + `field<report`. **This was an over-correction.**
3. **Third pass: read the AEGIS monograph/code.** AEGIS applies `T_0` and is Mie-certified absorbed-PD; it matches the report port at 1.027 with per-direction 0.83-1.20, which is **incompatible** with the report being 1.5-2x too large. Reverted toward "report ~= absorbed, paper probably fine, field dump is the buggy one."
4. **Lesson:** the strongest available evidence was the exact-Mie-certified AEGIS cross-check, and it should have been weighted above API naming and a datum (`field<report`) that a known-broken field dump explains equally well. When an independent, exactly-validated calculation is available, anchor on it. And when desk evidence genuinely conflicts (it still does, weakly), name the one experiment and stop asserting.

*End of report.*
