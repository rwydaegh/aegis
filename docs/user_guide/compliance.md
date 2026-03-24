# Compliance assessment

AEGIS evaluates exposure against ICNIRP 2020 basic restrictions and reference levels for frequencies above 6 GHz to 300 GHz. The source document is `theory/ICNIRPrfgdl2020.pdf`.

## Two types of compliance check

ICNIRP defines two categories of exposure limits, and AEGIS checks both:

- **Basic restrictions** limit the absorbed power density $S_{ab}$ on the body surface, averaged over 4 cm$^2$ and 6 minutes. This is the quantity AEGIS computes directly.
- **Reference levels** limit the incident power density $S_{inc}$ in free space at the body location. These are derived from basic restrictions under worst-case assumptions and are more conservative.

Compliance with either set is sufficient. In practice, if the reference level check passes, the basic restriction check will too (but not the reverse).

## Limits

All values from ICNIRP 2020 Tables 2, 5, and 6.

| Check | General public | Occupational | Source |
|-------|---------------|-------------|--------|
| $S_{ab}$ over 4 cm$^2$ | 20 W/m$^2$ | 100 W/m$^2$ | Table 2 |
| $S_{ab}$ over 1 cm$^2$ (>30 GHz) | 40 W/m$^2$ | 200 W/m$^2$ | Table 2, note 5 |
| Whole-body SAR | 0.08 W/kg | 0.4 W/kg | Table 2 |
| $S_{inc}$ local (4 cm$^2$) | $55/f_G^{0.177}$ W/m$^2$ | $275/f_G^{0.177}$ W/m$^2$ | Table 6 |
| $S_{inc}$ whole-body | 10 W/m$^2$ | 50 W/m$^2$ | Table 5 |

The 1 cm$^2$ constraint is 2$\times$ the 4 cm$^2$ basic restriction, applied only above 30 GHz to account for focused beams at higher frequencies. The local $S_{inc}$ limit depends on frequency: at 28 GHz it is approximately 31 W/m$^2$ for general public.

## Using the compliance module

```python
from aegis.compliance import (
    ExposureScenario,
    icnirp_limits,
    evaluate_compliance,
    summary_text,
)

# Get limits for a specific scenario and frequency
lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28e9)
print(f"S_ab limit: {lim.sab_4cm2} W/m²")
print(f"S_inc local limit: {lim.sinc_local:.1f} W/m²")

# Evaluate compliance from computed quantities
result = evaluate_compliance(
    scenario=ExposureScenario.GENERAL_PUBLIC,
    freq_hz=28e9,
    peak_sab_4cm2=12.3,
    peak_sinc_local=25.0,
    sinc_whole_body=4.2,
    sar_wb=0.012,
)

print(f"Overall: {'PASS' if result.overall_pass else 'FAIL'}")
print(f"Margin: {result.margin_db:+.1f} dB")

# Human-readable report
print(summary_text(result, tx_power_dbm=23.0))
```

### Evaluating compliance from a dosimetry result

If you already have a `DosimetryResult`, call `evaluate_compliance()` directly on it:

```python
result = engine.compute(body, paths, mode="spatial")
compliance = result.evaluate_compliance()

print(f"Overall: {'PASS' if compliance.overall_pass else 'FAIL'}")
print(f"Margin: {compliance.margin_db:+.1f} dB")
```

This populates all available checks from the result fields automatically. Pass `ExposureScenario.OCCUPATIONAL` for occupational limits.

### Maximum compliant power

Given a compliance result computed at some reference transmit power, `max_compliant_power` finds the largest power that keeps all checks passing:

```python
from aegis.compliance import max_compliant_power

compliance = result.evaluate_compliance()
p_max = max_compliant_power(compliance, ref_power_w=1.0)
print(f"Max compliant power: {p_max:.2f} W ({10 * np.log10(p_max * 1e3):.1f} dBm)")
```

$S_{ab}$ scales linearly with transmit power for all fidelity levels, so the calculation is exact: $P_{max} = P_{ref} \cdot \min_i(\text{limit}_i / \text{value}_i)$.

Combined with `DosimetryResult.scale()`, this enables parameter sweeps without rerunning the engine:

