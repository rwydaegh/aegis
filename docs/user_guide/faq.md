# Frequently asked questions

## Which fidelity level should I use?

Levels 0 to 8 trade cost and conservatism against physical detail. For many compliance-style checks on incoherent exposure, **level 2** (geometric ReLU plus $T_0$) or **level 3** (full Fresnel angle dependence) is the practical default. Levels 0 and 1 are aggregate or bound-style models and need extra geometry inputs (`A_ab`, directivity data). Levels 4 to 6 add polarisation, curvature, and diffraction terms. Levels 7 and 8 are **coherent MIMO** and require complex path amplitudes plus precoder or channel data, not just scalar powers.

See [Fidelity levels](fidelity_levels.md) for the full list and [Level overview](overview.md) for how they fit the pipeline.

## How do I add a custom tissue type?

Build a `TissueModel` in one of two ways:

1. **Explicit constants** at your frequency: `TissueModel.from_params(name, eps_r, sigma, freq_hz)` or construct `TissueModel(name, eps_r, sigma, freq_hz)` directly.
2. **IT'IS database**: `TissueModel.from_database("Skin", freq_hz)` (or another tissue name from the database) if you have `itis_v5.db` available.

There is no separate plugin registry. Your code holds the `TissueModel` instance and passes it to `DosimetryEngine(tissue)`.

## What coordinate system does the viewer use?

**Python and NumPy geometry in AEGIS use Z-up** (e.g. STL vertices, `BodyMesh`, ray directions in API examples).

The **browser viewer uses Three.js**, which by convention is **Y-up** in the 3D view. Internal transforms bridge the two; when you compare numeric vectors from Python to what you see on screen, expect axes to be permuted in the visualiser.

## How do I export dosimetry results?

`DosimetryResult` serialises without NumPy types:

- `result.to_dict()` returns plain Python types (`list` for arrays, skips `None` fields).
- `result.to_json(indent=2)` writes a JSON string via `to_dict()`.

For raw arrays you can still use `numpy.save`, `numpy.savetxt`, or your own dataframe pipeline from `result.sab` and `body.centroids` / triangle indices.
