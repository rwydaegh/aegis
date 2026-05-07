# Deployment realism for the transmit-to-path map

This note answers the practical question: if the JSAC paper says the network
can compute a dosimetric precoder, how does the real network know the
transmit-to-path map `B` and the relevant arrival directions?

The short answer is:

Real deployment should not claim exact ray-level $B$ for everyone.  It should
claim a beam/sector-level $B$ from existing beam-management and SRS
measurements, then wrap the uncertainty in robust exposure envelopes.

Ray tracing is useful as a prior and as an in-silico oracle, but it should not
be sold as the thing commercial base stations must run perfectly in real time.

## 1. What `B` is in deployment language

The mathematical object is

$$
Q_u(\xi_u) = B_u^H M_u(\xi_u) B_u .
$$

`M_u` says how a set of incident paths would couple into body `u`.
`B_u` says how the network's controllable transmit variables excite those
paths.

There are three abstraction levels:

$$
\text{element-level:}\qquad
(B_u)_{n m} = \alpha_n a_m(\Omega^{\mathrm{AoD}}_n).
$$

$$
\text{beam-level:}\qquad
(B_u)_{n b} = \alpha_n g_b(\Omega_n).
$$

$$
\text{ray-tracer special case:}\qquad
B_u = J_u,\quad (J_u)_{n m}=1\{j_u(n)=m\}.
$$

For a commercial story, beam-level `B` is the safest primary object.  It maps
beam or codebook weights to angular sectors.  Element-level `B` is realistic
for O-RAN, testbeds, and fully digital arrays.  Binary `J` is mostly a
simulation bookkeeping object.

## 2. Served users: plausible pipeline

For served users, a realistic closed loop can be built from measurements that
already exist in 5G NR FR2.

### 2.1 Downlink beam reports

The gNB sweeps SSB or CSI-RS resources.  The UE reports beam/resource indices
and L1-RSRP-type quantities, for example CRI-RSRP or SSB-index-RSRP.  This
does not expose raw UE per-element IQ.  It gives a ranked set of transmit
beams and received powers.

For dosimetry, this is enough to define a coarse angular support:

$$
\Omega_{u}^{\mathrm{DL}}
= \bigcup_{\text{reported beams }b}
\operatorname{supp}(g_b)
$$

and a beam-level transmit-to-path map:

$$
(B_u)_{n b} \approx \alpha_n g_b(\Omega_n),
\qquad \Omega_n\in\Omega_u^{\mathrm{DL}} .
$$

This is not exact geometric CSI.  It is a measured beam-sector posterior.
The correct safety move is to compute exposure envelopes over the sector.

### 2.2 Uplink SRS at the base station

In TDD systems, the gNB receives uplink SRS and estimates the uplink channel
across its antenna array.  With calibration and reciprocity, this supports
downlink beamforming.  Longer-term dominant directions can also be estimated
from uplink channel statistics.

For the paper, the credible claim is:

SRS gives the gNB a BS-side angular support and complex channel.

Not:

SRS gives exact body-surface ray data.

A reasonable estimator outputs

$$
\widehat{\mathcal P}_u =
\{(\widehat\Omega^{\mathrm{AoD}}_\ell,
   \widehat\tau_\ell,
   \widehat\alpha_\ell,
   \widehat{\mathrm{pol}}_\ell)\}_{\ell=1}^{L_u}
$$

or, more defensibly, an angular-delay covariance rather than individual rays.
Then `B_u` is built from the calibrated gNB array response.

### 2.3 UE IMU and body pose

The UE contributes the part commercial beam management is already moving
toward: sensor-assisted beam tracking.  Qualcomm publicly advertises
sensor-assisted, AI-based mmWave beam management in Snapdragon X75.

For AEGIS, the UE-side sensor loop should output:

$$
\widehat \xi_u(t)
= \text{NN}(\text{accelerometer},\text{gyroscope},\text{magnetometer},
            \text{beam reports},\text{proximity/grip})
$$

This gives phone attitude, coarse grip, and body-phone geometry.  Combined
with the measured beam-sector posterior, it converts "the UE reports beam b"
into "the user's body is exposed over this conservative set of incidence
directions."

The paper can therefore claim an OTA-style protocol extension:

$$
\text{UE reports }(\widehat \xi_u,\ \Sigma_{\xi,u},\ \text{beam/RSRP vector})
\text{ rather than raw RF samples.}
$$

## 3. Non-users: do not pretend they are equivalent to users

Non-users are the hard part.  They do not transmit SRS to this gNB, they do
not report beam measurements, and they may not consent to an exposure twin.

There are three realistic tiers.

### Tier A: cooperative-device non-users

The "non-user" is not served by this beam but still carries a device visible
to the operator federation or neutral coordinator.  Then the system can know:

- approximate position,
- coarse motion/pose from the device IMU,
- serving-beam or beam-report information from that device's own link.

This is the most defensible multi-operator DTN story.  The bystander is
anonymous to the serving BS but known as an exposure-relevant occupied body
to the coordinator.

### Tier B: sensed anonymous bystanders

The BS or cell infrastructure detects human occupancy using ISAC, radar-like
reflections, cameras, lidar, or external smart-city sensors.  This can provide
position, velocity, and coarse body class.