```python
# Compute once at 1 W
result_1w = engine.compute(body, paths, mode="spatial")

# Scale to explore the compliance boundary
for p_dbm in range(10, 40):
    p_w = 10 ** ((p_dbm - 30) / 10)
    scaled = result_1w.scale(p_w)
    c = scaled.evaluate_compliance()
    print(f"{p_dbm} dBm: {'PASS' if c.overall_pass else 'FAIL'} (margin {c.margin_db:+.1f} dB)")
```

## Command-line interface

Quick ICNIRP checks from the terminal without writing Python:

```bash
# Check a measured S_ab value
py -3.12 -m aegis.compliance --freq 28e9 --sab 15.0

# Include transmit power for max compliant power calculation
py -3.12 -m aegis.compliance --freq 28e9 --sab 15.0 --power 1.0

# Print limits only
py -3.12 -m aegis.compliance --freq 28e9 --limits

# JSON output for scripting
py -3.12 -m aegis.compliance --freq 28e9 --sab 15.0 --json

# Occupational limits
py -3.12 -m aegis.compliance --freq 60e9 --sab 80.0 --occupational
```

All quantities are optional. Pass any combination of `--sab`, `--sab-1cm2` (above 30 GHz), `--sar`, `--sinc`, `--sinc-wb`.

## Engine integration

The engine computes all quantities needed for compliance automatically:

```python
from aegis.engine import DosimetryEngine
from aegis.tissue.dielectric import SKIN_28GHZ

engine = DosimetryEngine(SKIN_28GHZ)
result = engine.compute(body, paths, mode="spatial")

# All fields populated automatically
print(f"Peak averaged S_ab: {result.peak_sab_averaged:.2f} W/m²")
print(f"S_inc: {result.sinc.max():.2f} W/m²")
print(f"Compliant: {result.compliant_sab}")
```

Spatial averaging is always-on. The engine precomputes and caches the sparse averaging matrix $\mathbf{G}$ per body mesh. For frequencies above 30 GHz, a second matrix for 1 cm$^2$ averaging is computed.

## Incident power density

$S_{inc}$ is the power density of the incident electromagnetic field at the body location, measured as if the body were absent. It does not depend on surface orientation or tissue properties.

In the AEGIS equation $S_{ab} = S_{inc} \cdot T_0 \cdot [\hat{n} \cdot (-\hat{k})]_+$, the $S_{inc}$ is the factor before tissue and geometry corrections. For the current kernel (far-field, broadcast), $S_{inc}$ equals the total path power and is spatially uniform across the body.

## Viewer

The 3D viewer includes a compliance panel showing all checks with margin bars, frequency, and exposure scenario. Five display modes are available:

| Mode | Quantity | Color scale |
|------|----------|-------------|
| Raw $S_{ab}$ | Per-triangle absorbed power density | Jet colormap |
| Averaged $S_{ab}$ | 4 cm$^2$ spatially averaged | Jet colormap |
| $S_{inc}$ | Incident power density | Jet colormap |
| Compliance ratio ($S_{ab}$) | $\bar{S}_{ab} / S_{ab,limit}$ | Green-yellow-orange-red |
| Compliance ratio ($S_{inc}$) | $\bar{S}_{inc} / S_{inc,limit}$ | Green-yellow-orange-red |

The compliance ratio modes are dimensionless and independent of frequency. Values below 1.0 are compliant. A red sphere marks the peak exposure location on the body.

## Compliance report

The viewer exposes a `/api/compliance/report` endpoint returning the full assessment as JSON. This includes all check values, limits, pass/fail status, margin, and peak location coordinates.

## Limitations

- Spatial averaging uses circular neighborhoods (KD-tree ball query). ICNIRP specifies square 4 cm$^2$ patches. The circular approximation is flagged in reports.
- Temporal averaging (6 minutes) is not modeled. AEGIS computes steady-state exposure, which is conservative for continuous sources.
- Below 6 GHz, different quantities apply (SAR over 10-g cubic mass). The compliance module raises `ValueError` for out-of-range frequencies.
- Multi-frequency compliance (ICNIRP equation 2) is not yet supported.
