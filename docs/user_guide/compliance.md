# Compliance assessment

For a step-by-step walkthrough, see the [compliance tutorial](../tutorials/compliance.md).

AEGIS evaluates exposure against ICNIRP 2020 basic restrictions and reference levels for frequencies above 6 GHz to 300 GHz. The source document is `theory/ICNIRPrfgdl2020.pdf`.

## Two types of compliance check

ICNIRP defines two categories of exposure limits, and AEGIS checks both:

- **Basic restrictions** limit the absorbed power density $S_{\mathrm{ab}}$ on the body surface, averaged over 4 cm$^2$ and 6 minutes. This is the quantity AEGIS computes directly.
- **Reference levels** limit the incident power density $S_{\mathrm{inc}}$ in free space at the body location. These are derived from basic restrictions under worst-case assumptions and are more conservative.

Compliance with either set is sufficient. In practice, if the reference level check passes, the basic restriction check will too (but not the reverse).

## Limits

All values from ICNIRP 2020 Tables 2, 5, and 6.

| Check | General public | Occupational | Source |
|-------|---------------|-------------|--------|
| $S_{\mathrm{ab}}$ over 4 cm$^2$ | 20 W/m$^2$ | 100 W/m$^2$ | Table 2 |
| $S_{\mathrm{ab}}$ over 1 cm$^2$ (>30 GHz) | 40 W/m$^2$ | 200 W/m$^2$ | Table 2, note 5 |
| Whole-body SAR | 0.08 W/kg | 0.4 W/kg | Table 2 |
| $S_{\mathrm{inc}}$ local (4 cm$^2$) | $55/f_G^{0.177}$ W/m$^2$ | $275/f_G^{0.177}$ W/m$^2$ | Table 6 |
| $S_{\mathrm{inc}}$ whole-body | 10 W/m$^2$ | 50 W/m$^2$ | Table 5 |

The 1 cm$^2$ constraint is 2$\times$ the 4 cm$^2$ basic restriction, applied only above 30 GHz to account for focused beams at higher frequencies. The local $S_{\mathrm{inc}}$ limit depends on frequency: at 28 GHz it is approximately 31 W/m$^2$ for general public.

## Using the compliance module

The `aegis.compliance` module provides `icnirp_limits`, `evaluate_compliance`, `max_compliant_power`, and `summary_text`. The [compliance tutorial](../tutorials/compliance.md) walks through each function with full code examples, including limit lookups, evaluating results, computing maximum compliant power, and running power sweeps.

### Key concepts

`evaluate_compliance()` can be called standalone with measured quantities or directly on a `DosimetryResult`. It populates all available checks from the result fields automatically. Pass `ExposureScenario.OCCUPATIONAL` for occupational limits.

`max_compliant_power` finds the largest transmit power that keeps all checks passing. Because $S_{\mathrm{ab}}$ scales linearly with transmit power for all fidelity levels, the calculation is exact: $P_{\mathrm{max}} = P_{\mathrm{ref}} \cdot \min_i(\text{limit}_i / \text{value}_i)$.

Combined with `DosimetryResult.scale()`, this enables parameter sweeps without rerunning the engine. See the tutorial for working examples of power sweeps and compliance heatmaps.

## Command-line interface

Quick ICNIRP checks from the terminal without writing Python:

```bash
# Check a measured S_ab value
python -m aegis.compliance --freq 28e9 --sab 15.0

# Include transmit power for max compliant power calculation
python -m aegis.compliance --freq 28e9 --sab 15.0 --power 1.0

# Print limits only
python -m aegis.compliance --freq 28e9 --limits

# JSON output for scripting
python -m aegis.compliance --freq 28e9 --sab 15.0 --json

# Occupational limits
python -m aegis.compliance --freq 60e9 --sab 80.0 --occupational
```

All quantities are optional. Pass any combination of `--sab`, `--sab-1cm2` (above 30 GHz), `--sar`, `--sinc`, `--sinc-wb`.

## Engine integration

The engine computes all quantities needed for compliance automatically:

```python
from aegis import DosimetryEngine
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

$S_{\mathrm{inc}}$ is the power density of the incident electromagnetic field at the body location, measured as if the body were absent. It does not depend on surface orientation or tissue properties.

In the AEGIS equation $S_{\mathrm{ab}} = S_{\mathrm{inc}} \cdot T_0 \cdot [\hat{n} \cdot (-\hat{k})]_+$, the $S_{\mathrm{inc}}$ is the factor before tissue and geometry corrections. For the current kernel (far-field, broadcast), $S_{\mathrm{inc}}$ equals the total path power and is spatially uniform across the body.

## Viewer

The 3D viewer includes a compliance panel showing all checks with margin bars, frequency, and exposure scenario. Five display modes are available:

| Mode | Quantity | Color scale |
|------|----------|-------------|
| Raw $S_{\mathrm{ab}}$ | Per-triangle absorbed power density | Jet colormap |
| Averaged $S_{\mathrm{ab}}$ | 4 cm$^2$ spatially averaged | Jet colormap |
| $S_{\mathrm{inc}}$ | Incident power density | Jet colormap |
| Compliance ratio ($S_{\mathrm{ab}}$) | $\bar{S}_{\mathrm{ab}} / S_{\mathrm{ab},\mathrm{limit}}$ | Green-yellow-orange-red |
| Compliance ratio ($S_{\mathrm{inc}}$) | $\bar{S}_{\mathrm{inc}} / S_{\mathrm{inc},\mathrm{limit}}$ | Green-yellow-orange-red |

The compliance ratio modes are dimensionless and independent of frequency. Values below 1.0 are compliant. A red sphere marks the peak exposure location on the body.

## Compliance report

The viewer exposes a `/api/compliance/report` endpoint returning the full assessment as JSON. This includes all check values, limits, pass/fail status, margin, and peak location coordinates.

## Limitations

- Spatial averaging uses circular neighborhoods (KD-tree ball query). ICNIRP specifies square 4 cm$^2$ patches. The circular approximation is flagged in reports.
- Temporal averaging (6 minutes) is not modeled. AEGIS computes steady-state exposure, which is conservative for continuous sources.
- Below 6 GHz, only whole-body SAR is checked. Local SAR over a 10 g cubic mass is not yet implemented.
- Multi-frequency compliance (ICNIRP equation 2) is not yet supported.
