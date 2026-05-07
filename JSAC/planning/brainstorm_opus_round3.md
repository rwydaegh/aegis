# Brainstorm round 3 — before the tex file

*Responding to your reply of 2026-04-24. You asked me not to dive into tex yet; you want more thinking first. Good call. Two background searches are running (ISAC vital-signs at plaza range; reference level vs basic restriction in ICNIRP 2020) — I'll splice their findings in when they return. Everything below is me thinking, with you.*

## The LOS-plus-NLOS / RT question (your pushback)

You wrote: *"so what you're really trying to say is: well, in a plaza, it's all LOS (with some NLOS components following after). the distance BS-to-UE can be found literally through the speed of light or something, this should be trivial. and they can be placed on the 3D scene perfectly. We'll just say fuck it on the NLOS components then? whats the point of RT then..."*

You caught a real hole in what I said. Let me walk it back and commit to a cleaner position.

**The hole.** I claimed rank-one $\mathbf{Q}^{(u)}$ for a plaza body. That's only true if the body is illuminated by *one* path from the BS. In reality:

- LOS direct path: always (if not occluded by another body).
- Ground bounce: present except at overhead-illumination angles.
- Building facade specular reflections: present if reflectors exist within ~60° cone of the BS→body line.
- Ground double-bounce, facade-to-ground, etc.: weaker but present.

Every distinct-direction path that lands on the body contributes a rank-one term to $\mathbf{Q}^{(u)}$:
$$
\mathbf{Q}^{(u)} \approx \sum_n \sigma_u(\hat{\mathbf{k}}_n; \boldsymbol\theta_u) \, \mathbf{a}_{\text{BS}}(\hat{\mathbf{k}}_{T,n})\,\mathbf{a}_{\text{BS}}(\hat{\mathbf{k}}_{T,n})^H
$$
where $\hat{\mathbf{k}}_{T,n}$ is the BS-side departure direction that originates path $n$, $\hat{\mathbf{k}}_n$ is the arrival direction at the body (in general different), and $\sigma_u$ is the body's per-direction ACS contribution. The rank of $\mathbf{Q}^{(u)}$ equals the number of BS-distinguishable incident paths, typically 2–4 in a plaza with flat facades.

**So the rank-1 simplification I sold you is really rank-low-few.** The precoder nulls a small set of BS-side directions per body, not a single direction. Algebraically still trivial — ZF with a few extra rows per body — but the BS has to know the *list* of paths per body.

**That's what RT buys you.** Without RT, you null the LOS direction only, and NLOS reflections deliver un-nulled power to the body. For a plaza next to a glass building, the facade reflection could carry 3–10 dB of the LOS exposure, pushing you over a tight regulatory cap even with perfect LOS nulling.

So: **RT is load-bearing, not ornamental.** The BS really does need to maintain a scene model and ray-trace it. This is the "BS has some mild thinking to do" angle you liked, and I think you're right to like it. It is what elevates the paper from "smart UE does the work" to "orchestrated twin at the network." That's the SI's own thesis: networks as adaptive substrate, twins as intelligent agents in the loop. A BS running RT to predict per-body path lists is exactly that.

**Concrete on what the BS-side RT has to do:**

1. Maintain a static scene model (buildings, ground). Cheap, load once.
2. Know body positions (from IMU+GPS or ISAC). This is a dynamic input.
3. For each body, compute the set of significant paths from BS → body. At plaza range with 2–4 dominant reflectors, this is 5–20 paths per body per update. Fast RT. Use Sionna-RT or DiffeRT — both are GPU-efficient, already in your AEGIS stack.
4. For each path, compute the BS-side departure direction $\hat{\mathbf{k}}_{T,n}$ and the per-path "absorption contribution" at the body (depends on incidence angle, body pose, via the ACS framework of Part 1).
5. Assemble the per-body quadratic constraint: $\sum_n \sigma_u(\hat{\mathbf{k}}_n;\boldsymbol\theta_u) |\mathbf{a}_{\text{BS}}(\hat{\mathbf{k}}_{T,n})^H \mathbf{x}|^2 \le L^{(u)}$.
6. Feed into the ZF-dosimetry solver.

This is all per-pose-update cadence (100 ms), which at 50 bodies × 10 paths × standard RT cost is easy on a GPU. Your 3 ms/body AEGIS measurement already covers this workload.

### The mild thing I want you to think about before locking in

The BS's ray tracer gives you *departure directions* for each body's path list. It does **not** give you the body's *arrival directions* $\hat{\mathbf{k}}_n$. Those depend on which reflector the path bounced off — you can get them from RT as a byproduct, but you have to actually run it (not just compute BS-to-body straight lines). Once you have arrival directions, the body's ACS contribution depends on incidence angle × body pose, which is where Part 1's $D(\hat{\mathbf{k}})$ earns its keep — evaluated at each arrival direction individually.

This is the exact sentence I want in the paper: *"For each body $u$, AEGIS's Part 1 framework gives the per-direction absorption contribution $\sigma_u(\hat{\mathbf{k}}_n;\boldsymbol\theta_u) = S_{\text{inc}} T_0 \,\text{ReLU}[\hat{\mathbf{n}}(\mathbf{r})\cdot(-\hat{\mathbf{k}}_n)]$ integrated over the body, which for the direction-averaged and posture-averaged case reduces to Cauchy's $T_0 A_{\text{ab}}/4 \cdot D(\hat{\mathbf{k}})$."* That keeps Cauchy centre-stage.

## The ISAC breathing question (status: running a search)

You asked: do we go all-in on respiration/heartbeat ISAC for bystanders? Is it real?

*I have a background search running; I'll update with what it finds. Here's my current confidence level.*

**What I'm willing to defend right now without more sources:**

