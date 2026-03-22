# Composability of incoherent corrections

This document derives the general combined formula for the incoherent
dosimetry corrections (polarisation, curvature, diffraction), verifies
they compose, and identifies a factor-of-4 bug in the aggregate level.

All equation references are to `monograph_v2.tex`.


## 1. Starting point: the exact absorption law

The monograph proves one exact result (eq. 5.8, line 1567):

$$S_{\mathrm{ab}}(\mathbf{r}) = S_{\mathrm{inc}} \; T_{\mathrm{eff}}(\mathbf{r}) \; \mathrm{ReLU}\!\bigl(\mu(\mathbf{r})\bigr) \tag{Exact}$$

where $\mu(\mathbf{r}) = \hat{\mathbf{n}}(\mathbf{r}) \cdot (-\hat{\mathbf{k}})$ and

$$T_{\mathrm{eff}}(\mathbf{r}) = |e_s(\mathbf{r})|^2 \, T_s(\theta) + |e_p(\mathbf{r})|^2 \, T_p(\theta) \tag{eq.~5.4}$$

**Assumptions**: surface is locally flat on the scale of $\lambda$, far-field
illumination. The ReLU gate is exact (back-facing triangles absorb nothing).

This is the single formula from which everything else derives.


## 2. Hierarchy of approximations

### 2.1 Approximation chain for the Fresnel factor

The Fresnel factor $T_{\mathrm{eff}}$ can be simplified in two independent steps:

**Step A: unpolarised average** ($q = 0$)

$$T_{\mathrm{eff}} = T_{\mathrm{avg}}(\theta) + \frac{q}{2}\,\Delta T(\theta) \;\xrightarrow{q=0}\; T_{\mathrm{avg}}(\theta)$$

where $T_{\mathrm{avg}} = \frac{1}{2}(T_s + T_p)$ and $\Delta T = T_p - T_s \ge 0$ (eq. 5.11).

This is exact when the illumination is circularly polarised, or when the
ensemble average of $q$ is zero (diffuse multipath).

**Step B: pseudo-Brewster compensation** (Section 5.3)

$$T_{\mathrm{avg}}(\theta) \;\approx\; T_0 \quad \text{(constant, normal-incidence value)}$$

Valid because $T_s$ decreases and $T_p$ increases (pseudo-Brewster peak) with
angle, and their average stays within 5.6% of $T_0$ for skin at 28 GHz.

These two steps give a ladder of Fresnel approximations:

| Fresnel level | Expression | Error (skin, 28 GHz) |
|---|---|---|
| Exact | $T_{\mathrm{eff}}(\theta, q)$ | 0 |
| Unpolarised | $T_{\mathrm{avg}}(\theta)$ | $\le 16\%$ worst case, $< 2.5\%$ multipath |
| Constant | $T_0$ | $\le 5.6\%$ additional |


### 2.2 The three physical corrections

Beyond the Fresnel factor, three corrections address effects beyond the
locally-flat assumption:

**Correction 1: Polarisation** (Part II, eq. 5.11)

Restores the $\frac{q}{2}\Delta T$ term:

$$T_{\mathrm{avg}} \;\to\; T_{\mathrm{eff}} = T_{\mathrm{avg}} + \frac{q}{2}\,\Delta T$$

This modifies the **Fresnel transmission coefficient**. It does not
introduce new terms or change the activation function.

**Correction 2: Curvature** (Section 2.10.1, eq. 2.42)

For a surface with twice mean curvature $H_j = 1/R_{1,j} + 1/R_{2,j}$,
the first-order Physical Optics correction is:

$$S_{\mathrm{ab},j} = T_0 \sum_i S_i \left[\mathrm{ReLU}(\mu_{ji}) + \frac{H_j}{k}\,\mathrm{ReLU}(\mu_{ji})^2\right] \tag{eq.~2.42}$$

