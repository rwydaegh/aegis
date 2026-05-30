# Monograph item inventory & paper-allocation strategy

Status: drafted 2026-05-09. Intended as a working document for deciding what stays/moves/gets added across TAP (submitted to co-authors), Paper C (TWC draft), and JSAC (draft).

## Strategic preface

Three things the inventory makes clear:

1. **TAP is roughly the right shape.** ~60 monograph items are already in main+SI; the gaps (no MIMO/coherent, no measurement, no near-field exposure operator) are positioned as future work. There is no content I think TAP must absolutely have that it lacks. Light additions only, and only where the cost of leaving them out is non-trivial.
2. **Paper C is theory-heavy and result-light.** All four crown jewels of coherent dosimetry are in it (Theorems 1–4), but its evidence base is one Pareto figure + one hot-spot map + one rank curve on a single geometry. That's the natural place for a reviewer (or Wout) to push back. The fix is more **validation, sensitivity, and physical-insight content** — *not* more theorems.
3. **JSAC is honest but thin on the time-axis depth.** The chronic-dose pivot is the right strategic move, but the supporting evidence (single seed, 20 s window standing in for 5 min, Shannon proxy, Cauchy bound failing 49–70% of the time) needs hardening before this can be the paper's main result.

The ambitious play: **Paper C absorbs the coherent hotspot physics and FDTD validation; JSAC absorbs the conditional-Cauchy theory + the dictionary tensor structure + Sionna PHY.** The common 3–4 pages on the operator definition are shared and that's fine.

## Strategic recommendations at a glance