- Presence detection (is there a moving body in this angular cell): **confident yes** at plaza range. This uses micro-Doppler of any body motion (breathing + small sways) integrated over a 1–2 s window. RCS argument alone gives you this without breathing.
- Position / angle estimation (which angular cell is the body in): **confident yes** at plaza range. Standard monostatic radar localization on the 8×8 aperture gives ~6° azimuth resolution at 26 GHz, which at 50 m is about 5 m — coarse but enough to flag "this direction has a body."
- Range estimation: **confident yes**. 400 MHz chirp bandwidth gives ~0.4 m range resolution.
- Respiration rate estimation (0.2–0.5 Hz micro-Doppler): **uncertain at plaza range**. Published demos I remember are all indoor at < 10 m. Outdoor at 50 m costs 40+ dB two-way path-loss margin vs. indoor short-range. I *think* the BS's 55 dBm EIRP + 18 dB array gain covers it, but outdoor turbulence / multipath can eat 10–20 dB of coherence. Needs the search.
- Heartbeat estimation (1–1.5 Hz micro-Doppler, sub-mm displacement): **skeptical at plaza range**. Even in the lab this is marginal. Don't claim this.

**Use-case split once I know the numbers:**

- For **cooperating non-users** (tier B in my previous tiering — phone on, no app): you *already have* IMU via UL. ISAC is redundant. Don't bother. IMU gives better pose than ISAC ever will.
- For **airplane-mode / no-phone bystanders**: ISAC is the only lever. If it only gives presence + angle (not pose), then the paper's story becomes: ISAC tells us where unaccompanied bodies are, and for them we use Cauchy $D \le 2$ worst-case pose. That's clean and defensible.
- Respiration as an **activity-class prior** (rest breathing ~12 bpm ⇒ standing/sitting; fast breathing ⇒ walking/running ⇒ different pose manifold) is a cute angle, but only if respiration rate is reliably recoverable at range, which I'm uncertain about.

**My current recommendation before the search returns:** plan the paper around ISAC giving *position only* for bystanders, and pose-agnostic Cauchy. If the search reveals respiration detection is solid at plaza range, promote it to a side-note on activity classification. Don't build the paper's compliance argument on respiration-rate estimation.

*[Will revise this section when the agent returns.]*

## The tier question — you're right, four is too many

Collapse to **two**, with an optional third that's just a different telemetry path:

| | Pose info? | Telemetry source | Exposure operator |
|---|---|---|---|
| Pose-informed | Yes (pose NN from IMU) | Phone UL + MNO app, cooperating (served user or not) | $\mathbf{Q}^{(u)} = \sum_n \sigma_u(\hat{\mathbf{k}}_n; \boldsymbol\theta_u) \mathbf{a}_n \mathbf{a}_n^H$ |
| Pose-agnostic | No, just position | ISAC (respiration-detected or RCS-detected body) OR vision (operator camera) OR regulator-assumed occupancy map | $\mathbf{Q}^{(u)}_{\max} = \sigma_u^{\max} \sum_n \mathbf{a}_n \mathbf{a}_n^H$ with $\sigma_u^{\max}$ from Cauchy $D \le 2$ |

Two categories. One optional axis for the pose-agnostic case: how you got the position (ISAC vs vision vs regulator envelope). But that's a sentence, not a tier.

No-phone / undetected: covered by the "regulator-assumed occupancy map" bullet above. The regulator says "assume a body could be anywhere in this public region," and you compute compliance against the envelope. This is the classical exclusion-zone approach, applied only to the occupancy-indeterminate part of the coverage cell. Inside that zone, you back off. Outside, you use body-centric.

This is cleaner. Paper has two categories + a regulator-envelope fallback. Done.

## q_complement — what I'd actually do with it, concretely

You're right I was fuzzy. Let me nail it.

**What q_complement actually says, for the record.** Under pseudo-Brewster (validated at mmWave for bare skin, smooth per Rayleigh), the operator $\mathbf{Q}_{\text{re}}$ whose Rayleigh quotient is "total body-specular-backscatter from precoder $\mathbf{x}$" satisfies $\mathbf{Q}_{\text{re}} \approx \frac{1-T_0}{T_0}\mathbf{Q}_{\text{ab}}$. Same eigenvectors, up to the scalar $(1-T_0)/T_0 \approx 1.7$ at 28 GHz.

**The tension I was obscuring.** This says **nulling exposure also nulls backscatter**. So if I'm using a precoder that kills exposure to body $u$ (because $\mathbf{x} \in \ker \mathbf{Q}^{(u)}_{\text{ab}}$), I also kill any backscatter-based detection of body $u$ from that same precoder. That's a *blocker*, not an enabler, for the "use the exposure operator as a free ISAC detector" story I oversold.

**So what's it actually good for?** Three honest options:

1. **Before the null is applied.** During a pilot-sweep / CSI-RS phase, the precoder is a full-aperture sounding waveform, *not* the exposure-null precoder. In that phase, the BS is radiating energy in all directions and receiving scatter from all bodies, including those it will subsequently null for the data phase. Body detection happens in the sounding phase; compliance enforcement happens in the data phase. Temporally separated. q_complement tells you that during the sounding phase, the modes that light up the bodies for detection are the same modes that *would* dose them maximally — so the sounding phase is "the worst-case exposure moment" and needs to be dose-limited. Actually interesting: the q_complement duality says the sounding duty cycle has to be short *because it is by design the most-dosing phase*. That's a novel design constraint worth a paragraph.

2. **For the bodies you are not trying to null.** If the BS has 50 bodies in scene and only 30 of them are in the null set (because of DoF constraints — see §"Budgeted, not nulled" below), the 20 non-null bodies are the ones whose exposure is managed softly (below cap but nonzero). For *those* bodies, the precoder is carrying non-trivial scatter energy into the BS, which can be demodulated as ISAC return. So ISAC happens passively for bodies-you-care-about-but-aren't-hard-nulling. This is actually useful.