But a single 8x8 FR2 panel at plaza range should not be claimed to recover
precise individual pose or exact final AoA on each body.  Its angular
resolution is too coarse.  The safe claim is:

ISAC provides occupied sectors or body hypotheses, not exact $Q$.

Then the dosimetry layer uses an anonymous body envelope:

$$
\overline Q_{\mathrm{anon}}(\text{occupied sector})
\succeq Q(\xi,\Omega)
\quad
\forall \xi\in\Xi_{\mathrm{human}},\ \Omega\in\Omega_{\mathrm{sector}} .
$$

This is still useful.  It turns uncertain bystanders into robust constraints
without pretending to know their private pose.

### Tier C: unknown people

If a body is neither connected nor sensed, the DT does not know it.  Then the
only defensible safety layer is the traditional regulatory grid or
exclusion-zone constraint.  The paper should keep this layer explicitly:

$$
\tr(R_g W)\le L_g^{\mathrm{inc}}.
$$

That makes the system honest: body-twin constraints improve performance when
people are known or sensed, while grid constraints remain the fallback for
unknown public occupancy.

## 4. Is ray tracing required in deployments?

No.  It should be positioned as:

1. **Offline prior.** Builds the initial environment model, likely reflectors,
   and candidate angular-delay supports.
2. **Simulation oracle.** Provides ground truth for in-silico experiments.
3. **Bayesian regularizer.** Constrains the estimator when measurements are
   sparse.

It should not be positioned as:

The deployed BS runs perfect real-time RT and trusts it for safety.

The more realistic deployment loop is:

$$
\text{RT prior}
\quad+\quad
\text{beam/CSI/SRS measurements}
\quad+\quad
\text{UE IMU body state}
\quad\longrightarrow\quad
\text{robust B and Q envelopes}.
$$

The DT is therefore measurement-corrected, not a blind simulator.

## 5. What to simulate in the paper

In silico we can have oracle paths, but the "commercial-equipment" version
should deliberately degrade them before control.

Suggested experiment pipeline:

1. Generate oracle scene with ray tracer:

$$
\mathcal P_u^{\mathrm{oracle}},\quad B_u^{\mathrm{oracle}},\quad
Q_u^{\mathrm{oracle}}.
$$

2. Generate realistic observations:

$$
\text{UE beam RSRP vector},\quad
\text{gNB SRS channel estimate},\quad
\text{IMU pose trace},\quad
\text{optional anonymous occupancy sectors}.
$$

3. Reconstruct a deployment-grade estimate:

$$
\widehat B_u,\quad \widehat \Xi_u,\quad
\overline Q_u
$$

where `overline Q_u` is an envelope, not a point estimate.

4. Compute "ZF-dosimetry":

$$
\max_W U(W)
\quad
\text{s.t.}\quad
\tr(\overline Q_{u,i} W)\le L_{u,i},
\quad
\tr(R_g W)\le L_g.
$$

5. Evaluate safety on oracle truth:

$$
\tr(Q_{u,i}^{\mathrm{oracle}} W)
$$

and compare to:

- ZF,
- MRT or WMMSE,
- power backoff,
- oracle dosimetry,
- deployment-grade robust dosimetry.

The key plot is the gap between oracle dosimetry and deployment-grade robust
dosimetry.  If that gap is small enough, the OTA-update story becomes
credible.

## 6. How to phrase the paper claim

Strong but defensible:

Existing FR2 beam-management and SRS procedures already produce the
measurements needed to construct a beam-sector posterior for each served UE.
Adding a low-rate UE body-state report from inertial sensors lets the gNB
replace ZF by exposure-constrained ZF over a robust body envelope.  For
non-users, the same controller accepts anonymous occupancy envelopes when
available and falls back to incident-field grid constraints otherwise.

Too strong:

Commercial networks know the exact final AoA and full path-level exposure
operator for every user and bystander.

## 7. Useful citations and anchors

- 3GPP NR CSI reporting includes beam-management reports such as CRI,
  SSBRI, and L1-RSRP rather than raw per-element UE IQ.  See ETSI/3GPP
  TS 38.214 and TS 38.331.
- Qualcomm Snapdragon X75 publicly advertises sensor-assisted, AI-based
  mmWave beam management and a sensor-modem-RF solution for mmWave beam
  management.
- Ericsson's advanced antenna systems white paper states that channel
  knowledge is the enabler for massive-MIMO beamforming and that dominant
  directions can be obtained by averaging uplink channel-estimate statistics.
- Qualcomm's mmWave antenna-module placement white paper is the right
  hardware anchor for UE module geometry and analog beam codebooks.

Reference URLs:

- https://www.etsi.org/deliver/etsi_ts/138200_138299/138214/
- https://www.etsi.org/deliver/etsi_ts/138300_138399/138331/
- https://www.qualcomm.com/news/onq/2023/02/worlds-first-5g-advanced-ready-modem-rf-snapdragon-x75
- https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/5G-Whitepaper-mmWave_Antenna_Module_Placement-Qualcomm.pdf
- https://www.ericsson.com/en/reports-and-papers/white-papers/advanced-antenna-systems-for-5g-networks