This adds a **perturbative correction term** proportional to $H/k$.
The correction is below 0.4% for the arm, $\sim$2% for the finger, and
$\sim$8% for the ear edge at 28 GHz (Table 2.9).

**Correction 3: Diffraction** (Section 2.10.2, eq. 2.44)

Replaces the sharp ReLU with a physically-derived GELU:

$$\mathrm{ReLU}_{\mathrm{phys}}(\mu) \approx \mu\;\frac{1}{2}\!\left[1 + \mathrm{erf}\!\left(\frac{\mu}{\sigma_j}\right)\right], \qquad \sigma_j = \sqrt{\frac{\lambda}{2\pi R_j}} \tag{eq.~2.44}$$

This replaces the **activation function** $g(\mu)$. The smoothing scale
$\sigma$ is set by the local radius of curvature and the wavelength.


## 3. Composability: the three corrections are orthogonal

### 3.1 Structure of the formula

The general incoherent formula has the structure:

$$S_{\mathrm{ab}} = \underbrace{T(\mu, q)}_{\text{Fresnel}} \cdot \underbrace{g(\mu, \sigma)}_{\text{activation}} \cdot \mathbf{s} \;+\; \underbrace{T_0 \cdot \frac{H}{k} \cdot g(\mu, \sigma)^2}_{\text{curvature}} \cdot \mathbf{s}$$

Each correction touches a different structural element:

| Correction | What it modifies | Independent of |
|---|---|---|
| Polarisation | $T$: the Fresnel factor | Activation function, curvature term |
| Curvature | Adds the $g^2$ term | Fresnel factor, activation function |
| Diffraction | $g$: the activation | Fresnel factor, curvature magnitude |

They are structurally orthogonal: no correction modifies the same part
of the formula as another.


### 3.2 The general combined formula

Composing all three corrections:

$$\boxed{S_{\mathrm{ab},j} = \left[T_{\mathrm{avg}}(\mu_j) + \frac{q}{2}\,\Delta T(\mu_j)\right] g(\mu_j, \sigma_j) \cdot \mathbf{s} \;+\; T_0 \cdot \frac{H_j}{k} \cdot g(\mu_j, \sigma_j)^2 \cdot \mathbf{s}}$$

where:
- $g = \mathrm{GELU}(\mu, \sigma)$ with diffraction, or $\mathrm{ReLU}(\mu)$ without
- Polarisation term present when $q \ne 0$
- Curvature term present when $H \ne 0$


### 3.3 Limiting case verification

Every subset of corrections must reduce to a known formula:

| Pol | Curv | Diff | Result | Matches |
|-----|------|------|--------|---------|
| off | off  | off  | $T_{\mathrm{avg}} \cdot \mathrm{ReLU} \cdot \mathbf{s}$ | Level 3 |
| on  | off  | off  | $T_{\mathrm{eff}} \cdot \mathrm{ReLU} \cdot \mathbf{s}$ | Level 4 |
| off | on   | off  | $T_{\mathrm{avg}} \cdot \mathrm{ReLU} + T_0(H/k)\mathrm{ReLU}^2$ | Level 5 |
| off | on   | on   | $T_{\mathrm{avg}} \cdot \mathrm{GELU} + T_0(H/k)\mathrm{GELU}^2$ | Level 6 |
| on  | on   | off  | $T_{\mathrm{eff}} \cdot \mathrm{ReLU} + T_0(H/k)\mathrm{ReLU}^2$ | **New** |
| on  | off  | on   | $T_{\mathrm{eff}} \cdot \mathrm{GELU}$ | **New** |
| on  | on   | on   | $T_{\mathrm{eff}} \cdot \mathrm{GELU} + T_0(H/k)\mathrm{GELU}^2$ | **New** |


### 3.4 Why the curvature term keeps $T_0$

The curvature correction is first-order in $H/k$. If we substituted
$T_{\mathrm{eff}}$ for $T_0$ in the curvature term, the additional contribution
would be:

$$\frac{q}{2}\,\Delta T \cdot \frac{H}{k} \cdot g^2$$

