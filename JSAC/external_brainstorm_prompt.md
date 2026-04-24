# External brainstorm prompt: JSAC DTN paper for AEGIS

You are being asked to think about a paper in progress. The author is Robin Wydaeghe (Ghent University + IMEC, end-of-PhD, spinning off AEGIS as a BV). Target venue is the **IEEE JSAC Special Issue on Digital Twins for Wireless Networks: Enabling Application-Aware and Closed-Loop Optimization** (submission 1 May 2026, ScholarOne). 13 page hard cap, single-blind, ~31% acceptance, max 3 submissions per author.

Read what is useful, ignore what is not. The context below is generous; you do not need to use all of it.

## What AEGIS is

AEGIS computes absorbed power density on human bodies in wireless environments. Core relation $S_{\mathrm{ab}}(\rr)=S_{\mathrm{inc}}\cdot T_0\cdot \mathrm{ReLU}[\hat n(\rr)\cdot(-\hat k)]$. Nine fidelity levels, level 7 is coherent MIMO with the exposure operator $\mathbf{Q}=\int_\Sigma \tilde{\mathbf G}^H\tilde{\mathbf G}\,dA$ (Hermitian PSD, $M\times M$), level 8 is exposure-constrained beamforming (ECBF) with closed-form precoder $\xx^\star\propto(\lambda\mathbf Q+\nu\mathbf I)^{-1}\hh^*$. Pipeline runs in milliseconds per pose. SMPL-X body posing, OpenStreetMap + 3D Tiles environment, DiffeRT/Sionna ray tracing, JAX-differentiable kernels. Multi-user $\mathbf{Q}^{(u)}$ already implemented. Full feature inventory: `docs/internal/features.md`.

## Robin's prior published work

- **Wydaeghe et al., npj Wireless Technology (2026)**, "Hybrid ray-tracing-QuaDRiGa/FDTD method for realistic 28 GHz exposure with 6G CF-MaMIMO in 3D outdoor environments." Helsinki + NYC case studies. Headline number: *users experience 20 dB higher exposure than non-users on average*. DOI 10.1038/s44459-026-00031-4.
- **Leeman, Wydaeghe et al., IEEE Access (2025)**, "City-Scale Spatio-Temporal Modeling of 5G Downlink Exposure of Users and Non-Users by Ray-Tracing in a Real Urban Environment." 10–50 users, agent-based pedestrians, 4×4 vs 8×8 arrays, MRT vs ZF. Found ZF reduces user exposure by 9.6 dB but only 1.1 dB for non-users. DOI 10.1109/ACCESS.2025.3541352.

So Robin's group already does urban downlink exposure simulation. The JSAC paper has to be a principled extension, not a pivot.

## SI scope (the editors' thesis)

Wireless networks are not the thing being twinned, they are the substrate that a twin runs on top of and uses to close a control loop in service of an application. Two pillars: closed-loop optimization, and application-aware design. Strong submissions hit both. None of the ten "representative papers" in `JSAC/representative_papers/review.md` combines EMF compliance with DT-driven closed-loop wireless control. Nobody twins the body. Full SI text in `JSAC/JSAC_SI_digital_twins.md`. Submission rules in `JSAC/author_guidelines/SUMMARY.md`.

## Earlier directions explored (now mostly archived)

Three technical drafts already exist as starting material:

- **Direction 4** (`JSAC/directions/direction_4_problem_codex_opus.tex`): At FR2, ICNIRP replaces whole-body SAR with the 4 cm² APD constraint applied everywhere on the body. Develops a per-patch local exposure operator family $\{\mathbf Q_{\mathrm{loc}}(\rr_0)\}$, an effective-illumination-area crossover criterion, and a hotspot-tracking ECBF. Empirically shows APD binds before SAR in every tested configuration on the thelonious phantom.
- **Direction 5** (`JSAC/directions/direction_5_math_opus_codex.tex`): Identifiability of $\mathbf Q$ from the UE channel $\hh$ alone (no-go), operator-theoretic perturbation bounds, translation/rotation split (translation kills $\mathbf Q$ in <1mm at 28 GHz, rotation is radian-scale), two-timescale architecture with safe refresh interval. Three control corollaries (uniform absorbed-power, robust compliance margin, alignment drift).
- **q_complement** (`theory/q_complement.tex`): A reflection operator $\mathbf Q_{\mathrm{re}}$ companion to $\mathbf Q$. Under pseudo-Brewster, $\mathbf Q_{\mathrm{re}}\approx (1-T_0)/T_0 \cdot \mathbf Q$ — they share eigenvectors. Implication: exposure operator doubles as a backscatter-sensing operator, opens a transparency subspace and a Kirchhoff thermal-reciprocal reading.

A separate research note documents that **commercial FR2 smartphones use analog beamforming, expose only beam-index RSRP (not per-element IQ), and run one module at a time** (`JSAC/UE_hardware/direction_5_ue_hardware_summary.md`). This kills any pose-estimation story that assumes UE-side MUSIC/ESPRIT.