3. **Normative claim for the paper.** "Under pseudo-Brewster (validated for bare skin at mmWave), absorption and specular backscatter are mode-parallel. This gives the paper a unified algebraic object: the same $\mathbf{Q}^{(u)}$ we bound for compliance is the match filter for sensing, up to a 1.7 multiplicative constant at 28 GHz. We exploit this in the ISAC-augmented tier." One paragraph of methods section. That's it.

**What I would NOT claim:** that q_complement lets you sense hard-nulled bodies. It doesn't.

**Specular-skin footnote.** Your note that skin is smooth at 26 GHz (Rayleigh roughness < λ/8 = 1.3 mm, which skin easily satisfies) is worth a half-sentence: it justifies treating body reflections as coherent specular rather than diffuse, which is a load-bearing assumption in q_complement. Cite your own Part 1 discussion of Fresnel reflection. Clothing roughness matters for clothed subjects but "most skin is exposed in summer outdoors or at the head/neck regardless" — even indoor bare skin at the head/hands/forearms is enough for the argument to work. Acknowledge and move on.

## Budgeted, not nulled — a reformulation I missed in round 2

Re-reading your `exposure_null_precoding.tex` more carefully: you already have this. It's the multi-body QCQP at (P-MB). I keep calling it "ZF-dosimetry" with the connotation of *hard* nulls, but the paper should actually do *soft* nulls — per-body absorbed-power caps — because:

**DoF budget argument.** 64 antennas, 25 served users, 25+ bystanders. Hard nulls use one DoF per constraint, so 50 nulls consume 50 of 64 DoF. In dense plazas with 100+ bystanders this runs out; the precoder stops having DoF for sum-rate. With soft nulls (per-body cap $\le L^{(u)}$), you allocate DoF proportionally to "how tight is each body's constraint." Bodies close to the cap get hard-null treatment; bodies with large margin get small caps, using less DoF.

**Algorithmic reformulation.**
$$
\max_{\mathbf{W}}\;\sum_k \log_2(1+\text{SINR}_k) \quad \text{s.t.}\quad
\mathbf{x}^H \mathbf{Q}^{(u)} \mathbf{x} \le L^{(u)}\ \forall u,\ \|\mathbf{x}\|^2 \le P.
$$
This is exactly your (P-MB). In the far-field rank-few limit, $\mathbf{Q}^{(u)} = \sum_n \sigma_u(\hat{\mathbf{k}}_n; \boldsymbol\theta_u)\,\mathbf{a}_{\text{BS},n}\mathbf{a}_{\text{BS},n}^H$ with a few $n$ per body. Each body contributes a few per-direction quadratic constraints. Dual variables $\lambda_u$ encode "how hard is body $u$'s cap biting." Bodies with $\lambda_u = 0$ are inactive (soft-null-free). Bodies with $\lambda_u > 0$ are binding.

**Precoder closed form.** Lagrangian KKT (your eq 6) becomes
$$
\mathbf{x}_k^\star = \Bigl(\sum_u \lambda_u \mathbf{Q}^{(u)} + \nu \mathbf{I}\Bigr)^{-1} \mathbf{g}_k
$$
for the WMMSE surrogate. This is what you wrote. The clean message is: **you don't need to null all bystanders; you apply a regularised multi-user ZF where the regulariser is per-body "how close to the cap" weighted.** That's the algorithm. It runs always, it gracefully degrades when DoF is short, it reduces to classical ZF when $\sigma_u \to \hh_j\hh_j^H$ (your Prop 4.3 recovering classical ZF).

**Why this matters for the paper.** "ZF-dosimetry" as a framing implies hard nulls, which (a) reviewers know have DoF limits, and (b) conflicts with your own QCQP formulation. "Budgeted beamforming" or "exposure-constrained ECBF with per-body caps" is more accurate and is what you already wrote the math for. I was inaccurate when I talked about hard ZF.

## Reference level vs basic restriction — the reframing I now think the paper needs

I started getting this right in the round-2 doc but didn't push it far enough. Let me commit.

**The ICNIRP hierarchy.** There's a basic restriction (the quantity that actually protects tissue: whole-body SAR for frequencies where tissue heats uniformly, APD or peak-SAR at mmWave for surface absorption) and a reference level (a conservative proxy in terms of easily measured free-space field). The reference level is *derived from* the basic restriction by assuming worst-case body geometry and orientation. If the operator can *demonstrate* compliance with the basic restriction (with a body model), the reference level is redundant. The hierarchy is: basic restriction is the real thing; reference level is a conservative heuristic.

*[Awaiting agent search for Brussels/Italy specifics — whether 14.57 V/m is a reference level or a restriction, whether ICNIRP 2020 permits basic-restriction-based demonstration.]*

**The paper's regulator-facing argument.** *"Cities that cap reference levels at 14.57 V/m (Brussels), 6 V/m (Italy), etc. do so because the reference level is a proxy for the tissue-protection basic restriction. The proxy is conservative: at mmWave, a standing adult has $D_{\max} \le 2$ by Cauchy 1841's projected-area theorem and empirically $D_{\max} \approx 1.2$ on realistic phantoms, with only 6.5% posture spread in a full backflip (Wydaeghe, forthcoming). This means the reference level over-estimates tissue absorption by a factor of $\sim 2.5\times$, or $4\,\mathrm{dB}$. A body-centric digital-twin compliance framework satisfies the basic restriction directly, recovers this headroom, and is verifiable by a regulator via a standardised audit protocol."*

**What this does for the paper.** Shifts the argument from "we satisfy Brussels reference level efficiently" (which is an engineering capacity story) to "we satisfy the tissue-protection basic restriction that reference levels proxy for, more faithfully than a reference level does" (which is a tissue-science story). Both stories are defensible but the second one leads with physics and ends with engineering, which is how JSAC papers should read.

