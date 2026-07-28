"""Headless study run entry.

One config to one run. Builds the city, samples the synchronized crowd, places a
sectored deployment, walks each agent through the time loop, reduces to per-person
exposure, and writes results (NPZ + JSON + a CDF figure). Job-array friendly via
``--agent-start`` / ``--agent-count``.

The orchestration (``run_study``) is separated from the physics (``RealKernel``)
so the control flow is testable with a fake kernel. The real kernel pulls in the
ray tracer, the coherent kernel, and the body poser.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from aegis.study.config import StudyConfig
from aegis.study.deployment import sectors_illuminating
from aegis.study.loop import run_agent
from aegis.study.reduce import as_icnirp_fraction, population_cdf, time_average


def _cadences(cfg: StudyConfig, n_slots: int) -> tuple[int, int]:
    """Resolve pose/recompute cadences, falling back if the spike has not run."""
    pose = cfg.temporal.pose_period or max(1, n_slots // 4)
    recompute = cfg.temporal.recompute_period or max(1, n_slots // 4)
    return pose, recompute


def run_study(cfg, agents, sites, kernel, out_dir, freq_hz, city=None) -> dict:
    """Run the crowd and write results. ``kernel`` supplies the physics callables.

    ``city`` (a CityCache), when given, adds per-city morphology covariates to
    the summary so the cross-city spread can be explained, not just stated.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_slots = max((len(a.trajectory.positions) for a in agents), default=0)
    pose_period, recompute_period = _cadences(cfg, n_slots)

    p_abs_w = []
    icnirp_frac = []
    is_user = []
    for agent in agents:
        result = run_agent(
            agent,
            sites,
            pose_period,
            recompute_period,
            pose_fn=kernel.pose_fn,
            channel_fn=kernel.channel_fn,
            gram_fn=kernel.gram_fn,
            refresh_fn=kernel.refresh_fn,
            beam_fn=kernel.beam_fn,
            sab_fn=getattr(kernel, "sab_fn", None),
        )
        p_abs_w.append(time_average(result.exposure_w))
        if result.peak_sab_w_m2 is not None:
            density = time_average(result.peak_sab_w_m2)
            icnirp_frac.append(as_icnirp_fraction(density, freq_hz=freq_hz))
        is_user.append(bool(result.is_user))

    p_abs_w = np.asarray(p_abs_w)
    icnirp_frac = np.asarray(icnirp_frac)
    is_user = np.asarray(is_user)

    np.savez(
        out_dir / "exposure.npz",
        p_abs_w=p_abs_w,
        icnirp_fraction=icnirp_frac,
        is_user=is_user,
    )

    # Headline CDF is the ICNIRP fraction when available, else absorbed power.
    headline = icnirp_frac if icnirp_frac.size else p_abs_w
    x, f = population_cdf(headline)
    summary = {
        "n_agents": int(len(agents)),
        "n_users": int(is_user.sum()),
        "freq_hz": float(freq_hz),
        "headline": "icnirp_fraction" if icnirp_frac.size else "p_abs_w",
        "cdf_x": x.tolist(),
        "cdf_f": f.tolist(),
        "median": float(np.median(headline)) if headline.size else None,
        "p95": float(np.percentile(headline, 95)) if headline.size else None,
    }
    # Users are periodically the beam target, bystanders never are: the split
    # matters, so publish both sub-CDFs alongside the whole-population one.
    if headline.size == is_user.shape[0]:
        for label, mask in (("users", is_user), ("bystanders", ~is_user)):
            xs, fs = population_cdf(headline[mask])
            summary[f"cdf_x_{label}"] = xs.tolist()
            summary[f"cdf_f_{label}"] = fs.tolist()
            summary[f"median_{label}"] = float(np.median(headline[mask])) if mask.any() else None

    # Whole-body SAR context: absorbed power / phantom mass against the ICNIRP
    # 2020 whole-body basic restriction. Nearly free, and it anchors the CDF to
    # a compliance scale even when the expensive peak-Sab map is off.
    phantom = getattr(getattr(getattr(kernel, "poser", None), "base_mesh", None), "name", None)
    if phantom is not None and p_abs_w.size:
        from aegis.compliance import ExposureScenario, icnirp_limits
        from aegis.study.covariates import phantom_mass_kg

        mass = phantom_mass_kg(phantom)
        if mass:
            sar_med = float(np.median(p_abs_w)) / mass
            limit = icnirp_limits(scenario=ExposureScenario.GENERAL_PUBLIC, freq_hz=freq_hz).sar_wb
            summary["phantom"] = phantom
            summary["mass_kg"] = mass
            summary["sar_wb_median_w_kg"] = sar_med
            summary["icnirp_wb_fraction_median"] = sar_med / limit

    if city is not None:
        from aegis.study.covariates import city_covariates

        summary["covariates"] = city_covariates(city, sites, agents, cfg.cities.radius_m)

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    _write_cdf_figure(x, f, summary["headline"], out_dir / "cdf.png")
    _write_scene_json(out_dir, agents, sites, p_abs_w, is_user)
    return summary


