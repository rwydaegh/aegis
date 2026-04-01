# Tutorial 4: ICNIRP 2020 compliance

This tutorial covers the `aegis.compliance` module: how to look up regulatory limits, evaluate a dosimetry result against those limits, find the maximum compliant transmit power, and run quick feasibility checks from RF link budget parameters.

Prerequisites: tutorials 1 through 3. You need the `aegis` package installed (`pip install -e ".[dev]"`). No STL files or external data are required.

---

## ICNIRP 2020 limits

ICNIRP 2020 defines basic restrictions and reference levels for frequencies from 6 GHz to 300 GHz. AEGIS implements Tables 2, 5, and 6 of that document.

**Basic restrictions** limit $S_{\mathrm{ab}}$, the absorbed power density averaged spatially over 4 cm$^2$ and temporally over 6 minutes. This is the quantity AEGIS computes directly. Above 30 GHz an additional 1 cm$^2$ constraint applies to guard against focused beams.

**Reference levels** limit $S_{\mathrm{inc}}$, the incident power density in free space at the body location. Reference levels are derived from basic restrictions under worst-case assumptions and are therefore more conservative. Passing either set of limits is sufficient for compliance.

| Quantity | General public | Occupational | Notes |
|---|---|---|---|
| $S_{\mathrm{ab}}$ over 4 cm$^2$ | 20 W/m$^2$ | 100 W/m$^2$ | Table 2 |
| $S_{\mathrm{ab}}$ over 1 cm$^2$ | 40 W/m$^2$ | 200 W/m$^2$ | Table 2, only >30 GHz |
| Whole-body SAR | 0.08 W/kg | 0.4 W/kg | Table 2 |
| $S_{\mathrm{inc}}$ local (4 cm$^2$) | $55 / f_G^{0.177}$ W/m$^2$ | $275 / f_G^{0.177}$ W/m$^2$ | Table 6, $f_G$ in GHz |
| $S_{\mathrm{inc}}$ whole-body | 10 W/m$^2$ | 50 W/m$^2$ | Table 5 |

The local $S_{\mathrm{inc}}$ limit decreases slowly with frequency. At 28 GHz it is approximately 31 W/m$^2$ for general public. At 60 GHz it drops to about 26 W/m$^2$.

---

## Getting limits programmatically

`icnirp_limits` returns an `ICNIRPLimits` dataclass with all applicable limits at a given scenario and frequency.

```python
import matplotlib.pyplot as plt
import scienceplots  # noqa: F401
plt.style.use(["science", "ieee", "no-latex"])
plt.rcParams.update({"figure.figsize": (3.5, 2.625)})

from aegis.compliance import ExposureScenario, icnirp_limits

lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, freq_hz=28e9)

print(f"S_ab (4 cm^2):  {lim.sab_4cm2} W/m^2")    # 20.0
print(f"S_ab (1 cm^2):  {lim.sab_1cm2}")             # None at 28 GHz (below 30 GHz threshold)
print(f"SAR_wb:         {lim.sar_wb} W/kg")           # 0.08
print(f"S_inc local:    {lim.sinc_local:.2f} W/m^2") # ~30.9
print(f"S_inc wb:       {lim.sinc_whole_body} W/m^2") # 10.0

# Above 30 GHz the 1 cm^2 constraint is active
lim_60 = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, freq_hz=60e9)
print(f"S_ab (1 cm^2) at 60 GHz: {lim_60.sab_1cm2} W/m^2")  # 40.0
```

The frequency argument must be above 6 GHz and at most 300 GHz. Passing an out-of-range value raises `ValueError`.

---

## Evaluating compliance from a dosimetry result

The most direct path is to compute dosimetry with the engine and call `evaluate_compliance()` on the result. The example below uses a sphere mesh and a single plane wave arriving from broadside.

```python
import numpy as np
from aegis import DosimetryEngine, BodyMesh, PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

# Synthetic sphere mesh, radius 0.1 m
body = BodyMesh.sphere(radius=0.1, n_subdivisions=3)

# Single plane wave, 1 W/m^2, arriving from +z
paths = PropagationPaths.from_powers(
    k_hat=np.array([[0.0, 0.0, -1.0]]),
    power=np.array([1.0]),
)

# Run dosimetry with spatial averaging (required for compliance)
engine = DosimetryEngine(SKIN_28GHZ)
result = engine.compute(body, paths, mode="spatial")

# Evaluate ICNIRP 2020 compliance (general public by default)
compliance = result.evaluate_compliance()

print(f"Overall: {'PASS' if compliance.overall_pass else 'FAIL'}")
print(f"Tightest margin: {compliance.margin_db:+.1f} dB")
```