A **competing recent paper** worth reading carefully: Zhou et al. arXiv 2601.19587 (`JSAC/related_works/2601.19587_transcription.tex`), "Exposure-Aware Beamforming for mmWave Systems: From EM Theory to Thermal Compliance." UL single-user, derives a per-sampling-point exposure manifold $\Phi_m$, uses Pennes BHTE → Lyapunov virtual queue for time-averaged thermal compliance. Has no real body, no pose, no Fresnel operator on a mesh, no DT.

Five older prior-art papers on exposure-constrained MIMO are in `JSAC/related_works/`. None has pose, none has a real anatomical body. Castellanos 2020 is the closest mathematically (rank-1 Fresnel on a sphere, no pose).

## The latest direction Robin gravitated toward

Specific scenario: real city (e.g., Grand Place Brussels), one BS at 26 GHz with an 8×8 panel on a building facade pointing at the plaza, ~50 bodies in the scene split into 25 served users and 25 non-users (bystanders). Pose for each body comes from IMU (or hand-waved as such) and is relayed to the BS. The BS builds per-body exposure operators $\mathbf Q^{(u)}$ from a pose dictionary, then solves a multi-constraint QCQP that maximizes sum-rate to users while keeping every body (users *and* bystanders) below an exposure limit.

The framing hook is **Brussels EMF regulation**:

- Brussels caps cumulative outdoor EMF at **14.57 V/m** (raised in 2023–2024 from 6 V/m specifically to allow 5G). Indoor cap is 9.19 V/m. Limit is **summed across all operators** in the cell.
- Brussels formally **halted 5G in April 2019** under Minister Fremault ("citizens are not guinea pigs") because operators could not run the 3.5 GHz pilot under the 6 V/m cap. Constitutional Court upheld the 2024 raise. First commercial 5G in Brussels September 2023.
- 26 GHz in Belgium is **not yet auctioned**. BIPT found no operator interest in 2019 and 2023. So the 26 GHz Brussels scenario is a near-future hypothetical, not today.
- Comparable cases: **Italy** national 6 V/m + 600+ municipal anti-5G resolutions; **Geneva** 2019 moratorium (repealed by Constitutional Chamber); various **Italian 5G-free zones**.

Robin drafted the math in **`theory/exposure_null_precoding.tex`** (compiled PDF in same folder). It develops:

- Multi-body QCQP with closed-form precoder $\ww_k^\star=(\mathbf Q_{\mathrm{tot}}(\lambda)+\nu\mathbf I)^{-1}\mathbf g_k$ where $\mathbf Q_{\mathrm{tot}}=\sum_u \lambda_u \mathbf Q^{(u)}$.
- Generalization of classical zero-forcing: ZF is the rank-1 degenerate case where $\mathbf Q^{(j)}=\hh_j\hh_j^H$. Defines a "quiet subspace" $\mathcal{Q}=\bigcap_u \ker \mathbf Q^{(u)}$.
- Worst-case pose via **Löwner envelope** $\overline{\mathbf Q}^{(u)}\succeq \mathbf Q^{(u)}(\theta)$ for all poses in a dictionary, computed as an SDP. Pose-independent compliance by construction.
- Multi-operator aggregation, cooperative vs non-cooperative, cooperation gap.
- Body-centric compliance vs traditional exclusion zones, regulator-facing rhetorical frame.
- Hero-experiment back-of-envelope for 8×8 at 26 GHz on Grand Place.
- Open threads (non-user identification, Shapley budget allocation, empirical Löwner slack, link to direction 5 translation phasor, multi-cell extension, regulator audit protocol).

## What you are being asked to do

Think about this paper. Be broad and deep at the same time.

What "broad and deep" looks like is up to you. You could pressure-test the latest direction, sketch a different paper, find the one math step that doesn't hold, draft the abstract that would make the work accepted, argue the JSAC DTN SI is the wrong venue, or follow a thread that nobody in this conversation noticed. None of those is more correct than the others. The point is to bring an outside read.

If you want texture to push against rather than a blank page, the Claude Opus thread that produced this brief came to believe the following themes were important. They may not actually be the important ones. Treat them as one read, not as the read:

- how load-bearing the "N" really is in a single-cell scenario
- how plausible the Löwner-envelope low-rank conjecture is at scale
- how a network defensibly knows about people who didn't sign up to be known about
- whether the Brussels regulatory hook strengthens or distracts
- whether Zhou 2026 is a collision or a parallel
- what the right pose-estimation story is given commercial UE hardware
- how to balance ICNIRP APD against the Brussels incident-PD ordinance

Same caveat applies to the unfollowed riffs the same thread noticed but did not pursue: a fully differentiable network DT with gradient flow through bodies (Hoydis-style); cooperative multi-operator exposure budgets as a mechanism-design problem; the q_complement sensing-exposure duality as a free closed-loop sensing modality; multi-cell handover with exposure continuity; pose-conditioned ISAC. They are listed because they were on the table, not because they are obviously right.

