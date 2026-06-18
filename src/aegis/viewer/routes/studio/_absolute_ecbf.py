"""Absolute-limit ECBF for the Coherent Exposure Studio.

The relative ECBF (``_precoders.build_ecbf_from_q``) caps absorbed power at a
fraction of the MRT operating point, so the constraint scales with transmit
power and never bites against a fixed regulatory limit. This module enforces the
two ICNIRP 2020 basic restrictions that matter at FR3 / mmWave as *absolute*
quadratic constraints on the precoder ``x``:

  - whole-body SAR:  ``x^H Q_glob x <= L_wb * mass``      [W vs W],
  - peak 4 cm^2 S_ab: ``max_r x^H Q_r x <= L_loc``        [W/m^2 vs W/m^2],

with the transmit power entering as ``||x||^2 <= P`` [W]. Both operators are
built from the same field channel realisation as the served body map:

    sab_t = sum_i |G_tilde[t, i, :] @ x|^2 = x^H Q_t x,   Q_t = sum_i g_ti^H g_ti
    Q_glob = sum_t area_t Q_t            (= integral S_ab dA = total absorbed power)
    Q_r    = sum_t G_avg[r, t] Q_t       (one local exposure operator per avg row)

so ``x^H Q_glob x`` is the total absorbed power and ``x^H Q_r x`` is the 4 cm^2
spatially-averaged S_ab at averaging row ``r``. No re-tracing: ``G_avg`` is the
cached row-stochastic averaging matrix and ``g_tilde`` is the channel pack.

The local peak is a max over many overlapping regions, handled by constraint
generation: solve, find the worst averaging row, add its operator, re-solve, warm
-started, until feasible or a cap is hit. Above the cap the studio logs the
truncation rather than silently under-reporting.

Reuses :func:`aegis.coherent.solve_multibody_ecbf` with ``K = 1`` and
``noise_power=None`` (matched-filter form), which collapses to the single-body
ECBF to machine precision, so this is a strict generalisation of the relative
solver.

Fork-free: imports only ``aegis.*`` plus numpy / scipy.
"""

from __future__ import annotations

import logging

import numpy as np

from ._channel import deposited_sab

logger = logging.getLogger(__name__)

# Relative slack on the local peak: a region counts as satisfied when its 4 cm^2
# average is within this fraction of the limit. The multibody solver projects the
# active operators onto their limits exactly, so this only governs how aggressively
# constraint generation chases the diffuse overlap tail.
_PEAK_TOL = 1e-3
# A restriction counts as binding when its utilisation (p_abs / budget) is within
# this of 1, i.e. the absorbed power sits on the limit.
_BINDING_TOL = 1e-3


def global_operator(g_tilde: np.ndarray, areas: np.ndarray) -> np.ndarray:
    """Whole-body absorbed-power operator ``Q_glob = sum_t area_t G_tilde_t^H G_tilde_t``.

    ``x^H Q_glob x = sum_t area_t sab_t`` is the total absorbed power in W (per
    transmitted watt when ``||x||^2 = 1``). Built as a single area-weighted Gram so
    the global and local operators share one channel realisation.
    """
    g = np.ascontiguousarray(g_tilde, dtype=np.complex128)
    t, three, m = g.shape
    w = np.sqrt(np.maximum(np.asarray(areas, dtype=float).ravel(), 0.0))
    a = (g * w[:, None, None]).reshape(t * three, m)
    return a.conj().T @ a


