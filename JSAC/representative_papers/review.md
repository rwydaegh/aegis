# Representative papers — review and in-scope assessment

Companion to the 10 PDFs in this folder. Scopes each paper against the IEEE JSAC Special Issue "Digital Twins for Wireless Networks: Enabling Application-Aware and Closed-Loop Optimization" (submission deadline 1 May 2026).

## The SI's thesis, in one sentence

The editors want a paradigm flip: wireless networks are **not** the thing being twinned, they are the **substrate** that a digital twin sits on top of and uses to close a control loop in service of an application.

| | Old view (DT *of* the network) | New view this SI pushes (DTN) |
|---|---|---|
| What is twinned | RAN / base stations / cells | The physical world or application (robot, vehicle, XR user, body) |
| Goal | Monitor, analyze, plan | Use the twin to reconfigure the network in real time |
| Network's role | Object | Adaptive substrate |
| DT's role | Passive mirror | Intelligent agent in the control loop |

Naming trap: ITU-T Y.3090 defines "DTN" as the old view. This SI deliberately co-opts the acronym for the new view. Submissions should be explicit about which they mean.

## The two pillars

The topics section splits into two literal headings — two dimensions of the same paradigm, not two sub-calls. Strong papers hit both.

- **Closed-loop optimization** — the control machinery: twin-in-the-loop, RL/differentiable control, cross-layer feedback, stability, edge–cloud coordination, synchronization, security of the loop.
- **Application-aware design** — how the twin is shaped by what it serves: task/QoS semantics, dynamic DT creation/migration/evolution, intent-based APIs, per-app architectures, AV/XR/agriculture use cases, standardization.

## Paper-by-paper

### Closed-loop pillar

**1. Ndikumana, Nguyen, Cheriet — Digital Twin Backed Closed-Loops for Energy-Aware and Open RAN-based FWA Serving Rural Areas** — arXiv 2411.05664, Nov 2024 (Synchromedia Lab, ÉTS Québec)

Two nested closed loops over an O-RAN FWA network in rural areas: one at slice timescale for radio allocation, one intra-slice for energy-aware scheduling. RL + successive convex approximation. DT "replicates" the PT by absorbing past solutions into future states.

*In scope:* yes. Pure closed-loop. DT is still of the network, but framed around application-side QoS (remote healthcare, home gaming). Strong template for a control-loop paper.

**2. Zhang, Huang, Zhang, Zheng, Yang, You — Digital Twin-Enhanced Deep Reinforcement Learning for Resource Management in Network Slicing** — IEEE TCOM, Oct 2024

DT acts as a pre-verification simulator for a DRL slicing agent. Historical data + neural net gives DT state dynamics, DRL trains there and deploys to the real net. Distillation and offline-RL extensions.

*In scope:* moderately. DT is a training surrogate for policies. Exactly the pattern an exposure-surrogate would play for beam/power policy. Valuable as a template even though it is soft new-view.

**3. Zhang, Liu, Peng, Chen, Xu, Cui — D-REC: Digital Twin-Assisted Data-Driven Optimization for Reliable Edge Caching in Wireless Networks** — IEEE JSAC, Nov 2024 (editor paper: Liu, Chen)

"Vertical + horizontal twinning" to build a network DT, then constrained-MDP RL with *reliability intervention modules* as safeguards. Framed around AR/VR/AV content delivery.

*In scope:* yes, strongly. Closed-loop plus application-tiered. Structurally the single closest paper to what an exposure-compliant control paper would look like. Swap "reliability constraint" for "SAR/APD constraint" and it's essentially the template.

**4. Polese, Bonati, D'Oro, Johari, Villa, Velumani, Gangula, Tsampazi, Robinson, Gemmi, Lacava, Maxenti, Cheng, Melodia — Colosseum: The Open RAN Digital Twin** — IEEE OJCOMS, Sep 2024 (editor paper: Melodia)

Tutorial on Colosseum (largest HW-in-the-loop RF emulator) as O-RAN DT. RF channel emulator plus softwarized O-RAN/5G stacks plus twinning automation. Includes real-time DT–real-network bridges.

*In scope:* hybrid — mostly old-view, but foundational. DT *is* the network. Gets in because Melodia is an editor and Colosseum is the testbed anchor the rest of the field plugs into. Cite it; don't imitate its framing.

**5. Hoydis, Aït-Aoudia, Cammerer, Euchner, Nimier-David, ten Brink, Keller — Learning Radio Environments by Differentiable Ray Tracing** — IEEE TMLCN, Oct 2024 (NVIDIA + University of Stuttgart)