The Brussels hook is preserved: it's the *reason* the problem binds in DL. The mathematics is body-centric (basic restriction on real SAR on real bodies). The operator's argument to the regulator is "our twin is more faithful than your reference level, here's the audit protocol." That's the policy-relevance paragraph you were trying to write.

**I want to double-check in ICNIRP 2020** whether basic-restriction-based compliance is explicitly permitted (I'm pretty sure it is — the ICNIRP text says reference levels "are intended to be conservative" and basic restrictions "are the limits that apply"). Background agent will tell me. If it's NOT permitted, the paper has to argue for adding it as a protocol extension, which is still interesting but is one step further up the policy chain.

## Cauchy 1841 — yes absolutely, centre it

You'd asked for it. The opening of §II Setup should be this tight:

*"The whole-body absorbed power under plane-wave incidence from direction $\hat{\mathbf{k}}$ satisfies $P_{\text{abs}}(\hat{\mathbf{k}}) = S_{\text{inc}} T_0 A_\perp(\hat{\mathbf{k}})$, where $A_\perp$ is the body's projected area along $\hat{\mathbf{k}}$ (Wydaeghe et al., forthcoming monograph §5.2; for the isotropic case, Cauchy 1841). For any convex body $A_\perp \le A/2$ where $A$ is the surface area (Cauchy's projection theorem), hence the direction-averaged absorbed power $\langle P_{\text{abs}}\rangle = S_{\text{inc}} T_0 A/4$. The absorption directivity $D(\hat{\mathbf{k}}) = A_\perp(\hat{\mathbf{k}})/\langle A_\perp\rangle$ is bounded by $D \le 2$ (convex) and $D \le 2A_{\text{CH}}/A_{\text{ab}}$ (non-convex). Posture variation shifts $D_{\max}$ by $\lesssim 7\%$ across a full backflip animation, so pose-agnostic worst-case compliance at $D_{\max} = 2$ is tight to within $\sim 1\,\mathrm{dB}$ of the true worst case and requires no pose estimation."*

This is the paragraph the reviewer reads and thinks "OK, the paper has a real closed-form worst case, not just a simulation." Cauchy 1841 referenced in a 2026 JSAC paper is a lovely narrative beat. I'd leave the citation as is and enjoy it.

## No-phone bystanders — Cauchy, not ML

I briefly entertained "statistical prior on pose for no-phone people" and retract it. The whole point of Cauchy $D \le 2$ with 7% pose spread is that we don't *need* to estimate their pose. Use the worst case. It costs us roughly 4 dB of headroom vs. the pose-known oracle, and that's fine.

If you ever wanted to tighten this: train an activity classifier on the RCS pattern or micro-Doppler pattern (once you have ISAC), which gives you walk/stand/sit prior without identifying individuals. That's a whole other paper. Footnote.

## What the paper's single-sentence pitch looks like now

*"We propose ZF-dosimetry: a zero-forcing-style multi-user precoder that adds per-body absorbed-power caps to the classical user-interference null set, supplied by a network-side digital twin that maintains a ray-traced scene model, pose-conditioned absorption cross-sections for cooperating bodies, and Cauchy-bounded worst-case cross-sections for bystanders detected via integrated-sensing-and-communication. The resulting system satisfies the ICNIRP basic restriction on whole-body SAR more faithfully than city-level reference-level caps (Brussels 14.57 V/m, Italy 6 V/m), is compatible with existing 3GPP primitives (IMU-in-modem, UL CSI feedback, pilot sweeps), and in a 5-minute real-time in-silico plaza simulation recovers $X\,\mathrm{dB}$ of capacity that a reference-level back-off discards."*

Cleaner than what I had in round 2. Anchored in the budgeted-beamforming reformulation, the Cauchy-based pose-agnostic worst case, and the basic-restriction-vs-reference-level policy angle. Still body-centric, still DT-in-loop, still Brussels-motivated.

## What I still don't know before I'd be comfortable writing the tex

Four things I want to settle before the theory section is more than a sketch:

1. **The ISAC respiration-at-plaza-range question.** Agent is searching. If it comes back "marginal but published," I write §V.3 as I have it. If it comes back "unpublished at plaza range," I downgrade to RCS-only presence detection and drop the respiration-rate claim.

2. **The ICNIRP hierarchy specifics.** Agent is searching. Need to know if basic-restriction-based compliance is explicitly permitted, whether Brussels 14.57 V/m is a reference level or a restriction, whether there's an averaging interval.

3. **The AEGIS compute envelope for the hero demo.** Your 3 ms/body on a 4-CPU machine is for one-body Part-1 physics. The full hero demo is 50 bodies × {paths per body} × {poses updated per pose-cadence}. I want to check: do you have GPU AEGIS somewhere? Can the 50-body per-frame recomputation run faster than 100 ms wall-clock? If yes, the "real-time in silico" claim is cheap. If no, we batch pose updates or use the translation-phasor shortcut for the rank-few case.

4. **One more math check on the rank-few $\mathbf{Q}^{(u)}$.** In the far-field with K dominant paths per body, I want to compute the empirical rank of $\mathbf{Q}^{(u)}$ on thelonious at 26 GHz for realistic plaza geometry and see whether the "rank a handful" claim survives. AEGIS can compute this — it's one run. If the empirical rank is 2–4, we have a clean story. If it's 10+, the "rank-few" framing wobbles and we're back toward the full coherent operator.

These are not reasons to stop thinking. They are reasons to stop *before the tex* and run a few checks. Once I have them, the tex I write will actually reflect facts, not hopes.

## What I'd want from you, concretely

- Would you run the rank-empirical check on thelonious for me? (50 m range, 26 GHz, 2–3 dominant reflectors as NLOS paths. Report the first 10 eigenvalues of $\mathbf{Q}^{(u)}$.)
- Do you have GPU AEGIS? If so, 50-body benchmark time?
- If the ICNIRP-basic-restriction-permission check fails (i.e., basic restriction is NOT an accepted compliance route in ICNIRP 2020), how do you want to handle that? Argue it should be, or step back to "we help the operator's reference-level margin" story?
- Are you wedded to SMPL-X? SMPL alone (body, no fingers/face) is simpler, already enough for ACS. SMPL-X adds expressive face + hands which don't matter for WB-SAR.

Not blocking. Just the stuff I'd ask for before I wrote the theory section.

## Plan from here

1. *Wait for the two search agents* (running now).
2. *You answer the two "what I'd want from you" questions above* (or say "skip, just commit to assumptions").
3. *I write the tex file* — theory section fleshed out: Part 1 physics extended to multi-body precoding in the rank-few regime, the QCQP, closed-form precoder, Cauchy bound as pose-agnostic case, pose-conditioned ACS predictor defined (NN architecture + training loss). I'd mark everything experimental as "[needs simulation — deferred to results]" so the theory can exist self-contained.

I'll add both agents' outputs to this file when they return, with a dated marker. Then I'll make the call on whether to start the tex.

---

# *Update — both search agents returned. Two important corrections.*

## A. ISAC vital-signs at plaza range — the literature does not support the claim

Agent searched Google Scholar / arXiv / PMC for mmWave vital-signs radar at 24–77 GHz. **Every reliable demonstration is indoor, at ≤ 5–10 m.** The state of the art for joint-communication-sensing vital signs is **2–4 m indoor** (Selles-Valls 2023 at UTwente, 26 GHz multi-beam comms testbed; and arXiv 2509.11767, 26.5 GHz OFDM JCAS). **Heartbeat detection is < 3 m in every published paper.** No outdoor 20+ m demonstration exists.

Link-budget wise, breathing at 20–30 m from an 8×8 BS at 26 GHz with long (tens-of-seconds) integration is "borderline plausible" to a reviewer — but they will demand an explicit budget, phase-noise assumptions, and an honest gap statement. Heartbeat at 50 m is not defensible.

**What I'm rolling back from round 2:**
- My link budget that said "breathing at 50 m with 60 dB margin" was too optimistic. I was scaling indoor numbers without properly accounting for phase noise, body sway, and outdoor clutter. Correction noted.
- The "free ISAC via q_complement eigenvector match filter" story is no longer defensible for respiration detection at plaza range.

**What I'll commit to instead:**
- ISAC is used for **presence detection and angular localization** of bystanders. Standard monostatic radar processing on the BS's own aperture. Human RCS ~1 m² at 26 GHz, body at 50 m is still ~40 dB SNR on 8×8 with 400 MHz bandwidth; angular resolution is ~6° azimuth at 26 GHz (aperture-limited), giving ~5 m linear resolution at 50 m. This is comfortably within standard radar territory and needs no vital-signs argument.
- Vital-signs detection is downgraded to **a discussion-section paragraph** on "toward BS-range vital-signs ISAC," with explicit gap citation (the 2–4 m indoor ceiling) and the paper's contribution being the link-budget / exposure-aware-precoding analysis, not a measurement. Frame as a forward-looking research direction, not a feature of the proposed system.
- The q_complement duality is still interesting for its theoretical content (exposure and backscatter share eigenvectors), but for ISAC implementation in the paper we use simpler RCS-based localization, which does not require the duality.

This is actually a *cleaner* paper. The main body doesn't hinge on a contentious vital-signs claim; the closed loop is body-presence-detection + body-position + pose-NN-for-cooperating + Cauchy-worst-case-for-everyone-else.

---

# *Round-3 self-correction — the yes-man flag you called me on*

You caught me. *"Ive noticed youre a bit of a yes man on this front. have you told me why we gave up on coherent?"* No — I did not give a real physics reason. Let me un-flip and commit to the honest answer.

## Why I was drifting toward rank-few, and why that was over-correction

Two reasons I was sliding toward "just use rank-few":

1. **Löwner SDP overkill**: Part 1's Cauchy $D \le 2$ bound makes the scalar *worst-case* compliance trivial. I conflated "the worst-case bound is trivial" with "the full operator is trivial." These are different things. The bound is scalar; the operator is not.

2. **Per-slot re-integration cost**: if $\mathbf{Q}^{(u)}$ has to be re-integrated at per-slot cadence, the paper's real-time story wobbles. But `system_formalism.tex`'s $\mathbf{Q} = \mathbf{J}^T \mathbf{M} \mathbf{J}$ factorisation already solves that: the heavy integral lives in $\mathbf{M}$, which refreshes at pose-cadence (100 ms), and the per-slot refresh is trivial. I had this and then forgot it.

Neither of those is a reason to give up coherent. They're reasons to use the formalism cleanly, which is what Parts I + III + `system_formalism.tex` already do.

## What I commit to for the tex

**The formalism is coherent.** $\mathbf{Q}^{(u)} = \int_{\Sigma^{(u)}} \tilde{\mathbf{G}}^H \tilde{\mathbf{G}} \, dA$ with all the apparatus of Part III. Path-space factorisation $\mathbf{Q} = \mathbf{J}^T \mathbf{M} \mathbf{J}$ for computational layout.

**The plaza regime is a regime, not a replacement of the formalism.** In the plaza regime, paths to a body are angularly resolvable at the BS aperture, so cross-path interference across the body surface averages to zero, and $\mathbf{Q}^{(u)}$ concentrates on a handful of eigenmodes corresponding to the distinguishable incident paths. That is *the empirical rank-few observation* — but it is a statement about the eigenvalue spectrum of $\mathbf{Q}^{(u)}$, not about replacing the operator. The paper writes: *"in the plaza regime, $\mathbf{Q}^{(u)}$ typically has $\sim 3-10$ dominant eigenmodes; the ECBF solver needs only these, at the cost of $O(M N_{\text{dom}})$ per slot rather than the full $O(M^2)$ inverse."* That's it. The formalism is unchanged.

**The rank-few claim becomes a measurement, not an assumption.** I no longer want to assume it; I want to *show* it on thelonious for plaza geometry, as one plot in the paper. If the empirical rank is 3, great. If it's 15, we still use the coherent Q solver but with more modes. Nothing in the theory changes.

**When does pure coherent matter (not just rank-few)?** Near-field (UE-side), low-aperture, or when LOS and ground-bounce are in the same angular cell at the BS — these are the cases where cross-path coherence on the body surface survives. All of them are in the plaza-scenario edge cases (sidewalk immediately below a low-mounted BS; subway platform), and the coherent formalism handles them automatically. The rank-few plot would show those cases have higher effective rank; the solver handles it.

**So: I keep coherent as the main formalism. The rank-few observation is a computational affordance, not a simplification of the theory.** That's the un-flipped commitment.

## What you get from coherent vs rank-few

- **Correctness**: coherent is exact. Rank-few breaks down in coherent-multipath geometries (same-angular-cell multi-bounce, near-field).
- **Pose-response accuracy**: coherent captures how pose shifts both *which modes* dominate and *their eigenvalues*. Rank-few with fixed steering vectors + scalar ACS captures only the eigenvalue shift.
- **Algorithmic uniformity**: one solver for all regimes. Switching between "rank-few ZF" and "coherent ECBF" in the paper forks the experimental section.
- **Fidelity to AEGIS**: AEGIS already computes coherent $\mathbf{Q}^{(u)}$ at level 7/8. Using rank-few in the paper artificially downgrades the monograph framework.
- **Future-proofing**: near-field follow-up papers use the same formalism.

Cost: slightly heavier per-pose integration. The `system_formalism.tex` factorisation says this is $O(N^2)$ per pose, with $N$ being the number of RT paths (typically $\le 10^3$ for a plaza). Fine.

**Takeaway.** I was yes-manning toward simplification because you flagged Löwner and Part-1-Cauchy and I over-rotated. Rolling back. The paper is **coherent ECBF with multi-body + pose-conditioned operator**, computed via the path-space factorisation, with the rank-few observation as an empirical plot in §VI, not a theoretical simplification.

---

# *Round-3 self-correction 2 — the BR framing is not a slam-dunk*

You also caught me on: *"you're acting like the BR thing is a huge realization but this is obvious. In fact, Brussel ASKS for reference limits that are stricter, so you can tjust say 'well we are satisfying ICNIRP's BR so brussels you should be happy with this'. But brussels law is about satisfying RL, no? they dont care abotu icnirp BR."*

You're right. Let me walk back.

**What ICNIRP 2020 permits** is a *regulatory framework* statement: within the ICNIRP guidelines, BR-based compliance is accepted as sufficient. That makes IEC/IEEE 62232:2022 and ITU-T K.122 standards that the RAN OEM can already apply. Useful for the *industry* readers of JSAC who will want to know which standards pointer to cite.

**What Brussels law requires** is RL compliance at public points, *independent* of what ICNIRP says. Brussels law is local law; ICNIRP is a reference. If the Brussels arrêté says "14.57 V/m time-averaged at every public point," the operator has to satisfy that. Even if the operator satisfies BR perfectly.

**So the paper's real regulatory argument has two parts, not one:**

- **Industry / standards story**: our body-centric compliance method operationalises the ICNIRP BR-based compliance that IEC/IEEE 62232 already permits. Useful for standardisation bodies and for RAN OEMs who want to document compliance via the BR path.
- **Jurisdictional story**: jurisdictions that enforce RL-only (Brussels, current French law, etc.) will need a *statutory update* before they can accept BR-based audit. The paper describes what such an update would look like but does not pretend it already exists. We help the operator in those jurisdictions by: (a) reducing EIRP via beamforming only where needed (ZF-dosimetry minimises the field strength at occupied public points, which is a subset of all public points — see below), (b) showing that RL-compliance can be achieved at lower capacity cost by steering beams around bodies.

**Reality check on (a):** Brussels law checks RL at *publicly accessible* points, not at *occupied* points. So the operator can't selectively satisfy RL-at-bodies; they have to satisfy RL at every public point. ZF-dosimetry doesn't directly help with that — it helps with *occupant* exposure, which is BR not RL.

So the paper's honest claim to a Brussels reader is: *"our twin-based audit could satisfy the BR that your RL is derived from, and we propose it as a complementary regulatory channel that other ICNIRP-aligned jurisdictions already permit. In the meantime, our method also reduces RL at occupied public points, which is where exposure actually occurs."* That's politically honest and scientifically defensible.

**The deployment-blocker hook stays.** Brussels is still a real barrier. The paper is still a DT-audit proposal. But the framing is "this is a path forward, not a solved problem" — not "we meet ICNIRP so Brussels should be happy." Brussels isn't bound by ICNIRP.

---

# *Round-3 self-correction 3 — the "what's the point of coherent" question deserves a direct answer*

Why coherent Q beats rank-few, in one paragraph:

*"At BS apertures larger than what resolves a body from its arrival-direction neighbours — i.e., sidewalk UEs serviced by a small cell on the same building — the coherent across-path interference on the body surface survives angular-cell averaging. In those geometries the body presents a distinct set of dominant eigenmodes that are not aligned with any single steering vector, and rank-few would under-count the exposure. The paper's experiment includes at least one such geometry (a user standing within 10 m of the BS panel) to show the coherent formalism in action. In the looser far-field plaza cases the rank-few regime emerges naturally as a spectrum of the coherent operator; we plot this and recover the 3–10 dominant-mode picture as an empirical observation."*

In other words: **coherent is the mother framework; rank-few is a plot in §VI.** That's what I should have said in round 2.

---

# *Round-3 self-correction 4 — DL compliance being "lowkey moot"*

You said: *"I just hope there is much to constrain in the end in DL if the limits are too high since that makes the paper lowkey moot."*

You're right to worry. If DL at normal EIRP is always compliant at Brussels/Milan/ICNIRP limits, then the paper's motivation collapses to "we do ZF-to-bystanders because it's algorithmically nicer." Not enough.

**What makes the paper non-moot:**

1. **Tight jurisdictions actually bind**: Brussels 14.57 V/m at 26 GHz on a multi-operator cumulative cap does bind at parts of the coverage cell. Your own §9.3 back-of-envelope in `exposure_null_precoding.tex` shows this. The paper has to show WHERE in the plaza cell the cap binds under baseline MRT, and then show ZF-dosimetry removes those hotspots. That's a compliance-coverage figure.
2. **ZF-dosimetry value beyond compliance**: reducing bystander exposure is valuable even when the cap isn't binding, because of the *24/7 DL / chronic exposure / dose accumulation* concern (GOLIAT motivation). Framing: "even when instantaneous compliance is easy, long-term dose minimisation is valuable, and ZF-dosimetry delivers it at minimal sum-rate cost." This is an independent value proposition.
3. **Near-future higher-EIRP deployments**: as mmWave evolves toward 6G and as multi-operator cumulative caps get stricter (Italy 2023 debate, etc.), the binding regime expands. Paper is positioned for this.
4. **Near-field cases**: small cells, indoor APs, UEs in dense venues — these cases DO bind even at ICNIRP. The paper's method extends there via the coherent formalism.

**The hero figure**: a CDF of "percentage of plaza configurations where the Brussels cap binds under X" where X ∈ {MRT, classical ZF, ZF-dosimetry worst-case, ZF-dosimetry pose-NN}. If this figure shows baseline MRT violating 10–30% and our method violating 0%, the paper is not moot. If it shows baseline MRT violating 0.1%, the paper needs to lean on (2) — chronic dose reduction — as the primary value prop.

I'd suggest you run a quick AEGIS check on the plaza scenario before we settle the framing. Does the Brussels cap bind at 26 GHz for the intended geometry?

---

# *What I commit to, now, cleanly*

1. **Formalism is coherent**. $\mathbf{Q}^{(u)} = \mathbf{J}^T \mathbf{M}^{(u)} \mathbf{J}$, Part III + `system_formalism`. No retreat to rank-one.
2. **Rank-few is an empirical regime observation**, shown as one plot in §VI. Not a theoretical simplification.
3. **Budgeted (not nulled) beamforming**. Multi-body QCQP with per-body BR caps. Classical ZF is a degenerate case.
4. **Cauchy bound for pose-agnostic worst case**. Scalar, applies to all ranks. Part 1's framework supplies it.
5. **Pose-conditioned $\sigma(\theta)$** for cooperating bodies via IMU + small NN on AEGIS training data. Simple supervised regression.
6. **ISAC = presence + angular localization via RCS**. Not vital signs. Respiration moved to future work.
7. **Regulatory story is two-pronged**: ICNIRP BR-compliance (industry-standards story) + proposed statutory extension (jurisdictional story). Brussels isn't automatically onboard.
8. **DL compliance matters via the hero figure + chronic exposure argument**. If the figure doesn't materialise under AEGIS simulation, we pivot to a tighter jurisdiction (Italy historical 6 V/m, if still relevant) or a near-field scenario.
9. **q_complement** is a theoretical aside. Keeps its beauty; not load-bearing.
10. **Brussels arrêté averaging**: 6-min time-average, not instantaneous. Verify before publication.

---

# *Two agent prompts — committed as files*

I've written two prompts for you to dispatch to another agent. They're in `JSAC/agent_prompts/`:

- `01_bystander_detection_alternatives.md` — what replaces vital-signs ISAC for bystander detection at plaza range
- `02_brussels_arrete_and_BR_audit_practice.md` — Brussels legal text + real-world regulatory practice on BR-based audit

Each is a self-contained prompt, PoC-style (not finished), telling an agent what's the question and what's the minimum viable answer. Feel free to modify before dispatch.

---

# *Plan from here*

I start the tex now. Scope for this pass:

- §I Intro — deployment hook (Brussels + chronic dose + near-future trends) + paper thesis. Mostly structural, numeric claims remain placeholders pending your AEGIS check.
- §II Setup — coherent dosimetry framework, per-body $\mathbf{Q}^{(u)}$, path-space factorisation, plaza assumptions, Cauchy.
- §III Multi-body exposure-constrained precoding — the QCQP, closed-form, classical ZF as degenerate case.
- §IV Pose-conditioned ACS — scalar $\sigma(\theta)$, NN, Cauchy bound.
- §V DT-in-the-loop architecture — data flow, cadence, tiered telemetry, BS-side RT.
- §VI Evaluation — structure + placeholders for numbers.
- §VII Regulatory discussion — two-pronged.
- §VIII Conclusion + future work.

IEEEtran double-column, targeting 13 pages. Placeholders everywhere experiments haven't been run. Math is fleshed out based on Parts I + III + `system_formalism`.

Relevant citations (from the search): Selles-Valls et al. 2023 "26 GHz Multi-Beam Comms Testbed for Vital Signs" (arXiv 2311.11275); anon. 2025 "Vital Signs Monitoring with mmWave OFDM JCAS" (arXiv 2509.11767); Mercuri et al. 2019 *Nat Electron* "Vital-sign monitoring of multiple people"; 2024 review in *ACM TOSN* on non-intrusive human vital-sign detection using mmWave; Adib & Katabi SIGCOMM 2013 through-wall mmVital.

## B. Reference level vs basic restriction — big finding, major reframing

**ICNIRP 2020 explicitly permits compliance demonstration via basic restriction alone.** From the ICNIRP differences page: *"an exposure is taken to be compliant with the guidelines if it is shown to be below either the relevant basic restrictions or the relevant reference levels."* Either/or. Not both. And in reactive-near-field / non-plane-wave scenarios, ICNIRP 2020 *mandates* BR-based assessment — reference levels *cannot* be used.

This is a dramatic strengthening of the paper's regulatory argument. The paper does not have to petition for a new audit protocol. **It is already the audit protocol that ICNIRP 2020 permits.** IEC/IEEE 62232:2022 and ITU-T K.122 operationalize this "BR-based assessment" — they are the standards the paper should cite as the protocol-level precedent.

**Cascading implications:**

1. **The paper's policy story is watertight, not speculative.** "Our body-centric twin satisfies the ICNIRP basic restriction, which ICNIRP 2020 explicitly accepts as sufficient for compliance regardless of reference-level status (ICNIRP 2020, Health Physics 118:483–524; ICNIRP 'Use of the EMF Guidelines'; IEC/IEEE 62232:2022)."
2. **The Brussels / Italy argument becomes cleaner.** National authorities that enforce reference-level caps only (Brussels, Italy) are *over-enforcing* the ICNIRP framework they derive from. A BR-based audit would satisfy the underlying ICNIRP basic restriction without necessarily clearing the national RL. This is a political/legal point, but it's a mild one: jurisdictional law may still require RL compliance even when ICNIRP would accept BR. The paper should acknowledge this carefully.
3. **We should cite IEC/IEEE 62232:2022 and ITU-T K.122.** These are the standards the RAN OEMs already follow for compliance assessment. The paper slots into an existing standards conversation, not a new one.

**Factual corrections I need to make to what I wrote earlier:**

- Brussels 14.57 V/m outdoor is a **reference level, 6-minute time-averaged** (following ICNIRP/1999/519/EC averaging). *Not instantaneous.* I had written "not 30-min averaged … every second" in round 2 based on your description; agent says it is averaged over 6 min. You should verify against the *arrêté* text directly before a paper claim, but the most likely reality is 6-min averaging.
- **Italy** changed the 6 V/m attention value to **15 V/m** under a 2023/2024 decree-law, averaged over 24-hour median rather than 6-min. So "Italy 6 V/m" may be outdated. Verify current Italian status before citation.
- The 6-min averaging is still much stricter than ICNIRP 2020's own limits (30-min averaging for WB-SAR at these frequencies) and is more stringent than the Brussels original 2007 ordinance. So Brussels is tighter than ICNIRP, but not "every-second tight."

**What this changes in the paper:**

- The "every-second" compliance is not the actual Brussels requirement. The paper should say: "Brussels 14.57 V/m (6-minute averaged) is 10–30× tighter than ICNIRP 2020 RLs and tighter than national transpositions in most EU jurisdictions." No claim of instantaneous.
- The 6-min averaging window is actually *useful to exploit*. Across a 6-min window, the BS can allocate per-body exposure budget dynamically — high-compute periods with exposure, coasting periods without. This is exactly Zhou 2026's Lyapunov-virtual-queue pattern applied to reference-level compliance. **You do need to differentiate from Zhou more carefully here**: either we make a strictly-stricter "per-slot compliance" claim (safer for the regulator, closer to "BR everywhere always"), or we use the 6-min budget allocation and then it looks more like Zhou. I lean toward the "strictly stricter per-slot compliance" framing — it reads better to the regulator and differentiates from Zhou's time-averaging.
- **The Italian 15 V/m update weakens the "Italy is tight" talking point.** Adjust accordingly. The deployment-blocker hook is still valid via Brussels, Geneva (historical), and activist-driven movements, but the hard numeric case against 6 V/m is no longer current for Italy.

## C. What these findings mean for the tex-file plan

Two adjustments and one strengthening:

1. **ISAC section is shorter.** Position + presence detection via monostatic RCS, no vital signs in the main story. Q_complement stays as a theoretical aside.
2. **Regulator section is stronger.** Lead with ICNIRP 2020's explicit permission for BR-based compliance. Cite IEC/IEEE 62232:2022 and ITU-T K.122 as operationalizing standards. Position the paper as an *instance* of BR-based compliance, not a new protocol.
3. **Brussels facts need verification.** 14.57 V/m = reference level, 6-min averaged, cumulative across operators. The instantaneous claim is retracted. I recommend you fetch the Brussels *arrêté* text directly (environnement.brussels has the French version) before we lock anything into the paper.

## D. Now am I ready to write tex? Almost.

**Blocked on:**
- Your answer on GPU AEGIS and 50-body benchmark timing (for §VI real-time-in-silico feasibility).
- Confirmation of Brussels 14.57 V/m averaging window (from the *arrêté*).
- Whether you want to verify rank-few $\mathbf{Q}^{(u)}$ on thelonious, or whether we assume rank 3–5 and flag the assumption.

**Not blocked on:** the theory. I can write §II–IV (setup, ZF-dosimetry / budgeted-beamforming formulation, pose-conditioned ACS definition and Cauchy bound) today without any further info. Those sections are math you already have in Part 1 and `exposure_null_precoding.tex`, re-organized around the rank-few plaza picture.

I'd suggest: **I write the tex now for §II–IV** (setup, physics-reduction, precoder formulation, pose-conditioned ACS, Cauchy worst case). That's 3–4 pages of tightly-argued theory. §V (DT architecture) and §VI (experiment) remain in pseudocode pending your answers. §VII (regulation) waits for the Brussels *arrêté* verification. §I intro also waits because it depends on numeric claims we haven't confirmed.

If you say "go," I start the tex now with that scope. If you want to argue any of the above first, say so. My confidence in the current plan is reasonable-not-high: the ISAC correction is genuinely a simplification (good); the regulatory correction is genuinely a strengthening (good); the "rank few" claim is the only one I'm still wobbling on, and it's a running-an-experiment question, not a thinking question.
