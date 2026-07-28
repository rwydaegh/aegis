"""Deterministic vs stochastic exposure comparison primitives.

The study's headline question is whether the geometry-blind stochastic 3GPP
TR 38.901 channel reproduces the ray-traced (deterministic) population exposure.
This module holds the comparison core: the P_LOS-weighted LOS/NLOS exposure
blend and the paired, scale-invariant agreement metric.

The blend is at the exposure-operator level. Absorbed power is x^H Q x, linear in
Q, so the statistical mixture E[Sab] = p*E[Sab|LOS] + (1-p)*E[Sab|NLOS] is the
convex blend of the two operators, Q = p*Q_LOS + (1-p)*Q_NLOS. (LOS and NLOS
cluster sets have different path counts, so the blend is done at Q, which is
always M_ant x M_ant, not at the path-correlation gram.)
"""

from __future__ import annotations

import numpy as np

from aegis.study.exposure import build_static_gram, refresh_Q, scalar_exposure_w


def blend_Q(q_los, q_nlos, p_los_val):
    """Convex P_LOS blend of two exposure operators: p*Q_LOS + (1-p)*Q_NLOS."""
    p = float(np.clip(p_los_val, 0.0, 1.0))
    q = p * np.asarray(q_los) + (1.0 - p) * np.asarray(q_nlos)
    return 0.5 * (q + np.conj(q).T)  # keep Hermitian against round-off


def stochastic_Q(body, center_los, center_nlos, array, freq_hz, p_los_val):
    """Blended exposure operator from a LOS and an NLOS coherent 38.901 channel.

    Each channel is a center-of-array path set (from generate_coherent_channel);
    its gram is built and evaluated at zero translation to get Q, then the two
    are P_LOS-blended.
    """
    q_los = refresh_Q(build_static_gram(body, center_los, array, freq_hz), center_los.k_hat, np.zeros(3), freq_hz)
    q_nlos = refresh_Q(build_static_gram(body, center_nlos, array, freq_hz), center_nlos.k_hat, np.zeros(3), freq_hz)
    return blend_Q(np.asarray(q_los), np.asarray(q_nlos), p_los_val)


def stochastic_exposure_w(body, center_los, center_nlos, array, freq_hz, p_los_val, x) -> float:
    """Per-person stochastic absorbed power x^H Q x with the P_LOS-blended Q."""
    return scalar_exposure_w(stochastic_Q(body, center_los, center_nlos, array, freq_hz, p_los_val), x)


