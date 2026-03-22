# Fidelity level composability analysis

## 1. The exact starting point

The monograph derives one exact absorption law (eq. 5.8, monograph line 1567):

$$S_{\mathrm{ab}}(\mathbf{r}) = S_{\mathrm{inc}} \; T_{\mathrm{eff}}(\mathbf{r}) \; \mathrm{ReLU}\!\bigl(\mu(\mathbf{r})\bigr)$$

where $\mu(\mathbf{r}) = \hat{\mathbf{n}}(\mathbf{r}) \cdot (-\hat{\mathbf{k}})$, and $T_{\mathrm{eff}}$ is the full polarisation-aware Fresnel transmission:

$$T_{\mathrm{eff}}(\mathbf{r}) = |e_s(\mathbf{r})|^2 \, T_s(\theta) + |e_p(\mathbf{r})|^2 \, T_p(\theta)$$

This is exact for any polarisation, any frequency, on any surface that is locally flat on the scale of $\lambda$. The ReLU gate is exact: back-facing points absorb nothing.

Everything else in the framework is an approximation or correction to this formula.

## 2. How the current "levels" relate to the exact law

The current nine levels are not a monotonic hierarchy. They are a mix of **computational shortcuts** (levels 0-2) and **physics corrections** (levels 3-6), plus a **separate coherent track** (levels 7-8). Here is how each derives from the exact law:

### Levels 0-2: computational shortcuts

These simplify the exact law to reduce cost. Each is genuinely less precise than the next:

| Level | Approximation applied | What you lose | Cost |
|---|---|---|---|
| 0 (Bound) | $D(\hat{k}) \to D_{\max}$, uniform $S_{\mathrm{ab}}$ | Spatial and directional resolution | $O(1)$ |
| 1 (Aggregate) | Uniform $S_{\mathrm{ab}}$, but exact directivity | Spatial resolution | $O(N)$ |
| 2 (Geometric) | $T_{\mathrm{eff}}(\theta) \to T_0$ | Angle-dependent Fresnel | $O(MN)$ |

These three form a true hierarchy: $0 \subset 1 \subset 2$. Each gives strictly more information.

### Level 3: angle-dependent Fresnel

Replaces the constant $T_0$ with $T_{\mathrm{avg}}(\theta) = \frac{1}{2}[T_s(\theta) + T_p(\theta)]$:

$$S_{\mathrm{ab}}(\mathbf{r}) = \sum_i S_i \; T_{\mathrm{avg}}(\mu_i) \; \mathrm{ReLU}(\mu_i)$$

This is the exact law with $q = 0$ (unpolarised assumption). It is the natural **baseline for all spatial corrections**, because it captures the dominant angle-dependent physics while avoiding the need for per-path polarisation data.

### Level 4: polarisation correction

Replaces $T_{\mathrm{avg}}$ with $T_{\mathrm{eff}} = T_{\mathrm{avg}} + \frac{q}{2} \Delta T$:

$$S_{\mathrm{ab}}(\mathbf{r}) = \sum_i S_i \left[ T_{\mathrm{avg}}(\mu_i) + \frac{q_i}{2} \Delta T(\mu_i) \right] \mathrm{ReLU}(\mu_i)$$

This modifies the **Fresnel transmission factor**. It does not touch the geometric gate or add any new terms.

### Level 5: curvature correction

Adds a first-order Physical Optics correction from the monograph (eq. 2.42, line 2866):

$$S_{\mathrm{ab},j} = T_0 \sum_i S_i \left[ \mathrm{ReLU}(\mu_{ji}) + \frac{H_j}{k} \, \mathrm{ReLU}(\mu_{ji})^2 \right]$$

where $H_j = 1/R_{1,j} + 1/R_{2,j}$ is twice the mean curvature. This adds a **perturbative correction term** proportional to $H/k$.

**Critical observation**: the monograph derives this starting from $T_0$ (the geometric absorption law), but the code applies it on top of $T_{\mathrm{avg}}(\mu)$ for the base term:

```python
sab_base      = (T_avg * mu_plus) @ power          # Level 3 base
sab_curvature = T0 * ((curvature_H / k) * mu_plus_sq) @ power  # curvature add-on
```

