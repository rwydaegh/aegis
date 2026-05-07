# Agent prompt — bystander detection alternatives at plaza range

*PoC, not a finished spec. This is the question I need informed by the literature. It affects §V of the JSAC paper (DT-in-the-loop architecture) and whether the paper's closed loop is plausible or hand-waved.*

## Context (what you need to know)

A JSAC paper in draft proposes **ZF-dosimetry**: a downlink mmWave precoder that nulls (or budgets) absorbed power on bodies in the coverage cell, *including bystanders who are not served users*. To do this, the base station's digital twin needs a list of bodies in the cell — positions at minimum, poses if possible. The paper's target scenario is a ~50 m plaza at 26 GHz with an 8×8 BS panel, 55 dBm EIRP, ~50 bodies of which ~25 are served users.

**Served users and cooperating phones** (phone on, UL-registered, MNO app permission) already report body-position and IMU-derived pose via uplink; for these, the DT has pose telemetry natively.

**The open question** is **bystanders** — bodies whose phone is off / in airplane mode, or who carry no phone. Round-2 proposed using **mmWave vital-signs ISAC** (respiration micro-Doppler on the BS's own aperture) for this. A search I ran came back with "every reliable demonstration is indoor, ≤ 5–10 m; heartbeat < 3 m in every paper; no outdoor 20+ m demonstration exists." So vital-signs is not defensible at plaza range. I need the **non-vital-signs replacement**.

## The minimum-viable answer

A ranked list of bystander-detection-and-localization approaches that are **defensible at 50 m outdoor, 26 GHz**, using the BS's own 8×8 panel (or a very modest auxiliary sensor if forced). For each candidate, report:

- **Technique** (one sentence): what signal / what processing / what hardware.
- **Range / resolution**: typical published numbers in outdoor-like or plaza-like settings.
- **Reliance on uplink**: does it need the target to transmit anything? (Our problem is precisely that they don't.)
- **Key paper** (1–2): pick the most defensible recent reference with numbers.
- **Paper-relevance score** (1–5): how well does this fit as a §V building block for a "BS knows where bystanders are" claim? Down-score anything that needs a camera in public space (privacy / deployment friction), an aux radar (hardware story), or a cooperating UE (defeats the purpose for bystanders).

## Candidates worth looking at (non-exhaustive, don't constrain yourself)

- **Static body RCS monostatic detection** on the BS's own 8×8 aperture. Human RCS ~1 m² at 26 GHz. Range and angular resolution at 50 m?
- **Micro-Doppler of body sway + walking gait** (not respiration — broader-band, stronger returns). Any published outdoor plaza demos at 24–77 GHz?
- **UL CSI perturbation from known transmitters** — if any consenting phone in the cell is transmitting an UL pilot, a bystander blocking or scattering it perturbs the measured CSI. Can the BS infer bystander presence/location this way?
- **Passive bistatic radar on ambient cellular signals** (FM, TV, other cells). A whole subfield.
- **RIS-assisted sensing** if a reconfigurable intelligent surface is in the scene.
- **Camera-based (YOLO, multi-view) from a colocated RGB sensor on the BS** — note privacy caveat. 
- **Acoustic presence** (footsteps) — dismiss quickly unless there is a real use case.
- **Regulator-supplied occupancy envelope** — not detection at all, but a worst-case assumption of "body could be anywhere in the public region of the cell." This is the fallback; the question is whether any of the above replaces or supplements it.

## What I do NOT need

- Vital-signs literature (already ruled out at plaza range).
- UWB indoor localization (range mismatch).
- Discussions of privacy law (I handle that separately).
- More than ~6 candidates, ranked. If fewer are defensible, say so.

## Output format

Single markdown, ≤ 1200 words. Table or bullets, your choice. Conclude with a **one-paragraph recommendation** on what the paper's §V should commit to for bystander detection, given the range constraint. If the answer is "use a fallback occupancy envelope and don't claim bystander detection at all," say that plainly.

## Why this matters

The alternative is that the paper's closed loop has a gap for tier-C/D bodies (airplane-mode / no-phone). If ISAC doesn't work and nothing replaces it, the paper should either (a) pivot to an *indoor or small-cell* scenario where ISAC is real, or (b) retreat to a pure occupancy-envelope fallback and honestly say that bystander-specific nulling applies only when occupancy is declared. I want to know which.