This is a product of two small quantities. At 28 GHz on an arm ($H/k \approx 0.004$)
with maximum polarisation contrast ($q \Delta T / 2 \approx 0.08$):

$$\text{cross-term} \approx 0.08 \times 0.004 = 0.00032 \quad (0.03\%)$$

This is three orders of magnitude below the leading-order curvature
correction itself. Including it would be "correcting a correction" and
is far below the accuracy of the Physical Optics expansion.


### 3.5 Further sanity checks

**Energy conservation**: For any combination of checkboxes, the total
absorbed power $P_{\mathrm{abs}} = \sum_j S_{\mathrm{ab},j} \cdot a_j$
satisfies $P_{\mathrm{abs}} \le S_{\mathrm{inc}} \cdot A_{\mathrm{total}}$
(no triangle absorbs more than the incident flux).

**Differentiability**: All components ($T_{\mathrm{avg}}$, $\Delta T$,
GELU, $H/k$) are smooth functions of their inputs. The combined formula
is differentiable everywhere except at $\mu = 0$ when using ReLU, and
fully differentiable when using GELU.

**Monotonicity at normal incidence**: At $\mu = 1$ (normal incidence),
$T_{\mathrm{avg}}(0) = T_p(0) = T_s(0) = T_0$ and $\Delta T(0) = 0$.
All checkboxes reduce to $T_0$ at normal incidence regardless of polarisation.
The curvature term adds $T_0 \cdot H/k > 0$ (convex surfaces). This is physical:
curved surfaces focus the field slightly at normal incidence.


## 4. Coherent composability

### 4.1 The coherent law

The coherent absorption law (Theorem 4.1, line 4441) is:

$$S_{\mathrm{ab}}(\mathbf{r}) = \|\tilde{\mathbf{G}}(\mathbf{r})\,\mathbf{x}\|^2$$

where the body-surface channel is:

$$\tilde{\mathbf{g}}_j(\mathbf{r}) = \sum_{n:\,j(n)=j} \sqrt{\frac{\sigma}{4\alpha_n}} \; \mathbf{F}_n(\mathbf{r})\,\boldsymbol{\psi}_n\,e^{-ik_0\hat{\mathbf{k}}_n\cdot\mathbf{r}}$$

**Polarisation** is already intrinsic: $\mathbf{F}_n$ applies exact complex
Fresnel amplitudes per TE/TM component. The coherent formulation uses
amplitude coefficients $t_s$, $t_p$ (with phase), not power coefficients
$T_s$, $T_p$. No checkbox needed.

### 4.2 Curvature in the coherent formulation

The curvature correction multiplies each path contribution by
$(1 + \mu_n/(kR))$. This is a **real scalar** per (triangle, path) pair:

$$\tilde{\mathbf{g}}_j^{\,\mathrm{curv}}(\mathbf{r}) = \sum_{n:\,j(n)=j} \sqrt{\frac{\sigma}{4\alpha_n}} \; \mathbf{F}_n\,\boldsymbol{\psi}_n\,e^{-ik_0\hat{\mathbf{k}}_n\cdot\mathbf{r}} \cdot \left(1 + \frac{\mu_n}{kR(\mathbf{r})}\right)$$

The squared-norm structure is preserved. $\mathbf{Q}$ remains Hermitian
positive-semidefinite. ECBF still works.

**Derivation**: The incoherent curvature correction (eq. 2.42) has the form

$$S_{\mathrm{ab}} = T_0 \sum_i S_i\,\mathrm{ReLU}(\mu)\left(1 + \frac{\mu}{kR}\right)$$

Factoring out the $\mathrm{ReLU}(\mu)$ gate, the factor $(1 + \mu/(kR))$
is a correction to the field amplitude (not the power), hence it appears as
$\sqrt{1 + \mu/(kR)} \approx 1 + \mu/(2kR)$ in the field. However, the
monograph derives the correction at the power level, so we should apply
it to $|\tilde{\mathbf{G}}\mathbf{x}|^2$, not to $\tilde{\mathbf{G}}$
directly. Two approaches:

