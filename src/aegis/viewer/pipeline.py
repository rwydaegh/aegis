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


# ---------------------------------------------------------------------------
# GLB texture fixup
# ---------------------------------------------------------------------------

_GLB_MAGIC = 0x46546C67  # 'glTF' in little-endian
_GLB_VERSION = 2
_CHUNK_JSON = 0x4E4F534A  # 'JSON'


def fix_glb_blob_uris(glb_path: Path) -> bool:
    """Remove invalid ``blob:nodedata:`` URIs from a GLB file in place.

    The Node.js pipeline sometimes writes image entries with both a
    ``bufferView`` (correct) and a ``uri`` produced by
    ``URL.createObjectURL()`` (invalid in browsers). When both fields are
    present and the URI starts with ``blob:``, the ``uri`` is removed so
    that THREE.GLTFLoader falls back to the ``bufferView``.

    If the image only has a ``blob:`` URI (no bufferView), the texture data
    was lost in the pipeline's Node.js memory. Replace with a 1x1 white
    PNG data URI to prevent browser errors.

    Returns True if the file was modified, False otherwise.
    """
    data = glb_path.read_bytes()

    if len(data) < 20:
        return False

    magic, version, _total = struct.unpack_from("<III", data, 0)
    if magic != _GLB_MAGIC or version != _GLB_VERSION:
        return False

    json_chunk_length, json_chunk_type = struct.unpack_from("<II", data, 12)
    if json_chunk_type != _CHUNK_JSON:
        return False

    json_start = 20
    json_end = json_start + json_chunk_length
    if json_end > len(data):
        return False

    gltf = json.loads(data[json_start:json_end].rstrip(b" "))

    # 1x1 white PNG as data URI fallback for images without bufferView
    _WHITE_1X1 = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQAB"
        "Nl7BcQAAAABJRU5ErkJggg=="
    )
    images = gltf.get("images", [])
    modified = False
    for img in images:
        uri = img.get("uri", "")
        if not uri.startswith("blob:"):
            continue
        if "bufferView" in img:
            del img["uri"]
        else:
            img["uri"] = _WHITE_1X1
            img.setdefault("mimeType", "image/png")
        modified = True

    if not modified:
        return False

    new_json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_padding = (4 - len(new_json_bytes) % 4) % 4
    new_json_bytes += b" " * json_padding

    remainder = data[json_end:]
    new_total = 12 + 8 + len(new_json_bytes) + len(remainder)

    header = struct.pack("<III", _GLB_MAGIC, _GLB_VERSION, new_total)
    json_hdr = struct.pack("<II", len(new_json_bytes), _CHUNK_JSON)

    glb_path.write_bytes(header + json_hdr + new_json_bytes + remainder)
    logger.info("Fixed blob URIs in %s", glb_path)
    return True


def fix_glb_tiles_dir(tiles_dir: Path) -> int:
    """Fix all GLB files in a tiles directory. Returns count of files modified."""
    if not tiles_dir.is_dir():
        return 0

    count = 0
    for glb_path in sorted(tiles_dir.glob("*.glb")):
        try:
            if fix_glb_blob_uris(glb_path):
                count += 1
        except Exception:
            logger.exception("Failed to fix GLB file: %s", glb_path)
    return count
