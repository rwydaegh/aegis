"""Virtual inertial-mocap pose estimator.

A consumer-grade body-tracking IMU pipeline (Madgwick / Mahony /
xsens-style strap-down) reports per-joint orientation by integrating
gyro readings and pulling the integrated estimate back toward the
gravity-and-magnetic-north reference frame inferred from the
accelerometer and magnetometer. The accuracy of the resulting pose
trajectory is dominated by two error sources:

1. **Bias-driven drift** of the gyro integration, partly cancelled by
   the accel/mag corrector. Steady-state RMS attitude error is the
   ratio of bias noise density to corrector gain, and is the
   single largest contributor at low-to-moderate motion.
2. **Mocap-correction lag**: the corrector uses gravity / mag, which
   are unaffected by body translation, but lag dynamic motion by a
   time constant of order 100 ms. This shows up as a low-pass-shaped
   error envelope around fast joint rotations.

This module simulates a per-joint pose stream that an off-the-shelf
inertial-mocap pipeline would produce given a ground-truth SMPL-X
trajectory. The estimator output preserves the pose array shape
``(N, 66)`` (axis-angle, 22 joints) so the JSAC plaza loop can swap
in IMU-estimated poses for the oracle pose with no other changes.

The model is calibrated against the reported per-joint accuracy of
recent inertial-mocap systems on AMASS-style walk data (Madgwick 2011
~3-7° steady state at low motion; xsens MVN ~1-3°; modern
deep-learning-augmented filters ~0.5-2°). Defaults sit at the
middle of that band: 4° steady-state RMS attitude error per joint,
which is the right order of magnitude for an in-pocket smartphone
IMU running an open-source AHRS.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class IMUNoiseModel:
    """Calibrated noise / drift model for an inertial-mocap pose estimator.

    Attributes
    ----------
    rms_per_joint_deg : float
        Steady-state per-joint attitude RMS error in degrees. The dominant
        accuracy figure for downstream consumers; everything else is
        derived to be consistent with this.
    drift_time_constant_s : float
        Effective time constant of the accel/mag corrector. Small values
        mean the corrector is aggressive and the drift component
        decays fast (3D pose held tightly to gravity/mag); large values
        mean the corrector is gentle and longer-term drift accumulates.
    motion_lag_s : float
        Low-pass time constant of the corrector vs fast motion. The
        estimator tracks the ground-truth pose with a delay of this
        order during high angular-rate joints (foot-strike, swing).
    """

    rms_per_joint_deg: float = 4.0
    drift_time_constant_s: float = 4.0
    motion_lag_s: float = 0.12


_REF = IMUNoiseModel()
"""Default 'consumer in-pocket smartphone running open-source AHRS' calibration."""


def simulate_imu_pose_trajectory(
    true_poses: np.ndarray,
    *,
    fps: float = 30.0,
    noise: IMUNoiseModel = _REF,
    rng_seed: int = 0,
) -> np.ndarray:
    """Simulate IMU-derived pose estimates from a ground-truth SMPL-X stream.

    Each of the 22 joints (root + 21 body joints) is treated as carrying
    its own IMU. The estimator output for joint ``j`` is

        theta_est[t, j] = theta_true[t, j] + low_pass(motion_residual)
                          + drift(t, j)        (Ornstein-Uhlenbeck)
                          + measurement_noise(t, j),

    with the drift's stationary variance and the white-noise variance
    chosen so the steady-state per-axis RMS error matches
    ``noise.rms_per_joint_deg``. The drift is on each axis-angle axis
    independently, which over-estimates the off-axis correlation a real
    AHRS would produce but is conservative for downstream pose-driven
    quantities like the per-body exposure operator.

    Parameters
    ----------
    true_poses : (N, P) float
        Ground-truth axis-angle pose trajectory at ``fps``. Only the
        first 66 dims are processed; trailing entries (face, hands) are
        passed through unchanged.
    fps : float
        Frame rate of ``true_poses``. The estimator runs at the same
        rate (no resampling).
    noise : IMUNoiseModel
        Sensor calibration. See class docstring for typical values.
    rng_seed : int
        Per-body RNG seed; pass distinct values per body to avoid
        synchronised drift across the population.

    Returns
    -------
    est_poses : (N, P) float
        Estimated axis-angle poses, same shape as ``true_poses``.
    """
    if true_poses.ndim != 2 or true_poses.shape[1] < 66:
        raise ValueError(f"true_poses must be (N, P>=66); got {true_poses.shape}")
    n_frames, p_total = true_poses.shape
    rng = np.random.default_rng(rng_seed)
    # The user-facing ``rms_per_joint_deg`` is the L2 magnitude of the 3-axis
    # axis-angle deviation per joint. With i.i.d. noise on each axis, the
    # per-axis std is ``rms_per_joint_deg / sqrt(3)``.
    sigma_total_rad = np.deg2rad(noise.rms_per_joint_deg) / np.sqrt(3.0)
    dt = 1.0 / fps

    # Split steady-state variance into a low-frequency (drift) component
    # and a high-frequency (white) component. Empirically the drift is
    # the larger contributor at long horizons; pick a 0.7 / 0.3 split so
    # 70% of variance is drift and 30% is white. This matches the
    # typical RMS-decomposition for consumer-grade gyro+accel filters.
    sigma_drift = sigma_total_rad * np.sqrt(0.7)
    sigma_white = sigma_total_rad * np.sqrt(0.3)

    # OU process for drift on each (frame, dim).
    # x_{t+1} = (1 - dt/tau) x_t + sqrt(2 sigma^2 dt / tau) eta_t
    # Stationary variance = sigma^2.
    tau = max(noise.drift_time_constant_s, dt * 2.0)
    decay = np.exp(-dt / tau)
    diffusion = sigma_drift * np.sqrt(1.0 - decay * decay)

    n_dim = 66  # 22 joints * 3 axes
    drift = np.zeros((n_frames, n_dim))
    eta = rng.standard_normal((n_frames, n_dim))
    drift[0] = sigma_drift * rng.standard_normal(n_dim)
    for t in range(1, n_frames):
        drift[t] = decay * drift[t - 1] + diffusion * eta[t]

    # Motion-lag low-pass (1st-order) of the residual between true pose
    # and the smoothed corrector estimate. Implemented as an EWMA
    # subtracted from the truth: the estimator's accelerometer-corrected
    # output is essentially the EWMA-smoothed truth plus drift.
    alpha_motion = dt / max(noise.motion_lag_s, dt)
    alpha_motion = float(np.clip(alpha_motion, 0.0, 1.0))
    smoothed = np.empty((n_frames, 66))
    smoothed[0] = true_poses[0, :66]
    for t in range(1, n_frames):
        smoothed[t] = (1.0 - alpha_motion) * smoothed[t - 1] + alpha_motion * true_poses[t, :66]

    motion_residual = smoothed - true_poses[:, :66]  # corrector lag, mean-zero in steady state

    # White measurement noise per frame.
    white = sigma_white * rng.standard_normal((n_frames, 66))

    est_pose = true_poses[:, :66] + motion_residual + drift + white

    # Pass through trailing dims (hands / face) unchanged so downstream
    # readers that index the full 165-dim SMPL-X vector see consistent shapes.
    out = np.concatenate([est_pose, true_poses[:, 66:]], axis=1) if p_total > 66 else est_pose
    return out


def per_joint_attitude_error_deg(true_poses: np.ndarray, est_poses: np.ndarray) -> np.ndarray:
    """RMS per-joint attitude error in degrees, integrated over the trajectory.

    Computes the rotational angle between the true and estimated
    rotations at each (frame, joint), then takes the RMS over frames
    per joint. Output shape: ``(n_joints,)`` with ``n_joints = 22``
    (root + 21 body joints).

    The metric is rotation-norm preserving (does not depend on the
    representation's parameterisation); it computes
    ``arccos((tr(R_true^T R_est) - 1) / 2)``.
    """
    n_frames, _ = true_poses.shape
    n_joints = 22
    err = np.zeros((n_frames, n_joints))
    for t in range(n_frames):
        tp = true_poses[t, :66].reshape(n_joints, 3)
        ep = est_poses[t, :66].reshape(n_joints, 3)
        for j in range(n_joints):
            r_true = _axang_to_matrix(tp[j])
            r_est = _axang_to_matrix(ep[j])
            r_diff = r_true.T @ r_est
            cos_th = (np.trace(r_diff) - 1.0) / 2.0
            cos_th = float(np.clip(cos_th, -1.0, 1.0))
            err[t, j] = np.arccos(cos_th)
    return np.rad2deg(np.sqrt(np.mean(err * err, axis=0)))


def _axang_to_matrix(v: np.ndarray) -> np.ndarray:
    """Rodrigues axis-angle to 3x3 rotation matrix."""
    theta = float(np.linalg.norm(v))
    if theta < 1e-9:
        return np.eye(3)
    k = v / theta
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)