**(a) Multiplicative field correction**: Multiply each path's field contribution
by $\sqrt{1 + H_j/(k\mu_n)}$. Preserves the squared-norm structure but
introduces a square root that may cause numerical issues when $\mu_n$ is
small.

**(b) Additive power correction**: Compute $S_{\mathrm{ab}}^{(0)}$ from
the standard coherent law, then add the curvature correction separately:

$$S_{\mathrm{ab}} = \|\tilde{\mathbf{G}}\mathbf{x}\|^2 + T_0 \frac{H}{k}\,g(\mu)^2 \cdot \mathbf{s}_{\mathrm{coh}}$$

where $\mathbf{s}_{\mathrm{coh}}$ accounts for the coherent power
distribution. This breaks the pure quadratic-in-$\mathbf{x}$ structure.

**(c) Direct scalar weight** (recommended): Since $H/k \ll 1$, apply the
correction as a per-(triangle, path) real weight on the body channel:

$$w_{nj} = 1 + \frac{H_j \cdot \mu_{nj}}{k}$$

This preserves the structure because $w_{nj}$ is a real scalar that multiplies
each term in the sum defining $\tilde{\mathbf{g}}_j$. The coherent law
becomes $S_{\mathrm{ab}} = \|\tilde{\mathbf{G}}^w \mathbf{x}\|^2$ where
$\tilde{\mathbf{G}}^w$ absorbs the weights. $\mathbf{Q}^w$ is still
Hermitian PSD.

**Conclusion**: Curvature composes with the coherent formulation via approach (c).
The error is $O(H^2/k^2)$ from ignoring higher-order terms, which is negligible.

### 4.3 Diffraction in the coherent formulation

In the incoherent case, diffraction replaces $\mathrm{ReLU}(\mu)$ with
$\mathrm{GELU}(\mu, \sigma)$. In the coherent case, the shadow boundary
is enforced by the Heaviside $H(\mu_n)$ in the transmitted field (eq. 4.18,
line 4232):

$$\mathbf{E}_n^{\mathrm{trans}} = (\ldots) \cdot H(\mu_n)$$

A diffraction correction replaces this hard gate with a smooth one:

$$H(\mu_n) \;\to\; w_{\mathrm{diff}}(\mu_n, \sigma) = \frac{1}{2}\left[1 + \mathrm{erf}\!\left(\frac{\mu_n}{\sigma_j}\right)\right]$$

This is again a real scalar per (triangle, path) pair. The squared-norm
structure and Q remain valid.

**Important subtlety**: The incoherent GELU is $\mu \cdot \frac{1}{2}[1 + \mathrm{erf}(\mu/\sigma)]$.
The factor $\mu$ is the cosine projection. In the coherent case, the cosine
projection is already encoded in $\mathbf{F}_n$ through the angle dependence
of $t_s(\mu)$, $t_p(\mu)$. So the coherent diffraction correction is only
the smooth gate $w_{\mathrm{diff}}$, not the full GELU.

**Conclusion**: Diffraction composes with the coherent formulation by
replacing $H(\mu_n)$ with $w_{\mathrm{diff}}(\mu_n, \sigma_j)$.


## 5. Bug: factor-of-4 error in Level 0/1

### 5.1 The monograph's definition of $A_{\mathrm{ab}}$

The monograph defines the absorption directivity (eq. 2.23, line 2196):

$$D(\hat{\mathbf{k}}) = \frac{A_\perp(\hat{\mathbf{k}})}{\langle A_\perp \rangle} = \frac{4\,A_\perp(\hat{\mathbf{k}})}{A_{\mathrm{ab}}}$$

Therefore: $A_{\mathrm{ab}} = 4\langle A_\perp \rangle$.