Gradient-based calibration of a ray tracer using channel measurements. Differentiable parametrizations of materials, scattering, antenna patterns. RT-as-computational-graph, parameters trained like NN weights.

*In scope:* as enabling tool, yes. Not a DT paper on its own, but the scope explicitly lists "differentiable control for self-optimizing DTNs", and this is the gradient machinery that makes that possible. An exposure surrogate wants to be this pattern — differentiable and gradient-trainable — rather than a black-box lookup.

### Application-aware pillar

**6. Aliyu, Oh, Oh, Kim — Digital Twin-Assisted In-Network and Edge Collaboration for Joint User Association, Task Offloading, and Resource Allocation in the Metaverse** — arXiv 2604.02938, Apr 2026 (Chonnam National University)

XR/metaverse with asymmetric UL/DL (2D up, 3D down). DT coordinates in-network computing plus MEC. Stackelberg Markov game to Nash-async RL for joint user-association, offloading, DL power.

*In scope:* yes, strongly. Both pillars: XR app-aware plus game-theoretic closed loop. Recent and high-profile, a center-of-mass paper.

**7. Yigit, Maglaras, Buchanan, Canberk, Shin, Duong — AI-Enhanced Digital Twin Framework for Cyber-Resilient 6G Internet of Vehicles Networks** — IEEE IoT Journal, Nov 2024 (editor paper: Canberk)

"Cyber twin layer" with stacked sparse autoencoders plus online learning for network-attack detection in IoV. Reduces latency, energy, RAM; improves packet delivery.

*In scope:* moderately. Application-aware (IoV), predictive analytics (attack detection), but the loop closes on security not on resource control. Fits the "predictive DT analytics for fault detection/resilience" bullet. Editor paper signals acceptance.

**8. Zhang, Fang, Chen, Liu — On Transferring, Merging, and Splitting Task-Oriented Network Digital Twins** — MSWIM 2025 (editor paper: Liu, Chen)

Unified Twin Transformation (UTT) framework: intra- and inter-DT operations for lightweight task-oriented twins. Apps: trajectory reconstruction, human localization, sensory data generation.

*In scope:* yes. Nails the CFP bullet "Dynamic creation, migration, and evolution of DTs across wireless domains". Light paper but precisely on target.

**9. Jiang, Du, Jiang, Han, Alhammadi, Debbah — Over-the-Air Federated Learning in Digital Twins Empowered UAV Swarms** — IEEE TWC, Nov 2024

Build the DT via over-the-air FL across a UAV swarm doing IIoT inspection. Heterogeneity-aware scheduling, energy budgets via virtual queue.

*In scope:* yes. Both pillars: UAV application plus privacy/energy-constrained federated twin construction. Good reference for how to frame constraint budgets — maps neatly to exposure budgets.

**10. Masaracchia, Nguyen, da Costa, Ak, Canberk, Sharma, Duong — Toward 6G-Enabled URLLCs: Digital Twin, Open RAN, and Semantic Communications** — IEEE Communications Standards Magazine, Mar 2025 (editor paper: Canberk)

Vision piece: DT + O-RAN + semantic comms as the three pillars for URLLC in 6G. Target: 1 ms E2E, 10⁻⁷ BER. Use cases: autonomous driving, industrial automation.

*In scope:* yes, strongly. The SI thesis in miniature. The clearest editor-voiced articulation of what the SI wants. A vision paper for this SI should rhyme structurally with this one.

## Two template picks for an exposure-aware submission

- **Research paper, control-loop style: mimic D-REC (#3).** Replace the "reliability intervention module" with an "SAR/APD intervention module"; replace their "network DT via vertical + horizontal twinning" with a "body-pose DT via FDTD-trained surrogate"; keep the constrained-MDP framing wholesale.
- **Vision/position paper: mimic Masaracchia/Canberk CSM'25 (#10).** Three pillars (DT, beamforming-capable RAN, exposure-aware control), one motivating application domain (e.g. mmWave FWA to users in close proximity), close with challenges. Editor-approved template.

## Where the niche is

None of the ten papers above, and none of the ~40 landscape papers identified earlier, combine **EMF exposure compliance** with **DT-driven closed-loop wireless control**. The twinned object in every reviewed paper is either (a) the network, or (b) an industrial/vehicular/XR application. No one twins the body, and no one treats SAR/APD as a first-class control objective alongside latency, energy, or QoE.

Adding differentiability on top (the Hoydis pattern applied to exposure rather than propagation) would put a submission on both pillars plus a technical-novelty hook nobody else has.
