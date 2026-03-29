"""DiffeRT ray tracer on Modal T4 GPU."""

from __future__ import annotations

import time

import modal

from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
from aegis.modal_rt.app import app, differt_image


@app.cls(
    image=differt_image,
    gpu="T4",
    scaledown_window=120,
    timeout=120,
)
class DiffeRTTracer:
    @modal.enter()
    def setup(self):
        import jax

        jax.config.update("jax_platform_name", "gpu")
        self._jax_ready = True

    @modal.method()
    def trace(
        self,
        scene_xml: str,
        tx_pos: list[float],
        rx_pos: list[float],
        max_order: int = 1,
        freq_hz: float = DEFAULT_FREQ_HZ,
        tx_power_dbm: float = DEFAULT_POWER_DBM,
        reflection_loss_per_order: float = 0.5,
        method: str = "exhaustive",
        num_rays: int = 1_000_000,
        chunk_size: int | None = None,
        scene_files: dict[str, bytes] | None = None,
    ) -> dict:
        """Run DiffeRT ray tracing on GPU.

        Returns {"paths": PropagationPaths.to_dict(), "path_viz": [...],
                 "timings": {...}, "gpu_backend": "T4"}.
        """
        import shutil
        import tempfile
        from pathlib import Path

        import numpy as np

        from aegis.viewer.raytracer import compute_paths_differt

        t0 = time.perf_counter()

        # Reconstruct scene directory (XML + mesh files)
        tmpdir = tempfile.mkdtemp()
        scene_path = Path(tmpdir) / "scene.xml"
        scene_path.write_text(scene_xml)
        for relpath, data in (scene_files or {}).items():
            fpath = Path(tmpdir) / relpath
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_bytes(data)

        try:
            paths, path_viz = compute_paths_differt(
                scene_path=scene_path,
                tx_pos=np.array(tx_pos),
                rx_pos=np.array(rx_pos),
                max_order=max_order,
                freq_hz=freq_hz,
                tx_power_dbm=tx_power_dbm,
                reflection_loss_per_order=reflection_loss_per_order,
                method=method,
                num_rays=num_rays,
                chunk_size=chunk_size,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        trace_ms = (time.perf_counter() - t0) * 1000

        return {
            "paths": paths.to_dict(),
            "path_viz": path_viz,
            "timings": {"trace_ms": trace_ms},
            "gpu_backend": "T4",
        }
