# Agent log: peak-local APD implementation

Date: 2026-05-10

## Task

Implement `peak_local_apd.py` in `JSAC2/code/` for ICNIRP 2020 FR2 compliance
assessment. The metric is the peak spatially-averaged absorbed power density
over any 4 cm^2 surface disc, with a general-public limit of 10 W/m^2.

## Implementation

File: `/home/user/aegis/JSAC2/code/peak_local_apd.py`

### `peak_local_apd()` function

- Builds a `scipy.spatial.cKDTree` on triangle centroids (O(T log T))
- Queries `query_ball_point` with `r = region_radius_cm * 0.01` metres
- Computes area-weighted average Sab over each triangle's neighbourhood
- Returns: `max_apd`, `local_apd` (T,), `peak_triangle_idx`, `neighborhood_size_distribution`, `whole_body_avg_apd`
- Radius default: 1.13 cm = sqrt(4 cm^2 / pi) => 4 cm^2 averaging disc

### `compute_sab_per_triangle()` function

Derives per-triangle Sab from scene geometry using the geometric-Fresnel
formula (monograph level-3 kernel):

    Sab(t) = IPD(t) * T_avg(theta_t) * max(0, mu_t)

IPD model: coherent MRT beamforming toward body centroid. Per-element
phasor = exp(i*k0*(r_tj - r_j0)) / r_tj, amplitude calibrated to Friis
(P_per_element / (4*pi) * |sum_j phasor_j|^2). Fresnel T_avg computed
inline (skin: eps_r=16.5, sigma=25.8 S/m, 28 GHz).

### Recomputation requirement

The existing pose_sweep NPZ files (S2, S2bind, S3) store only channel
coefficients (h_los_norm, h_body_norm etc.), not per-triangle Sab. The
scene_loss_db_los parameter in those files affects only the LOS attenuation
for SINR/rate calculations; it does not change the incident power from the
BS. Therefore all three scenarios have identical APD results -- the body
is at the same location relative to the BS in all three.

## Validation tests

All 5 tests pass (runtime ~100s on Thelonious mesh with T=23826 triangles):

1. **Tiny radius (0.001 cm)**: peak-local APD = max per-triangle Sab (1.000000e+00) -- PASS
2. **Huge radius (10000 cm)**: peak-local APD = whole-body area-weighted average (5.074301e-03) -- PASS
3. **Shuffle invariance**: result unchanged after random permutation of triangle indices -- PASS
4. **All-zero Sab**: peak APD = 0.0 -- PASS
5. **Non-negativity**: all local_apd values >= 0 -- PASS

## Per-regime peak-APD numbers

Scene geometry: 28 GHz, P_tx = 43 dBm (20 W total), 8x8 UPA at [0,0,8] m,
Thelonious phantom at [30, 0, 1.2] m, yaw sweep -45 to +45 degrees.

All three scenarios (S2, S2bind, S3) give identical APD because APD depends
only on body pose relative to BS, not on the LOS wall-loss parameter.

| Regime   | Max peak-local APD (W/m^2) | Whole-body avg at 0 deg | % of ICNIRP 10 W/m^2 |
|----------|---------------------------|--------------------------|----------------------|
| S2       | 5.799e-02                 | 1.592e-02                | 0.58%                |
| S2bind   | 5.799e-02                 | 1.592e-02                | 0.58%                |
| S3       | 5.799e-02                 | 1.592e-02                | 0.58%                |

Peak over all poses: **5.799e-02 W/m^2 (0.58% of ICNIRP limit)**

The peak occurs at yaw = +10 deg (slight asymmetry in Thelonious mesh relative
to the frontal projection of the 8x8 array). Variation across yaw angles is
small (~1.4% relative) because the BS is in the far field at 30 m and the
frontal illumination geometry changes little with +/-45 deg torso rotation.

## Fraction-of-ICNIRP-limit numbers

At the JSAC scenario distance of 30 m with 43 dBm TX power (which is the
3GPP NR FR2 maximum EIRP for a gNB), the peak-local APD is 58 mW/m^2
-- 172x below the ICNIRP 2020 general-public limit of 10 W/m^2.

This strongly supports the paper's "compliance is not the binding constraint"
argument: even at maximum licensed TX power, the body-mediated channel
exploits power levels roughly two orders of magnitude below the regulatory
ceiling. The binding constraints are the link budget (noise floor, beamforming
gain) and the MCS cap, not RF safety.

For the ICNIRP occupational limit (50 W/m^2), the margin is even larger: 862x.

## Departures from spec

1. **S2, S2bind, S3 have identical APD.** The three NPZ files differ only
   in `scene_loss_db_los` (35, 55, 80 dB), which affects the LOS channel
   attenuation but not the BS radiated power toward the body. This is the
   correct physical interpretation: the BS emits the same power regardless
   of what a wall does to the direct-path signal. The three scenarios are
   therefore degenerate for APD purposes.

2. **MRT coherent IPD model.** The `compute_sab_per_triangle()` function
   uses MRT beamforming toward the body centroid for IPD computation. This
   is the worst-case (maximum exposure) scenario, which is conservative for
   compliance assessment. An isotropic or incoherent model would give lower
   APD by a factor of M = 64 (incoherent) or sqrt(M) ~ 8 (random phases).

3. **Effective k_hat uses BS centroid.** For the Fresnel incidence angle
   computation, we use the direction from the BS array centroid to each
   triangle, rather than a per-element weighted average. At 30 m distance
   with an 8x8 array spanning < 0.3 m, this is accurate to < 0.5 deg.

## Output files

- `/home/user/aegis/JSAC2/code/outputs/peak_local_apd_S2.npz`
- `/home/user/aegis/JSAC2/code/outputs/peak_local_apd_S2bind.npz`
- `/home/user/aegis/JSAC2/code/outputs/peak_local_apd_S3.npz`
- `/home/user/aegis/JSAC2/code/outputs/peak_local_apd_summary.txt`

Each NPZ contains: `yaws_deg`, `peak_local_apd`, `whole_body_avg_apd`,
`pct_icnirp`, `sab_all_poses` (N_poses x T), `areas`.
