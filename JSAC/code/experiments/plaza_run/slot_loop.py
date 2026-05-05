"""Per-slot tick for plaza_run.

Cadence layout (all in ``slot_index`` units; frames at 30 Hz):

    pose update     every ``pose_period`` slots  (default 30 = 1 s)
    path refresh    every ``rt_period`` slots    (default 30 = 1 s)
    Q translate     every slot                   (warm-refresh per §III.C)
    precoder solve  every slot
    sum-rate eval   every slot

Pose period defaults to 30 (1 s) rather than the paper's 100 ms (3 frames)
because the SMPL-X forward + ``compute_static_path_gram`` cost scales linearly
in pose-update count and 1 s is enough to capture meaningful walk motion in
the 5 minute scenario. The script accepts ``--pose-period`` to override.

The five precoders are evaluated each slot, all against the same H but
different per-body ``Q_list``:

    mrt              ignores Q (matched filter)
    zf               ignores Q (zero-forcing on served users)
    wc_backoff       MRT scaled by sqrt(L_min / max p_abs across all bodies)
    multibody_ecbf   proposed; tier-A/B = posed Q (or T-pose if --ablate),
                     tier-C-detected = T-pose Q, tier-C-undet excluded
    oracle           multibody_ecbf with posed Q for all bodies (no Cauchy)

Per-body absorbed power and compliance are always evaluated against the
ground-truth posed Q (``Q_actual``), so ``violation`` reflects the truth
even when the solver only saw a Cauchy approximation.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from aegis._array_backend import xp
from aegis.coherent.multibody_ecbf import solve_multibody_ecbf
from aegis.coherent.translation import compute_static_path_gram
from aegis.constants import C_0
from aegis.geometry.parametric import ParametricBody
from aegis.geometry.pose_stream import PoseStream
from aegis.mimo.channel import compute_channel_vector
from aegis.mimo.precoders import mrt, zf
from aegis.tissue.dielectric import TissueModel

from .paths import PathSpec
from .phy import shannon_sumrate_bps
from .scenario import Body, BSPanel
from .tier_c import SensingConfig, detect_bodies

logger = logging.getLogger(__name__)

PRECODER_NAMES = ["mrt", "zf", "wc_backoff", "multibody_ecbf", "oracle"]
DEFAULT_NOISE_POWER = 1e-2
DEFAULT_ORACLE_NOISE_POWER = 1e-3
DEFAULT_POSE_PERIOD = 30  # slots
DEFAULT_RT_PERIOD = 30


def _decimate_arrays(
    normals: np.ndarray, centroids: np.ndarray, areas: np.ndarray, stride: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decim-N stride matching ``gpu_benchmark/bench_50body_fast.py``.

    Keeps every ``stride``-th triangle and multiplies the kept areas by
    ``stride`` so total surface area is preserved.
    """
    if stride <= 1:
        return normals.copy(), centroids.copy(), areas.copy()
    return (
        normals[::stride].copy(),
        centroids[::stride].copy(),
        (areas[::stride] * stride).copy(),
    )


def _translate_to_world(centroids: np.ndarray, vertices: np.ndarray, world_xyz: np.ndarray) -> np.ndarray:
    """Return centroids translated so the body's lowest vertex sits at z=world_z.

    Returns the shifted centroids; callers don't need full vertex updates
    because translation phasor keys off centroids only.
    """
    v_flat = vertices.reshape(-1, 3)
    z_min = float(v_flat[:, 2].min())
    shift = np.array([world_xyz[0], world_xyz[1], world_xyz[2] - z_min], dtype=np.float64)
    return centroids + shift[None, :]


@dataclass
class SlotLoopConfig:
    pose_period: int = DEFAULT_POSE_PERIOD
    rt_period: int = DEFAULT_RT_PERIOD
    decim_stride: int = 10
    noise_power: float = DEFAULT_NOISE_POWER
    oracle_noise_power: float = DEFAULT_ORACLE_NOISE_POWER
    paths_mode: str = "plaza_specular"
    ablate_pose_telemetry: bool = False
    sensing: SensingConfig = field(default_factory=SensingConfig)


@dataclass
class _BodyState:
    """Per-body mutable state (refreshed at pose / rt cadence)."""

    posed_M_static: np.ndarray | None = None
    tposed_M_static: np.ndarray | None = None
    posed_centroids_ref: np.ndarray | None = None  # body centroid at pose snapshot
    tposed_centroids_ref: np.ndarray | None = None
    last_path_set: object | None = None  # PropagationPaths (centre-of-array form)
    detected: bool = True