The code is more accurate than the monograph formula: it uses angle-dependent Fresnel for the leading term and $T_0$ only for the perturbative correction. This is correct because the curvature term is already $O(H/k)$; using $T_{\mathrm{avg}}$ vs $T_0$ in it would be a second-order effect.

### Level 6: diffraction smoothing

Replaces the sharp ReLU with a physically-derived GELU (eq. 2.44, line 2894):

$$\mathrm{ReLU}_{\mathrm{phys}}(\mu) \approx \mu \; \frac{1}{2} \left[ 1 + \mathrm{erf}\!\left(\frac{\mu}{\sigma_j}\right) \right], \qquad \sigma_j = \sqrt{\frac{\lambda}{2\pi R_j}}$$

This replaces the **activation function** $g(\mu)$. The sharp shadow boundary (ReLU) becomes a smooth diffraction transition (GELU) with a physically-determined width $\sigma$.

### The problem: levels 4-6 are not additive in the current numbering

The current code implements:

| Level | Formula | What it includes |
|---|---|---|
| 3 | $T_{\mathrm{avg}} \cdot \mathrm{ReLU}$ | Fresnel |
| 4 | $T_{\mathrm{eff}} \cdot \mathrm{ReLU}$ | Fresnel + polarisation |
| 5 | $T_{\mathrm{avg}} \cdot \mathrm{ReLU} + T_0 \cdot (H/k) \cdot \mathrm{ReLU}^2$ | Fresnel + curvature, **no polarisation** |
| 6 | $T_{\mathrm{avg}} \cdot \mathrm{GELU} + T_0 \cdot (H/k) \cdot \mathrm{GELU}^2$ | Fresnel + curvature + diffraction, **no polarisation** |

Level 5 builds on level 3, not level 4. Level 6 builds on level 5. **Polarisation is lost** at levels 5 and 6. Running level 6 does not give you all the physics of levels 0-5.

## 3. Composability analysis

The three corrections operate on **different parts of the absorption formula**:

$$S_{\mathrm{ab}} = \underbrace{T(\mu, q)}_{\text{Fresnel factor}} \cdot \underbrace{g(\mu, \sigma)}_{\text{activation}} \;\cdot\; \mathbf{s} \;+\; \underbrace{T_0 \cdot \frac{H}{k} \cdot g(\mu, \sigma)^2}_{\text{curvature correction}} \;\cdot\; \mathbf{s}$$

where:

- **Polarisation** modifies $T$: $\; T_{\mathrm{avg}} \to T_{\mathrm{eff}} = T_{\mathrm{avg}} + \frac{q}{2} \Delta T$
- **Diffraction** modifies $g$: $\; \mathrm{ReLU}(\mu) \to \mathrm{GELU}(\mu, \sigma)$
- **Curvature** adds the second term: $\; + T_0 \cdot (H/k) \cdot g^2$

### Why they compose: orthogonality of corrections

Each correction modifies a structurally independent part of the formula:

1. **Polarisation** is about the air-tissue interface physics: how much power transmits as a function of TE/TM decomposition. It changes the coefficient in front of the geometric factor. It is independent of surface curvature and shadow boundaries.

2. **Curvature** is about how the incident field amplitude varies near a curved surface. The Physical Optics expansion gives a correction proportional to $H/k$. This is a perturbation to the *field amplitude*, independent of what the transmission coefficient is.

3. **Diffraction** is about the shadow boundary transition. ReLU creates a sharp cutoff at $\mu = 0$; real waves diffract around it. This smoothing is independent of both the Fresnel transmission and the curvature.

### The general combined formula

$$\boxed{S_{\mathrm{ab}}(\mathbf{r}) = \left[ T_{\mathrm{avg}}(\mu) + \frac{q}{2} \Delta T(\mu) \right] \cdot g(\mu, \sigma) \;\mathbf{s} \;+\; T_0 \cdot \frac{H}{k} \cdot g(\mu, \sigma)^2 \;\mathbf{s}}$$

where $g = \mathrm{GELU}(\mu, \sigma)$ with diffraction, or $\mathrm{ReLU}(\mu)$ without. The polarisation term is present when $q \neq 0$.

### Verification: all limiting cases reduce correctly

