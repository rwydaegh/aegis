"""Machine, source, and runtime provenance for GPU parity workers."""

from __future__ import annotations

import hashlib
import os
import pathlib
import platform
import subprocess
import sys
from dataclasses import asdict
from typing import Any

import numpy as np


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_hash() -> str:
    package = pathlib.Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(package.rglob("*.py")):
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_provenance() -> dict[str, Any]:
    study = pathlib.Path(__file__).resolve().parents[2]

    def run(*args: str) -> str | None:
        answer = subprocess.run(
            ["git", *args],
            cwd=study,
            check=False,
            capture_output=True,
            text=True,
        )
        return answer.stdout.strip() if answer.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain", "--untracked-files=all")
    return {
        "commit": commit,
        "dirty": bool(status) if status is not None else None,
        "status_sha256": hashlib.sha256(status.encode()).hexdigest() if status is not None else None,
    }


def _version(module: str) -> str | None:
    try:
        imported = __import__(module)
    except ImportError:
        return None
    return str(getattr(imported, "__version__", "unknown"))


def _gpu_provenance() -> list[dict[str, str]]:
    query = "name,uuid,driver_version,memory.total"
    try:
        answer = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if answer.returncode != 0:
        return []
    fields = ("name", "uuid", "driver_version", "memory_mib")
    return [
        dict(zip(fields, (part.strip() for part in line.split(",")), strict=True))
        for line in answer.stdout.splitlines()
    ]


def _cpu_model() -> str | None:
    try:
        for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


def _cuda_runtime_visible_to_driver() -> str | None:
    try:
        answer = subprocess.run(["nvidia-smi"], check=False, capture_output=True, text=True)
    except FileNotFoundError:
        return None
    marker = "CUDA Version:"
    if answer.returncode == 0 and marker in answer.stdout:
        return answer.stdout.split(marker, 1)[1].split()[0]
    return None


def _runtime_provenance() -> dict[str, Any]:
    import drjit as dr
    import mitsuba as mi

    affinity = None
    if hasattr(os, "sched_getaffinity"):
        affinity = len(os.sched_getaffinity(0))
    thread_environment = {
        name: os.environ.get(name)
        for name in (
            "OPENBLAS_NUM_THREADS",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "CUDA_VISIBLE_DEVICES",
            "DRJIT_LIBLLVM_PATH",
        )
    }
    thread_count = getattr(dr, "thread_count", None)
    backend = getattr(dr, "backend_v", None)
    jit_flags = {flag.name: bool(dr.flag(flag)) for flag in dr.JitFlag if flag != dr.JitFlag.Default}
    return {
        "cpu_model": _cpu_model(),
        "logical_cpus": os.cpu_count(),
        "affinity_cpus": affinity,
        "drjit_thread_count": int(thread_count()) if callable(thread_count) else None,
        "drjit_backend": str(backend(mi.Float)) if callable(backend) else None,
        "drjit_jit_flags": jit_flags,
        "cuda_runtime_visible_to_driver": _cuda_runtime_visible_to_driver(),
        "mitsuba_variant": mi.variant(),
        "mitsuba_available_variants": list(mi.variants()),
        "environment": thread_environment,
    }


def collect_provenance(config: Any, variant: str) -> dict[str, Any]:
    """Collect enough state to reproduce or reject a comparison."""
    mesh = pathlib.Path(config.mesh).resolve()
    face_class = pathlib.Path(config.face_class).resolve() if config.face_class else None
    return {
        "git": _git_provenance(),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "executable": sys.executable,
        "numpy": np.__version__,
        "mitsuba": _version("mitsuba"),
        "drjit": _version("drjit"),
        "runtime": _runtime_provenance(),
        "gpus": _gpu_provenance(),
        "variant": variant,
        "mesh": {"path": str(mesh), "sha256": sha256_file(mesh)},
        "face_class": (
            {"path": str(face_class), "sha256": sha256_file(face_class)} if face_class is not None else None
        ),
        "source_sha256": _source_hash(),
        "config": asdict(config),
    }
