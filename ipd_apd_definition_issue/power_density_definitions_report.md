# Power density above 6 GHz: $S_{ab}$, $S_{inc}$, the three Poynting reductions, and the $\tfrac12$ / RMS question

**A working reference distilled from this conversation.**
Scope: ICNIRP 2020 basic restrictions above 6 GHz, their formal definition from Maxwell's equations, the relationship to IEEE/IEC standards, the three competing scalar reductions of the Poynting vector, and the factor‑of‑½ (RMS‑vs‑peak) ambiguity between ICNIRP and Sim4Life. Primary sources used: the ICNIRP 2020 guidelines PDF and the Sim4Life 7.2 Reference Guide (both read directly), plus the standards/literature cited inline.

---

## 0. Executive conclusions (read this first)

1. **The basic restriction above 6 GHz is absorbed power density $S_{ab}$** (W m⁻²), not SAR. SAR is dropped because absorption becomes superficial (penetration depth ≈ 8 mm at 6 GHz, ≈ 0.2 mm at 300 GHz) and a mass‑averaged quantity stops tracking the surface temperature rise that actually drives the health effect.

2. **$S_{ab}$ is, formally, the inward normal flux of the time‑averaged Poynting vector**, spatially averaged over a 4 cm² square (plus a 1 cm² constraint above 30 GHz). This follows directly from Poynting's theorem: the net power crossing the body surface equals the ohmic dissipation inside.

3. **The "$\tfrac12$ vs no $\tfrac12$" discrepancy between ICNIRP and Sim4Life is not physical.** It is entirely the RMS‑vs‑peak phasor convention. ICNIRP uses RMS fields (provably, from its plane‑wave equation), so it writes $S=\mathrm{Re}(\mathbf E\times\mathbf H^*)$ with no $\tfrac12$; Sim4Life uses peak‑amplitude fields, so it writes $S=\tfrac12\mathbf E\times\mathbf H^*$. They are the **same** time‑averaged W m⁻².

4. **There is a second, genuinely physical ambiguity** that is independent of the $\tfrac12$ issue: which scalar you extract from the (vector, complex) Poynting field — the **normal real part**, the **norm of the real part**, or the **norm of the complex vector**. These three coincide for a normally incident plane wave and diverge in the reactive near field. ICNIRP, IEEE, ISED and Sim4Life all enumerate exactly these three.

5. **ICNIRP itself uses two different reductions**: the basic restriction $S_{ab}$ (eq. 16) is the *normal real part*; the reference level $S_{inc}$ (eq. 18) is the *norm of the complex vector* (the most conservative, because up to ~50% of incident power reflects and you want the proxy to over‑, not under‑, predict).

6. **For 28 GHz device pre‑compliance:** report **sPD_n+** for the absorbed/basic‑restriction quantity and **sPD_mod+** for the conservative incident check; quote the spread across the three as your near‑field definitional uncertainty. The choice only matters in the reactive near field ($d<\lambda/2\pi\approx1.7$ mm at 28 GHz) and at large oblique incidence.

---

## 1. The basic restriction above 6 GHz

ICNIRP 2020 (Health Phys. 118(5):483–524) splits the spectrum at **6 GHz**:

| Range | Basic‑restriction quantity | Rationale |
|---|---|---|
| 100 kHz – 6 GHz | SAR (whole‑body avg; local SAR over 10 g) | EMF penetrates deep; mass‑averaged power tracks temperature |
| > 6 – 300 GHz | **Absorbed power density $S_{ab}$** (W m⁻²) | Absorption is superficial; area‑averaged surface power tracks skin temperature |

The transition is at 6 GHz because there most absorbed power sits in cutaneous tissue, representable by the 2.15 cm × 2.15 cm face of the 10 g SAR cube — which is ≈ 4 cm², giving a continuous handover.

**Local $S_{ab}$ limits (≥ 6 min averaging, square 4 cm²):**

| | Occupational | General public |
|---|---|---|
| $S_{ab}$ (4 cm²), > 6–300 GHz | 100 W m⁻² | 20 W m⁻² |
| Additional 1 cm² constraint, > 30 GHz | 200 W m⁻² | 40 W m⁻² (= 2× the 4 cm² value) |

The 1 cm² rule above 30 GHz stops a compliant 4 cm² average from concealing a focused‑beam peak. Brief‑exposure (< 6 min) limits are set on **absorbed energy density** $U_{ab}$ (J m⁻²) with a $\sqrt{t}$ time dependence.

The **derivation chain** is thermal, not field‑based: operational adverse‑health‑effect thresholds of 5 °C (Type‑1 tissue) and 2 °C (Type‑2), an absorbed power density of ~200 W m⁻² to reach the 5 °C rise, then reduction factors of 2 (occupational) and 10 (general public).