def _build_M_static(
    normals: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    paths,
    array,
    array_offsets: np.ndarray,
    n_tilde: complex,
    sigma: float,
    freq_hz: float,
) -> np.ndarray:
    """Wrap ``compute_static_path_gram`` with element-gain-folded ``center_psi``.

    Mirrors the gain-folding step in ``expand_paths_to_array``: the
    monograph's per-path ``psi`` includes the element gain via
    ``C_T,j(n)``, so multiply by the array's per-direction element gain
    before handing to the static-gram kernel (this is the same fold the
    factored body channel applies internally).
    """
    gain = array.element_gain(paths.k_hat)  # (N,)
    psi_gained = paths.psi * gain[:, None]
    return np.asarray(
        compute_static_path_gram(
            normals=xp.asarray(normals),
            centroids_0=xp.asarray(centroids),
            areas=xp.asarray(areas),
            center_k_hat=xp.asarray(paths.k_hat),
            center_psi=xp.asarray(psi_gained),
            array_offsets=xp.asarray(array_offsets),
            n_tilde=n_tilde,
            sigma=sigma,
            freq_hz=freq_hz,
        )
    )


def _per_body_p_abs(W: np.ndarray, Q: np.ndarray) -> float:
    """``trace(W^H Q W)`` summed over precoder columns. Real-valued by Hermiticity."""
    return float(np.real(np.einsum("ik,ij,jk->", np.conj(W), Q, W)))


def _batch_p_abs(Q_stack: np.ndarray, W: np.ndarray) -> np.ndarray:
    """``trace(W^H Q[b] W)`` for every body ``b`` in one einsum.

    Parameters
    ----------
    Q_stack : (B, M, M) Hermitian
    W : (M, K)

    Returns
    -------
    p_abs : (B,) real
    """
    return np.real(np.einsum("bij,ik,jk->b", Q_stack, np.conj(W), W))


def _translation_phasor_np(center_k_hat: np.ndarray, delta_t: np.ndarray, freq_hz: float) -> np.ndarray:
    """Per-body translation phasor in numpy (slot-cadence; tiny op)."""
    k0 = 2.0 * np.pi * freq_hz / C_0
    return np.exp(-1j * k0 * (center_k_hat @ delta_t))


def _q_translate_np(M_static: np.ndarray, phi: np.ndarray) -> np.ndarray:
    """Refresh Q under translation by sandwiching M_static with phi (numpy)."""
    Q = np.einsum("c,d,cdpq->pq", np.conj(phi), phi, M_static)
    return 0.5 * (Q + np.conj(Q).T)


def _wc_backoff_W(W_mrt: np.ndarray, p_abs_mrt: np.ndarray, budgets: np.ndarray) -> np.ndarray:
    """Scale MRT power so the worst body's budget is met (paper baseline 3)."""
    margin = budgets / np.maximum(p_abs_mrt, 1e-30)
    scale = float(np.sqrt(min(1.0, np.min(margin))))
    return W_mrt * scale


@dataclass
class _RunBuffers:
    """Per-run output tensors, allocated once."""

    p_abs: np.ndarray  # (T, B, P)
    sumrate: np.ndarray  # (T, P)
    violation: np.ndarray  # (T, B, P)
    infeasible: np.ndarray  # (T, P)
    body_positions: np.ndarray  # (T, B, 3)
    cadence_ms: np.ndarray  # (T, 4)


def allocate_buffers(n_slots: int, n_bodies: int, n_precoders: int) -> _RunBuffers:
    return _RunBuffers(
        p_abs=np.zeros((n_slots, n_bodies, n_precoders), dtype=np.float32),
        sumrate=np.zeros((n_slots, n_precoders), dtype=np.float32),
        violation=np.zeros((n_slots, n_bodies, n_precoders), dtype=bool),
        infeasible=np.zeros((n_slots, n_precoders), dtype=bool),
        body_positions=np.zeros((n_slots, n_bodies, 3), dtype=np.float32),
        cadence_ms=np.zeros((n_slots, 4), dtype=np.float32),
    )


