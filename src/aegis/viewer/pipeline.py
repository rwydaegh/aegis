"""Pipeline runner for the Voxel Earth Node.js pipeline."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from collections.abc import Generator
from pathlib import Path

# String constants (avoid duplicate literals)
_PIPELINE_SCRIPT = "run_pipeline.js"

# Per-session process handles for cancellation
_active_processes: dict[str, subprocess.Popen] = {}
_pipeline_mutex = threading.Lock()


def find_pipeline(pipeline_dir: str | None = None) -> Path | None:
    """Locate the run_pipeline.js script.

    Search order:
    1. Explicit *pipeline_dir* argument (from ``--pipeline-dir`` CLI flag)
    2. ``VOXELEARTH_DIR`` environment variable
    3. ``../nodejs-voxelearth/`` relative to the repo root
    """
    if pipeline_dir:
        p = Path(pipeline_dir) / _PIPELINE_SCRIPT
        if p.exists():
            return p

    env_dir = os.environ.get("VOXELEARTH_DIR")
    if env_dir:
        p = Path(env_dir) / _PIPELINE_SCRIPT
        if p.exists():
            return p

    # Fallback: sibling directory of the repo root
    repo_root = Path(__file__).resolve().parents[3]  # src/aegis/viewer -> repo root
    p = repo_root.parent / "nodejs-voxelearth" / _PIPELINE_SCRIPT
    if p.exists():
        return p

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
    pipeline_dir: str | None = None,
    session_id: str = "default",
) -> Generator[str]:
    """Run the Voxel Earth pipeline, yielding stdout lines for progress.

    Parameters
    ----------
    location : place name (e.g. "Ghent, Belgium")
    radius : radius in meters
    api_key : Google API key
    output_dir : directory for pipeline output (parent of voxels/)
    resolution : voxel resolution (default 200)
    session_id : caller session identifier used to scope process ownership

    Yields
    ------
    str : each line of stdout/stderr from the pipeline process
    """
    if not _pipeline_mutex.acquire(blocking=False):
        yield "ERROR: pipeline busy"
        return

    pipeline_js = find_pipeline(pipeline_dir)
    if pipeline_js is None:
        _pipeline_mutex.release()
        yield "ERROR: run_pipeline.js not found"
        return

    node_bin = shutil.which("node")
    if node_bin is None:
        _pipeline_mutex.release()
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

    proc: subprocess.Popen | None = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(pipeline_js.parent),
            env=env,
        )
        _active_processes[session_id] = proc

        for line in proc.stdout:
            line = line.rstrip("\n\r")
            if line:
                yield line

        proc.wait()

        if proc.returncode != 0:
            yield f"ERROR: Pipeline exited with code {proc.returncode}"
        else:
            yield "Pipeline completed successfully"

    except Exception as e:
        yield f"ERROR: {e}"

    finally:
        _active_processes.pop(session_id, None)
        _pipeline_mutex.release()
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def cancel_pipeline(session_id: str = "default") -> bool:
    """Kill the running pipeline subprocess for the given session.

    Returns True if a process was found and killed.
    """
    proc = _active_processes.get(session_id)
    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        _active_processes.pop(session_id, None)
        return True
    return False
