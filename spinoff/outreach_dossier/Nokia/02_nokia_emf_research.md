# Nokia's EMF research ecosystem

Nokia's EMF research runs through two distinct clusters, both feeding Grangeat.
Understanding the structure lets Robin talk to the *right* Nokia problem
depending on how the call goes.

## Cluster 1 — Nokia Poland (Bell Labs Wroclaw / Warsaw): channel modelling and per-beam exposure physics

**Core researchers:** Kamil Bechta (5G Senior Radio Research Engineer), Marcin
Rybakowski. External academic collaborator: Pawel Kabacik (Wroclaw University
of Science and Technology).

**Research question:** given the beamforming algorithm, the antenna array, the
channel model, and the traffic distribution, what is the *actual* time-averaged
EIRP or absorbed power density, and how much lower than the theoretical max?
Everything they publish serves the F_PR (power reduction factor) number that
feeds into IEC 62232 Annex C.

**Key papers (Grangeat co-authored):**

| Year | Title | Journal / venue | Headline number |
|---|---|---|---|
| 2018 | A Statistical Approach for RF Exposure Compliance Boundary Assessment in Massive MIMO Systems | WSA Bochum (arXiv 1801.08351) | Compliance distance reduces by ~50% vs traditional method |
| 2023 | Impact of Beamforming Algorithms on the Actual RF EMF Exposure from Massive MIMO Base Stations | IEEE Access | 95th percentile of per-beam transmitted power = 7-22% of theoretical max, across grid-of-beams, eigen-beamforming, zero-forcing |
| 2024 | Statistical Analysis of the Actual RF Exposure from Massive MIMO Base Stations Serving Moving User Equipment | IEEE (Sept 2024, DOI 10.1109/... 10693600) | Moving UE gives −1.5 to −3.5 dB additional PRF headroom vs static UE |
| 2024 | Evaluation of the Actual EMF Exposure from Extreme Massive MIMO Base Stations Around 10 GHz Using Channel Modelling | 2024 (unclear venue) | FR3 (7-15 GHz), arrays from 192 to 796 antenna elements, aimed at 6G |

**The 2018 paper is foundational.** Baracca, Weber, Wild, Grangeat — this is a
seed paper for the actual-maximum approach that later became Clause 6.2.3 of
IEC 62232. Baracca has since moved between Nokia/Ericsson ecosystems, but the
key point is Grangeat has been publishing on this since 2018 and drove it
through the committee.

**Earlier Nokia work in the same lineage:** Bechta's 2017 URSI paper "Impact
of Effective Antenna Pattern on Radio Frequency EMF Exposure" (Poland-language,
Bechta 2020 URSI GA presentation). Establishes that per-beam patterns dominate
per-element patterns in the exposure integral.

## Cluster 2 — Nokia France (Bell Labs Paris-Saclay): RRM, MAC scheduling, EIRP control

**Core researchers:** Lorenzo Maggi, Silvio Mandelli, Alois Herzog, Azra
Zejnilagic, Bill Zheng.

**Research question:** given a target actual-EIRP threshold that the network
operator has to stay below, how does the base station *actually operate* to
satisfy it while preserving throughput, fairness, and QoS? This is the
implementation side of the standard.

**Key papers (Grangeat co-authored):**

| Year | Title | Venue | Approach |
|---|---|---|---|
| 2024 | Smooth Actual EIRP Control for EMF Compliance with Minimum Traffic Guarantees | arXiv 2404.06624 | Drift-Plus-Penalty control theory, exact + conservative algorithms with linear + constant complexity for the "EIRP budget" |
| 2024 | EMF Exposure Mitigation via MAC Scheduling | arXiv 2404.06830 | Water-filling power allocation at MAC scheduler level, throughput fairness preserved, positioned for 5G and 6G |

**The two papers converge on a common finding:** setting the actual EIRP
threshold at ~4× below the theoretical maximum (i.e. −6 dB, corresponding to
F_PR ≈ 0.25) has minimal impact on end-user performance under realistic
traffic. This is exactly the F_PR value that IEC 62232:2022 defaults to.