def _write_scene_json(out_dir, agents, sites, p_abs_w, is_user):
    """Dump exact deployment + walks + per-agent exposure for visualization (and
    as a step toward a replay artifact). Positions are local XY metres."""
    scene = {
        "sites": [
            {
                "position": [float(s.position[0]), float(s.position[1]), float(s.position[2])],
                "sectors": [
                    {
                        "boresight_az_deg": float(sec.boresight_az_deg),
                        "az_coverage_deg": float(sec.az_coverage_deg),
                        "max_range_m": float(sec.max_range_m),
                        "m_ant": int(sec.m_ant),
                    }
                    for sec in s.sectors
                ],
            }
            for s in sites
        ],
        "agents": [
            {
                "agent_id": int(a.agent_id),
                "is_user": bool(is_user[i]) if i < len(is_user) else bool(a.is_user),
                "exposure_w": float(p_abs_w[i]) if i < len(p_abs_w) else None,
                "positions": np.asarray(a.trajectory.positions, dtype=float).tolist(),
            }
            for i, a in enumerate(agents)
        ],
    }
    (out_dir / "scene.json").write_text(json.dumps(scene))


def _write_cdf_figure(x, f, headline, path):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        try:
            import scienceplots  # noqa: F401

            plt.style.use(["science", "ieee"])
        except Exception:
            pass

        fig, ax = plt.subplots(figsize=(3.3, 2.5))
        if x.size:
            ax.step(x, f, where="post")
        ax.set_xlabel(headline)
        ax.set_ylabel("CDF")
        ax.set_ylim(0, 1)
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
    except Exception as exc:  # pragma: no cover - figure is non-essential
        print(f"CDF figure skipped: {exc}")


