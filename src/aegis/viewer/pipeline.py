"""Pipeline runner for the Voxel Earth Node.js pipeline."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Generator
from pathlib import Path

# Module-level handle for cancellation
_active_process: subprocess.Popen | None = None


def find_pipeline() -> Path | None:
    """Locate the run_pipeline.js script.

    Checks VOXELEARTH_DIR env var first, then auto-detects relative to the
    aegis repo root (../../nodejs-voxelearth).
    """
    env_dir = os.environ.get("VOXELEARTH_DIR")
    if env_dir:
        p = Path(env_dir) / "run_pipeline.js"
        if p.exists():
            return p

    # Auto-detect: aegis repo root -> ../../nodejs-voxelearth
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    candidates = [
        repo_root.parent / "nodejs-voxelearth" / "run_pipeline.js",
        repo_root.parent.parent / "nodejs-voxelearth" / "run_pipeline.js",
    ]
    for c in candidates:
        if c.exists():
            return c

    return None


def _slugify(text: str) -> str:
    """Convert location string to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "unnamed"


def cache_dir_for(location: str, radius: int, base_cache_dir: Path) -> Path:
    """Return the cache directory for a given location and radius."""
    slug = _slugify(location)
    return base_cache_dir / f"{slug}_r{radius}" / "voxels"


def run_pipeline(
    location: str,
    radius: int,
    api_key: str,
    output_dir: Path,
    resolution: int = 200,
) -> Generator[str]:
    """Run the Voxel Earth pipeline, yielding stdout lines for progress.

    Parameters
    ----------
    location : place name (e.g. "Ghent, Belgium")
    radius : radius in meters
    api_key : Google API key
    output_dir : directory for pipeline output (parent of voxels/)
    resolution : voxel resolution (default 200)

    Yields
    ------
    str : each line of stdout/stderr from the pipeline process
    """
    global _active_process

    pipeline_js = find_pipeline()
    if pipeline_js is None:
        yield "ERROR: run_pipeline.js not found"
        return

    node_bin = shutil.which("node")
    if node_bin is None:
        yield "ERROR: node not found in PATH"
        return

    cmd = [
        node_bin,
        str(pipeline_js),
        "--location",
        location,
        "--radius",
        str(radius),
        "--resolution",
        str(resolution),
        "--out",
        str(output_dir),
        "--key",
        api_key,
    ]

    env = os.environ.copy()
    env["GOOGLE_API_KEY"] = api_key

    yield f'Running: node run_pipeline.js --location "{location}" --radius {radius}'

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(pipeline_js.parent),
            env=env,
        )
        _active_process = proc

        for line in proc.stdout:
            line = line.rstrip("\n\r")
            if line:
                yield line

        proc.wait()
        _active_process = None

        if proc.returncode != 0:
            yield f"ERROR: Pipeline exited with code {proc.returncode}"
        else:
            yield "Pipeline completed successfully"

    except Exception as e:
        _active_process = None
        yield f"ERROR: {e}"


def cancel_pipeline() -> bool:
    """Kill the running pipeline subprocess. Returns True if a process was killed."""
    global _active_process
    if _active_process is not None:
        try:
            _active_process.terminate()
            _active_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _active_process.kill()
        _active_process = None
        return True
    return False