## Why the split matters for the call

Grangeat is the only Nokia author who co-authors with both clusters. So the
conversation can pivot to whichever side is more productive:

- **If he leans channel-modelling** ("we can't defend our F_PR at FR3 yet"), then
  AEGIS's speed advantage on channel-modelling per-scene evaluation is the pitch.
  A body-aware, scene-aware, fast forward model lets Nokia extend the 2023-2024
  Poland Bell Labs studies to arbitrary deployment scenarios, arbitrary body
  models, arbitrary FR3 codebooks — millions of Monte Carlo runs where FDTD
  can do dozens.
- **If he leans control-side** ("the operational headroom is fine, the problem
  is proving it to regulators"), then AEGIS's certificate framing (uncertainty-
  axis, tissue-permittivity bounds) is the pitch. See point 2 in
  `../../differentiability/SYNTHESIS.md` — the axis IEC 62232 and ISO GUM
  *legally require you to report* is uncertainty, not configuration.

## Nokia FCC filings (product-side compliance)

**FCC ID 2AD8UAWKUCD01** — Nokia 5G RF Exposure Compliance Report on the FCC
report portal. This is the compliance dossier for a Nokia mmW device. Not
Grangeat's work directly but it tells Robin what the *submitted* compliance
methodology looks like at Nokia. WebFetch returned binary; not fully extracted.
Worth reading manually if the call goes deep on FCC-side compliance.

## The competitive/adjacent view — Physics-Informed ML

A parallel wave of physics-informed ML surrogate approaches is arriving in
this space:

- **Bilson, Loh, Heliot, Thompson (NPL, Surrey) 2024** — "Physics-Informed
  Machine Learning Modelling of RF-EMF Exposure in Massive MIMO Systems," IEEE
  Access. Gradient-boosted decision trees, R² = 0.86 on 10-fold cross-validated
  data.
- **Phy2-ExposNet (arXiv 2605.03207)** — physics-informed neural network for
  EMF exposure mapping in complex urban environments.

Neither is closed-form. Both are data-hungry, and their R² is not spectacular.
This is the *background wave* AEGIS's closed-form differentiable approach is
distinct from — a talking point if Grangeat asks "isn't ML solving this
already?" Answer: ML surrogates need training data, and generating training
data still requires FDTD or measurements. AEGIS is upstream of the ML
approach — it can *generate* the training data faster than FDTD, or replace
the ML surrogate entirely with a physically-derived closed form.

## What Nokia does NOT seem to publish publicly

- No Nokia patents I could surface on the actual-maximum control feature
  itself (the algorithm inside the base station that enforces F_PR). The
  US 12395250 patent I checked on "EMF strength control method" was
  inaccessible (WebFetch 403). Worth searching Google Patents for
  `assignee:Nokia RF exposure EIRP` if this thread matters.
- No Nokia whitepapers on fast forward modelling for pre-compliance. The
  category is empty at Nokia. AEGIS's positioning is not competing against
  a Nokia internal tool.
- No Nokia public position on differentiable / gradient-based EMF forward
  modelling. This is white space for Grangeat's committee.

## Talking points from this cluster analysis

1. Grangeat has been publishing on actual-max since 2018. If Robin references
   the 2018 statistical paper by name ("the Bochum WSA statistical approach
   piece"), Grangeat will notice.
2. The 2024 moving-UE paper is Grangeat's most recent Poland-cluster result.
   Reference *specifically* the −1.5 to −3.5 dB additional headroom finding
   and ask where FR3 will land.
3. The MAC-scheduling papers are Nokia's implementation answer. If Robin frames
   AEGIS as "the piece that lets you *choose* the threshold rigorously rather
   than defaulting to F_PR = 0.25," that connects to the Maggi/Mandelli line.
4. Kamil Bechta and Marcin Rybakowski are named intros to ask about after
   Grangeat. They are the Poland channel-modelling side.
5. Lorenzo Maggi is the France Bell Labs intro — Paris-Saclay, adjacent to
   Wiart's Télécom Paris circle Robin is already reaching into.
