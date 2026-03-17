"""Launch the AEGIS interactive viewer.

Usage
-----
    py -3.12 -m aegis.viewer
    py -3.12 -m aegis.viewer --voxel-json ../nodejs-voxelearth/pipeline_output/voxels/tile.json
    py -3.12 -m aegis.viewer --voxel-dir ../nodejs-voxelearth/pipeline_output/voxels/
    py -3.12 -m aegis.viewer --port 8080 --max-voxels 50000
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path


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


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS interactive 3D viewer")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--voxel-json", default=None, help="Path to voxel JSON file")
    parser.add_argument(
        "--voxel-dir",
        default=None,
        help="Path to directory of voxel JSON files (alternative to --voxel-json)",
    )
    parser.add_argument("--max-voxels", type=int, default=60000)
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
        help="Pipeline output cache directory (default: <pipeline-dir>/pipeline_cache)",
    )
    parser.add_argument("--no-open", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    data_dir = args.data_dir
    if data_dir is None:
        # Default: ../../data relative to aegis repo root
        data_dir = str(Path(__file__).resolve().parent.parent.parent.parent.parent / "data")

    _kill_previous_on_port(args.port)

    from aegis.viewer.server import create_app

    app = create_app(
        data_dir=data_dir,
        voxel_json=args.voxel_json,
        voxel_dir=args.voxel_dir,
        max_voxels=args.max_voxels,
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
