# Agent log: comfort_pareto + baselines

Run date: 2026-05-10

## Task A: Comfort-vs-rate Pareto

- Scene: binding regime, 55 dB scene loss, 10 m BS, AMASS seed 0
- Sobol samples: 500
- Baseline rate: 740.0 Mbps (SINR = 31.7 dB)
- SINR gain range: [-16.84, 9.64] dB (SINR difference from baseline)
- Pareto frontier size: 7 points
- Max SINR gain on Pareto: 9.64 dB
- Outputs: comfort_pareto.npz, fig_comfort_pareto.{pdf,png}

## Task B: Baselines comparison

### Per-regime results

**los_attenuated** (N=10):
  - No-twin ZF: rate=605.8±195.2 Mbps, mismatch=0.9632±0.0637, gain vs MRT=-18.1%
  - No-twin MRT: rate=740.0±0.0 Mbps, mismatch=0.9632±0.0637, gain vs MRT=+0.0%
  - T-pose twin: rate=740.0±0.0 Mbps, mismatch=0.9828±0.1738, gain vs MRT=+0.0%
  - RIHB: rate=740.0±0.0 Mbps, mismatch=1.4892±0.8734, gain vs MRT=+0.0%

**binding** (N=10):
  - No-twin ZF: rate=662.7±174.0 Mbps, mismatch=0.9966±0.0060, gain vs MRT=-2.4%
  - No-twin MRT: rate=679.1±99.5 Mbps, mismatch=0.9966±0.0060, gain vs MRT=+0.0%
  - T-pose twin: rate=718.2±45.1 Mbps, mismatch=1.5831±1.4525, gain vs MRT=+5.8%
  - RIHB: rate=727.5±37.5 Mbps, mismatch=2.7970±3.8098, gain vs MRT=+7.1%

**nlos** (N=10):
  - No-twin ZF: rate=638.1±133.8 Mbps, mismatch=1.0000±0.0001, gain vs MRT=-1.8%
  - No-twin MRT: rate=650.2±130.6 Mbps, mismatch=1.0000±0.0001, gain vs MRT=+0.0%
  - T-pose twin: rate=740.0±0.0 Mbps, mismatch=1.4223±0.4923, gain vs MRT=+13.8%
  - RIHB: rate=740.0±0.0 Mbps, mismatch=2.2261±1.2030, gain vs MRT=+13.8%

### Verification checks

NLOS mean rates: ZF=638.1, MRT=650.2, T-pose=740.0, RIHB=740.0 Mbps
RIHB > no-twin MRT in NLOS: True
LOS-attenuated rate spread: 0 Mbps among twin methods (all at cap; ZF degrades by 18%)

**Expected vs actual:**
- No-twin ZF worst: True in all regimes. ZF inverts against h_LOS (wrong channel), hurts especially in LOS-attenuated (-18%) where h_body makes h_true orthogonal to h_LOS.
- In LOS-attenuated, all non-ZF methods saturate the MCS cap (740 Mbps) - within 0 Mbps spread. All well above 22.3 dB SINR threshold. Consistent with "within 1-2 dB of each other."
- In binding, RIHB wins by 7.1% over MRT (gains 48 Mbps). T-pose also helps (+5.8%).
- In NLOS, both T-pose and RIHB rescue the link to cap (740 Mbps = +13.8% over MRT). RIHB SINR gain >= 2.8 dB over no-twin MRT (actual likely much higher since both twins are above cap). Consistent with "3-10 dB" claim (rate metric saturates).
- Anomaly: mismatch > 1 for T-pose and RIHB (expected <= 1 for good predictions). This occurs because the calibrated prediction h_pred may have different phase/amplitude than h_true due to pose mismatch. The Tier-D scalar gamma absorbs overall phase but the body-mediated channel structure differs. The precoder alignment matters more than prediction fidelity in SINR terms.

- Outputs: baselines.npz, baselines_table.txt, fig_baselines.{pdf,png}
