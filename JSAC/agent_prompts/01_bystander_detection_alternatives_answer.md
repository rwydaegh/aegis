# Bystander detection at plaza range — non-vital-signs candidates

*Answer to `01_bystander_detection_alternatives.md`. Scope: 26 GHz, ~50 m outdoor, 8×8 BS panel, detection of bodies whose phones are off / absent. Scored for §V of the JSAC paper.*

## Quick numbers to anchor the discussion

An 8×8 at 26 GHz has a half-power beamwidth of roughly λ/D ≈ 1/8 rad ≈ 7°. At 50 m that is a **~6 m crossrange cell**. Human RCS at 26 GHz is in the 0 to −10 dBsm band (Marchetti et al.; Chen et al. RCS at 26/79 GHz). With 55 dBm EIRP, 400 MHz NR FR2 waveform, and CPI integration of a few hundred ms, the monostatic link budget closes for **presence detection** but not for sub-meter localization. Keep this mismatch in mind — it is what forces most of the ranking below.

## Ranked candidates

### 1. Monostatic wide-band detection on the BS's own 8×8 — **3/5**
- **Technique.** Transmit the scheduled NR DL waveform (SSB/CSI-RS or dedicated sensing symbols), take the reflected path on the same panel, range-Doppler process.
- **Range / resolution.** Range detection of a 0 dBsm pedestrian at 50–70 m is consistent with the radar equation and with published pedestrian-radar demos. Range resolution c/2B ≈ 0.375 m at 400 MHz. Angular resolution is the killer: ~6 m crossrange with 8×8. Panel density would need to roughly quadruple (32×32) to hit body-scale localization at 50 m.
- **Reliance on uplink.** None. This is what makes it attractive for bystanders.
- **Key paper.** Ericsson's 2024 NR-DL bistatic trial reported 99.7% human-zone detection and single-person tracking at 12.7 cm / 18.2 cm (75/95 percentile) — but indoors, with multi-panel geometry. (Ericsson Research blog, 2024.) For outdoor plaza-scale, there is *no* peer-reviewed demonstration at 50 m with an 8×8-class aperture that I could find.
- **Score rationale.** 3/5: you can honestly claim "BS sees that a body is out there in range cell X and bearing sector Y" within a 0.4 m range × 6 m crossrange × tens of cm/s Doppler cell. That is enough to **count** bystanders and place them in sectors, not enough to **null** them.

### 2. Walking-gait and body-sway micro-Doppler (monostatic, same panel) — **3/5**
- **Technique.** Same hardware as #1 but exploit torso/limb micro-Doppler rather than static RCS. Gait returns are broader-band than respiration and stronger than static RCS against clutter because they sit off-zero-Doppler.
- **Range / resolution.** Gait-MD at 77 GHz has been validated for multi-person ID up to ~10–15 m indoors at ~88% accuracy (MGait, MCGait). I found no 50 m outdoor demonstration at 24–28 GHz.
- **Reliance on uplink.** None.
- **Key paper.** Passive Multi-user Gait Identification via micro-Doppler Calibration (MCGait), 77 GHz FMCW, 2023.
- **Score rationale.** 3/5: useful as a confirmatory layer on top of #1 (moving-body confirmation, clutter rejection, rough count). Not a standalone bystander locator at 50 m. The literature gap is large — any strong claim here would be speculation.

### 3. Passive bistatic radar on neighbour-cell or broadcast illuminators — **2/5**
- **Technique.** Treat the serving BS as the receiver, use a second cell's DL or an FM/DVB-T transmitter as the illuminator, cross-correlate to extract range-Doppler of targets in the common footprint.
- **Range / resolution.** LTE-based passive bistatic radar has demonstrated detection of cars, motorbikes, and human bodies at kilometre-scale ranges (Salah 2014; Abdullah 2016). 5G-SSB passive radar has been shown against vehicles (Pisciottano et al. 2023). Human-body outdoor detection specifically at 50 m with a modern 5G illuminator is lightly documented.
- **Reliance on uplink.** None on the bystander; requires a second cooperating illuminator in the scene.
- **Key paper.** LTE-based passive radars: a review, Int. J. Remote Sensing, 2021 (Abdullah et al.).
- **Score rationale.** 2/5. Gives you large-area surveillance but at the cost of a second-illuminator geometry story the paper does not want. Range resolution is poor (LTE ~1.4 MHz useful, 5G SSB limited to synchronization bandwidth) and the usable Doppler for a stationary pedestrian is weak.

### 4. UL-CSI perturbation from consenting phones — **2/5**
- **Technique.** When a served UE is transmitting UL pilots, a nearby bystander body perturbs the multipath, shifting delay/angle components of the measured CSI. Infer presence and rough location from CSI deviation relative to a clean channel model.
- **Range / resolution.** Wi-Fi-analog device-free localization is well established indoors. Recent 5G NR CSI device-free work reports RMSE ~3.45 m in outdoor blockage scenarios (ADP-ViT, 2024).
- **Reliance on uplink.** The *bystander* does not transmit, but detection requires at least one consenting UE transmitting UL pilots near the bystander — coverage is coupled to served-user density.
- **Key paper.** Device-free localization via UL CSI with 5G NR, attention-based ADP, 2024.
- **Score rationale.** 2/5. Attractive because it rides on the existing served-user channel that the DT already uses. But 3 m outdoor RMSE is coarser than the #1 coarse beam, and coverage holes open wherever no consenting UE is nearby — i.e. exactly the bystander-heavy corners of the cell.