| Polarisation | Curvature | Diffraction | Reduces to |
|---|---|---|---|
| off | off | off | Level 3: $T_{\mathrm{avg}} \cdot \mathrm{ReLU}$ |
| on | off | off | Level 4: $T_{\mathrm{eff}} \cdot \mathrm{ReLU}$ |
| off | on | off | Level 5: $T_{\mathrm{avg}} \cdot \mathrm{ReLU} + T_0 (H/k) \mathrm{ReLU}^2$ |
| off | on | on | Level 6: $T_{\mathrm{avg}} \cdot \mathrm{GELU} + T_0 (H/k) \mathrm{GELU}^2$ |
| **on** | **on** | off | **New**: $T_{\mathrm{eff}} \cdot \mathrm{ReLU} + T_0 (H/k) \mathrm{ReLU}^2$ |
| **on** | off | **on** | **New**: $T_{\mathrm{eff}} \cdot \mathrm{GELU}$ |
| **on** | **on** | **on** | **New**: $T_{\mathrm{eff}} \cdot \mathrm{GELU} + T_0 (H/k) \mathrm{GELU}^2$ |

All seven spatial configurations are physically valid and reduce to known results when corrections are turned off.

### Why the curvature term keeps $T_0$, not $T_{\mathrm{eff}}$

The curvature correction comes from a first-order expansion:

$$S_{\mathrm{ab}} = S_{\mathrm{ab}}^{(0)} + \frac{H}{k} S_{\mathrm{ab}}^{(1)} + O\!\left(\frac{H}{k}\right)^2$$

If we substituted $T_{\mathrm{eff}}$ into $S_{\mathrm{ab}}^{(1)}$, the additional contribution would be:

$$\frac{q}{2} \Delta T \cdot \frac{H}{k} \cdot g(\mu)^2$$

This is a product of two small quantities: the polarisation splitting $\frac{q}{2}\Delta T$ (a few percent) and the curvature parameter $H/k$ (a few percent). The cross-term is well within the error budget of the first-order expansion. Using $T_0$ in the curvature correction is sufficient regardless of whether polarisation is on.

### Error budget for combined corrections

From the monograph:

| Correction | Magnitude | Source |
|---|---|---|
| Pseudo-Brewster ($T_{\mathrm{avg}} \to T_0$) | $\leq 5.6\%$ (skin, 28 GHz) | monograph Table 5.2 |
| Polarisation ($T_{\mathrm{eff}}$ vs $T_{\mathrm{avg}}$) | $\leq 16\%$ worst case, $< 2.5\%$ multipath | monograph sec. 10.4 |
| Curvature | $< 0.4\%$ arm, $\sim 2\%$ finger, $\sim 8\%$ ear | monograph Table 2.9 |
| Diffraction | $\sim 10\%$ near shadow boundary | monograph sec. 2.10 |
| Combined cross-term (pol $\times$ curv) | $< 0.5\%$ | product of small corrections |

The corrections are small enough that their cross-terms are negligible. This confirms they compose safely.

## 4. Coherent track: what composes and what does not

### What the coherent law already handles

The coherent absorption law (Theorem 4.1, line 4441) is:

$$S_{\mathrm{ab}}(\mathbf{r}) = \left\| \tilde{\mathbf{G}}(\mathbf{r}) \, \mathbf{x} \right\|^2$$

where the body-surface channel is:

$$\tilde{\mathbf{g}}_j(\mathbf{r}) = \sum_{n:\,j(n)=j} \sqrt{\frac{\sigma}{4\alpha_n}} \; \mathbf{F}_n(\mathbf{r}) \, \boldsymbol{\psi}_n \, e^{-ik_0 \hat{\mathbf{k}}_n \cdot \mathbf{r}}$$

The Fresnel operator $\mathbf{F}_n$ applies exact TE/TM amplitude coefficients:

$$\mathbf{F}_n = t_{s,n} \, \hat{e}_s \hat{e}_s^\top + t_{p,n} \, \hat{e}_p \hat{e}_p^\top$$

**Polarisation is intrinsic to the coherent formulation.** Each path's $\boldsymbol{\psi}_n$ carries full polarisation information, and $\mathbf{F}_n$ applies exact (not averaged) Fresnel amplitudes per component. No polarisation checkbox is needed for coherent, it is always on.

The coherent law also reduces correctly in limiting cases:

