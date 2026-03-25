"""DiffeRT ray tracer on Modal T4 GPU."""

from __future__ import annotations

import time

import modal

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
        freq_hz: float = 28e9,
        tx_power_dbm: float = 60.0,
        reflection_loss_per_order: float = 0.5,
        method: str = "exhaustive",
        num_rays: int = 1_000_000,
    ) -> dict:
        """Run DiffeRT ray tracing on GPU.

        Returns {"paths": PropagationPaths.to_dict(), "path_viz": [...],
                 "timings": {...}, "gpu_backend": "T4"}.
        """
        import tempfile
        from pathlib import Path

        import numpy as np

        from aegis.viewer.raytracer import compute_paths_differt

        t0 = time.perf_counter()

        # Write scene XML to a temp file (DiffeRT expects a file path)
        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            f.write(scene_xml)
            scene_path = f.name

        try:
            paths, path_viz = compute_paths_differt(
                scene_path=Path(scene_path),
                tx_pos=np.array(tx_pos),
                rx_pos=np.array(rx_pos),
                max_order=max_order,
                freq_hz=freq_hz,
                tx_power_dbm=tx_power_dbm,
                reflection_loss_per_order=reflection_loss_per_order,
                method=method,
                num_rays=num_rays,
            )
        finally:
            Path(scene_path).unlink(missing_ok=True)

        trace_ms = (time.perf_counter() - t0) * 1000

        return {
            "paths": paths.to_dict(),
            "path_viz": path_viz,
            "timings": {"trace_ms": trace_ms},
            "gpu_backend": "T4",
        }