def region_operator(g_tilde: np.ndarray, cols: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Local exposure operator ``Q_r = sum_t G_avg[r, t] G_tilde_t^H G_tilde_t``.

    ``cols`` / ``weights`` are the nonzero column indices and values of averaging
    matrix row ``r`` (the few triangles inside the 4 cm^2 window), so
    ``x^H Q_r x = (G_avg @ sab)_r`` is the spatially-averaged S_ab there. Built
    lazily, only for the regions constraint generation actually visits.
    """
    g = np.ascontiguousarray(g_tilde, dtype=np.complex128)
    sub = g[np.asarray(cols, dtype=np.intp)]  # (n, 3, M)
    w = np.sqrt(np.maximum(np.asarray(weights, dtype=float).ravel(), 0.0))
    a = (sub * w[:, None, None]).reshape(-1, sub.shape[-1])
    return a.conj().T @ a


def build_ecbf_absolute(
    g_tilde: np.ndarray,
    areas: np.ndarray,
    g_avg,
    h: np.ndarray,
    freq_hz: float,
    mass: float | None,
    power_w: float,
    sar_wb_on: bool = True,
    peak_on: bool = True,
    scenario: str = "general_public",
    max_gen: int = 8,
    max_regions: int = 16,
    q_glob: np.ndarray | None = None,
) -> dict:
    """Absolute-limit ECBF precoder against the active ICNIRP restrictions.

    Enforces whole-body SAR (``sar_wb_on``) and/or peak 4 cm^2 S_ab (``peak_on``)
    as absolute quadratic constraints at transmit power ``power_w`` [W]. Returns

        {x, regime, per_constraint, n_regions_active, n_gen_iters, converged, ...}

    where ``regime`` is one of ``free`` / ``sar_wb`` / ``peak_sab`` / ``both`` /
    ``infeasible`` (which restriction binds), and ``per_constraint`` lists each
    enforced restriction with its value, limit, utilisation and active flag.

    Limits come from :func:`aegis.compliance.icnirp_limits`. The 4 cm^2 S_ab limit
    only exists above 6 GHz; at or below it ``peak_on`` is ignored (falls back to
    SAR_wb-only). When ``mass`` is unknown the SAR_wb restriction is skipped.

    ``q_glob`` optionally supplies the whole-body operator ``Q_glob`` (which is
    independent of the transmit power), so a power sweep can build it once and pass
    it to every point instead of re-forming the area-weighted Gram each call.
    """
    from aegis.coherent import solve_multibody_ecbf
    from aegis.compliance import ExposureScenario, icnirp_limits

    g_tilde = np.ascontiguousarray(g_tilde, dtype=np.complex128)
    areas = np.asarray(areas, dtype=float).ravel()
    h = np.asarray(h, dtype=np.complex128).ravel()
    m = h.shape[0]
    p = float(power_w)
    if p <= 0:
        raise ValueError(f"power_w must be positive, got {power_w}")

    scen = ExposureScenario.OCCUPATIONAL if str(scenario) == "occupational" else ExposureScenario.GENERAL_PUBLIC
    limits = icnirp_limits(scen, freq_hz=float(freq_hz))
    l_wb = float(limits.sar_wb)
    l_loc = limits.sab_4cm2  # None at or below 6 GHz

    has_mass = mass is not None and float(mass) > 0
    sar_active = bool(sar_wb_on) and has_mass
    peak_active = bool(peak_on) and (l_loc is not None)

    # Active constraint set. Order is the entry order in lambdas, so names[] maps
    # each multiplier back to the restriction it enforces.
    q_list: list[np.ndarray] = []
    l_list: list[float] = []
    names: list = []
    if sar_active:
        q_list.append(global_operator(g_tilde, areas) if q_glob is None else np.asarray(q_glob))
        l_list.append(l_wb * float(mass))
        names.append("sar_wb")

    indptr = np.asarray(g_avg.indptr)
    indices = np.asarray(g_avg.indices)
    data = np.asarray(g_avg.data)

    lambda_init: np.ndarray | None = None
    diag = None
    region_rows: list[int] = []
    n_gen_iters = 0
    cap_hit = False
    x = np.sqrt(p) * np.conj(h) / max(float(np.linalg.norm(h)), 1e-30)

    while True:
        if q_list:
            w_mat, diag = solve_multibody_ecbf(
                h[None, :],
                q_list,
                l_list,
                p,
                noise_power=None,
                return_diagnostics=True,
                lambda_init=lambda_init,
            )
            x = np.asarray(w_mat).reshape(m, -1)[:, 0]
            lambda_init = np.asarray(diag.lambdas, dtype=float).copy()
        else:
            # No enforceable restriction yet: matched filter at full power.
            x = np.sqrt(p) * np.conj(h) / max(float(np.linalg.norm(h)), 1e-30)
            diag = None

        if not peak_active:
            break

        sab = deposited_sab(g_tilde, x)
        avg = np.asarray(g_avg @ sab).ravel()
        if avg.size == 0:
            break
        r_max = int(np.argmax(avg))
        if avg[r_max] <= l_loc * (1.0 + _PEAK_TOL):
            break  # feasible: no region exceeds the local limit beyond tolerance
        if r_max in region_rows:
            # The worst region is already enforced (projected onto the limit) yet
            # still flags as violating: the joint solve cannot push it below
            # tolerance, so stop rather than spin and report non-convergence.
            cap_hit = True
            break
        if len(region_rows) >= max_regions or n_gen_iters >= max_gen:
            cap_hit = True
            break

        s, e = int(indptr[r_max]), int(indptr[r_max + 1])
        q_list.append(region_operator(g_tilde, indices[s:e], data[s:e]))
        l_list.append(float(l_loc))
        names.append(("region", r_max))
        region_rows.append(r_max)
        if lambda_init is not None:
            # solve_multibody_ecbf requires lambda_init.shape == (B,); pad the new
            # region's multiplier with a cold 0 so the warm start does not crash.
            lambda_init = np.concatenate([lambda_init, [0.0]])
        n_gen_iters += 1

    if cap_hit:
        logger.warning(
            "absolute ECBF: local-peak constraint generation hit the cap "
            "(regions=%d, gen_iters=%d) at %.3g GHz, P=%.3g W; peak may still exceed L_loc",
            len(region_rows),
            n_gen_iters,
            float(freq_hz) / 1e9,
            p,
        )

    solver_failed = diag is not None and (diag.method == "min-absorption" or not diag.converged)

    # A restriction is active (binding) when its absorbed power sits on its budget.
    # This is the KKT active set, read off the primal (p_abs == L) rather than the
    # dual multipliers, which is robust to the tiny residual lambdas the Newton
    # ascent can leave on a slack constraint once a tighter one takes over.
    glob_active = False
    n_regions_active = 0
    if diag is not None:
        p_abs_u = np.asarray(diag.p_abs, dtype=float)
        l_u = np.maximum(np.asarray(diag.L, dtype=float), 1e-30)
        for nm, util in zip(names, p_abs_u / l_u, strict=False):
            if util >= 1.0 - _BINDING_TOL:
                if nm == "sar_wb":
                    glob_active = True
                else:
                    n_regions_active += 1
    region_active = n_regions_active > 0

    if solver_failed:
        regime = "infeasible"
    elif glob_active and region_active:
        regime = "both"
    elif glob_active:
        regime = "sar_wb"
    elif region_active:
        regime = "peak_sab"
    else:
        regime = "free"

    # Final readout at the returned beam.
    sab = deposited_sab(g_tilde, x)
    avg = np.asarray(g_avg @ sab).ravel()
    p_abs_w = float(np.sum(sab * areas))

    per_constraint: list[dict] = []
    if sar_active:
        sar_val = p_abs_w / float(mass)
        per_constraint.append(
            {
                "name": "sar_wb",
                "value": sar_val,
                "limit": l_wb,
                "unit": "W/kg",
                "utilisation": (sar_val / l_wb) if l_wb > 0 else None,
                "active": glob_active,
            }
        )
    if peak_active:
        peak_val = float(avg.max()) if avg.size else 0.0
        per_constraint.append(
            {
                "name": "peak_sab",
                "value": peak_val,
                "limit": float(l_loc),
                "unit": "W/m^2",
                "utilisation": (peak_val / float(l_loc)) if l_loc > 0 else None,
                "active": region_active,
            }
        )

    converged = (not cap_hit) and (not solver_failed)

    return {
        "x": x,
        "regime": regime,
        "per_constraint": per_constraint,
        "n_regions_active": int(n_regions_active),
        "n_region_constraints": len(region_rows),
        "n_gen_iters": int(n_gen_iters),
        "converged": bool(converged),
        "cap_hit": bool(cap_hit),
        "p_abs_w": p_abs_w,
        "power_w": p,
    }
