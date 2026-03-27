"""Sionna RT ray tracer on Modal L4 GPU."""

from __future__ import annotations

import time

import modal

from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
from aegis.modal_rt.app import app, scene_volume, sionna_image


@app.cls(
    image=sionna_image,
    gpu="L4",
    scaledown_window=120,
    volumes={"/scenes": scene_volume},
    timeout=120,
)
class SionnaTracer:
    @modal.enter()
    def setup(self):
        import sionna.rt  # noqa: F401 - triggers OptiX init

        self._scene_cache: dict = {}

    @modal.method()
    def trace_bundled(
        self,
        scene_name: str,
        tx_pos: list[float],
        rx_pos: list[float],
        max_bounces: int = 5,
        freq_hz: float = DEFAULT_FREQ_HZ,
        tx_power_dbm: float = DEFAULT_POWER_DBM,
        rt_config: dict | None = None,
    ) -> dict:
        """Load a bundled Sionna scene by name, trace, return paths.

        Returns {"paths": PropagationPaths.to_dict(), "path_viz": [...],
                 "timings": {...}, "gpu_backend": "L4"}.
        """
        import numpy as np
        import sionna.rt

        from aegis.integration.sionna import paths_from_sionna_scene

        rt_config = rt_config or {}
        t0 = time.perf_counter()

        # Load scene (cached in self._scene_cache for warm re-traces)
        if scene_name in self._scene_cache:
            scene = self._scene_cache[scene_name]
        else:
            scene = sionna.rt.load_scene(getattr(sionna.rt.scene, scene_name))
            self._scene_cache[scene_name] = scene

        scene_load_ms = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()

        paths, path_viz = paths_from_sionna_scene(
            scene=scene,
            tx_positions=np.array([tx_pos]),
            rx_position=np.array(rx_pos),
            freq_hz=freq_hz,
            max_bounces=max_bounces,
            tx_power_dbm=tx_power_dbm,
            return_viz=True,
            **{
                k: v
                for k, v in rt_config.items()
                if k
                in {
                    "los",
                    "specular_reflection",
                    "diffuse_reflection",
                    "refraction",
                    "diffraction",
                    "edge_diffraction",
                    "diffraction_lit_region",
                    "samples_per_src",
                    "max_num_paths_per_src",
                    "synthetic_array",
                    "seed",
                }
            },
        )

        trace_ms = (time.perf_counter() - t1) * 1000

        return {
            "paths": paths.to_dict(),
            "path_viz": path_viz,
            "timings": {
                "scene_load_ms": scene_load_ms,
                "trace_ms": trace_ms,
            },
            "gpu_backend": "L4",
        }

    @modal.method()
    def trace_voxel(
        self,
        scene_key: str,
        scene_data: dict | None,
        tx_pos: list[float],
        rx_pos: list[float],
        max_bounces: int = 5,
        freq_hz: float = DEFAULT_FREQ_HZ,
        tx_power_dbm: float = DEFAULT_POWER_DBM,
        rt_config: dict | None = None,
    ) -> dict:
        """Trace on voxel geometry. scene_data sent on first call, cached after.

        scene_data format: {"vertices": list, "triangles": list, "materials": list}
        If scene_key is already cached (memory or Volume), scene_data can be None.
        """
        import json
        from pathlib import Path

        import numpy as np

        from aegis.integration.sionna import paths_from_sionna_scene

        rt_config = rt_config or {}
        t0 = time.perf_counter()

        # Tier 3: hot cache (container memory)
        if scene_key in self._scene_cache:
            scene = self._scene_cache[scene_key]
            scene_load_ms = (time.perf_counter() - t0) * 1000
        else:
            # Tier 2: Volume cache
            vol_path = Path(f"/scenes/{scene_key}.json")
            if vol_path.exists() and scene_data is None:
                raw = json.loads(vol_path.read_text())
                vertices = np.array(raw["vertices"])
                triangles = np.array(raw["triangles"])
                materials = raw["materials"]
            elif scene_data is not None:
                vertices = np.array(scene_data["vertices"])
                triangles = np.array(scene_data["triangles"])
                materials = scene_data["materials"]
                # Write to Volume for future cold starts
                vol_path.parent.mkdir(parents=True, exist_ok=True)
                vol_path.write_text(
                    json.dumps(
                        {
                            "vertices": vertices.tolist(),
                            "triangles": triangles.tolist(),
                            "materials": materials,
                        }
                    )
                )
                scene_volume.commit()
            else:
                raise ValueError(f"Scene '{scene_key}' not cached and no scene_data provided")

            # Build Sionna Scene from mesh geometry
            scene = self._build_scene_from_mesh(vertices, triangles, materials, freq_hz)
            self._scene_cache[scene_key] = scene
            scene_load_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()

        paths, path_viz = paths_from_sionna_scene(
            scene=scene,
            tx_positions=np.array([tx_pos]),
            rx_position=np.array(rx_pos),
            freq_hz=freq_hz,
            max_bounces=max_bounces,
            tx_power_dbm=tx_power_dbm,
            return_viz=True,
            **{
                k: v
                for k, v in rt_config.items()
                if k
                in {
                    "los",
                    "specular_reflection",
                    "diffuse_reflection",
                    "refraction",
                    "diffraction",
                    "edge_diffraction",
                    "diffraction_lit_region",
                    "samples_per_src",
                    "max_num_paths_per_src",
                    "synthetic_array",
                    "seed",
                }
            },
        )

        trace_ms = (time.perf_counter() - t1) * 1000

        return {
            "paths": paths.to_dict(),
            "path_viz": path_viz,
            "timings": {
                "scene_load_ms": scene_load_ms,
                "trace_ms": trace_ms,
            },
            "gpu_backend": "L4",
        }

    def _build_scene_from_mesh(
        self,
        vertices,
        triangles,
        materials: list[str],
        freq_hz: float,
    ):
        """Build a Sionna Scene from raw mesh data.

        This is the key function that converts voxel geometry into a
        Sionna-compatible scene. Implementation note: Sionna's Scene API
        requires loading from an XML file or using its programmatic API.
        The exact approach depends on which Sionna v2 APIs are available
        for mesh-based scene construction.

        TODO: Implement during task execution. Check Sionna v2 docs for
        Scene.from_mesh() or similar API. If no direct API exists, write
        the mesh to a temporary Mitsuba XML file and load via
        sionna.rt.load_scene().
        """
        raise NotImplementedError(
            "_build_scene_from_mesh: resolve during implementation. "
            "Check Sionna v2 API for mesh-based scene construction."
        )