- **Single wave** (Corollary 4.1, line 4450): recovers the exact polarisation-aware law $S_{\mathrm{ab}} = S_{\mathrm{inc}} T_{\mathrm{eff}} \mathrm{ReLU}(\mu)$
- **Random phases** (Corollary 4.2, line 4481): cross-terms average to zero, recovering the incoherent multi-source formula

### Curvature in the coherent formulation

The Physical Optics curvature correction modifies the field amplitude near a curved surface by a factor $(1 + \mu_n / (kR))$. In the coherent formulation, this would multiply each path contribution:

$$\tilde{\mathbf{g}}_j^{\,\mathrm{curv}}(\mathbf{r}) = \sum_{n:\,j(n)=j} \sqrt{\frac{\sigma}{4\alpha_n}} \; \mathbf{F}_n \, \boldsymbol{\psi}_n \, e^{-ik_0 \hat{\mathbf{k}}_n \cdot \mathbf{r}} \cdot \left(1 + \frac{\mu_n}{k R(\mathbf{r})}\right)$$

Since the curvature factor $(1 + \mu/(kR))$ is a **real scalar** per (triangle, path) pair, it does not break the squared-norm structure. The coherent law still holds:

$$S_{\mathrm{ab}} = \left\| \tilde{\mathbf{G}}^{\mathrm{curv}}(\mathbf{r}) \, \mathbf{x} \right\|^2$$

and the exposure operator is still well-defined:

$$\mathbf{Q}^{\mathrm{curv}} = \int_\Sigma \tilde{\mathbf{G}}^{\mathrm{curv}}(\mathbf{r})^H \, \tilde{\mathbf{G}}^{\mathrm{curv}}(\mathbf{r}) \, \mathrm{d}A$$

**Curvature composes with the coherent formulation.** The modification is a per-path scalar weight. Q remains Hermitian positive-semidefinite. ECBF still works.

**Error budget**: The curvature factor introduces an additional $O(H/k)$ term. Combined with Approximation 1 ($\leq 4\%$) and Approximation 2 ($\leq 0.44\%$), the total error is still $\sim 5\%$ since $H/k$ is small.

### Diffraction in the coherent formulation

In the incoherent case, diffraction replaces $\mathrm{ReLU}(\mu)$ with $\mathrm{GELU}(\mu, \sigma)$. In the coherent case, the shadow boundary is enforced by the Heaviside function $H(\mu_n)$ in the transmitted field (eq. 4.18, line 4232):

$$\mathbf{E}_n^{\mathrm{trans}} = (\ldots) \cdot H(\mu_n)$$

A diffraction correction would replace this hard gate with a smooth one:

$$H(\mu_n) \;\to\; w(\mu_n, \sigma) = \frac{1}{2}\left[1 + \mathrm{erf}\!\left(\frac{\mu_n}{\sigma}\right)\right]$$

where $\sigma = \sqrt{\lambda / (2\pi R)}$ as before. This is again a **real scalar weight** per (triangle, path) pair. The squared-norm structure is preserved, Q remains valid, and ECBF works.

However, there is a subtlety. The GELU in the incoherent case is $\mu \cdot \frac{1}{2}[1 + \mathrm{erf}(\mu/\sigma)]$, not just the error function gate. The factor of $\mu$ is the cosine projection (the geometric factor), which in the coherent case is already encoded in the Fresnel operator $\mathbf{F}_n$ through the incidence angle dependence of $t_s$, $t_p$. So the coherent diffraction correction is only the smooth gate $w(\mu, \sigma)$, not the full GELU.

**Diffraction composes with the coherent formulation**, with the caveat that the smooth gate replaces the Heaviside, not the full activation function.

### Summary: coherent composability

| Correction | Composes with coherent? | How | New physics needed? |
|---|---|---|---|
| Polarisation | Already intrinsic | $\mathbf{F}_n$ uses exact $t_s$, $t_p$ | No |
| Curvature | Yes | Multiply per-path weight by $(1 + \mu/(kR))$ | Minimal: derivation is straightforward |
| Diffraction | Yes | Replace $H(\mu)$ with smooth gate $w(\mu, \sigma)$ | Minimal: smooth Heaviside |
| ECBF | Yes | Q structure preserved under both corrections | No change to solver |

## 5. Proposed architecture: baseline + checkboxes

### The monograph already suggests this