---

## 2. The formal definition from Maxwell's equations

Start from the complex Poynting theorem. With $e^{j\omega t}$ convention and $\nabla\times\mathbf H=(\sigma+j\omega\varepsilon)\mathbf E$, the divergence of the complex Poynting vector $\mathbf S=\tfrac12\mathbf E\times\mathbf H^*$ gives, after taking the real part and integrating over a tissue volume $V$ bounded by $\partial V$:

$$
P_{abs} \;=\; -\oint_{\partial V}\mathrm{Re}\{\mathbf S\}\cdot d\mathbf A \;=\; \tfrac12\int_V \sigma|\mathbf E|^2\,dV .
$$

In words: **the net inward flux of the time‑averaged Poynting vector across the surface equals the total ohmic dissipation inside.** $S_{ab}$ is this quantity localised to the surface and spatially averaged. With $\hat n$ the inward surface normal and $A$ the averaging area:

$$
\boxed{\,S_{ab}=\frac{1}{A}\iint_A \mathrm{Re}\!\left\{\tfrac12\,\mathbf E\times\mathbf H^*\right\}\cdot\hat n\;dA\,}
$$

evaluated with the **total** (incident + scattered) fields at the physical body surface.

**This is exactly what ICNIRP 2020 writes** (Appendix A):

- **Eq. 15** — equivalent volumetric form: $S_{ab}=\iint_A dx\,dy\!\int_0^{Z_{max}}\rho(x,y,z)\,\mathrm{SAR}(x,y,z)\,dz / A$ (depth integral of dissipation).
- **Eq. 16** — Poynting form: $S_{ab}=\iint_A \mathrm{Re}[\mathbf E\times\mathbf H^*]\,ds/A$, with $ds$ normal to the averaging area.
- **Eq. 20** — planar link to incident: $S_{ab}=(1-|\Gamma|^2)\,S_{inc}$.

> **Note the absence of the $\tfrac12$ in ICNIRP eq. 16.** That is the RMS convention (Section 4), not an error. Eqs. 15 and 16 are the same quantity: the surface Poynting integral equals the depth‑integrated dissipation, which is the entire content of Poynting's theorem.

---

## 3. Relationship to standards

| Body | Limit name | Quantity above 6 GHz |
|---|---|---|
| **ICNIRP 2020** | Basic restriction (BR) | Absorbed power density $S_{ab}$ |
| **IEEE C95.1‑2019** | Dosimetric reference limit (DRL) | Epithelial power density |
| Both | Reference level / ERL | Incident power density $S_{inc}$ |