`evaluate_compliance()` uses `result.freq_hz`, which the engine sets from the tissue model. Spatial averaging must have been enabled (it is on by default) so that `sab_averaged` is populated. If `sab_averaged` is `None`, the method falls back to the raw per-triangle peak as a conservative upper bound.

For occupational scenarios, pass the scenario explicitly:

```python
from aegis.compliance import ExposureScenario

compliance_occ = result.evaluate_compliance(ExposureScenario.OCCUPATIONAL)
print(f"Occupational margin: {compliance_occ.margin_db:+.1f} dB")
```

---

## Individual compliance checks

`ComplianceResult` holds one `ComplianceCheck` per quantity. Each check exposes the measured value, the applicable limit, a pass/fail flag, and the margin in decibels.

```python
# Iterate over all populated checks
for check in compliance.all_checks:
    status = "PASS" if check.compliant else "FAIL"
    print(
        f"{check.label}: {check.value:.4g} / {check.limit:.4g} {check.unit} "
        f"[{status}] ({check.margin_db:+.1f} dB)"
    )

# Access individual checks by name (may be None if not computed)
if compliance.sab_4cm2 is not None:
    print(f"S_ab ratio: {compliance.sab_4cm2.ratio:.3f}")   # value / limit

if compliance.sar_wb is not None:
    print(f"SAR margin: {compliance.sar_wb.margin_db:+.1f} dB")
```

A positive margin means the measured value is below the limit. A negative margin means the limit is exceeded. The `margin_db` property on `ComplianceResult` returns the tightest (smallest) margin across all populated checks.

---

## Human-readable summary

`summary_text` formats the full compliance assessment as a plain-text report. Pass the transmit power in dBm to include it in the header.

```python
from aegis.compliance import summary_text

print(summary_text(compliance, tx_power_dbm=23.0))
```

Example output:

```
ICNIRP 2020 compliance (general_public)
Frequency: 28.000 GHz
Tx power: 23.0 dBm

  S_ab (4 cm^2): 1.234 / 20 W/m^2 [PASS] (margin +12.1 dB)
  SAR_wb: 0.00123 / 0.08 W/kg [PASS] (margin +18.1 dB)
  S_inc (local): 0.987 / 30.86 W/m^2 [PASS] (margin +14.9 dB)

Overall: PASS (tightest margin: +12.1 dB)
```

---

## Maximum compliant power

$S_{\mathrm{ab}}$ scales linearly with transmit power for all fidelity levels (0-8). Given a result computed at reference power $P_{\mathrm{ref}}$, the maximum compliant power is:

$$P_{\mathrm{max}} = P_{\mathrm{ref}} \cdot \min_i \frac{\mathrm{limit}_i}{\mathrm{value}_i}$$

The `max_compliant_power` function computes this from a `ComplianceResult` and the reference power.

```python
from aegis.compliance import max_compliant_power
import numpy as np

# Result was computed at 1 W reference power
ref_power_w = 1.0
p_max = max_compliant_power(compliance, ref_power_w=ref_power_w)
p_max_dbm = 10 * np.log10(p_max * 1e3)

print(f"Max compliant power: {p_max:.3f} W ({p_max_dbm:.1f} dBm)")
```

This identifies the tightest constraint across all checks and scales the reference power accordingly.

---

## Scaling results for power sweeps

Rather than re-running the engine at every power level, compute once at a reference power and scale the result. `DosimetryResult.scale(factor)` returns a new result with all power quantities multiplied by `factor`.

```python
import numpy as np

# Compute once at 1 W
result_1w = engine.compute(body, paths, mode="spatial")

powers_dbm = np.linspace(0, 40, 200)
margins = []

for p_dbm in powers_dbm:
    p_w = 10 ** ((p_dbm - 30) / 10)
    scaled = result_1w.scale(p_w)
    c = scaled.evaluate_compliance()
    margins.append(c.margin_db)

margins = np.array(margins)

fig, ax = plt.subplots()
ax.plot(powers_dbm, margins)
ax.axhline(0, color="r", linestyle="--", label="Compliance limit")
ax.fill_between(powers_dbm, margins, 0, where=margins >= 0, alpha=0.15, color="g")
ax.fill_between(powers_dbm, margins, 0, where=margins < 0, alpha=0.15, color="r")
ax.set_xlabel("TX power (dBm)")
ax.set_ylabel("Compliance margin (dB)")
ax.legend(fontsize=6)
plt.show()
```

The `power_sweep` function in `aegis.compliance` automates this sweep and returns a dict with power, margin, and compliance arrays.

```python
from aegis.compliance import power_sweep

# compliance was computed at ref_power_w = 1.0 W
sweep = power_sweep(compliance, ref_power_w=1.0, p_min_w=1e-3, p_max_w=10.0)

print(f"Max compliant power: {sweep['p_max_compliant_w']:.3f} W")
# sweep['power_dbm'] and sweep['margin_db'] are ready to plot
```