### 5. RIS-assisted sensing — **2/5**
- **Technique.** A passive reconfigurable surface in the scene provides a second view angle; the BS switches RIS phase profiles and reads the composite channel to localize scatterers.
- **Range / resolution.** Simulation-heavy literature; outdoor human-localization demonstrations are rare. Drone-detection RIS studies exist (He et al. 2024) but at dB-link not body-precision scales.
- **Reliance on uplink.** None.
- **Key paper.** RIS-Augmented mmWave MIMO for Passive Drone Detection, 2024 (arXiv 2402.07259).
- **Score rationale.** 2/5. Mostly a paper-in-a-paper: pulling in RIS drags the model-complexity and deployment story away from the JSAC narrative. Reserve as a "future work" bullet.

### 6. Colocated RGB camera on the BS — **4/5 technical, 1/5 deployability**
- **Technique.** One or two colocated cameras + YOLO-class detector + mmWave-camera calibration. Solves the localization problem outright.
- **Range / resolution.** Routinely ≤0.3 m at 50 m for pedestrian bounding boxes in daylight.
- **Reliance on uplink.** None.
- **Score rationale.** Technically the best match. But: public-space cameras at every cell are a regulatory and social non-starter in EU jurisdictions and the paper positioning explicitly wants to *avoid* privacy-sensitive sensors. Keep as a footnote ("an RGB camera trivially closes this gap in jurisdictions where it is permitted").

### Dismissed
- **Acoustic footsteps.** Not defensible at 50 m in a plaza.
- **Vital-signs mmWave ISAC.** Ruled out by the prompt.

## Recommendation for §V

The honest story is that **none of the non-camera options localize bystanders to body scale at 50 m with an 8×8 aperture**. Monostatic detection on the BS gives presence + sector + range, not null-steering-grade coordinates. I would commit §V to a **two-tier fallback**:

1. **Tier-A / B (served or consenting UE):** precise pose from phone-side SLAM/IMU as already drafted.
2. **Tier-C / D (bystanders):** per-sector **occupancy envelope** — the DT partitions the public region of the cell into ~6 m × 0.4 m range-bearing cells matching the 8×8 beamwidth, declares each cell either "occupied" or "free" using monostatic detection on the BS panel (walkers confirmed by gait-MD), and budgets the coverage precoder against a worst-case body location within every occupied cell. This is dosimetrically conservative, defensible in the worst case, and — crucially — relies only on sensing modalities that the 26 GHz 8×8 can actually deliver.

If §V wants to claim anything stronger than "envelope nulling" against bystanders (e.g. zero-forcing a specific bystander body), the paper should either (a) scale the aperture to 32×32 or (b) pivot to an indoor / small-cell scenario where ISAC bystander localization has actual published precedent. Anything in between is hand-waving.

## Sources

- [Measurement-based characterization of ISAC channels with distributed mmWave beamforming and human body scattering (2024)](https://arxiv.org/html/2411.01254)
- [mmHSense: Multi-modal mmWave ISAC Datasets for Human Sensing (2025)](https://arxiv.org/html/2509.21396v1)
- [ISAC: Integrated Sensing and Communication — Ericsson Research blog](https://www.ericsson.com/en/blog/2024/6/integrated-sensing-and-communication)
- [High-resolution mmWave automotive radar (Nature Scientific Reports, 2023)](https://www.nature.com/articles/s41598-023-30406-4)
- [RCS measurements for vehicles and pedestrians at 26 and 79 GHz](https://www.researchgate.net/publication/261025183_RCS_Measurements_for_Vehicles_and_Pedestrian_at_26_and_79GHz)
- [RCS of pedestrians in the low-THz band (IET Radar, Sonar & Navigation, 2018)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/iet-rsn.2018.5016)
- [Passive multi-user gait identification via micro-Doppler calibration (MCGait), 77 GHz](https://www.researchgate.net/publication/373748855_Passive_Multi-user_Gait_Identification_through_micro-Doppler_Calibration_using_mmWave_Radar)
- [mmWave Wi-Fi gait-based person identification (arXiv 2510.08160, 2025)](https://arxiv.org/html/2510.08160v1)
- [LTE-based passive radars: a review (Int. J. Remote Sensing, 2021)](https://www.tandfonline.com/doi/full/10.1080/01431161.2021.1959669)
- [5G network-based passive radar (2022)](https://www.researchgate.net/publication/357287822_5G_Network-Based_Passive_Radar)
- [SSB-based passive radar signal processing for 5G (2023)](https://www.researchgate.net/publication/369606175_SSB-Based_Signal_Processing_for_Passive_Radar_Using_a_5G_Network)
- [RIS-augmented mmWave MIMO for passive drone detection (arXiv 2402.07259, 2024)](https://arxiv.org/html/2402.07259)
- [RIS with integrated sensing capability (Nature Scientific Reports, 2021)](https://www.nature.com/articles/s41598-021-99722-x)
- [Localization with RIS: an active sensing approach (arXiv 2312.09002)](https://arxiv.org/html/2312.09002)