- **ICNIRP $S_{ab}$ vs IEEE epithelial PD**: conceptually the same transmitted/surface power density, harmonised in the 2019/2020 cycle; they differ in reference plane (body surface vs epithelium), producing small numerical differences in how the outermost lossy layer is handled.
- **Assessment procedures (IEC/IEEE 63195 series)**: 63195‑1 (2022) measurement, 63195‑2 (2022) computational — both originally codified **surface power density (sPD / mpsPD)**. The forthcoming **63195‑4** specifies FDTD/FEM procedures for **absorbed/epithelial power density** directly (solving Maxwell's equations).
- **Base stations**: IEC 62232 (2022, updated 2025).
- **Access note:** IEEE C95.1‑2019 is **free** via the IEEE GET program; the freely posted *Synopsis of IEEE Std C95.1‑2019* (hal‑03499674) summarises the DRL/ERL structure. The genuinely paywalled material is IEC/IEEE 63195 — but the Sim4Life manual reproduces the operative sPD definitions from it.

---

## 4. The $\tfrac12$ / RMS‑vs‑peak question — resolved

### 4.1 What each source literally writes (verified)

| Source | Complex Poynting vector | Incident PD | Field convention |
|---|---|---|---|
| **ICNIRP 2020** | $\mathbf S=\mathbf E\times\mathbf H^*$ (eq. 16, no $\tfrac12$) | $S_{inc}=\lvert\mathbf E\times\mathbf H^*\rvert$ (eq. 18) | **RMS** |
| **Sim4Life 7.2** | $\mathbf S=\tfrac12\,\mathbf E\times\mathbf H^*$ | (uses sPD reductions) | **peak amplitude** |

Both transcriptions are correct.

### 4.2 Proof that ICNIRP is RMS

ICNIRP eq. 19, for a plane wave: $S_{inc}=|E|^2/Z_0=Z_0|H|^2$. The physically unambiguous time‑averaged intensity of a plane wave is

$$
\langle S\rangle=\frac{|E_{pk}|^2}{2Z_0}=\frac{|E_{rms}|^2}{Z_0}.
$$

ICNIRP's eq. 19 has **no $\tfrac12$** and equals $|E|^2/Z_0$, so ICNIRP's $E$ **must** be RMS. Corroborated by eq. 10 (SAR uses "rms" $E$) and the reference‑level figures labelled "unperturbed rms values."

### 4.3 Sim4Life is peak

The manual defines $|\vec H|_{RMS}=\tfrac1{\sqrt2}|\vec H(\vec r)|$, i.e. the stored complex field is the **peak** amplitude — which is exactly why the $\tfrac12$ appears.

### 4.4 They are identical

$$
\underbrace{\mathrm{Re}\!\left(\mathbf E_{rms}\times\mathbf H_{rms}^*\right)}_{\text{ICNIRP, no }\frac12}
\;=\;
\underbrace{\tfrac12\,\mathrm{Re}\!\left(\mathbf E_{pk}\times\mathbf H_{pk}^*\right)}_{\text{S4L, with }\frac12}
\qquad\text{since}\quad \mathbf E_{rms}=\mathbf E_{pk}/\sqrt2 .
$$

**The $\tfrac12$ and the $\sqrt2$‑per‑field are the same fact.** "$S_{ICNIRP}=2\,S_{S4L}$" is true only if you feed *identical numbers* into both formulas — i.e. if you drop S4L's **peak** fields into ICNIRP's **no‑$\tfrac12$** formula. That mismatch is the only place a real 2× error can sneak in. **Fix:** use S4L's RMS fields with ICNIRP's no‑$\tfrac12$ formulas, or keep peak fields and keep the $\tfrac12$.

---

## 5. The three Poynting reductions — the genuinely physical ambiguity

Independent of the $\tfrac12$ convention, a (complex, vector) Poynting field can be reduced to a scalar surface power density in three ways. Christ et al. (2020, *Bioelectromagnetics* 41(5)) named and compared them; ISED RSS‑102.IPD.MEAS codifies them; Sim4Life's Power Density Evaluator implements them:

| Sim4Life name | Definition | Maps to |
|---|---|---|
| **sPD_n+** | $\hat n\cdot\mathrm{Re}\{\mathbf S\}$ (normal component of real part) | **ICNIRP $S_{ab}$, eq. 16** (basic restriction) |
| **sPD_tot+** | $\lvert\mathrm{Re}\{\mathbf S\}\rvert$ (norm of real part) | the "active flux" / Sergei's quantity |
| **sPD_mod+** | $\lvert\mathbf S\rvert$ (norm of complex vector) | **ICNIRP $S_{inc}$, eq. 18** (reference level) |

**Relationships (exact):**

$$
|\mathbf S|^2=|\mathrm{Re}\,\mathbf S|^2+|\mathrm{Im}\,\mathbf S|^2,
\qquad
|\mathrm{Re}\{S_n\}|\le|\mathrm{Re}\,\mathbf S|\le|\mathbf S|
\;\Rightarrow\;
\text{sPD\_n+}\le\text{sPD\_tot+}\le\text{sPD\_mod+}.
$$

**Convergence/divergence:**
- *Normally incident plane wave:* $\mathbf E\perp\mathbf H$, in phase, flow purely along $\hat n$ ⇒ $\mathrm{Im}\,\mathbf S=0$, no tangential part ⇒ **all three equal $|E|^2/2\eta_0$.** This is why the distinction was invisible until mmWave device exposure.
- *Reactive near field ($d<\lambda/2\pi$):* $\mathbf E,\mathbf H$ acquire a phase difference ⇒ non‑zero $\mathrm{Im}\,\mathbf S$ (stored, non‑propagating energy) and tangential real flow ⇒ the three split. The gap between sPD_n+ and sPD_mod+ is precisely the reactive + tangential content.

**Why ICNIRP defaults $S_{inc}$ to the modulus:** Christ et al. found incident PD can **underestimate** the actual transmitted PD by > 6 dB (×4) near the source, and that **the modulus gives the smallest underestimation** — i.e. it is the most conservative proxy. Hence ICNIRP eq. 18 = modulus, with the explicit caveat (after eq. 21) that in near‑field scenarios the Poynting components are complex and warrant detailed investigation. The reassuring counterweight: for realistic source‑to‑body separations the reactive‑near‑field contribution to deposited energy is small, and the definitions track peak temperature for small‑to‑moderate incidence angles, diverging mainly at large oblique angles.

---

## 6. Critique of the 2022 letter to Sergei Shikhantsov

**Right:**
- The literal transcriptions of ICNIRP (eqs. 16, 18) and Sim4Life ($\tfrac12\mathbf E\times\mathbf H^*$) are accurate.
- The instinct that eq. (me) and eq. (sergei) "use a different definition of $S_{inc}$" is correct.

**Wrong / conflated:**
- **"$\mathbf S_{ICNIRP}=2\,\mathbf S_{S4L}$" is a phantom.** It only holds for identical numerical inputs; once the RMS‑vs‑peak convention is applied consistently, the 2× vanishes and the two are equal. (See §4.)
- **eq.(me) ≠ eq.(sergei) stacks two effects.** After removing the spurious 2×, the *only* residual difference is **modulus‑of‑complex** (eq. me = ICNIRP $S_{inc}$ = sPD_mod+) vs **modulus‑of‑real‑part** (eq. sergei = sPD_tot+). That residual is the reactive‑near‑field term — the real, physical distinction.
- **A benign math slip in the Sergei derivation:** writing $\mathrm{RQ}_{sergei}=\tfrac1T\int_0^T|\mathbf S(t)|\,dt$ and then pulling the modulus outside swaps "average of the magnitude" for "magnitude of the average":

$$
\big\langle|\mathbf S(t)|\big\rangle \;\ge\; \big|\langle\mathbf S(t)\rangle\big| = \big|\tfrac12\mathrm{Re}(\mathbf E\times\mathbf H^*)\big|
\quad\text{(Jensen; equality only for unidirectional far‑field flux).}
$$

The closed form is exact in the far field and approximate near the antenna — and that approximation error is *itself* a reactive‑near‑field term.

**Net:** transcriptions right; the 2× is a convention artifact (they agree); the eq.(me)≠eq.(sergei) point is real but had a phantom 2× riding on the genuine modulus‑vs‑real‑part split; plus a far‑field‑only average/magnitude swap.

---

## 7. Practical guidance for AEGIS / 28 GHz pre‑compliance

1. **Pin the field convention once.** Decide RMS or peak at the export boundary and never mix. If using ICNIRP's no‑$\tfrac12$ formulas, feed RMS fields; if using $\tfrac12\mathbf E\times\mathbf H^*$, feed peak fields. A silent 2× here is the single most likely numerical bug.
2. **Report sPD_n+ for the absorbed / basic‑restriction quantity** — it is literally ICNIRP eq. 16 and the reduction that couples to heating.
3. **Report sPD_mod+ for the conservative incident‑side (reference‑level) check** — matches ICNIRP $S_{inc}$ (eq. 18).
4. **Quote the spread across the three reductions** at your evaluation distance as the near‑field definitional uncertainty. Expect it to be small beyond ~$\lambda/2\pi$ (≈ 1.7 mm at 28 GHz) and at near‑normal incidence; non‑negligible inside the reactive zone and at large oblique angles.
5. **Averaging geometry matters too** — the 4 cm² (and 1 cm² > 30 GHz) square, with the rotating‑square max, is part of the definition, not a post‑hoc choice.
6. **The off‑axis / reactive‑near‑field choice is the one thing no document settles for you** — the standards pick conservative defaults; your own RT/FDTD numbers for the specific geometry are what decide whether the proxy is adequate or over‑conservative.

---

## 8. Symbol reference

| Symbol | Meaning |
|---|---|
| $\mathbf S=\tfrac12\mathbf E\times\mathbf H^*$ (peak) or $\mathbf E_{rms}\times\mathbf H_{rms}^*$ | complex Poynting vector |
| $S_{ab}$ | absorbed power density — ICNIRP basic restriction > 6 GHz; $\hat n\cdot\mathrm{Re}\{\mathbf S\}$ averaged over $A$ |
| $S_{inc}$ | incident power density — reference level; $|\mathbf E\times\mathbf H^*|$ (modulus) |
| $U_{ab}$ | absorbed energy density (J m⁻²), brief‑exposure restriction |
| $\Gamma$, $T=1-|\Gamma|^2$ | reflection coefficient / transmittance at the air–tissue interface |
| sPD_n+ / sPD_tot+ / sPD_mod+ | normal‑real / norm‑of‑real / norm‑of‑complex reductions (IEC/IEEE, Sim4Life) |
| $\lambda/2\pi$ | reactive‑near‑field boundary (≈ 1.7 mm at 28 GHz) |

---

*Sources read directly: ICNIRP 2020 Guidelines (Health Phys. 118(5):483–524); Sim4Life 7.2 Reference Guide. Literature/standards cited inline: Christ et al. 2020 (Bioelectromagnetics 41(5)); IEC/IEEE 63195‑1/‑2 (2022), draft ‑4; IEEE C95.1‑2019; IEC 62232; ISED RSS‑102.IPD.MEAS; Hashimoto et al. 2017; Sasaki et al. 2017; Funahashi et al. 2018.*