---

## Compliance heatmap over frequency and power

`compliance_heatmap` builds a 2D grid of compliance margin over (frequency, power) pairs. Because the $S_{\mathrm{inc}}$ local limit depends on frequency while the $S_{\mathrm{ab}}$ limit does not, the heatmap becomes non-trivial when `sinc_local` is provided.

```python
from aegis.compliance import compliance_heatmap

hm = compliance_heatmap(
    sab_4cm2=5.0,           # measured S_ab at 1 W reference
    ref_power_w=1.0,
    sinc_local=8.0,         # measured S_inc at 1 W reference
    freq_min_hz=7e9,
    freq_max_hz=100e9,
)

fig, ax = plt.subplots(figsize=(3.5, 2.8))
pcm = ax.pcolormesh(
    hm["freq_hz"] / 1e9,
    hm["power_dbm"],
    hm["margin_db"],
    cmap="RdYlGn",
    vmin=-10,
    vmax=10,
    shading="auto",
    rasterized=True,
)
ax.contour(
    hm["freq_hz"] / 1e9,
    hm["power_dbm"],
    hm["margin_db"],
    levels=[0],
    colors="k",
    linewidths=0.8,
)
fig.colorbar(pcm, ax=ax, label="Margin (dB)")
ax.set_xlabel("Frequency (GHz)")
ax.set_ylabel("TX power (dBm)")
plt.show()
```

The return dict also includes `p_max_per_freq`, the maximum compliant power at each frequency.

---

## Link budget compliance

`link_budget_compliance` estimates exposure and evaluates compliance directly from RF system parameters, without running the full dosimetry engine. It assumes free-space propagation, isotropic spreading, and normal-incidence absorption. This is a conservative upper bound.

```python
from aegis.compliance import link_budget_compliance

result_lb = link_budget_compliance(
    tx_power_w=1.0,
    antenna_gain_dbi=15.0,
    distance_m=3.0,
    freq_hz=28e9,
    scenario=ExposureScenario.GENERAL_PUBLIC,
)

print(f"S_inc:         {result_lb['sinc']:.4g} W/m^2")
print(f"S_ab estimate: {result_lb['sab_estimate']:.4g} W/m^2 (T0 = {result_lb['T0']:.4f})")
print(f"Compliant:     {result_lb['compliant']}")
print(f"Margin:        {result_lb['margin_db']:+.1f} dB")
print(f"Max TX power:  {result_lb['max_tx_power_w']:.3f} W ({result_lb['max_tx_power_dbm']:.1f} dBm)")
```

The transmission coefficient `T0` is estimated from the skin tissue dielectric model at the given frequency. Pass `T0` explicitly to override it.

---

## Command-line interface

For quick spot checks without writing Python, use the `aegis.compliance` CLI:

```text
# Check a measured S_ab value at 28 GHz
python -m aegis.compliance --freq 28e9 --sab 15.0

# Include whole-body SAR and incident power density
python -m aegis.compliance --freq 28e9 --sab 15.0 --sar 0.05 --sinc 8.0

# Print ICNIRP limits only
python -m aegis.compliance --freq 28e9 --limits

# Find max compliant TX power given a reference measurement
python -m aegis.compliance --freq 28e9 --sab 15.0 --power 1.0

# JSON output for scripting
python -m aegis.compliance --freq 28e9 --sab 15.0 --json

# Occupational scenario
python -m aegis.compliance --freq 60e9 --sab 80.0 --occupational

# Link budget check: 1 W, 15 dBi gain, 3 m distance
python -m aegis.compliance --freq 28e9 --link-budget --tx-power 1.0 --gain 15 --distance 3
```

---

## Limitations

- **Spatial averaging shape.** AEGIS uses circular neighborhoods (KD-tree ball query) to approximate the 4 cm$^2$ patch. ICNIRP specifies a square patch. The approximation is conservative for smooth surfaces and is noted in compliance reports.
- **Temporal averaging.** AEGIS computes steady-state exposure. The 6-minute temporal average is not modeled. For continuous sources this is exact. For pulsed sources the result is conservative.
- **Frequency range.** The compliance module covers 100 kHz to 300 GHz. Above 6 GHz, all ICNIRP 2020 limits are evaluated (S_ab, S_inc, SAR_wb). Below 6 GHz, only whole-body SAR is checked. Local SAR over a 10 g cubic mass is not yet implemented.
- **Multi-frequency exposure.** ICNIRP equation 2 defines a sum rule for simultaneous exposure at multiple frequencies. This is not yet implemented.

---

## Next steps

Tutorial 5, [Coherent MIMO and ECBF](coherent_mimo.md), covers the field channel matrix, the exposure operator $\mathbf{Q}$, maximum-ratio transmission beamforming, and exposure-constrained beamforming.
