---
name: physics-review
description: Review physics changes for dimensional consistency, conservation, and monograph fidelity
user-invocable: true
---

# /physics-review - Physics correctness review

Review changes to physics code before committing. Run this after modifying anything in `kernels/`, `tissue/`, or `coherent/`.

## Usage

```
/physics-review              # review all uncommitted physics changes
/physics-review <file>       # review a specific file
```

## Step 1: Identify what changed

```bash
git diff --name-only src/aegis/kernels/ src/aegis/tissue/ src/aegis/coherent/ 2>/dev/null
git diff --cached --name-only src/aegis/kernels/ src/aegis/tissue/ src/aegis/coherent/ 2>/dev/null
```

If no physics files changed, report "No physics changes to review" and exit.

## Step 2: Read the diff

```bash
git diff src/aegis/kernels/ src/aegis/tissue/ src/aegis/coherent/
git diff --cached src/aegis/kernels/ src/aegis/tissue/ src/aegis/coherent/
```

For each changed file, also read the full file to understand context.

## Step 3: Five-lens review

### Lens 1: Dimensional analysis

For every arithmetic expression in the diff, verify units balance:
- Sab: W/m^2
- power, P_abs: W
- k_hat, n_hat: unitless (unit vectors)
- areas: m^2
- Fresnel coefficients (T0, Ts, Tp, rs, rp): dimensionless
- psi: V/m (complex field amplitude)
- Q: W/m^2 (exposure operator)
- Z0: Ohms (377 Ohms, impedance of free space)

### Lens 2: Conservation laws

- Total absorbed power <= total incident power
- Sab >= 0 everywhere (ReLU or equivalent guarantees this)
- Energy balance: sum(Sab * area) = P_abs
- Q must be Hermitian positive semidefinite
- Eigenvalues of Q must be real and non-negative

### Lens 3: Monograph fidelity

For each modified formula:
1. Identify which equation in the monograph it corresponds to
2. Read that section from `../monograph/summary_paper.tex`
3. Verify the code matches the equation exactly
4. Flag any discrepancies with the specific equation number

### Lens 4: Sign and factor check

Common physics bugs to look for:
- Missing complex conjugate (should be `np.conj()` or `.conj()`)
- Factor-of-2 errors (especially in power vs amplitude conversions)
- Wrong sign in reflection coefficients (TE vs TM convention)
- Missing `1/Z0` or `Z0` factor in power density from field
- ReLU applied to wrong operand
- Dot product vs element-wise multiply confusion

### Lens 5: Regression tests

Run:
```bash
py -3.12 -m pytest tests/test_mie.py -v
py -3.12 -m pytest tests/golden/ -v
py -3.12 -m pytest tests/test_properties.py -v
```

All must pass.

## Report format

```
## Physics review

### Lens 1: Dimensional analysis
- PASS/FAIL: [details, cite file:line for any issues]

### Lens 2: Conservation laws
- PASS/FAIL: [details]

### Lens 3: Monograph fidelity
- PASS/FAIL: [equation numbers checked, any discrepancies]

### Lens 4: Sign and factor check
- PASS/FAIL: [details]

### Lens 5: Regression tests
- PASS/FAIL: [test counts]

### Verdict: PASS / FAIL
[One-line summary]
```

## Rules

- Never weaken an assertion or test tolerance to make the review pass
- If a formula does not match the monograph, the code is wrong until proven otherwise
- When in doubt, read the full monograph section, not just the summary paper
