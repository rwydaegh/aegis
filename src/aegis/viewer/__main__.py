"""Launch the AEGIS interactive viewer.

Usage
-----
    py -3.12 -m aegis.viewer                                # empty scene, load via UI
    py -3.12 -m aegis.viewer --location "Ghent, Belgium"    # fetch and load
    py -3.12 -m aegis.viewer --voxel-dir path/to/voxels/    # use local data
    py -3.12 -m aegis.viewer --bbox 40                      # 40m scene box
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path

# Load .env from project root if present
_env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())


def _kill_previous_on_port(port: int) -> None:
    """Kill any existing process listening on the given port (Windows only)."""
    if sys.platform != "win32":
        return
    try:
        out = subprocess.check_output(["netstat", "-aon"], text=True, stderr=subprocess.DEVNULL)
        pids_killed = set()
        my_pid = os.getpid()
        for line in out.splitlines():
            if f"127.0.0.1:{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid != my_pid and pid not in pids_killed:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        pids_killed.add(pid)
                    except OSError:
                        pass
        if pids_killed:
            import time

            time.sleep(1)
            print(f"  Killed {len(pids_killed)} old viewer process(es) on port {port}")
    except Exception:
        pass


def _fetch_location(location: str, radius: int, cache_dir: str | None) -> str | None:
    """Fetch voxels for a location via the pipeline. Returns voxel dir path or None."""
    from aegis.viewer.pipeline import cache_dir_for, find_pipeline, run_pipeline

    pipeline_js = find_pipeline()
    if pipeline_js is None:
        print("  Warning: nodejs-voxelearth pipeline not found, cannot fetch location")
        return None

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("  Warning: GOOGLE_API_KEY not set, cannot fetch location")
        return None

    base_cache = Path(cache_dir or os.environ.get("VOXELEARTH_CACHE_DIR") or str(pipeline_js.parent / "pipeline_cache"))
    voxel_output = cache_dir_for(location, radius, base_cache)

    # Check cache
    if voxel_output.exists() and any(voxel_output.glob("*.json")):
        print(f"  Using cached voxels: {voxel_output}")
        return str(voxel_output)

    # Run pipeline
    print(f"  Fetching voxels for '{location}' (radius={radius}m)...")
    pipeline_output = voxel_output.parent
    for line in run_pipeline(location, radius, api_key, pipeline_output):
        print(f"    {line}")
        if line.startswith("ERROR:"):
            return None

    if voxel_output.exists() and any(voxel_output.glob("*.json")):
        return str(voxel_output)

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS interactive 3D viewer")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--location",
        default=None,
        help="Location to fetch voxels for (e.g. 'Ghent, Belgium')",
    )
    parser.add_argument("--voxel-json", default=None, help="Path to voxel JSON file")
    parser.add_argument(
        "--voxel-dir",
        default=None,
        help="Path to directory of voxel JSON files",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        default=30.0,
        help="Scene bounding box size in meters (default: 30)",
    )
    parser.add_argument("--body", default="thelonious", help="Body mesh name (without .stl)")
    parser.add_argument("--data-dir", default=None, help="Path to data directory")
    parser.add_argument(
        "--pipeline-dir",
        default=None,
        help="Path to nodejs-voxelearth (default: auto-detect)",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Pipeline output cache directory",
    )
    parser.add_argument("--no-open", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    data_dir = args.data_dir
    if data_dir is None:
        data_dir = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data")

    # Resolve voxel source: explicit dir > explicit json > location fetch
    voxel_dir = args.voxel_dir
    voxel_json = args.voxel_json
    if not voxel_dir and not voxel_json and args.location:
        voxel_dir = _fetch_location(
            args.location,
            int(args.bbox / 2),
            args.cache_dir,
        )

    _kill_previous_on_port(args.port)

    from aegis.viewer.server import create_app

    app = create_app(
        data_dir=data_dir,
        voxel_json=voxel_json,
        voxel_dir=voxel_dir,
        bbox_radius=args.bbox / 2.0,
        body_name=args.body,
        pipeline_dir=args.pipeline_dir,
        cache_dir=args.cache_dir,
    )

    url = f"http://{args.host}:{args.port}"
    print(f"\n  AEGIS Viewer: {url}\n")

    if not args.no_open:
        webbrowser.open(url)

    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
