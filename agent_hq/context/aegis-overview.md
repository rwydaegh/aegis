# AEGIS

AEGIS computes absorbed power density (Sab) on human body meshes exposed to wireless
base station radiation. Core equation: Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)].
Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming with ECBF
optimization. Python physics stack (NumPy/SciPy, optional JAX). Flask + React/Three.js
3D viewer with Zustand state. Ray tracing via Sionna and DiffeRT.

This is Robin's PhD research tool at Ghent University + IMEC. It is a real product
deployed at https://aegis.waves-ugent.be. The summary paper
(../monograph/summary_paper.tex) is a condensed reference for the physics. The code
should match the math.

## Codebase map

- `src/aegis/engine.py` - main dispatch, 9 fidelity levels
- `src/aegis/kernels/` - one file per level, the actual physics
- `src/aegis/tissue/` - Fresnel, Cole-Cole, tissue database
- `src/aegis/geometry/` - mesh ops, spatial averaging, ambient occlusion
- `src/aegis/coherent/` - field channel, exposure operator Q, ECBF solver
- `src/aegis/compliance/` - ICNIRP 2020 limits
- `src/aegis/viewer/` - Flask backend, routes, config
- `src/aegis/integration/` - DiffeRT and Sionna bridges
- `aegis-web/` - React + Three.js frontend (Vite, R3F, Zustand)
- `data/` - phantom meshes (STL), IT'IS tissue database, channel presets
- `tests/` - ~1600 tests, Hypothesis property tests, golden tests