class RealKernel:
    """Physics callables backed by the ray tracer and the coherent kernel."""

    def __init__(
        self,
        scene,
        engine,
        poser,
        sites,
        freq_hz,
        level,
        user_agents,
        recompute_period,
        torso_z=1.1,
        rt_engine="sionna",
        samples_per_src=None,
        diffraction=None,
        max_center_paths=None,
        compute_peak_sab=True,
    ):
        self.scene = scene
        self.engine = engine
        self.poser = poser
        self.sites = sites
        self.freq_hz = freq_hz
        self.level = level
        self.user_agents = list(user_agents)
        self.recompute_period = max(1, int(recompute_period))
        self.torso_z = torso_z
        self.rt_engine = rt_engine
        self.samples_per_src = samples_per_src
        self.diffraction = diffraction
        self.max_center_paths = max_center_paths
        # run_study reads kernel.sab_fn via getattr; None disables the per-triangle
        # map so only the cheap scalar exposure is computed.
        self.sab_fn = self._peak_sab if compute_peak_sab else None
        self._beam_cache: dict = {}

    def _trace_kwargs(self):
        # Traces always run at the 30 dBm = 1 W field reference: the configured
        # transmit power enters the exposure exactly once, via the MRT
        # normalization ||x||^2 = sector.tx_power_w. Passing the config power
        # here as well would square it.
        kw = {"tx_power_dbm": 30.0}
        if self.samples_per_src is not None:
            kw["samples_per_src"] = int(self.samples_per_src)
        if self.diffraction is not None:
            kw["diffraction"] = bool(self.diffraction)
        if self.max_center_paths is not None:
            kw["max_center_paths"] = int(self.max_center_paths)
        return kw

    def pose_fn(self, pos_xy, heading_rad, frame_idx, z_ground):
        return self.poser.pose(pos_xy, heading_rad, z_ground=z_ground, frame_idx=frame_idx)

    def channel_fn(self, sector, body, pos_xy):
        from aegis.study.channel_det import center_paths

        rx = np.array([pos_xy[0], pos_xy[1], self.torso_z])
        return center_paths(self.scene, sector, rx, self.freq_hz, engine=self.rt_engine, **self._trace_kwargs())

    def gram_fn(self, body, center_paths, sector):
        from aegis.study.exposure import build_static_gram

        return build_static_gram(body, center_paths, sector.array, self.freq_hz)

    def refresh_fn(self, m_static, center_k_hat, delta3):
        from aegis.study.exposure import refresh_Q

        return refresh_Q(m_static, center_k_hat, delta3, self.freq_hz)

    def _served_users(self, sector, t):
        served = []
        for ua in self.user_agents:
            pos = ua.trajectory.positions[min(t, len(ua.trajectory.positions) - 1)]
            pos3 = np.array([pos[0], pos[1], ua.z_ground])
            if any(s is sector for s in sectors_illuminating(pos3, self.sites)):
                served.append(ua)
        return served

    def beam_fn(self, sector, t):
        m_ant = sector.m_ant
        served = self._served_users(sector, t)
        if not served:
            return np.zeros(m_ant, dtype=complex)
        user = served[t % len(served)]  # round-robin time-share
        rf = (t // self.recompute_period) * self.recompute_period
        key = (id(sector), user.agent_id, rf)
        if key not in self._beam_cache:
            self._beam_cache[key] = self._mrt_to_user(sector, user, rf)
        return self._beam_cache[key]

    def _mrt_to_user(self, sector, user, slot):
        from aegis.mimo.array_paths import expand_paths_to_array
        from aegis.study.channel_det import center_paths
        from aegis.study.precoding import mrt_for_user, user_channel_vector

        pos = user.trajectory.positions[min(slot, len(user.trajectory.positions) - 1)]
        rx = np.array([pos[0], pos[1], self.torso_z])
        center = center_paths(self.scene, sector, rx, self.freq_hz, engine=self.rt_engine, **self._trace_kwargs())
        per_elem = expand_paths_to_array(center, sector.array, self.freq_hz)
        h = user_channel_vector(per_elem, sector.m_ant)
        if not np.any(np.abs(h) > 0):
            # Deep-shadowed user with zero traced channel: a real scheduler
            # would not serve it, and Precoder.mrt's e_0 fallback would blast
            # full power on one element instead. Keep the sector silent.
            return np.zeros(sector.m_ant, dtype=complex)
        return mrt_for_user(h, sector.tx_power_w).x

    def _peak_sab(self, body, sector, x, center_paths):
        from aegis.mimo.array_paths import expand_paths_to_array
        from aegis.precoder import Precoder

        per_elem = expand_paths_to_array(center_paths, sector.array, self.freq_hz)
        result = self.engine.compute(body, per_elem, level=self.level, precoder=Precoder(x=x))
        peak = result.peak_sab_averaged
        return 0.0 if peak is None else float(peak)


def _sample_xy_in_disk(rng, radius_m):
    """Uniform point in a disk of the given radius (server XY, metres)."""
    import numpy as np

    r = radius_m * np.sqrt(rng.uniform())
    a = rng.uniform(0.0, 2.0 * np.pi)
    return np.array([r * np.cos(a), r * np.sin(a)])


def _directions_route_xy(city, rng, radius_m, cache_dir):  # pragma: no cover - network
    """A real Google Directions walking route between two uniformly sampled
    points in the core, returned as local XY (the study/mesh frame).

    Origin/destination are sampled uniformly in the disk (population weighting is
    deferred). Endpoints are projected to lat/lon for the Directions call, and
    the returned street polyline is projected back to the local frame so the walk
    shares the mesh origin. Falls back to the straight OD line only if the API
    cannot route this pair, with a logged warning (not silent)."""
    import numpy as np

    from aegis.study.geo import enu_to_latlon, latlon_to_enu
    from aegis.study.mobility import route_walk

    o_xy = _sample_xy_in_disk(rng, 0.85 * radius_m)
    d_xy = _sample_xy_in_disk(rng, 0.85 * radius_m)
    o_ll = enu_to_latlon(float(o_xy[0]), float(o_xy[1]), city.origin_lat, city.origin_lon)
    d_ll = enu_to_latlon(float(d_xy[0]), float(d_xy[1]), city.origin_lat, city.origin_lon)
    try:
        coords = route_walk(o_ll, d_ll, cache_dir)
        xy = np.array([latlon_to_enu(lat, lon, city.origin_lat, city.origin_lon) for lat, lon in coords])
        if xy.shape[0] >= 2:
            return xy
        print(f"[walk] degenerate route ({xy.shape[0]} pts), using straight OD")
    except Exception as exc:
        print(f"[walk] Directions failed ({exc}); using straight OD for this agent")
    return np.array([o_xy, d_xy])


def _build_agents(cfg, city, rng, agent_start, agent_count, cache_dir, seed=0):  # pragma: no cover
    """Build the crowd. ``routing='directions'`` walks real Google street routes;
    otherwise synthetic radial diameters across the core."""
    import numpy as np

    from aegis.study.loop import Agent
    from aegis.study.walk import sample_trajectory

    n = cfg.mobility.n_agents
    radius_m = cfg.cities.radius_m
    routing = getattr(cfg.mobility, "routing", "radial")
    max_slots = max(2, int(round(cfg.mobility.window_s / 1.0)))
    # User assignment honours mobility.user_fraction, drawn from the seed alone
    # (not the shared rng stream) so job-array shards agree on who the users are.
    n_users = int(round(float(cfg.mobility.user_fraction) * n))
    users = set(np.random.default_rng([int(seed), 1701]).permutation(n)[:n_users].tolist())

    agents = []
    for i in range(agent_start, min(agent_start + agent_count, n)):
        if routing == "directions":
            route = _directions_route_xy(city, rng, radius_m, cache_dir)
        else:
            ang = 2 * np.pi * i / n
            route = np.array(
                [[-radius_m * np.cos(ang), -radius_m * np.sin(ang)], [radius_m * np.cos(ang), radius_m * np.sin(ang)]]
            )
        traj = sample_trajectory(route, cfg.mobility.walk_speed_mps, dt_s=1.0)
        # Bound the walk to the synchronised window so per-agent cost stays fixed
        # regardless of how long a sampled OD route happens to be.
        if len(traj.positions) > max_slots:
            traj = type(traj)(
                positions=traj.positions[:max_slots],
                headings_rad=traj.headings_rad[:max_slots],
                t0_s=traj.t0_s,
            )
        agents.append(Agent(trajectory=traj, is_user=(i in users), agent_id=i))
    return agents


def _build_real(cfg, out_dir, seed, agent_start, agent_count, city_latlon=(51.0536, 3.7253)):  # pragma: no cover
    import numpy as np

    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.study.bodies import StaticPhantomPoser
    from aegis.study.city import CityCache
    from aegis.study.deployment import build_sites, select_rooftop_sites
    from aegis.tissue.dielectric import TissueModel

    rng = np.random.default_rng(seed)
    eq = cfg.deployment.equipment
    freq = eq.freq_hz

    lat, lon = float(city_latlon[0]), float(city_latlon[1])
    city = CityCache.build(lat, lon, cfg.cities.radius_m, out_dir / "city")
    n_sites = max(1, int(round(3 * cfg.deployment.densification)))
    site_xy = select_rooftop_sites(
        city.candidates,
        n_sites,
        rng,
        min_spacing_m=60.0,
        height_band_m=(cfg.deployment.site_height_min_m, cfg.deployment.site_height_max_m),
        mount_height_m=cfg.deployment.mount_height_m,
    )
    if site_xy.shape[0] == 0:
        site_xy = np.array([[0.0, 0.0, 15.0]])
    sites = build_sites(
        site_xy,
        cfg.deployment.sectoring.sectors,
        cfg.deployment.sectoring.az_coverage_deg,
        cfg.deployment.sectoring.max_range_m,
        freq,
        eq.array,
        eq.tx_power_dbm,
        downtilt_deg=cfg.deployment.sectoring.downtilt_deg,
        rng=rng,
    )

    agents = _build_agents(cfg, city, rng, agent_start, agent_count, out_dir / "routes", seed=seed)

    from aegis.study.covariates import data_dir

    poser = StaticPhantomPoser(BodyMesh.load(data_dir() / "duke.stl", name="duke"))
    engine = DosimetryEngine(TissueModel.from_database("Skin", freq))
    n_slots = max((len(a.trajectory.positions) for a in agents), default=1)
    _, recompute_period = _cadences(cfg, n_slots)
    kernel = RealKernel(
        city.sionna_scene,
        engine,
        poser,
        sites,
        freq,
        cfg.dosimetry.level,
        [a for a in agents if a.is_user],
        recompute_period,
        rt_engine="sionna",
        samples_per_src=getattr(cfg.channel, "samples_per_src", None),
        diffraction=getattr(cfg.channel, "diffraction", None),
        max_center_paths=getattr(cfg.channel, "max_center_paths", None),
        compute_peak_sab=getattr(cfg.dosimetry, "peak_sab", True),
    )
    return agents, sites, kernel, freq, city


def _resolve_city(spec: str | None, cfg) -> tuple[float, float]:
    """Resolve --city into (lat, lon): 'lat,lon' literal, a name from
    cfg.cities.specs, or a name from run_cities.DEFAULT_CITIES. Defaults to
    Ghent when omitted (the historical single-city behavior)."""
    if spec is None:
        return (51.0536, 3.7253)
    if "," in spec:
        lat, lon = spec.split(",", 1)
        return (float(lat), float(lon))
    from aegis.study.run_cities import DEFAULT_CITIES

    for entry in list(getattr(cfg.cities, "specs", []) or []) + DEFAULT_CITIES:
        if entry.get("name") == spec:
            return (float(entry["lat"]), float(entry["lon"]))
    raise SystemExit(f"unknown city {spec!r}: not in cities.specs or DEFAULT_CITIES")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="HPC population-exposure study run")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", default="results/study_run")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--agent-start", type=int, default=0)
    parser.add_argument("--agent-count", type=int, default=None)
    parser.add_argument(
        "--city",
        default=None,
        help="city name (cities.specs or DEFAULT_CITIES) or 'lat,lon'; default Ghent",
    )
    args = parser.parse_args(argv)

    cfg = StudyConfig.from_yaml(args.config)
    seed = args.seed if args.seed is not None else cfg.channel.seed
    agent_count = args.agent_count if args.agent_count is not None else cfg.mobility.n_agents
    out_dir = Path(args.out)

    agents, sites, kernel, freq, city = _build_real(
        cfg, out_dir, seed, args.agent_start, agent_count, city_latlon=_resolve_city(args.city, cfg)
    )
    summary = run_study(cfg, agents, sites, kernel, out_dir, freq, city=city)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
