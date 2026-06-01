"""Multi-city batch driver: run the study across a list of cities and overlay
their population-exposure CDFs into one figure.

Reads the city list from ``cfg.cities.specs`` (each entry a dict with ``name``,
``lat``, ``lon``). Each city is built and run independently into its own output
subdirectory via the single-city pipeline in :mod:`aegis.study.run`, then the
per-city CDFs are collected into one overlay plot and a combined summary. A city
that fails (network, empty mesh, no illuminated receiver) is logged and skipped
so one bad city does not sink the batch.

This is the driver behind the headline deliverable: ten cities of differing
morphology, one CDF figure.
"""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

import numpy as np

from aegis.study.config import StudyConfig
from aegis.study.run import _build_real, run_study

# Default city set: ten real cores of deliberately distinct morphology. Used when
# the config carries no explicit ``cities.specs``. Coordinates are city-centre-ish
# points; the same radius_m is applied to each so the analysis area is fixed.
DEFAULT_CITIES = [
    {"name": "ghent", "lat": 51.0536, "lon": 3.7253},  # dense medieval European core
    {"name": "manhattan", "lat": 40.7589, "lon": -73.9851},  # high-rise grid
    {"name": "barcelona", "lat": 41.3851, "lon": 2.1734},  # Eixample uniform grid
    {"name": "amsterdam", "lat": 52.3676, "lon": 4.9041},  # low-rise canal
    {"name": "tokyo", "lat": 35.6595, "lon": 139.7005},  # dense Asian high-rise (Shibuya)
    {"name": "los_angeles", "lat": 34.0407, "lon": -118.2468},  # downtown sprawl
    {"name": "dubai", "lat": 25.1972, "lon": 55.2744},  # sparse modern towers
    {"name": "paris", "lat": 48.8566, "lon": 2.3522},  # Haussmann uniform mid-rise
    {"name": "london", "lat": 51.5128, "lon": -0.0918},  # mixed historic + towers (City)
    {"name": "sao_paulo", "lat": -23.5505, "lon": -46.6333},  # dense vertical Latin American
]


def _cities(cfg) -> list[dict]:
    specs = list(getattr(cfg.cities, "specs", []) or [])
    if specs:
        return specs
    return DEFAULT_CITIES[: max(1, int(cfg.cities.count))]


def run_cities(cfg, out_dir, seed) -> dict:
    """Run every city in the config and write a combined CDF overlay."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cities = _cities(cfg)

    results = []
    for spec in cities:
        name = spec["name"]
        city_out = out_dir / name
        print(f"[run_cities] building + running {name} ({spec['lat']}, {spec['lon']})")
        try:
            agents, sites, kernel, freq = _build_real(
                cfg, city_out, seed, 0, cfg.mobility.n_agents, city_latlon=(spec["lat"], spec["lon"])
            )
            summary = run_study(cfg, agents, sites, kernel, city_out, freq)
            summary["name"] = name
            results.append(summary)
            print(f"[run_cities] {name} done: n={summary['n_agents']} median={summary.get('median')}")
        except Exception:
            print(f"[run_cities] {name} FAILED, skipping:\n{traceback.format_exc()}")

    combined = {
        "n_cities_requested": len(cities),
        "n_cities_succeeded": len(results),
        "cities": results,
    }
    (out_dir / "cities_summary.json").write_text(json.dumps(combined, indent=2))
    _overlay_cdf(results, out_dir / "cities_cdf")
    return combined


def _overlay_cdf(results, path_stem):
    """One overlaid step-CDF per city. Saves PDF (vector) and PNG (preview)."""
    if not results:
        print("[run_cities] no successful cities, skipping overlay figure")
        return
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        try:
            import scienceplots  # noqa: F401

            plt.style.use(["science", "ieee"])
        except Exception:
            pass

        headline = results[0].get("headline", "exposure")
        fig, ax = plt.subplots(figsize=(3.5, 2.7))
        for r in results:
            x = np.asarray(r["cdf_x"], dtype=float)
            f = np.asarray(r["cdf_f"], dtype=float)
            if x.size:
                ax.step(x, f, where="post", label=r.get("name", "?"), lw=0.9)
        if headline == "icnirp_fraction":
            ax.set_xscale("log")
            ax.set_xlabel("ICNIRP fraction")
        else:
            ax.set_xlabel(headline)
        ax.set_ylabel("Population CDF")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=5, ncol=2, frameon=False)
        fig.tight_layout()
        fig.savefig(f"{path_stem}.pdf")
        fig.savefig(f"{path_stem}.png", dpi=200)
        plt.close(fig)
        print(f"[run_cities] wrote {path_stem}.pdf and .png")
    except Exception as exc:  # pragma: no cover - figure is non-essential
        print(f"[run_cities] overlay figure skipped: {exc}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Multi-city population-exposure study")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", default="results/cities")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    cfg = StudyConfig.from_yaml(args.config)
    seed = args.seed if args.seed is not None else cfg.channel.seed
    combined = run_cities(cfg, args.out, seed)
    print(json.dumps({k: v for k, v in combined.items() if k != "cities"}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
