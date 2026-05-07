# 02 — AMASS pose ingest

**Goal.** End up with a corpus of walk-cycle pose sequences, on the order of 50, expressed as SMPL-X parameters at 30 Hz, ready for the plaza scenario to consume one trace per body.

## Blockers

- **01 (SMPL-X seeding)** — you can't apply pose to SMPL-X if SMPL-X itself isn't loadable.

## Why this matters

The paper's hero scenario (paper §VII; `paper_spine.md` §5) puts 50 bodies in a Brussels plaza walking around for 5 minutes. For this to feel real, each body needs a plausible pose trajectory — not a static T-pose, not a synthesised gait, real human walking captured from mocap. AMASS is the field-standard corpus for SMPL-family pose data: ~40 hours of mocap, retargeted onto SMPL/SMPL-H/SMPL-X, distributed as `.npz` per sequence.

Once this brief is done, brief 08 (plaza_run) just picks N walking sequences, assigns one to each body, and steps through them at 30 Hz.

## What's already in place

- Nothing on disk. There is no AMASS data, no loader, no pose-stream concept.
- `src/aegis/geometry/parametric.py` (after 01 lands) can apply a SMPL-X pose vector to a body and return a posed mesh. That's the consumer-side API.
- The viewer's `AnimatedBody.tsx` plays GLB animations through Three.js — different problem, different code path. Don't try to share infrastructure with it.

## Where AMASS lives

- Project page: `https://amass.is.tue.mpg.de/`. Same registration / EULA pattern as SMPL-X (research / non-commercial).
- Distributed as per-subject `.tar.bz2` archives, each containing many `.npz` sequences. Each `.npz` carries `poses` (frames × 156 axis-angle parameters for SMPL-X), `betas`, `gender`, `mocap_framerate`, `trans` (root translation per frame).
- Subdatasets: CMU, BMLrub, KIT, MPI_HDM05, etc. The walking-heavy ones tend to be CMU, BMLmovi, BMLrub.

## Open questions for the dev

- **How many sequences and which subset.** 50 is a notional target. Whether we want 50 distinct subjects each walking once, or a smaller pool resampled with offsets, or one long trace per body — pick what's cheapest to assemble.
- **Whether to include body-shape variation.** AMASS sequences carry per-subject `betas`. Using them would give the paper's 50 bodies real demographic spread. Or we standardise on one betas vector and only vary the pose. Defer if not obvious.
- **Where the corpus sits on disk.** `data/poses/` is suggested in the ROADMAP but not consecrated. Convention should match how AMASS terms-of-use treat redistribution — usually you don't check the data into a public repo.
- **Frame rate handling.** Mocap is captured at 30 / 60 / 120 Hz depending on subset. Resampling to a common 30 Hz is on this brief.
- **Trimming and looping.** Walks are typically a few seconds long; the paper wants 5 minutes per body. Either loop a short walk or stitch several. The ARCHEOLOGY.md round-2 entry mentions "AMASS mocap → virtual IMU → small NN" was considered then dropped — we don't need the IMU virtualisation layer here, just the pose stream.
- **Whether to virtualise an IMU.** The paper says "cite, don't invent" — so probably skip. But if 08 ends up wanting tier-A/B telemetry that mimics phone-IMU noise, an ICM-20948 noise model on top of the ground-truth pose would be ~50 LOC. Decide when 08 demands it, not now.

## What "done" looks like

- A small ingest script in `scripts/` that consumes downloaded AMASS archives (or one canonical subset) and emits per-body `.npz` files at 30 Hz.
- An on-disk corpus (location TBD, probably `data/poses/`, gitignored) with enough sequences for the plaza scenario to pick from.
- A loader in `src/aegis/geometry/` (or wherever feels right alongside `parametric.py`) that takes a pose-stream `.npz` plus a frame index and returns a posed SMPL-X mesh — i.e. the API that brief 08 will call once per body per slot.
- A quick visual sanity check: pick one trace, render five frames as PNGs, eyeball that the body is walking. Doesn't need to be a test, just confidence.

## What this is NOT

- A retargeting toolchain from generic FBX / Mixamo to SMPL-X. AMASS already comes in SMPL family format.
- A pose-prediction or pose-estimation system. We have ground-truth mocap, that's the input.
- A skeletal animation system in the viewer. The viewer's GLB animation path exists separately and stays as it is.
- A real IMU sim. Defer.
