"""PHY / served-user sum-rate.

Default is a Shannon-rate proxy: per-user ``log2(1 + SINR_k)`` with MCS
clipping at the 3GPP NR FR2 cap (~7.4 bits/s/Hz at MCS28). The Sionna NR
PHY path is wired but only used when ``--phy=sionna`` is set; brief 08's
default run is Shannon, with one in-flight Sionna timing probe to decide
whether a follow-up Sionna pass fits the wall-clock budget.
"""

from __future__ import annotations

import time

import numpy as np

# 3GPP NR FR2 spectral efficiency cap, TS 38.214 Table 5.1.3.1-2,
# 256-QAM, MCS=27, coderate 948/1024 -> SE 7.4063 bps/Hz.
NR_SE_CAP_BPS_PER_HZ = 7.4
DEFAULT_BANDWIDTH_HZ = 400e6
# -90 dBm receiver noise floor at 400 MHz: optimistic (kT*B at 290K = -88 dBm
# implies NF = -2 dB which is unphysical). Use this for clean unit-test runs;
# realistic NF=6 dB receiver noise should set this to 6.4e-12 W (= -82 dBm).
# The SINR-margin of the binding-regime experiments was checked to hold at
# both values (see paper §IV.B).
DEFAULT_NOISE_POWER_W = 1e-12


def shannon_sumrate_bps(
    H: np.ndarray,
    W: np.ndarray,
    *,
    noise_power_w: float = DEFAULT_NOISE_POWER_W,
    bandwidth_hz: float = DEFAULT_BANDWIDTH_HZ,
    se_cap_bps_per_hz: float = NR_SE_CAP_BPS_PER_HZ,
) -> float:
    """Sum-rate over served users under linear precoder ``W``.

    Parameters
    ----------
    H : (K, M) complex channel matrix, one row per user.
    W : (M, K) complex precoder; each column is one user's beam.
    """
    if H.shape[0] == 0:
        return 0.0
    # h_k^H w_k for desired signal, h_k^H w_j (j != k) for interference.
    HW = H @ W  # (K, K), entry (k, j) = h_k^H w_j
    sig_pow = np.abs(np.diag(HW)) ** 2
    inter_pow = np.sum(np.abs(HW) ** 2, axis=1) - sig_pow
    sinr = sig_pow / (inter_pow + noise_power_w)
    se = np.minimum(np.log2(1.0 + sinr), se_cap_bps_per_hz)
    return float(np.sum(se) * bandwidth_hz)


def shannon_per_user_se(
    H: np.ndarray,
    W: np.ndarray,
    *,
    noise_power_w: float = DEFAULT_NOISE_POWER_W,
    se_cap_bps_per_hz: float = NR_SE_CAP_BPS_PER_HZ,
) -> np.ndarray:
    """Per-user spectral efficiency [bits/s/Hz]; same model as ``shannon_sumrate_bps``."""
    if H.shape[0] == 0:
        return np.zeros(0)
    HW = H @ W
    sig_pow = np.abs(np.diag(HW)) ** 2
    inter_pow = np.sum(np.abs(HW) ** 2, axis=1) - sig_pow
    sinr = sig_pow / (inter_pow + noise_power_w)
    return np.minimum(np.log2(1.0 + sinr), se_cap_bps_per_hz)


def time_one_slot(
    fn,
    *args,
    n_warmup: int = 1,
    **kwargs,
) -> float:
    """Median wall-clock of ``fn(*args, **kwargs)`` over a few calls [ms]."""
    for _ in range(n_warmup):
        fn(*args, **kwargs)
    samples = []
    for _ in range(3):
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        samples.append((time.perf_counter() - t0) * 1e3)
    samples.sort()
    return samples[len(samples) // 2]