- **TAP**: leave alone unless co-authors ask for changes. One optional addition I'd consider: a brief cross-link forward to coherent (single sentence on what Q reduces to in the incoherent limit, since C will cite back).
- **Paper C** (TWC, theory-heavy): add three things — (i) **coherent hotspot physics** as a full section, (ii) **direct FDTD validation** at a tractable subscale, (iii) a **Castellanos β head-to-head** to justify analytical Q. Add one figure of **Q-eigenmodes visualised on the body** (the conceptual bridge to TAP's directivity D(k̂)).
- **JSAC** (DTN SI): the spine is good. Run **one binding-regime experiment** (recommendation: federated multi-operator cap) to fix the hero-figure null. Add a **§VIII ISAC paragraph** drawing on q_complement's pseudo-Brewster eigenvector locking. Add a **§VI tracking-under-motion paragraph** to land the SI's closed-loop/stability beat. Cut Appendices A and B (Fresnel + Cauchy proofs already in TAP) to free page budget. Full reshape in §"JSAC spine reshape" below.
- **Orphaned items** (no good home yet): coherent hotspot physics, reflection operator Q_ref, thermal-emission reciprocity dual. Leading candidate is C; Q_ref might be a separate short paper or a TWC follow-up.

## Inventory and rankings

Score is interest×publishability×fit-with-story, on a 1–10 scale. ✓ = currently included, ∼ = partially / mentioned, − = absent, **+** = my recommendation to add.

| #  | Item                                                                 | Monograph         | /10 | TAP | C   | JSAC | Verdict |
|----|----------------------------------------------------------------------|-------------------|-----|-----|-----|------|---------|
| **Foundational physics** ||||||||
| 1  | Exact absorption law $S_{ab}=S_{inc}T_{eff}\mathrm{ReLU}[n\cdot(-k)]$ | §1.1, l. 371      | 10  | ✓   | ✓   | ✓    | The master equation. Anchors all three. |
| 2  | Geometric absorption law (with $T_0$)                                | §1.1, l. 397      | 10  | ✓   | ∼   | ∼    | TAP's centerpiece. Used implicitly elsewhere. |
| 3  | Polarisation cancellation (3 conditions)                             | TAP S1            | 9   | ✓   | −   | −    | Stays in TAP. C/JSAC don't need it (coherent + linear). |
| 4  | TE/TM Fresnel amplitudes                                             | §1438–1507        | 5   | ✓   | ✓   | ∼    | Workhorse. Cite, don't re-derive. |
| 5  | Normal-incidence transmission $T_0=4n/[(1+n)^2+\kappa^2]$            | §1523             | 7   | ✓   | ∼   | ∼    | TAP defines; C/JSAC use as scalar reference. |
| 6  | Polarisation directivity $D_B$ + cylinder bound 27.9%                | §3469, S1         | 7   | ✓   | −   | −    | TAP-only is correct. |
| **Pseudo-Brewster compensation** ||||||||
| 7  | Pseudo-Brewster angle $\theta_{pB}\approx\arctan|\tilde n|$          | Prop 1.1, l. 1698 | 8   | ✓   | −   | −    | TAP. |
| 8  | TE/TM compensation mechanism                                         | §1689–1723        | 9   | ✓   | −   | −    | TAP. |
| 9  | Sphere ratio $R(f)=T_0/\bar T$ crossover at 40.4 GHz                 | §1840, Tab. 3     | 9   | ✓   | −   | −    | TAP signature result. |
| 10 | Tissue universality of compensation                                  | Tab. 1816, S2     | 7   | ✓   | −   | −    | TAP-only is correct. |
| **Integral geometry** ||||||||
| 11 | Cauchy convex formula $\langle A_\perp\rangle = A/4$                 | Thm 1, l. 2032    | 6   | ✓   | −   | ∼    | TAP. JSAC uses naive form (and shows it fails). |
| 12 | Generalised Cauchy with absorption area $A_{ab}$                     | Thm 2, l. 2069    | 10  | ✓   | −   | ∼    | TAP signature theorem. JSAC currently uses; **+ needs conditional form**. |
| 13 | Exposure fraction $\eta(r)$ ↔ ambient occlusion                      | §1950             | 8   | ✓   | −   | −    | TAP. Connects to graphics primitive. |
| 14 | Convex-hull bound $\langle P_{abs}\rangle\le S_{inc}A_{CH}/4$        | l. 2150           | 6   | ✓   | −   | −    | TAP. Could be cited in JSAC as a sanity check. |
| 15 | Inter-body self-compensation (radiosity, ~1–4%)                      | l. 2165           | 5   | ✓   | −   | −    | TAP. Niche. |
| 16 | Absorption directivity $D(\hat k)$, four-factor decomposition        | Prop, l. 2213     | 9   | ✓   | −   | −    | TAP signature. **+ Mention in C as the incoherent limit of Q-eigenmodes.** |
| 17 | $D(\hat k)$ values for Thelonious (1.22 max, 0.45 min)               | §2239             | 7   | ✓   | −   | −    | TAP. |
| 18 | $D(\hat k)$ posture sensitivity (6.5% over backflip)                 | §2316             | 6   | ✓   | −   | ∼    | TAP. **+ Could go in JSAC as a chronic-dose argument** (D variability bounds tier-C uncertainty). |
| 19 | Spherical-harmonic compression of $D(\hat k)$ ($L=4$, <1%)           | §2281             | 7   | ✓   | −   | −    | TAP. Beautiful. **+ Hint at coherent analog in C discussion.** |
| 20 | Angular power spectrum coupling factor $F$                           | l. 2350           | 6   | ✓   | −   | ∼    | TAP. JSAC implicitly uses (F≈1 for downtilt-broadside). |
| **Compliance & anthropometry** ||||||||
| 21 | Whole-body SAR closed-form: $S_{inc}<0.16m/(\bar T A)$               | §2378             | 9   | ✓   | −   | ∼    | TAP signature. **+ Cite in JSAC §VI for regulatory framing.** |
| 22 | Du Bois scaling, infant→adult 2× threshold spread                    | §2469, S5         | 8   | ✓   | −   | ∼    | TAP. **+ Add to JSAC for tier-C population variation.** |
| 23 | Cube psSAR$_{10g}$ APD bound ($\le 0.66$ W/kg at 10 W/m²)            | TAP S3            | 8   | ✓   | −   | −    | TAP. |
| 24 | Peak APD bound: $\max S_{ab}=S_{inc}T_0$ (exact)                     | Prop, l. 3681     | 7   | ✓   | −   | −    | TAP. Crisp peak-SAR theorem. |
| **Sub-6 GHz / layered tissue** ||||||||
| 25 | Flux-weighted $\bar T(f)$ closed form                                | §3735             | 8   | ✓   | −   | −    | TAP. |
| 26 | Cauchy with $\bar T$ (any frequency, exact for total power)          | §3757             | 9   | ✓   | −   | −    | TAP. |
| 27 | Layered Fabry-Pérot fat resonance + 3 GHz dip                        | §3837, S3         | 9   | ✓   | −   | −    | TAP signature. Major contribution. |
| 28 | Standing-wave SAR depth profile                                      | TAP S3            | 7   | ✓   | −   | −    | TAP. |
| 29 | Validity traffic-light table (frequency × quantity)                  | §3862             | 7   | ✓   | −   | −    | TAP. Excellent figure. |
| **Computational structure** ||||||||
| 30 | ReLU neural-network encoding                                         | §2523             | 8   | ✓   | −   | −    | TAP. Differentiability is the hook. |
| 31 | Three-level computation hierarchy (1, N, MN cost)                    | §2608             | 7   | ✓   | −   | ∼    | TAP. JSAC implicitly relies on level-3. |
| 32 | GELU diffraction smoothing                                           | §2889             | 6   | ✓   | −   | −    | TAP. Connects ReLU to physics. |
| 33 | Curvature correction (PO, $1+\mu/(kR)$)                              | §2854             | 6   | ✓   | −   | −    | TAP. |
| 34 | Diffuse-environment limit $S_{ab}=(S_{tot}T_0/4)\eta$                | §2675             | 7   | ✓   | −   | −    | TAP. Reverberation chamber. |
| **Validation** ||||||||
| 35 | Mie residual decomposition (Fresnel + diffraction terms)             | §3014, S4         | 9   | ✓   | −   | −    | TAP signature. |
| 36 | FDTD comparison on Thelonious (Sim4Life 0.45–5.8 GHz)                | §5 of TAP         | 9   | ✓   | −   | −    | TAP. |
| 37 | Dosimetry literature waterfall (168 volunteers + 5 phantoms)         | §5 of TAP         | 10  | ✓   | −   | −    | TAP signature. The headline result. |
| 38 | Error budget summary                                                 | §3178             | 7   | ✓   | −   | −    | TAP. |
| **Applications mentioned in monograph** ||||||||
| 39 | Differentiable RT integration (Sionna)                               | §3234             | 8   | ∼   | −   | ∼    | Mentioned in TAP discussion. JSAC depends on it operationally. |
| 40 | Real-time GPU dosimetry (microseconds)                               | §3285             | 7   | ∼   | −   | ∼    | Same. |
| **Coherent MIMO theory (Part III)** ||||||||
| 41 | Field channel matrix $\mathbf{G}(r)$                                  | l. 4025           | 7   | −   | ✓   | ✓    | C/JSAC core. |
| 42 | UE channel vector $\mathbf{h}=\mathbf{J}^T\mathbf{b}$                 | l. 4035           | 6   | −   | ✓   | ✓    | C/JSAC core. |
| 43 | Fresnel transmission operator $\mathbf{F}_n$                          | l. 4256           | 7   | −   | ✓   | ✓    | C/JSAC core. |
| 44 | Exposure channel matrix $\tilde{\mathbf{G}}(r)$                       | l. 4406           | 8   | −   | ✓   | ✓    | C/JSAC core. |
| 45 | **Coherent absorption law** $S_{ab}=\|\tilde G x\|^2$                 | Thm 1, l. 4441    | 10  | −   | ✓   | ✓    | The crown jewel of C. |
| 46 | Approximation 1 (TM direction, $\le 4\%$)                             | Prop 1, l. 4201   | 9   | −   | ✓   | ✓    | C central. JSAC cites. |
| 47 | Approximation 2 (universal depth coupling, $\le 0.5\%$)              | Prop 2, l. 4344   | 9   | −   | ✓   | ✓    | C central. JSAC cites. |
| 48 | **Exposure operator** $\mathbf{Q}=\int\tilde G^H\tilde G\,dA$         | Def, l. 4515      | 10  | −   | ✓   | ✓    | C+JSAC core object. |
| 49 | $\mathbf{Q}$ properties (Hermitian PSD, rank, eigenmodes)             | §4524             | 8   | −   | ✓   | ∼    | C deeper than JSAC. |
| 50 | Exposure-signal alignment $\rho$                                      | l. 4572           | 8   | −   | ✓   | −    | C only. **+ Could go in JSAC for tier interpretation.** |
| 51 | Absorbed power under MRT $P_{abs}^{MRT}=P\rho\lambda_{max}(\mathbf{Q})$ | l. 4590         | 7   | −   | ✓   | −    | C. |
| **Coherent hotspot physics (orphaned!)** ||||||||
| 52 | Coherent hotspot definition (co-phase + co-pol)                      | §4650             | 9   | −   | −   | −    | **+ Add to C as a major new section.** |
| 53 | Coherent vs incoherent scaling $N^2$ vs $N$                          | Tab, l. 4686      | 9   | −   | −   | −    | **+ C.** |
| 54 | Hotspot size via Fourier uncertainty $\delta_{coh}\sim\lambda/(2\pi\sigma_\Omega)$ | §4709 | 9   | −   | −   | −    | **+ C.** Genuinely beautiful. |
| 55 | Fresnel filtering effects on hotspot (grazing supp + pol mix + visibility) | §4745       | 8   | −   | −   | −    | **+ C.** |
| **ECBF & multi-user** ||||||||
| 56 | QCQP single-user (S-procedure)                                       | l. 4798           | 8   | −   | ✓   | ∼    | C. JSAC generalises to multi-user. |
| 57 | **Optimal precoder closed form** $(λQ+νI)^{-1}h^*$                    | Thm 3, l. 4816    | 10  | −   | ✓   | ∼    | C signature. JSAC's Eq. 14 generalises. |
| 58 | Limiting regimes (MRT vs absorption-null steering)                   | §4839             | 7   | −   | ✓   | −    | C. |
| 59 | Path-space factorisation $\mathbf{Q}=\mathbf{J}^T\mathbf{M}\mathbf{J}$ | Thm 2 of C       | 10  | −   | ✓   | ✓    | The other crown jewel of C. JSAC uses operationally. |
| 60 | Worst-case eigenvalue lift (Corollary 1 of C)                        | C §3              | 7   | −   | ✓   | −    | C only. |
| 61 | Push-through identity (Theorem 4 of C)                               | C §4              | 8   | −   | ✓   | −    | C only. Useful when $N<M$. |
| 62 | Multi-user incoherent stream superposition                           | l. 4891           | 8   | −   | ∼   | ✓    | JSAC core. |
| 63 | Per-body $\mathbf{Q}^{(u)}=\mathbf{J}^T\mathbf{M}^{(u)}\mathbf{J}$    | l. 4910           | 9   | −   | ∼   | ✓    | JSAC core. |
| 64 | **Multi-user QCQP closed form** (Eq. 14 of JSAC)                     | JSAC §III         | 10  | −   | ∼   | ✓    | JSAC signature. |
| 65 | **Rank-one ZF degenerate limit** (Prop 1 of JSAC)                    | JSAC §III.2       | 9   | −   | −   | ✓    | JSAC signature. Beautiful. |
| 66 | Soft-budget vs hard-null DoF cost                                    | JSAC §III.3       | 7   | −   | −   | ✓    | JSAC. |
| 67 | Channel dynamics & exposure tracking remarks                         | l. 4959           | 6   | −   | −   | ∼    | JSAC operationalises (cadence table). |
| **JSAC architecture** ||||||||
| 68 | Body twin (per-body $\mathbf{M}^{(u)}$ + pose state)                  | JSAC §IV          | 9   | −   | −   | ✓    | JSAC signature. |
| 69 | Scene path dictionary (offline ray-trace, runtime O(1))              | JSAC §IV          | 9   | −   | −   | ✓    | JSAC signature. |
| 70 | Tiered telemetry (A served / B coop / C ISAC / D occupancy)          | JSAC §IV, Tab.1   | 8   | −   | −   | ✓    | JSAC. Strong story element. |
| 71 | Translation phasor identity (sub-grid motion)                        | JSAC Eq. 16       | 7   | −   | −   | ✓    | JSAC. |
| 72 | CSI calibration via ridge LS                                         | JSAC Eq. 18       | 7   | −   | −   | ✓    | JSAC. |
| 73 | Cadence table (UE 1ms, solver 31ms, pose 100ms, dict offline)        | JSAC Tab.2        | 7   | −   | −   | ✓    | JSAC. |
| **JSAC empirical findings** ||||||||
| 74 | Brussels cap slack by ~10⁴ at plaza scale                            | JSAC §V, Fig.2    | 9   | −   | −   | ✓    | JSAC central pivot. |
| 75 | Effective rank 3–4 at 99% trace (Q low-rank generically)             | JSAC §V, Fig.1    | 8   | −   | −   | ✓    | JSAC. **+ Could be in C too as motivation for low-rank extension.** |
| 76 | Binding distance $r^*\approx 3$–13 m (table 3)                       | JSAC §V, Tab.3    | 7   | −   | −   | ✓    | JSAC. **+ Sweep this** (see §"Tingles" below). |
| 77 | Chronic-dose ECDF tier ratio 1.5× (A:B), 0.4× (B:A)                  | JSAC §V, Fig.3    | 9   | −   | −   | ∼    | JSAC headline. **Needs hardening (multi-seed, longer window).** |
| 78 | Cauchy bound breach 49–70%, +2.86 to +6.34 dB                        | JSAC §V, Fig.8    | 8   | −   | −   | ∼    | JSAC. **+ Convert to a contribution by deriving conditional Cauchy form.** |
| 79 | Pose-aware vs Cauchy: 4.7× compliance gain (binding regime)          | JSAC §V, Fig.5    | 7   | −   | −   | ✓    | JSAC. |
| 80 | M=256 panel scaling, ZF violations climb to 18.7%                    | JSAC §V, Fig.4    | 7   | −   | −   | ✓    | JSAC. |
| 81 | Bound demoted from universal to conditional                          | JSAC App.C        | 6   | −   | −   | ∼    | JSAC honest framing. **+ Tighten direction set in main text.** |
| **Coherent extensions (perturbative)** ||||||||
| 82 | Broadband (per-frequency factorisation)                              | C §3.2.1          | 6   | −   | ✓   | −    | C. **+ Demo numerically (currently stated only).** |
| 83 | Near-field kernel $\Phi^{NF}$                                        | C §3.2.2          | 7   | −   | ✓   | −    | C. **+ Validate against FDTD on a contact-distance case.** |
| 84 | Stochastic channel ensemble                                          | C §3.2.3          | 6   | −   | ✓   | −    | C. |
| 85 | Low-rank truncation bound $\lambda_{r+1}P$                           | C §3.2.4          | 7   | −   | ✓   | ∼    | C. JSAC empirically observes rank-3. |
| **Reciprocity / dual / orphaned** ||||||||
| 86 | Reflection operator $\mathbf{Q}_{ref}$                                | C discussion      | 8   | −   | ∼   | −    | Orphaned. Maybe a separate note or new C subsection. |
| 87 | Thermal-emission Kirchhoff dual                                      | C discussion      | 8   | −   | ∼   | −    | Orphaned. **+ I'd put a half-page sketch in C if possible.** |
| **Reference / appendix** ||||||||
| 88 | Complex refractive index conversion (parametric tables)              | App, l. 5035      | 4   | ∼   | ∼   | ∼    | Cite IT'IS / TAP. |
| 89 | Fresnel from Maxwell BC derivation                                   | l. 5083           | 3   | ∼   | −   | −    | Textbook. Cite. |
| 90 | Fidelity-level hierarchy (implicit 0–8)                              | §2514–2761        | 7   | ∼   | −   | −    | Useful framing device. **+ Could be a TAP §1 figure.** |

## Per-paper recommendations

### TAP (submitted, hands mostly off)

Touch lightly only. The honest critique is:

1. **One-sentence forward-link to coherent.** In §8.3 ("future directions") TAP already says "coherent beamforming via SAR matrix formulation" is upcoming. I'd add a single sentence: *"The geometric law (Eq. 8) is the incoherent limit of an exposure operator $\mathbf{Q}$ whose dominant eigenmode plays the role of the worst-case absorption directivity $D(\hat k)$; that connection is developed in [Paper C]."* This costs nothing and earns a clean cross-citation.
2. **Optional: add the fidelity-level table (item 90).** The monograph has an implicit 0–8 hierarchy that isn't explicit in TAP. A small table tying levels 0–3 to the paper's results and naming levels 4+ as "future" would help reviewers situate the contribution. Skip if co-authors push back.
3. **What I would NOT add.** Coherent material (would change the paper's identity); direct measurement (a different study); near-field (genuinely future work). The paper is internally complete.

### Paper C (TWC, theory paper that needs more weight on the results side)

Three substantial additions, in priority order. Each is a section, not a paragraph.

**(a) Coherent hotspot physics — new full section, currently orphaned in monograph §4650–4783.**

This is the single biggest content hole. The exposure operator $\mathbf{Q}$ tells you *how much* is absorbed and what precoder concentrates it; the hotspot physics tells you *where it concentrates and how big it is*. Without it, a reviewer can fairly ask "I now have $\mathbf{Q}$, but I still don't have physical intuition." The section should contain:

- Coherent vs incoherent scaling: $N^2$ vs $N$ for $N$ co-phased, co-polarised paths (item 53). Crisp, memorable.
- Fourier-uncertainty hotspot size $\delta_{coh}\sim\lambda/(2\pi\sigma_\Omega)$ (item 54). Closed-form theory.
- Fresnel filtering effects on the absorbed peak vs the free-space peak: shift, broadening, polarisation reshaping (item 55). I have a strong tingle that the *displacement* is derivable in closed form (see Tingles §1 below).
- Numerical demonstration: take the same 64-element URA setup as the existing Fig 2, and visualise how an MRT precoder produces both an absorbed hotspot on the body AND a free-space field hotspot, then plot their offset and width ratio. This connects directly to the Pareto figure already in the paper.

**(b) Direct FDTD validation at tractable subscale.**

The current paper rests on (i) analytical bounds, (ii) limit recovery, (iii) internal consistency. None is a direct comparison. To get one without buying a GPU cluster:

- Pick a small array (4×4 = 16 elements at 2.45 GHz, where wavelength is 12 cm and FDTD is tractable).
- Pick a body model that's small but realistic (e.g., a torso section, or a single-arm cylinder phantom).
- Run Sim4Life FDTD per-element with a fixed reference signal, extract the SAR matrix $\mathbf{S}_{FDTD}$ (16×16 Hermitian), and compare entry-by-entry to $\mathbf{Q}$ derived from the path-traced model on the same geometry.
- Report eigenvalue agreement, eigenvector agreement (subspace angles), and Pareto front agreement.
- Even if we only succeed at 2.45 GHz on a torso section, this is the validation that lets us claim the framework with confidence.

This is the Wout-friendly result: weeks of FDTD distilled into minutes of $\mathbf{Q}$, then shown to agree.

**(c) Castellanos β head-to-head.**

Currently the paper says "Castellanos used per-element scalar β; we have analytical $\mathbf{Q}$." That claim deserves a numerical comparison: redo the Pareto figure (Fig. 1) under three conditions — (i) full analytical $\mathbf{Q}$, (ii) Castellanos's scalar β, (iii) the ground-truth FDTD $\mathbf{S}$ from (b) above. Show how much of the Pareto frontier is recovered by each. If the gap is small at normal incidence and grows at oblique incidence (as I expect), that's the case for analytical $\mathbf{Q}$ in one figure.

**Smaller additions to consider:**

- **Q-eigenmodes visualised on the body.** One figure of the top-3 eigenmodes of $\mathbf{Q}$ shown as illuminated regions on the Thelonious surface, with an arrow indicating the corresponding incident direction the mode is "tuned to." This is the bridge sentence to TAP's $D(\hat k)$ — "incoherent absorption directivity is the angular spectrum of the dominant eigenmode under appropriate equivalent illumination."
- **Sensitivity plot for Approximation 1 vs incidence angle.** Currently the bound is stated as ≤4% uniform. A figure showing actual cross-term error vs incidence in the [0°, 85°] range would tighten the claim and answer reviewers preemptively.
- **Broadband demo (item 82).** Extend the existing Pareto run with a 100 MHz pulse to demonstrate per-frequency factorisation under 5G-style waveforms. Even one figure suffices.
- **Thermal-emission dual half-page (item 87).** Sensing-by-exposure: if Q is the absorption operator, then by Kirchhoff reciprocity the body's thermal emission produces a measurable equivalent at the array. A short discussion subsection (no full theorem) makes this paper much more interesting at the conceptual level.

### JSAC (DTN SI): the spine is good, the hero figure is the risk — see §"JSAC spine reshape" below

The previous round of brainstorming did the hard work: pose-differentiable Q(θ), Löwner SDP machinery, and pose-NN surrogates were all walked back in favour of Cauchy D≤2 + ZF-dosimetry. The current spine (`JSAC/paper_v2.tex`) has eight sections that each do real work, lands within 13 pages, and explicitly hits both DTN-SI pillars (closed-loop in §VI, application-aware in §I). I would not redo any of the structural choices.

The structural risk is one figure: the hero plot in §VII shows ~10⁴× slack on Brussels' RL with all five precoders collapsing on the budget axis. A reviewer's first question becomes "if the cap is trivially satisfied, what's the algorithmic contribution?" The current answer ("chronic-dose stratification is the deployable value at slack scale") is defensible but defensive. The fix is not more theory or more tingles — it's running one configuration where the cap actually binds, and choosing that configuration so the binding-regime experiment also reinforces the SI scope.

The full positioning analysis (binding-regime options, keep/change/add/remove, title and abstract) is the next section.

## Big picture: the JSAC chameleoning is correct, and the SI scope dictates priorities

After reading `JSAC/planning/JSAC_SI_digital_twins.md` and `theory/q_complement.pdf`, the strategic landscape is much clearer than my first pass suggested. Two recontextualisations:

**(1) JSAC is targeting the "Digital Twins for Wireless Networks" SI (original deadline 1 May 2026, since extended — paper is pre-submission, not under review).** The SI scope explicitly asks for:

- *Twin-in-the-loop architectures for real-time feedback and control* → exactly the body-twin + scene-dictionary + closed-loop solver
- *Cross-layer optimization frameworks for DT-guided wireless adaptation* → the per-body Q^(u) feeding into the WMMSE-style precoder
- *Convergence and stability analysis for feedback-driven DTNs* → not in current paper; should be
- *Energy-efficient and latency-bounded DT synchronization* → the cadence ladder (1ms → 31ms → 100ms → 1s → offline) is literally this
- *Federated and hierarchical management of heterogeneous DT ecosystems* → multi-operator Brussels cumulative cap is literally this
- *Open interfaces and intent-based APIs* → the regulatory-audit pathway in §VI is literally this

The chameleoning move is correct. The paper isn't an exposure-aware-MIMO paper that happens to use a body twin; it's a DTN paper whose twin happens to govern exposure. **Every tingle should be re-ranked through that lens.** Things that look like "extra theorems" become much higher-value if they reinforce the DTN frame, and lower-value if they don't.

**(2) `theory/q_complement.pdf` already contains three serious results that aren't in any paper yet.** This is a major correction to my first inventory — I missed it because I hadn't read the file. The three results, in order of importance:

- **Pseudo-Brewster eigenvector locking** (Prop 4.2 of q_complement). Under the same pseudo-Brewster regime that powers TAP, $\mathbf{Q}_{\mathrm{re}}\approx \frac{1-T_0}{T_0}\mathbf{Q}_{\mathrm{ab}} + \Delta$ with $\|\Delta\|/\|\mathbf{Q}_{\mathrm{ab}}\|\lesssim 5\%$. The two operators **share their dominant eigenvectors**. Consequence: the worst-case precoder for body exposure IS the worst-case precoder for body scattering. This is *the* result for a JSAC SI submission about wireless+sensing+exposure: one twin operator governs both compliance and the JSAC dual.
- **Transparency subspace** $\mathcal{T}=\ker\mathbf{Q}_{\mathrm{in}}$ (q_complement §5). Generic when $M>3M_\triangle$, conjectured $\dim\mathcal{T}/M \in [0.3, 0.7]$ for 256-element URA at 28 GHz. Precoders here illuminate the body for neither absorption nor scattering. *Quiet communication mode* in the JSAC framing.
- **Kirchhoff array-form dual** (q_complement Prop 6.1). Up to a Planck prefactor, $\langle|\mathbf{y}^H\mathbf{n}_{\mathrm{body}}|^2\rangle \approx \Phi(f,T)\cdot\mathbf{y}^H\mathbf{Q}_{\mathrm{ab}}\mathbf{y}$. The receive combiner that maximises body thermal pickup is the conjugate of the transmit precoder that maximises exposure. The array can self-verify compliance by listening.

Plus the global identity $\mathbf{Q}_{\mathrm{ab}}+\mathbf{Q}_{\mathrm{re}}+\mathbf{Q}_{\mathrm{mi}}=\mathbf{I}$ (Theorem 3.1 of q_complement), which is a clean array-level energy book-keeping that gives a free trace-level compliance bound.

These three should not all stay in `q_complement.tex`. **The eigenvector-locking result belongs in the JSAC paper as a §III contribution** (it's exactly the "selected area" angle), not as a follow-up. The transparency subspace is a strong JSAC §IV addition. The Kirchhoff dual is a Paper C discussion section, not a separate paper, because it's the natural conceptual closing of Paper C's framework.

**Therefore the chameleoning isn't just a relabel of the existing paper — there is content already written in `q_complement.tex` that should migrate into JSAC and Paper C.** That changes my Paper-allocation table: q_complement.tex isn't a future paper, it's a reservoir to be drained into JSAC and C.

## Inventory: q_complement additions

These are the items I missed in the first table because I hadn't read q_complement.tex. Treat as inventory rows 91–100.

| #   | Item                                                                | Source            | /10 | TAP | C   | JSAC | Verdict |
|-----|---------------------------------------------------------------------|-------------------|-----|-----|-----|------|---------|
| 91  | Reflection operator $\mathbf{Q}_{\mathrm{re}}$ definition            | q_comp Def 2.2    | 8   | −   | +   | +    | Add to JSAC §III as the JSAC-dual operator. |
| 92  | Local energy balance $\Sab+\Sref=\Sinn$ (Prop 3.1)                  | q_comp Prop 3.1   | 7   | −   | +   | ∼    | Discussion in C; framing in JSAC. |
| 93  | Operator identity $\mathbf{Q}_{\mathrm{in}}=\mathbf{Q}_{\mathrm{ab}}+\mathbf{Q}_{\mathrm{re}}$ | q_comp Eq 9    | 8   | −   | +   | +    | The book-keeping spine. |
| 94  | Array-level conservation $\mathbf{Q}_{\mathrm{ab}}+\mathbf{Q}_{\mathrm{re}}+\mathbf{Q}_{\mathrm{mi}}=\mathbf{I}$ | q_comp Thm 3.1 | 9   | −   | +   | +    | Trace-level compliance bound free of charge. |
| 95  | **Pseudo-Brewster eigenvector locking** $\mathbf{Q}_{\mathrm{re}}\approx\frac{1-T_0}{T_0}\mathbf{Q}_{\mathrm{ab}}$ | q_comp Prop 4.2 | 10 | − | + | + | **The JSAC-SI signature theorem.** Move into JSAC §III. |
| 96  | Worst-exposure-precoder = worst-sensing-precoder corollary           | q_comp §4.3       | 9   | −   | +   | +    | The literal "joint sensing and communication" duality the JSAC reviewer wants to see. |
| 97  | Transparency subspace $\ker\mathbf{Q}_{\mathrm{in}}$, dim conjecture | q_comp Def 5.1, Prop 5.2 | 8 | − | + | +  | "Quiet comm" precoders. Add to JSAC §IV. |
| 98  | Soft transparency projector $\mathbf{P}_\varepsilon$                 | q_comp §5.2       | 6   | −   | +   | ∼    | Operational form of the transparency subspace. |
| 99  | **Kirchhoff array dual** $\langle|\mathbf{y}^H\mathbf{n}_{\mathrm{body}}|^2\rangle\propto\mathbf{y}^H\mathbf{Q}_{\mathrm{ab}}\mathbf{y}$ | q_comp Prop 6.1 | 9 | − | + | ∼ | Add to C as discussion. JSAC mentions for self-calibration. |
| 100 | Trace-level compliance: albedo, capture cross-section                | q_comp §7         | 7   | −   | +   | +    | Free trace identities; useful framing. |
| 101 | Multi-bounce Neumann series for $\mathbf{Q}_{\mathrm{ab}}^{(\infty)}$ | q_comp §8.1     | 5   | −   | ∼   | −    | Coherent radiosity; ~1–4% effect (matches TAP item 15). Defer. |

## JSAC spine reshape: positioning the v1 submission to the DTN SI

This is the main act. Source material: the current `JSAC/paper_v2.tex` (8 sections + 3 appendices, ~12.8 pages of 13), the prior round's planning in `JSAC/planning/paper_spine.md` and `brainstorm_opus_round3.md`, and the SI scope in `JSAC/planning/JSAC_SI_digital_twins.md`.

### What the paper currently claims (one paragraph)

The base station maintains a per-body coherent exposure operator $\mathbf{Q}^{(u)}\in\mathbb{C}^{M\times M}$ for every body in the cell. A scene-ray-traced path dictionary indexed by body position supplies the operator without any body-side angle estimation; runtime CSI calibration fits per-path scales against served-user uplink pilots. The multi-body precoder maximises sum-rate under per-body absorbed-power budgets via a closed-form QCQP that reduces to regularised ZF in the rank-one degenerate case. The Cauchy bound $D(\hat k)\le 2$ plus a measured 6.5% posture spread closes the compliance loop without pose estimation, so tiered telemetry (A served / B cooperating / C sensed / D occupancy-grid) is sufficient. GPU measurements show 7.5 ms per body Q-refresh and 50 bodies fit a 100 ms cadence; the loop is real-time-in-silico on a workstation. Plaza demonstration shows ~10⁴× slack on the Brussels reference-level cap, so the chronic-dose ECDF is presented as the deployable value, with binding-regime back-of-envelope ($r^*\approx 2.7$ m at K=25) given honestly.

### The single risk worth fixing

The hero figure is a null result on the headline metric. Everything else in the paper survives the slack regime — the algorithm is correct, the architecture is feasible, the chronic-dose result is real — but a reviewer scanning Fig. 1 sees five precoders collapsing on the budget axis and asks "what binds?" The fix is to run **one configuration where the cap actually binds**, position it as the headline alongside the chronic-dose result, and pick the configuration so the experiment also lands an SI-shaped narrative beat.

### Binding-regime configurations, ranked

Robin's note: he can run new configurations. Here are the candidates I would consider, ranked by joint impact on (a) showing binding, (b) hitting the DTN-SI scope, (c) effort.

| Option | Mechanism | Bindiness | DTN-SI fit | Effort | Recommendation |
|---|---|---|---|---|---|
| **Multi-operator cumulative cap** | 2–3 operators share Brussels' 14.57 V/m budget; each operator's per-body L⁽ᵘ⁾ shrinks by ~3–5 dB | High at plaza scale | **Direct hit on SI's "Federated and hierarchical management of heterogeneous DT ecosystems"** | Medium (instantiate 2–3 panel/dictionary instances; share a global budget; coordinator allocates to operators) | **Lead with this.** Two birds: binding-regime hero and federation angle in one experiment. |
| **Local APD (4 cm² hotspot) per Direction 4** | ICNIRP 2020 APD₄cm² binds before whole-body SAR per Direction 4 analysis | Highest | Moderate (technical novelty; doesn't itself say "DTN") | High (Q_local(r₀) family of constraints; needs a finite covering or representer-like scheme) | **Defer to follow-up paper.** Real but too ambitious for v1. |
| **Higher EIRP at same plaza** | Push Tx power 6–10 dB or move panel closer to put bodies inside r*≈2.7 m | High | Low (just engineering; SI doesn't reward power tuning) | Low | **Backup plan** if multi-operator falls through. |
| **Tighter cap jurisdiction** | Italy historical 6 V/m or Geneva regime | Medium | None (just rescaling) | Trivial | **Supplementary curve only.** Don't lead with it. |
| **Indoor corridor / narrow geometry** | Shorter range geometry tightens binding | Maybe | Weak (indoor not a DTN-SI emphasis) | Medium | Skip. |
| **Near-field / RIS / coherent multi-path** | Rank-few assumption breaks, coherent gain stacks | Yes | Strong but breaks the paper's simplification | High | Future paper. |

**Recommendation: run the multi-operator simulation.** Three operators sharing the Brussels cap under quadrature combining gives each ~8.4 V/m effective; per-body L⁽ᵘ⁾ shrinks proportionally; binding regime activates at ~2× larger range. Beyond just binding, this experiment naturally invites a §VII subsection on **federated body-twin coordination** — exactly what the SI's "Federated and hierarchical management of heterogeneous DT ecosystems" topic asks for. Either operators run independent twins (no coordination, conservative) or share a coordinator that allocates the budget; the gap is a real measurable quantity the paper can report.

### Spine reshape: keep / change / add / remove

**Keep unchanged** (load-bearing, well-positioned):

- §I framing (Brussels as deployment blocker; body as application; DTN as substrate). Already in SI language.
- §II Cauchy D≤2 + 6.5% pose spread. The simplification that earned the pivot.
- §III $\mathbf{Q}^{(u)}$ operator + path-space factorisation $\mathbf{Q}=\mathbf{J}^T\mathbf{M}\mathbf{J}$.
- §IV multi-body QCQP closed form with ZF degenerate limit (Prop. 1).
- §V path dictionary + CSI calibration. Your unique contribution; nobody else has this.
- §VIII regulatory framing (BR audit + RL footprint reduction). Defensible and regulator-shaped.

**Change** (repositioning existing content, no new derivations):

- **§VII evaluation arc.** Currently: plaza → no binding → chronic-dose pivot. Reshape to: **multi-operator binding scenario as primary headline → plaza-slack scenario as the wide-baseline complement → chronic-dose ECDF stratifies in both regimes.** The paper claims a wider span: "we characterise both regimes and show the twin earns its keep in either."
- **§VI closed loop.** Reframe as "twin-in-the-loop" with explicit reference to SI scope language. Tier system stays; cadence ladder stays. Add one paragraph about feedback-driven stability under bounded body motion (no new theorem in v1; a one-paragraph empirical observation drawn from the existing trajectory simulation if you can re-instrument it; otherwise a forward reference to T4 in follow-up).
- **§I introduction first paragraph.** Lead with "body as the application the network must serve safely" — currently this is mixed into the regulatory framing. Front-loading it primes the application-aware reading.
- **Title.** Current: "A Body-Twin in the Precoder Loop: Application-Aware, Closed-Loop Exposure Control for Regulated mmWave Downlink." Candidate v1.1: "**Body-Twin Networks for Application-Aware Wireless: Closed-Loop Exposure Control under Federated Reference-Level Caps**". The phrase "Body-Twin Network**s**" mirrors the SI's "Digital Twin Network**s**" as a sub-class; "Federated" is added if the multi-operator experiment runs.
- **Abstract.** Add "twin-in-the-loop" verbatim (it's the SI scope's exact phrase). Lead the result paragraph with the binding-regime finding, not the slack one. Keep the two regulatory-pathway sentences.

**Add** (new content, ~0.3–0.7 page each):

- **§VII new subsection: federated multi-operator binding** (~0.7 p). The multi-operator experiment + a paragraph framing operators' twin coordination (no full mechanism design; a remark that independent twins are conservative and a coordinator that knows each operator's $\mathbf{Q}^{(u)}$ allocation closes the gap by ~X% in this scenario). Hits SI scope and fixes the hero.
- **§VIII new paragraph: pseudo-Brewster eigenvector locking as ISAC implication** (~0.3 p). Pull from `q_complement.tex` Prop. 4.2: $\mathbf{Q}_{\mathrm{re}}\approx \frac{1-T_0}{T_0}\mathbf{Q}_{\mathrm{ab}}$, shared dominant eigenvectors. Says "the same operator governs body specular signature; an exposure-aware precoder is automatically a low-RCS-on-body waveform, with body-universal ratio (1−T₀)/T₀≈1.7 at 28 GHz skin." This is the JSAC-flavoured remark, not a §III theorem.
- **§VI new paragraph: tracking under body motion** (~0.3 p). One-paragraph empirical observation: at body velocity $v$ and twin update latency $\tau$, the precoder tracks the optimal-feasible solution within $\epsilon$. Numbers from the existing trajectory simulation. SI cares about closed-loop stability; one paragraph of evidence is enough for v1.
- **Optional, §VI: tier-uncertainty operator $\mathbf{Q}^{(u)}_\mathrm{unc}$** (~0.4 p). Define tier C's Cauchy envelope as $\mathbf{Q}^{(u)}_\mathrm{env}=\mathbf{Q}^{(u)}_\mathrm{truth}+\mathbf{Q}^{(u)}_\mathrm{unc}$; bound $\|\mathbf{Q}^{(u)}_\mathrm{unc}\|$ as a function of pose-uncertainty cone. Operationalises tier C; lets a regulator turn a knob.

**Remove / cut** (free page budget for the additions):

- **Appendix A (Fresnel derivation)**, currently 0.3 p. Cite TAP and the monograph; drop derivation entirely. Saves 0.2 p.
- **Appendix B (Cauchy bound proof)**, currently 0.3 p. Cite TAP §4 (where this is fully proved); keep one paragraph on empirical tightness on Thelonious. Saves 0.2 p.
- **§V CSI calibration ridge LS detail.** Trim to one paragraph + figure caption; details to a small appendix line if needed. Saves ~0.15 p.
- **Any remaining ISAC vital-signs (heartbeat/respiration) text.** Per `ARCHEOLOGY.md` this was already downgraded; verify it's a footnote or gone. Saves 0–0.1 p.

Net: ~0.55 p removed, ~1.3–1.7 p added. Lands ~+0.8 p over current 12.8, so 13.6 — slight overshoot. Tighten figure captions and merge the two §V subsections to recover the half-page.

**Defer explicitly to follow-ups** (one-line each in §IX conclusion, no work in v1):

- Pose-differentiable $\mathbf{Q}(\theta)$ for tier-A served users (already flagged in handoff).
- Local APD hotspot family $\mathbf{Q}_\mathrm{local}(r_0)$ (Direction 4 follow-up paper).
- Multi-operator Shapley/VCG mechanism design (beyond the federation framing).
- Coherent near-field / RIS extension where rank-few breaks.
- Full transparency-subspace and Kirchhoff-dual treatment from `q_complement.tex` (own short paper or monograph appendix).

### What this gets the paper

After the reshape:

1. **The hero figure shows binding** in a configuration that is regulator-realistic and SI-flavoured (federated cap), not engineered (just cranking Tx power).
2. **Chronic-dose ECDF becomes the wide-baseline complement** rather than the defensive pivot. The paper now spans both regimes.
3. **The §VIII ISAC paragraph** lands the "selected area" tonal beat without committing to a sensing experiment.
4. **The §VI tracking-under-motion paragraph** lands the closed-loop / stability / feedback-DTN beat the SI explicitly asks for.
5. **The federated experiment** lands the federation/heterogeneous-management beat the SI explicitly asks for.
6. **Page budget stays in range** with appendix trimming.
7. **No new theorems committed in v1.** Everything additive is pulled from existing material (q_complement, the trajectory sim) or is a paragraph of new framing.

### What I'm explicitly NOT recommending

I previously over-weighted T1 (pseudo-Brewster eigenvector locking) as a §III theorem. Walked back: it's a §VIII paragraph, not a structural theorem. The paper's JSAC-SI fit comes from the architecture and the federated experiment, not from the eigenvector locking.

I previously had the conditional Cauchy theorem (T3) at high priority. Reconsidered: the current paper already presents the bound as conditional in App. C with honest framing of the 49–70% breach rate. Promoting it to a "theorem" is satisfying but it's polishing, not load-bearing for SI acceptance. Defer.

I previously had the dictionary tensor compression (T2) at high priority. Reconsidered: the current paper already reports 7.5 ms/body Q-refresh and shows the dictionary fits tens of MB. The compression result is real but it's a deployability bonus, not a paper-shaping addition. Defer to a follow-up or a one-figure addition if page budget permits after the binding-regime experiment lands.

The tingles list (next section) is now appendix material — items for follow-up papers, not the v1 spine.

## Appendix: deferred items and tingles for follow-up papers

Below is the rank-ordered tingles list from earlier rounds, kept here as a reference for follow-up papers (Paper C v2, q_complement-as-paper, future-DTN-SI). **None of these is a v1 JSAC item.** If any one of them clearly belongs in v1 after Robin reads the spine reshape above, we'll promote it back; the default is appendix.



This replaces the loose list I gave first. Each tingle is rated:

- **Viability**: how confident am I that the result is mathematically correct, on a 1–10 scale.
- **Effort**: rough person-weeks to get to a first complete derivation (and demo if applicable).
- **Strategic fit**: whether it lands in TAP, C, or JSAC, and how strongly.
- **Verdict**: do, defer, or drop.

I've also added several tingles that emerged from `q_complement.tex` and the DTN-SI reframing, and dropped or downgraded some from the first list that don't survive scrutiny.

### Tier 1 — high confidence, high impact, do these.

**T1. Pseudo-Brewster eigenvector locking, fully proved + numerically validated.**

- *What*: $\mathbf{Q}_{\mathrm{re}}\approx \frac{1-T_0}{T_0}\mathbf{Q}_{\mathrm{ab}}+\Delta$ with $\|\Delta\|/\|\mathbf{Q}_{\mathrm{ab}}\|\lesssim 5\%$ at mmWave skin. Prop 4.2 of q_complement gives a sketch; the proof needs to be tightened and the numerical claim verified.
- *Viability*: 9/10. The pseudo-Brewster collapse $t_s\approx t_p\approx\sqrt{T_0}e^{i\phi_t}$, $r_s\approx r_p\approx\sqrt{1-T_0}e^{i\phi_r}$ is the exact result of TAP's pseudo-Brewster theorem (which is rigorously established) lifted to amplitudes — almost free. The remaining step (showing the outgoing-direction phase $e^{ik_0(\hat k - \hat k_{re})\cdot r}$ doesn't break the proportionality) needs more care than the q_comp sketch gives. The cross-element terms in $\mathbf{Q}_{\mathrm{ab}}$ involve $\int_\Sigma e^{-ik_0(\hat k_n - \hat k_{n'})\cdot r}\,dA$, while $\mathbf{Q}_{\mathrm{re}}$ involves $\int_\Sigma e^{ik_0(\hat k_n^{re}-\hat k_{n'}^{re})\cdot r}\,dA$. These are *not* equal off-diagonal. So strict eigenvector equality fails; what the proof actually delivers is shared eigenvectors *modulo a shape-dependent $\sim 5\%$ off-diagonal perturbation*. That's still strong, and a numerical eigen-overlap check (subspace angles between $\mathrm{span}(v_1,\dots,v_r)$ of $\mathbf{Q}_{\mathrm{ab}}$ and of $\mathbf{Q}_{\mathrm{re}}$) on the existing AEGIS code will pin it down.
- *Effort*: 0.5 weeks rigorous proof + 0.5 weeks numerical demo on the Thelonious 64-element scenario.
- *Fit*: JSAC §III as a major theorem; cited from C.
- *Verdict*: **do**. Highest priority. This is the paper's selected-area-of-comm-engineering angle for the JSAC SI.

**T2. Dictionary tensor compression — empirical demonstration.**

- *What*: $\mathbf{M}^{(u)}(r_0)$ over the 1 m grid is data; Tucker-3 / CP / matrix-CUR decomposition will compress it. Conjecture: rank scales as $O(\log V)$ in wavelengths-cubed but the practically relevant claim is "at $V$=10⁵ grid cells we get 100× compression at 1% reconstruction error." Don't try to prove the scaling; demonstrate it.
- *Viability*: 9/10. It's just data compression. The only way it fails is if the operator is genuinely full-rank across positions, which is implausible given the spatial smoothness of paths.
- *Effort*: 1 week (wrap existing dictionary in tensor-decomposition library, scan ranks, plot).
- *Fit*: JSAC §IV (deployability). Directly hits the SI's "scalable DT deployment" topic.
- *Verdict*: **do**. JSAC editors will care.

**T3. Conditional Cauchy direction set — promote bound failure to theorem.**

- *What*: derive the explicit set $\mathcal{S}_\tau\subset\mathbb{C}^M$ on which the projected-area Cauchy bound holds. Present form: $\mathcal{S}_\tau=\{\mathbf{x}: \sum_k|\mathbf{x}^H\mathbf{v}_k(\mathbf{Q})|^2\,(1-|\langle\mathbf{v}_k,\mathbf{a}_{BS}\rangle|^2)\le \tau\}$ with the threshold derived from the geometry.
- *Viability*: 8/10. The mechanism (mode-misalignment with steering vector) is a clean geometric fact. The theorem statement needs a careful parametrisation of "direction set" but the structure is dictated by the eigenmodes of $\mathbf{Q}$ and the array's reachable steering manifold.
- *Effort*: 1.5 weeks theory + 0.5 weeks numerical verification (replot Fig. 8 of JSAC under the new bound).
- *Fit*: JSAC §V-H (current Cauchy section) and Appendix C.
- *Verdict*: **do**. Converts the paper's most defensive footnote into a contribution.

**T4. Twin-in-the-loop convergence/stability sketch.**

- *What*: model the closed loop (body moves → twin updates $\mathbf{M}^{(u)}$ → solver re-solves → precoder applied → next slot) as a discrete dynamical system. Provide a stability theorem: under bounded body velocity $v_{\max}$ and bounded twin-update latency $\tau_{\mathrm{up}}$, the precoder tracks the optimal-feasible solution within $\epsilon = O(v_{\max}\tau_{\mathrm{up}})$ of the per-slot optimum.
- *Viability*: 7/10. The structure is standard linear-systems; the work is in defining the right operator-norm metric on $\mathbf{M}^{(u)}$ change vs body motion. Not difficult, but not trivial either.
- *Effort*: 2 weeks theory + 1 week numerical (drive a body trajectory, measure tracking error vs latency, compare to bound).
- *Fit*: JSAC §IV — directly hits the SI's "Convergence and stability analysis for feedback-driven DTNs" topic.
- *Verdict*: **do**. This is what makes the paper a legit DTN paper rather than a PHY paper with a twin-flavored marketing wrapper.

### Tier 2 — likely to work, medium impact.

**T5. Transparency subspace dimension — numerical conjecture verification.**

- *What*: q_complement §5 conjectures $\dim\ker\mathbf{Q}_{\mathrm{in}}/M \in [0.3, 0.7]$ for representative array+body geometries. Empirically check across 4–8 configurations on the AEGIS code.
- *Viability*: 9/10 numerically. The bound $\dim\mathcal{T}\ge\max(0, M-N_{\mathrm{body}})$ is correct, the question is just whether the actual rank gap is large in practice.
- *Effort*: 0.5 weeks.
- *Fit*: JSAC §IV companion to T2 (dictionary compression) — both are about deployability and DoF structure. Could also live as the bridge between Paper C and a quiet-comm follow-up.
- *Verdict*: **do**.

**T6. Coherent ↔ incoherent eigenvalue bridge.**

- *What*: claim $\lambda_{\max}(\mathbf{Q})=\max_{\rho:\int\rho=1, \rho\in\mathcal{R}_{\mathrm{array}}}\int\rho(\hat k)D(\hat k)d\Omega$ where $\mathcal{R}_{\mathrm{array}}$ is the array's angular-reachability set.
- *Viability*: 6/10. I had this at "I'd bet" before; on reflection, I think it's *almost* right but the actual statement should involve a polarisation-augmented directivity (since $\mathbf{Q}$ tracks polarisation while $D(\hat k)$ averages over it). The right form is probably with the polarisation-aware $\tilde{A}_\perp(\hat k)$ from monograph §3399 (item 55 in inventory), not $D(\hat k)$. Need to verify, not assume.
- *Effort*: 1.5 weeks theory.
- *Fit*: Paper C discussion; bridges TAP and C.
- *Verdict*: **defer until after T1–T4**. Beautiful but not load-bearing.

**T7. Closed-form hotspot displacement.**

- *What*: $\Delta r_{\mathrm{peak}} \approx -[\nabla^2_{\Sigma}|E_{\mathrm{free}}|^2]^{-1}\nabla_\Sigma[T_{\mathrm{eff}}(\hat k(r))\cos\theta(r)]$ evaluated at the free-space peak.
- *Viability*: 6/10. The Laplace-method structure is right, but: (i) the Hessian is on the body surface, not in 3D; (ii) the Fresnel weight depends on the local normal which is curved; (iii) at points where the field peak is *not* near a body point, the formula doesn't apply (the absorbed peak is constrained to $\Sigma$). I think the cleanest statement is for the case where the free-space peak lies on or very near $\Sigma$, which is the relevant regime anyway.
- *Effort*: 2 weeks theory + numerical verification on a sphere.
- *Fit*: Paper C hotspot section.
- *Verdict*: **do, but lower priority than T1–T4**. The hotspot section in C can land without the closed form (just numerical demonstration); the closed form is icing.

**T8. Pose-differentiable Q(θ) for tier-A served users — sketch + numerical demo.**

- *What*: SMPL-X is differentiable in joint angles; AEGIS dosimetry is differentiable in mesh; the only non-smoothness is binary visibility, fixable with the GELU smoothing from TAP item 32. So $\partial\mathbf{Q}/\partial\theta$ exists almost everywhere. Demonstrate gradient-descent on torso orientation to minimise $\lambda_{\max}(\mathbf{Q})$ for a fixed BS-UE configuration.
- *Viability*: 7/10. The pieces are all there; integration is the work.
- *Effort*: 2–3 weeks.
- *Fit*: JSAC future-work section (Tidbit 39 from the JSAC handoff already flags this). I'd promote it from "future work" to a half-page sketch with a numerical example, because the DTN-SI scope explicitly likes "differentiable control."
- *Verdict*: **do** at sketch level. Full implementation can stay future work.

### Tier 3 — speculative, hold for now.

**T9. Multi-user Pareto envelope closed form.**

- *What*: characterise the K+B-user Pareto frontier in closed form rather than only per-iteration.
- *Viability*: 5/10. The 50-dim Lagrangian has too much structure to admit a clean envelope; complementary slackness gives a parametric description but I doubt there's a real closed form.
- *Verdict*: **drop** (or rather, downgrade to "characterise convergence rate of the dual ascent," which is a more modest claim and probably 6/10 viable).

**T10. Near-field exposure operator perturbation series.**

- *What*: $\mathbf{Q}_{NF}=\mathbf{Q}+(1/k)\mathbf{Q}^{(1)}+\dots$ as a series in inverse Fresnel parameter.
- *Viability*: 5/10. The perturbation expansion is ad hoc — there's no natural small parameter for a 28 GHz array at 5 cm distance from the body. The path-space factorisation $\mathbf{Q}=\mathbf{J}^T\mathbf{M}\mathbf{J}$ does survive; what changes is the kernel $\mathbf{M}$ ↔ amplitude-phase Fresnel kernel. That's worth saying, but it's more of a "form persists, kernel changes" remark than a perturbation theorem.
- *Verdict*: **drop**. State the structural persistence in C as a one-paragraph remark; don't claim a perturbation series.

**T11. Cross-person reflection operator $\mathbf{Q}^{(u,v)}_{\mathrm{re}}$.**

- *What*: user $v$'s body reflects path power that hits user $u$. New coherent object.
- *Viability*: 6/10 to derive; 4/10 in terms of practical impact (incoherent radiosity in TAP gives 1–4%; coherent should be similar magnitude).
- *Verdict*: **drop for current papers**. Mention as future work in q_complement (it's already in the q_complement Loose Threads list).

**T12. Multi-bounce coherent radiosity.**

- *What*: Neumann series for $\mathbf{Q}_{\mathrm{ab}}^{(\infty)}$.
- *Viability*: 6/10 to derive; 3/10 in terms of impact.
- *Verdict*: **drop for current papers**. Already in q_complement §8.

### New tingles from the DTN-SI lens.

**T13. Federated digital twin: multi-operator twin synchronisation.**

- *What*: Brussels' cumulative cap is shared across operators. Each operator maintains its own twin. When does federated twin-sharing pay off vs. each operator running independently? Pose as a coordination problem; closed form for the regret-optimal allocation.
- *Viability*: 7/10. This is mechanism design (Tidbit 39 flags Shapley/VCG). Not from-scratch theory; pulling well-understood game-theoretic machinery onto our operators.
- *Effort*: 2 weeks — but probably skippable for the current submission and instead flagged as future work.
- *Fit*: JSAC §VII discussion, future work — directly hits the SI's "Federated and hierarchical management of heterogeneous DT ecosystems" topic.
- *Verdict*: **do at half-page sketch level for current paper; full treatment is a follow-up.**

**T14. Tier-uncertainty operator $\mathbf{Q}^{(u)}_{\mathrm{unc}}$.**

- *What*: define $\mathbf{Q}^{(u)}_{\mathrm{unc}}=\mathbf{Q}^{(u)}_{\mathrm{envelope}}-\mathbf{Q}^{(u)}_{\mathrm{truth}}$ and bound it as a function of telemetry tier (A → ε_A; B → ε_B; C → ε_C using Cauchy envelope). Convert tier into an explicit budget penalty: regulator choosing tolerance $\sigma$ accepts a budget reduction $L^{(u)}_{RL}\to L^{(u)}_{RL}(1-\sigma)$.
- *Viability*: 8/10. This is just bounding the difference between two PSD operators; a Loewner-order argument gives bounds.
- *Effort*: 1 week.
- *Fit*: JSAC §IV (operationalising the tier system) and §VI (regulatory framing).
- *Verdict*: **do**. Makes the tier system rigorous rather than hand-wavy.

### Reciprocity-based passive Q-sensing — re-examined.

I had this at #7 before (with tag "stunning if it works"). On reflection, after reading q_complement Prop 6.1, the result is correct in expectation but the practical story is more subtle than I stated:

- **What works**: the receive combiner $\mathbf{y}=\mathbf{v}_1(\mathbf{Q}_{\mathrm{ab}})$ collects more body thermal noise than any other combiner, and the *trace* $\mathrm{tr}\mathbf{Q}_{\mathrm{ab}}$ is recoverable from per-element thermal noise PSDs (those are measurable on idle radios).
- **What doesn't immediately work**: recovering the off-diagonal entries of $\mathbf{Q}_{\mathrm{ab}}$ requires an interferometric measurement (cross-correlation between elements) under controlled body-thermal-radiation conditions. That's harder; it's a phantom-free *measurement protocol*, not a free identity.
- **Verdict**: include as **C discussion / q_complement-followup**. The eigenvalue/eigenvector recovery is a measurement-research problem that we shouldn't commit to in either current paper. The conceptual sketch (one operator, two physical interpretations) is a great closing paragraph for C.

## Updated simulation queue

Re-ordered by impact-per-effort under the DTN reframing.

1. **Pseudo-Brewster eigenvector locking — numerical demo on existing 64-element scenario.** Half a day's compute on AEGIS coherent code. Eigendecompose $\mathbf{Q}_{\mathrm{ab}}$ and $\mathbf{Q}_{\mathrm{re}}$, plot subspace angles. Highest impact-per-effort by a wide margin.
2. **Multi-seed + 5-min chronic-dose runs with Sionna NR PHY.** Highest scientific weight for JSAC's headline result.
3. **Dictionary tensor compression — empirical scan.** One week. Direct hit on SI scope.
4. **Conditional Cauchy direction set — derive + replot Fig. 8.** Two weeks. Converts a defensive footnote into a contribution.
5. **Transparency subspace dimension — measure on 4–8 configurations.** Half a week.
6. **Twin-in-the-loop convergence numerical.** Two weeks.
7. **Direct FDTD validation on 16-element 2.45 GHz subarray (Paper C).** The longest pole; start now if Paper C is on the critical path.
8. **Hotspot displacement — numerical on a sphere first, then closed form.**
9. **Castellanos β head-to-head Pareto.** Quick win for Paper C.
10. **Pose-differentiable Q(θ) gradient-descent demo.** Three weeks.

## Big-picture answer to "what's best to include"

If I had to rank the candidate inclusions by overall impact on the JSAC paper's chance of acceptance to the DTN SI, in priority order:

1. **Pseudo-Brewster eigenvector locking** as a §III theorem — this IS the JSAC selected-area angle, and it's already 80% derived in q_complement.
2. **Twin-in-the-loop convergence/stability** — directly hits the SI scope item that the current paper is silent on.
3. **Dictionary tensor compression** — directly hits "scalable DT deployment."
4. **Conditional Cauchy direction set** as a theorem (not a footnote) — turns the paper's biggest defensive moment into a contribution.
5. **Tier-uncertainty operator** — operationalises the tier system, gives regulators a knob, fits SI scope.
6. **Multi-seed + Sionna NR PHY chronic-dose** — hardens the headline pivot.
7. **Federated DT half-page sketch** — single subsection of §VII discussion. Free hit on SI scope.
8. **Transparency subspace** as a §IV deployability fact.

The first four are theorem-grade work; the rest are integration / numerical / discussion. Together, they reshape the paper from "exposure-aware MIMO with a twin flavour" into "a digital-twin-network paper whose application happens to be exposure compliance," which is exactly the chameleoning move the SI invites.

For Paper C, the priority order is unchanged from my first pass (FDTD validation, hotspot section, Castellanos comparison), with one addition: a discussion subsection on the Kirchhoff dual + transparency-subspace + reciprocity story, citing q_complement.tex as the technical reservoir.

For TAP, no change.

## Open questions for Robin (revised)

1. **Migrating q_complement content into JSAC.** Is the eigenvector-locking result already in the JSAC paper in some form, or is it living entirely in q_complement.tex right now? If the former I'm overstating; if the latter, this is the single highest-impact edit.
2. **JSAC SI submission window — resolved.** Confirmed: deadline was extended, paper is pre-submission. T1–T4 are all viable for v1 if we want them; the question is just sequencing vs. how soon you want to submit. My recommendation: T1 (eigenvector locking) and T3 (conditional Cauchy theorem) are both small enough and high-enough impact that they should land in v1. T2 (dictionary compression) and T4 (twin-in-the-loop convergence) are also v1-viable but bigger; if either threatens schedule, they're the natural cut to v2.
3. **q_complement.tex authorship and trajectory.** It's marked "wandering companion to Part III, not a theorem-proof paper." Is the plan to (a) merge content into JSAC + Paper C and retire q_complement, (b) keep q_complement as an appendix-style note for the monograph, or (c) eventually publish q_complement as its own short paper? My recommendation is (a) with (b) as a fallback.
4. **Twin-in-the-loop convergence.** Does any of the existing JSAC simulation code already record per-slot tracking error vs body-motion, or would T4 require a new instrumentation pass?

## Things to actually go simulate

If the goal is "infinitely ambitious," here's the simulation queue ranked by impact-per-effort:

1. **FDTD validation at 2.45 GHz, 16-element subarray, single torso phantom** (Paper C). High effort, very high impact. Even a partial result silences the main reviewer objection.
2. **Multi-seed chronic-dose runs at full 5-min window with Sionna NR PHY** (JSAC). Medium effort, very high impact. This is the paper's headline and needs to be airtight.
3. **Hotspot-physics demonstration figure** (Paper C). Low effort, medium impact. Take the existing 64-element setup, plot absorbed-peak vs free-space-peak under MRT and ECBF, measure shift and width.
4. **Castellanos β Pareto comparison** (Paper C). Low effort, high impact. Just two extra curves on Figure 1.
5. **Q-eigenmodes on body** (Paper C). Low effort, medium impact. One figure.
6. **Conditional-Cauchy direction set numerical verification** (JSAC). Medium effort, high impact. Validates the proposed theorem.
7. **Binding-regime 2D parameter sweep** (JSAC). Medium effort, medium impact.
8. **Dictionary tensor compression empirical** (JSAC). Medium effort, medium-to-high impact (depends on whether rank really is low).
9. **Approximation-1 sensitivity vs incidence** (Paper C). Low effort, medium impact.
10. **Broadband demo with 100 MHz pulse** (Paper C). Low effort, medium impact.

## Dependencies and ordering

- Paper C additions are mostly independent of JSAC additions. The two papers share the operator definition; everything beyond is paper-specific.
- The hotspot section in C is a natural next step from Paper C's existing scope and doesn't require new code; it requires running existing code with new analysis hooks.
- The FDTD validation in C is the longest-poles item and worth starting first.
- For JSAC, the multi-seed runs are blocking on having a stable simulation harness; if that exists, this is just compute time.
- Cross-citation: TAP cites C in §8.3; C cites TAP for the incoherent limit; JSAC cites both for the operator definition and for the regulatory framing of $S_{inc}<0.16m/(\bar T A)$.

## Open questions for Robin

A few things I genuinely am not sure about and would like a steer on:

1. **C ↔ JSAC overlap of the operator section.** Currently both papers re-derive $\mathbf{Q}=\mathbf{J}^T\mathbf{M}\mathbf{J}$. C does it slowly with proofs; JSAC does it as background. Fine as-is, or trim JSAC's derivation to a "summary box" + citation to C? My instinct: keep both, JSAC reading well stand-alone matters more than minimal duplication.
2. **Where does $\mathbf{Q}_{ref}$ (reflection operator) live?** Currently orphaned in C's discussion. Options: (i) add as a C section (extends scope), (ii) defer to a follow-up TWC short paper, (iii) put a sketch in C's appendix, full derivation later. Default: (iii).
3. **TAP edits.** Co-authors have it. Do you want me to draft the one-sentence forward-link (TAP recommendation 1) for you to optionally include, or is TAP fully off-limits now?
4. **JSAC venue confidence.** With the chronic-dose pivot, is this still a clean fit for JSAC's "selected areas" remit, or has it drifted toward IEEE TWC territory? I think it's still JSAC-shaped (selected area = exposure-aware comm), but worth a sanity check.

