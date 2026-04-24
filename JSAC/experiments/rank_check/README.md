# Empirical rank of Q on Thelonious, plaza geometry at 26 GHz

## Status

Running.  See `rank_cdf.{pdf,png}`, `rank_table.md`, and `spectra.npz` for the
current numerical output.  This README is updated once the run completes.

## Scenario

- Phantom: **Thelonious** STL (23826 triangles, ~0.79 m^2 surface area).
- BS: 8×8 UPA, half-wavelength spacing at 26 GHz (d ≈ 5.77 mm), mounted at 8 m
  height, 10° down-tilt, broadside toward +x.
- Tissue: skin at 26 GHz (IT'IS Cole-Cole: ε\_r ≈ 17.7, σ ≈ 24.4 S/m).
- 20 bodies drawn from a 20–80 m range ring with azimuth within ±60°, feet
  placed on the ground (z = 0).
- Two path models are evaluated on every body:
    - **A. Plaza specular** — LOS + ground bounce + 2 facade specular reflections
      (image-method at z=0 and y=±20 m planes).  4 distinct incident directions
      per body.
    - **B. 3GPP 38.901 UMa-LOS stochastic** — 12 clusters × 5 subpaths = 60
      physical subpaths per body, drawn via
      `aegis.channel.generator.generate_channel`.

The reason for running both: model A gives a geometric rank ceiling of 4 by
construction, so it can confirm but not falsify the paper's "3–10 dominant
modes" claim.  Model B delivers ~60 physical arrival directions per body, far
in excess of M\_ant = 64 times any plausible rank-few prediction; its dominant
rank is a genuine array-resolution observation.

## How to reproduce

```bash
python3 JSAC/experiments/rank_check/run_rank_check.py
```

Writes `rank_cdf.pdf`, `rank_cdf.png`, `rank_table.md`, `spectra.npz` next to
the script.  Runtime ~5–15 min on a laptop (NumPy backend, single process).

## Takeaway

_To be filled in once the run completes._