def compare_city(cfg, city_latlon, out_dir, seed=42):  # pragma: no cover - heavy
    """Run both arms on one city's crowd and write the det-vs-stoch comparison.

    For each agent at its mid-walk position, the served-user exposure is computed
    two ways under the same deployment: deterministic (ray-traced channel) and
    stochastic (coherent 38.901, P_LOS-blended Q). v1 simplifications: the beam is
    self-served (MRT toward the agent itself, so this is the served-user exposure,
    not bystander sidelobes), and the stochastic beam is built from the LOS
    realization while Q is the P_LOS blend. Writes det/stoch CDFs, the paired dB
    error, and a JSON summary.
    """
    from pathlib import Path

    import numpy as np

    from aegis.channel.generator import generate_coherent_channel
    from aegis.channel.path_loss import p_los
    from aegis.channel.presets import load_preset
    from aegis.mimo.array_paths import expand_paths_to_array
    from aegis.study.channel_det import _cap_paths, center_paths
    from aegis.study.deployment import sectors_illuminating
    from aegis.study.precoding import mrt_for_user, user_channel_vector
    from aegis.study.run import _build_real

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    agents, sites, kernel, freq, _city = _build_real(
        cfg, out_dir, seed, 0, cfg.mobility.n_agents, city_latlon=city_latlon
    )
    scene, poser = kernel.scene, kernel.poser
    freq_ghz = freq / 1e9
    env = getattr(cfg.channel, "stochastic_env", "umi")
    preset_env = {"umi": "UMi", "uma": "UMa"}[env.lower()]
    preset_dir = Path("data/channel_presets")
    los = load_preset(f"3GPP_38.901_{preset_env}_LOS", preset_dir)["params"]
    nlos = load_preset(f"3GPP_38.901_{preset_env}_NLOS", preset_dir)["params"]
    samp = getattr(cfg.channel, "samples_per_src", 3_000_000)
    cap = getattr(cfg.channel, "max_center_paths", 16)
    diffraction = getattr(cfg.channel, "diffraction", None)
    det_kw = {"samples_per_src": samp, "max_center_paths": cap}
    if diffraction is not None:
        det_kw["diffraction"] = bool(diffraction)
    torso_z = 1.1

    det_w, stoch_w = [], []
    n_skipped = 0
    for a in agents:
        pos = np.asarray(a.trajectory.positions)
        xy = pos[len(pos) // 2]
        rx = np.array([xy[0], xy[1], torso_z])
        lit = sectors_illuminating(rx, sites)
        if not lit:
            continue
        sector = lit[0]
        body = poser.pose(xy, heading_rad=0.0, z_ground=0.0)
        ant = np.asarray(sector.position, dtype=float)
        d2d = float(np.hypot(ant[0] - rx[0], ant[1] - rx[1]))
        # Deterministic arm. Both arms trace at the 30 dBm = 1 W field
        # reference; the configured transmit power enters exactly once, via the
        # MRT normalization ||x||^2 = tx_power_w.
        cdet = center_paths(scene, sector, rx, freq, engine="sionna", **det_kw)
        if cdet is None or cdet.k_hat is None or cdet.k_hat.shape[0] == 0:
            n_skipped += 1
            continue
        pe = expand_paths_to_array(cdet, sector.array, freq)
        xd = mrt_for_user(user_channel_vector(pe, sector.m_ant), sector.tx_power_w).x
        qd = refresh_Q(build_static_gram(body, cdet, sector.array, freq), cdet.k_hat, np.zeros(3), freq)
        e_det = scalar_exposure_w(qd, xd)
        # Stochastic arm (geometry-blind): per-hypothesis MRT beams, blended in
        # probability. Beam-matching only the LOS realization while blending Q
        # would bias low-P_LOS links (the NLOS term would see a random beam).
        # Channels are capped like the deterministic arm: the (N, N, M, M) gram
        # is quadratic in paths and an uncapped 400-sub-path NLOS draw is ~5 GB.
        xpr_l = float(los.get("XPR_mu", 8.0))
        xpr_n = float(nlos.get("XPR_mu", 8.0))
        cl = _cap_paths(
            generate_coherent_channel(los, freq_ghz, ant, rx, 30.0, seed=seed, xpr_db=xpr_l),
            cap,
            array=sector.array,
        )
        cn = _cap_paths(
            generate_coherent_channel(nlos, freq_ghz, ant, rx, 30.0, seed=seed + 1, xpr_db=xpr_n),
            cap,
            array=sector.array,
        )
        p = p_los(d2d, env)
        e_stoch = 0.0
        for c, weight in ((cl, p), (cn, 1.0 - p)):
            pe_s = expand_paths_to_array(c, sector.array, freq)
            xs = mrt_for_user(user_channel_vector(pe_s, sector.m_ant), sector.tx_power_w).x
            qs = refresh_Q(build_static_gram(body, c, sector.array, freq), c.k_hat, np.zeros(3), freq)
            e_stoch += weight * scalar_exposure_w(qs, xs)
        det_w.append(e_det)
        stoch_w.append(e_stoch)

    det_w = np.asarray(det_w)
    stoch_w = np.asarray(stoch_w)
    err = paired_db_error(det_w, stoch_w)
    summary = {
        "n_paired": int(det_w.size),
        "n_skipped_no_det_paths": int(n_skipped),
        "det_median_w": float(np.median(det_w)) if det_w.size else None,
        "stoch_median_w": float(np.median(stoch_w)) if stoch_w.size else None,
        "db_error_median": float(np.median(err)) if err.size else None,
        "db_error_p10": float(np.percentile(err, 10)) if err.size else None,
        "db_error_p90": float(np.percentile(err, 90)) if err.size else None,
        "det_w": det_w.tolist(),
        "stoch_w": stoch_w.tolist(),
    }
    import json

    (out_dir / "compare_summary.json").write_text(json.dumps(summary))
    _write_compare_figure(det_w, stoch_w, err, out_dir / "det_vs_stoch")
    return summary


def _write_compare_figure(det_w, stoch_w, err, stem):  # pragma: no cover - figure
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        try:
            import scienceplots  # noqa: F401

            plt.style.use(["science", "ieee"])
        except Exception:
            pass

        def cdf(v):
            x = np.sort(np.maximum(np.asarray(v), 1e-18))
            return x, np.arange(1, x.size + 1) / x.size

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 2.6))
        if det_w.size:
            ax1.step(*cdf(det_w), where="post", label="deterministic (RT)", lw=1.0)
            ax1.step(*cdf(stoch_w), where="post", label="stochastic (38.901)", lw=1.0, ls="--")
        ax1.set_xscale("log")
        ax1.set_xlabel(r"served-user $\mathbf{x}^H Q\,\mathbf{x}$ [W]")
        ax1.set_ylabel("CDF")
        ax1.legend(fontsize=5, frameon=False)
        if err.size:
            ax2.hist(err, bins=12, color="0.5")
            ax2.axvline(0.0, color="k", lw=0.8)
        ax2.set_xlabel("paired error 10 log10(stoch/det) [dB]")
        ax2.set_ylabel("agents")
        fig.tight_layout()
        fig.savefig(f"{stem}.pdf")
        fig.savefig(f"{stem}.png", dpi=200)
        plt.close(fig)
        print(f"wrote {stem}.pdf and .png")
    except Exception as exc:
        print(f"compare figure skipped: {exc}")


def paired_db_error(det_w, stoch_w, floor=1e-18):
    """Paired, scale-invariant error per person: 10 log10(stoch / det) [dB].

    Magnitude divides out, so high-exposure cities do not dominate. Values are
    clamped at ``floor`` to keep the log finite for uncovered (zero-exposure)
    pedestrians.
    """
    det = np.maximum(np.asarray(det_w, dtype=float), floor)
    stoch = np.maximum(np.asarray(stoch_w, dtype=float), floor)
    return 10.0 * np.log10(stoch / det)


def main(argv=None) -> int:  # pragma: no cover - heavy
    import argparse
    import json

    from aegis.study.config import StudyConfig

    ap = argparse.ArgumentParser(description="Deterministic vs stochastic exposure comparison for one city")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="results/compare")
    ap.add_argument("--lat", type=float, default=51.0536)
    ap.add_argument("--lon", type=float, default=3.7253)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)
    cfg = StudyConfig.from_yaml(args.config)
    summary = compare_city(cfg, (args.lat, args.lon), args.out, args.seed)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("det_w", "stoch_w")}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