For a convex body, Cauchy's formula gives $\langle A_\perp \rangle = A_{\mathrm{total}}/4$.

Therefore: $A_{\mathrm{ab}} = 4 \cdot A_{\mathrm{total}}/4 = A_{\mathrm{total}}$.

**$A_{\mathrm{ab}}$ equals the total surface area for convex bodies.**

### 5.2 The Level 1 formula

The monograph gives (eq. 2.24, line 2209):

$$P_{\mathrm{abs}} = S_{\mathrm{inc}} \, T_0 \, \frac{A_{\mathrm{ab}}}{4} \, D(\hat{\mathbf{k}})$$

For multi-source (eq. 2.31, line 2598):

$$P_{\mathrm{abs}} = T_0 \, \frac{A_{\mathrm{ab}}}{4} \sum_i S_i \, D(\hat{\mathbf{k}}_i)$$

### 5.3 The code's error

The viewer sets (`compute.py` line 186-187):

```python
# Comment: "Cauchy formula: A_ab = A_total / 4 for convex bodies"
extra_kwargs["A_ab"] = body.total_area * 0.25
```

This gives $A_{\mathrm{ab}} = A_{\mathrm{total}}/4$. But it should be
$A_{\mathrm{ab}} = A_{\mathrm{total}}$.

The comment confuses $A_{\mathrm{ab}}$ with $\langle A_\perp \rangle$.
The Cauchy formula gives $\langle A_\perp \rangle = A_{\mathrm{total}}/4$,
but the division by 4 is already present in the Level 1 formula ($A_{\mathrm{ab}}/4$).
Applying 0.25 again means the factor of 4 is applied twice.

### 5.4 Consequence

With the bug:

$$P_{\mathrm{abs}}^{L1} = T_0 \cdot \frac{A_{\mathrm{total}}/4}{4} \cdot \sum S_i D_i = T_0 \cdot \frac{A_{\mathrm{total}}}{16} \cdot \sum S_i D_i$$

Without the bug:

$$P_{\mathrm{abs}}^{L1} = T_0 \cdot \frac{A_{\mathrm{total}}}{4} \cdot \sum S_i D_i$$

**Level 1 underestimates $P_{\mathrm{abs}}$ by a factor of 4.**

### 5.5 Verification against Level 2

Level 2 computes:

$$P_{\mathrm{abs}}^{L2} = T_0 \sum_i S_i \sum_j \mathrm{ReLU}(\mu_{ji}) \cdot a_j = T_0 \sum_i S_i \cdot A_\perp(\hat{\mathbf{k}}_i)$$

With correct $A_{\mathrm{ab}} = A_{\mathrm{total}}$, Level 1 gives:

$$P_{\mathrm{abs}}^{L1} = T_0 \cdot \frac{A_{\mathrm{total}}}{4} \cdot \sum_i S_i \cdot \frac{A_\perp(\hat{\mathbf{k}}_i)}{A_{\mathrm{total}}/4} = T_0 \sum_i S_i \cdot A_\perp(\hat{\mathbf{k}}_i) = P_{\mathrm{abs}}^{L2}$$

The two levels agree, as they must by the projected-area identity.

### 5.6 Affected code

1. `src/aegis/viewer/compute.py` line 186-187: `convex_body_area_factor` should be 1.0
2. `src/aegis/viewer/config.py` line 208: default should be 1.0
3. `tests/test_engine.py` line 273: `A_ab = ico_mesh.total_area / 4.0` should be `total_area`
4. The test `test_isotropic_D_matches_level2_total_power` validates the wrong formula.
   It should also compare Level 1's $P_{\mathrm{abs}}$ against Level 2's.

### 5.7 The same bug applies to Level 0

Level 0 uses $P_{\mathrm{abs}} \le T_0 \cdot (A_{\mathrm{ab}} D_{\max}/4) \cdot \sum S_i$.
If $A_{\mathrm{ab}}$ is 4x too small, the bound is 4x too loose (non-conservative).