The monograph's own Table 2.11 (line 2926) uses "$+$ Curvature" and "$+$ Diffraction" notation, explicitly treating them as additive corrections, not replacement levels. The framework naturally decomposes into:

**Computation mode** (how much spatial detail):

| Mode | Output | Cost |
|---|---|---|
| Bound | Upper bound on $P_{\mathrm{abs}}$ | $O(1)$ |
| Aggregate | Exact $P_{\mathrm{abs}}$, $\mathrm{SAR}_{\mathrm{wb}}$ | $O(N)$ |
| Spatial | Full $S_{\mathrm{ab}}(\mathbf{r})$ map | $O(MN)$ |

**Physics corrections** (checkboxes, all require Spatial mode):

| Checkbox | Requires | Effect on formula |
|---|---|---|
| Angle-dependent Fresnel | $\tilde{n}$ (tissue) | $T_0 \to T_{\mathrm{avg}}(\mu)$ |
| Polarisation | $q$ per path | $T_{\mathrm{avg}} \to T_{\mathrm{eff}}$ |
| Curvature | $H$ per triangle | Adds $T_0 (H/k) g^2$ term |
| Diffraction | $H$ per triangle | $\mathrm{ReLU} \to \mathrm{GELU}$ |

**Coherent mode** (separate track, but can accept curvature/diffraction):

| Feature | Requires | Description |
|---|---|---|
| Coherent combining | $\boldsymbol{\psi}$, element index, precoder $\mathbf{x}$ | $S_{\mathrm{ab}} = \|\tilde{\mathbf{G}} \mathbf{x}\|^2$ |
| ECBF optimisation | + channel $\mathbf{h}$, $P_{\mathrm{abs,max}}$ | Solves QCQP for optimal $\mathbf{x}^*$ |

### Dependency constraints

Not all checkbox combinations are valid:

- **Diffraction requires curvature data** (the GELU width $\sigma$ depends on local radius $R$). So curvature data must be available, though the curvature *correction term* can be independently on/off.
- **Polarisation requires per-path $q$**. Without it, defaults to $q = 0$ (unpolarised).
- **Coherent mode is exclusive with incoherent checkboxes**: the coherent formulation has its own physics (amplitude Fresnel, depth coupling). Curvature and diffraction can be added as multiplicative weights on the body channel, but angle-dependent Fresnel and polarisation are already intrinsic.

### Mapping old levels to new checkboxes

| Old level | New equivalent |
|---|---|
| 0 | Mode: Bound |
| 1 | Mode: Aggregate |
| 2 | Mode: Spatial (Fresnel off) |
| 3 | Mode: Spatial + Fresnel |
| 4 | Mode: Spatial + Fresnel + Polarisation |
| 5 | Mode: Spatial + Fresnel + Curvature |
| 6 | Mode: Spatial + Fresnel + Curvature + Diffraction |
| 4+5 (new) | Mode: Spatial + Fresnel + Polarisation + Curvature |
| 4+6 (new) | Mode: Spatial + Fresnel + Polarisation + Diffraction |
| 4+5+6 (new) | Mode: Spatial + Fresnel + Polarisation + Curvature + Diffraction |
| 7 | Mode: Coherent (optionally + Curvature, + Diffraction) |
| 8 | Mode: Coherent + ECBF (optionally + Curvature, + Diffraction) |

The checkbox approach gives 7 valid spatial configurations instead of the current 4, and allows coherent mode with curvature/diffraction, which is currently impossible.

## 6. Conclusion

The fidelity levels as currently numbered suggest a monotonic hierarchy that does not exist. Levels 4-6 are **independent corrections** to a shared baseline (level 3). The monograph itself presents them as additive ("+Curvature", "+Diffraction"), and the physics confirms they compose: each correction modifies a structurally independent part of the absorption formula.

The coherent formulation is a separate track that already handles polarisation intrinsically. Curvature and diffraction can be added to it as per-path scalar weights without breaking the squared-norm structure or the ECBF solver.

A checkbox architecture would:

1. **Fix the broken hierarchy** (level 5 no longer drops polarisation)
2. **Enable new physics combinations** (polarisation + curvature, polarisation + diffraction)
3. **Unify incoherent and coherent** under a shared set of physics corrections
4. **Match the monograph's own presentation** more faithfully