def run_slots(
    *,
    n_slots: int,
    bs_panel: BSPanel,
    bodies: list[Body],
    pose_streams: list[PoseStream],
    parametric: ParametricBody,
    body_positions: np.ndarray,
    body_budgets: np.ndarray,
    path_generator: Callable[[PathSpec], object],
    config: SlotLoopConfig,
    progress_every: int = 200,
) -> _RunBuffers:
    """Run the per-slot loop and return per-slot tensors."""
    n_bodies = len(bodies)
    n_precoders = len(PRECODER_NAMES)
    buffers = allocate_buffers(n_slots, n_bodies, n_precoders)

    tissue = TissueModel.from_database("Skin", bs_panel.freq_hz)
    n_tilde = tissue.n_complex
    sigma = float(tissue.sigma)

    array = bs_panel.array
    array_offsets = array.element_positions - array.reference_position

    state: list[_BodyState] = [_BodyState() for _ in range(n_bodies)]

    served_idx = np.array([b.index for b in bodies if b.tier == "A"], dtype=np.int64)
    bystander_c_idx = np.array([b.index for b in bodies if b.tier == "C"], dtype=np.int64)

    # Tier-C detection runs at pose cadence (presence-tracking is slow).
    bs_pos = bs_panel.position
    sensing = config.sensing

    pose_count = 0
    t_log_last = time.perf_counter()

    for t in range(n_slots):
        slot_t0 = time.perf_counter()
        # ------------------------------------------------------------------
        # Pose / RT cadence ticks
        # ------------------------------------------------------------------
        do_pose = (t % config.pose_period) == 0
        do_rt = (t % config.rt_period) == 0

        rt_t0 = time.perf_counter()
        if do_rt or do_pose:
            for b in bodies:
                spec = PathSpec(
                    bs_position=bs_pos,
                    body_target=body_positions[t, b.index].astype(np.float64),
                    freq_hz=bs_panel.freq_hz,
                    tx_power_w=bs_panel.tx_power_w,
                    body_index=b.index,
                    slot_index=t,
                )
                state[b.index].last_path_set = path_generator(spec)
        rt_ms = (time.perf_counter() - rt_t0) * 1e3

        q_t0 = time.perf_counter()
        if do_pose:
            # Tier-C detection at pose cadence.
            if bystander_c_idx.size:
                pos = body_positions[t, bystander_c_idx, :].astype(np.float64)
                decisions = detect_bodies(bs_pos, pos, sensing)
                for k, dec in zip(bystander_c_idx, decisions, strict=True):
                    state[k].detected = bool(dec.detected)

            for b in bodies:
                pose_axang, _trans = pose_streams[b.index].frame(pose_count, loop=True)
                betas = pose_streams[b.index].betas
                world_pos = body_positions[t, b.index].astype(np.float64)
                paths_b = state[b.index].last_path_set

                # Posed mesh (full pose; used for proposed/oracle and eval).
                posed_local = parametric.generate(betas=betas[:10], pose=pose_axang[:66], name=f"body{b.index}_t{t}")
                posed_cents = _translate_to_world(posed_local.centroids, posed_local.vertices, world_pos)
                n_p, c_p, a_p = _decimate_arrays(
                    posed_local.normals, posed_cents, posed_local.areas, config.decim_stride
                )
                state[b.index].posed_M_static = _build_M_static(
                    n_p, c_p, a_p, paths_b, array, array_offsets, n_tilde, sigma, bs_panel.freq_hz
                )
                state[b.index].posed_centroids_ref = world_pos.copy()

                # T-pose mesh (built once per body; static envelope).
                if state[b.index].tposed_M_static is None:
                    tpose_local = parametric.generate(betas=betas[:10], pose=np.zeros(66), name=f"body{b.index}_tpose")
                    tpose_cents = _translate_to_world(tpose_local.centroids, tpose_local.vertices, world_pos)
                    n_t, c_t, a_t = _decimate_arrays(
                        tpose_local.normals, tpose_cents, tpose_local.areas, config.decim_stride
                    )
                    state[b.index].tposed_M_static = _build_M_static(
                        n_t, c_t, a_t, paths_b, array, array_offsets, n_tilde, sigma, bs_panel.freq_hz
                    )
                    state[b.index].tposed_centroids_ref = world_pos.copy()
            pose_count += 1

        # ------------------------------------------------------------------
        # Per-slot Q refresh via translation phasor.
        # ------------------------------------------------------------------
        Q_actual = []
        Q_proposed: list[np.ndarray] = []
        Q_oracle: list[np.ndarray] = []
        L_proposed: list[float] = []
        L_oracle: list[float] = []

        for b in bodies:
            paths = state[b.index].last_path_set
            world = body_positions[t, b.index].astype(np.float64)

            posed_dt = world - state[b.index].posed_centroids_ref
            phi_pose = _translation_phasor_np(paths.k_hat, posed_dt, bs_panel.freq_hz)
            Q_pose = _q_translate_np(state[b.index].posed_M_static, phi_pose)
            Q_actual.append(Q_pose)

            tposed_dt = world - state[b.index].tposed_centroids_ref
            phi_tp = _translation_phasor_np(paths.k_hat, tposed_dt, bs_panel.freq_hz)
            Q_tp = _q_translate_np(state[b.index].tposed_M_static, phi_tp)

            # Proposed Q + budget by tier.
            if b.tier == "A" or b.tier == "B":
                Q_proposed.append(Q_tp if config.ablate_pose_telemetry else Q_pose)
                L_proposed.append(float(body_budgets[b.index]))
            elif b.tier == "C":
                if state[b.index].detected:
                    Q_proposed.append(Q_tp)
                    L_proposed.append(float(body_budgets[b.index]))
                # Else: undetected → envelope (skipped from problem).

            # Oracle: posed for everyone.
            Q_oracle.append(Q_pose)
            L_oracle.append(float(body_budgets[b.index]))
        q_ms = (time.perf_counter() - q_t0) * 1e3

        # ------------------------------------------------------------------
        # Build channel matrix H from served users (tier A).
        # ------------------------------------------------------------------
        K = served_idx.size
        if K == 0:
            # Degenerate scenario: skip.
            continue
        H = np.zeros((K, array.n_elements), dtype=complex)
        for k_row, body_i in enumerate(served_idx):
            paths = state[body_i].last_path_set
            ue_pos = body_positions[t, body_i].astype(np.float64).copy()
            ue_pos[2] = 1.6  # head height for UE antenna
            H[k_row] = compute_channel_vector(
                center_paths=paths,
                array=array,
                device_position=ue_pos,
                device_orientation=np.array([0.0, 0.0, 1.0]),
                freq_hz=bs_panel.freq_hz,
            )

        # ------------------------------------------------------------------
        # Five precoders.
        # ------------------------------------------------------------------
        prec_t0 = time.perf_counter()
        P_tx = bs_panel.tx_power_w
        precoders: dict[str, np.ndarray] = {}
        infeas_flags: dict[str, bool] = {n: False for n in PRECODER_NAMES}

        precoders["mrt"] = mrt(H, P=P_tx)
        precoders["zf"] = zf(H, P=P_tx)

        # Stack the actual posed Q's once per slot for batched p_abs evals.
        Q_actual_stack = np.stack(Q_actual, axis=0)

        # WC back-off uses MRT scaled by min margin.
        p_abs_mrt = _batch_p_abs(Q_actual_stack, precoders["mrt"])
        precoders["wc_backoff"] = _wc_backoff_W(precoders["mrt"], p_abs_mrt, body_budgets)

        if Q_proposed:
            try:
                W_p, diag_p = solve_multibody_ecbf(
                    H,
                    Q_proposed,
                    L_proposed,
                    P_tx,
                    noise_power=config.noise_power,
                    return_diagnostics=True,
                    max_outer=8,
                )
                infeas_flags["multibody_ecbf"] = diag_p.method == "min-absorption"
            except Exception as exc:  # pragma: no cover - solver crash
                logger.warning("multibody_ecbf failed at slot %d: %s", t, exc)
                W_p = precoders["wc_backoff"]
                infeas_flags["multibody_ecbf"] = True
        else:
            W_p = precoders["mrt"]
        precoders["multibody_ecbf"] = W_p

        try:
            W_o, diag_o = solve_multibody_ecbf(
                H,
                Q_oracle,
                L_oracle,
                P_tx,
                noise_power=config.oracle_noise_power,
                return_diagnostics=True,
                max_outer=8,
            )
            infeas_flags["oracle"] = diag_o.method == "min-absorption"
        except Exception as exc:  # pragma: no cover
            logger.warning("oracle ECBF failed at slot %d: %s", t, exc)
            W_o = precoders["wc_backoff"]
            infeas_flags["oracle"] = True
        precoders["oracle"] = W_o

        prec_ms = (time.perf_counter() - prec_t0) * 1e3

        # ------------------------------------------------------------------
        # Evaluate p_abs / violation / sumrate (always vs ground-truth Q).
        # ------------------------------------------------------------------
        phy_t0 = time.perf_counter()
        for p_idx, name in enumerate(PRECODER_NAMES):
            W = precoders[name]
            pa = _batch_p_abs(Q_actual_stack, W).astype(np.float32)
            buffers.p_abs[t, :, p_idx] = pa
            buffers.violation[t, :, p_idx] = pa > body_budgets
            buffers.sumrate[t, p_idx] = shannon_sumrate_bps(H, W)
            buffers.infeasible[t, p_idx] = infeas_flags[name]
        phy_ms = (time.perf_counter() - phy_t0) * 1e3

        buffers.cadence_ms[t] = [q_ms, prec_ms, rt_ms, phy_ms]
        buffers.body_positions[t] = body_positions[t]

        if progress_every and (t + 1) % progress_every == 0:
            now = time.perf_counter()
            slot_ms = (now - slot_t0) * 1e3
            window_s = now - t_log_last
            t_log_last = now
            logger.info(
                "slot %d/%d total=%.1fms window=%.1fs (q=%.1f prec=%.1f rt=%.1f phy=%.1f)",
                t + 1,
                n_slots,
                slot_ms,
                window_s,
                q_ms,
                prec_ms,
                rt_ms,
                phy_ms,
            )

    return buffers
