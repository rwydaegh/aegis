---
paths: ["src/aegis/kernels/**", "src/aegis/tissue/**", "src/aegis/coherent/**"]
description: Physics and mathematical correctness rules for dosimetry code
---

# Physics rules

## Before modifying any formula

Read the relevant section from `../monograph/summary_paper.tex` (quick reference, 1142 lines). For full derivations and proofs, use `../monograph/monograph_v2.tex`.

## Dimensional consistency

Every arithmetic expression must have balanced units:
- `Sab`: W/m^2 (absorbed power density)
- `power`, `P_abs`: W
- `k_hat`, `n_hat`: unitless (unit direction vectors)
- `areas`: m^2
- Fresnel coefficients (`T0`, `Ts`, `Tp`, `rs`, `rp`): dimensionless ratios
- `psi`: V/m (complex electric field amplitude)
- `Q`: W/m^2 (exposure operator, Hermitian PSD)

## Conservation laws

- Total absorbed power <= total incident power
- Sab >= 0 everywhere (ReLU guarantees this)
- Energy balance: `sum(Sab * triangle_area) = P_abs`
- Q matrix must be Hermitian positive semidefinite

## Regression testing

After any physics change, run:
```bash
py -3.12 -m pytest tests/test_mie.py -v        # Mie canary (most important)
py -3.12 -m pytest tests/golden/ -v             # monograph table values
py -3.12 -m pytest tests/test_properties.py -v  # physics invariants
```

## Absolute rule

Never weaken assertions to make tests pass. Fix the code, not the test.