Permission to invent is explicit. If the right paper is something nobody in this thread named, that is a useful answer. If the latest direction is genuinely the right one and the version Robin should write is X, that is also a useful answer. If the math file has a subtle error, point at it. If you want to spend half your output on one figure and the other half on a single sentence about scope, that is fine.

## What to read

The brief below is a starting frame, not a substitute for the source material. Reading the relevant files is encouraged when the framing here feels thin. Recommended priority if you go that route:

1. `theory/exposure_null_precoding.tex` (the latest direction's math).
2. `theory/monograph_v2.tex`, especially Part III (sections starting around line 3913) — the canonical $\mathbf Q$ definition, ECBF derivation, multi-user generalization.
3. `JSAC/JSAC_SI_digital_twins.md` (SI scope) and `JSAC/representative_papers/review.md` (positioning vs the 10 representative papers).
4. `JSAC/related_works/2601.19587_transcription.tex` (Zhou, the closest competitor).
5. `JSAC/directions/direction_4_problem_codex_opus.tex` and `JSAC/directions/direction_5_math_opus_codex.tex` (the math chapters that may or may not survive into the paper).
6. `theory/q_complement.tex` (sensing-exposure duality, transparency subspace).
7. `docs/internal/features.md` (what AEGIS can actually compute today).
8. `JSAC/UE_hardware/direction_5_ue_hardware_summary.md` (FR2 UE hardware reality, kills some otherwise-attractive ideas).
9. `skeletal-animation-primer/README.md` (SMPL primer if pose representation is a question).
10. The five older ECBF prior-art PDFs in `JSAC/related_works/` (Hochwald 2014, Ying 2015, Ying 2017, Castellanos 2020, Ebadi-Shahrivar 2019).
11. Robin's own published abstracts (npj Wireless Tech 2026, IEEE Access 2025) for the existing research arc.

## Output

No required format. Be honest about confidence. Distinguish what you believe from what you suspect. Where you flag a risk, give a way to check it. Where you propose a pivot, name what is gained and what is lost. The goal is for Robin to read your output and either commit, pivot, or pose a better question.


#### Robin additions

oh and btw acn theory/system_formalism.tex this be useful? have you read the monograph? JSAC like generality and
  beautiful maths, but only relevant things ofc

oh and feel free to go down rabbit holes by writing down maths, searching online, ... questoin things! some stuff
  may be subtly wrong (or not at all, idk).

I should also add: do NOT care about the deadline being close. Disregard that 100%. In fact, you can be quite
  ambitious, if that is where the best paper lives. Your job is NOT to take into account the difficulty of execution,
  just the most optimal paper to be written

important: to know exposure, you dont just need body pose via IMU, but also AoA for the rays (propagation paths psi, right). how tf are we gonna get this.

Btw, it might sound scary when I say non-users, at it is when they're literally airplane mode, but I see it kinda as "those where a symbol of 0 is sent towards in ZF". And presumably they still send their (current or latest) IMU data for body pose. And AoA?

always write to md (with XeTeX) OR tex+compile

look. its a jsac paper. the idea is that somehwo we convince people that what we're simulating could be easily
  added to commercial equipment and we could literally with an OTA update to smartphones and BS somehow change ZF to
  ZF-dosimetry and voila. So we have a DT. We know all the CSI in the world. The IMU is the thing that will determine
  things like body pose and stuff. So, even there, I will probably add a virtual accelerometer, gyroscope and compass
  to it and fit a small NN, cuz the reviewers probably want a fully closed loop. But then, I also need to convince
  them with a very concrete idea on how one knows this J (or B you say?). Like, to determine dosimetry, we need to
  know final AoA for each user. Somehow. Im a bit of a noob on that subject though. I dont know how feasible it is to
  know AoA for users AND non-users... Do you think nowadays RT is required in deployments? that the BS is literally
  simulating the DT (which is far from accurate) and trying to guess AoA that way? or is there a better, more
  realistic way? My in silico experiment will obviously have all the CSI in the world, but both the UE and BS need to
  pretend that theyre in a realistic deployment scenario, down to the hardware that qualcomm uses on UE-side...

one perhaps somewhat wild idea was to have the skeleton with its rotations and translations embdeded into the system formalsim?? 

FULL LIST OF POTENTIALLY RELEVANT STUFF (please read lots)

skeletal-animation-primer/README.md
  theory/q_complement.tex
  theory/monograph_v2.tex (part 3 mostly)
  JSAC/related_works/2601.19587_transcription.tex
  JSAC/directions/direction_5_math_opus_codex.tex
  JSAC/directions/direction_4_problem_codex_opus.tex
  JSAC/author_guidelines/SUMMARY.md (for what we can write)
  JSAC/representative_papers/review.md (for scope)
  this whole repo is obviously huge but you can find all features here docs/internal/features.md (dont get too
  distracted)


