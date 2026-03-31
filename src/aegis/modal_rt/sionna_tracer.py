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
        May be gzip+pickle compressed: {"_compressed": True, "_data": bytes}
        If scene_key is already cached (memory or Volume), scene_data can be None.
        """
        import gzip
        import json
        import pickle
        from pathlib import Path

        import numpy as np

        from aegis.integration.sionna import paths_from_sionna_scene

        # Decompress if the proxy gzip-compressed the payload
        if scene_data is not None and scene_data.get("_compressed"):
            scene_data = pickle.loads(gzip.decompress(scene_data["_data"]))

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
        """Build a Sionna Scene from pre-triangulated mesh data.

        Writes temporary Mitsuba XML + PLY files per material group,
        then loads via sionna.rt.load_scene(). Mirrors the approach in
        aegis.environment.export.to_sionna_xml().
        """
        import struct
        import tempfile
        from pathlib import Path

        import numpy as np
        import sionna.rt

        vertices = np.asarray(vertices, dtype=np.float32)
        triangles = np.asarray(triangles, dtype=np.int32)

        mat_colors = {
            "concrete": (0.6, 0.6, 0.6),
            "brick": (0.7, 0.3, 0.2),
            "asphalt": (0.3, 0.3, 0.3),
            "vegetation": (0.2, 0.6, 0.2),
            "glass": (0.5, 0.7, 0.9),
            "metal": (0.7, 0.7, 0.8),
            "wood": (0.6, 0.4, 0.2),
            "water": (0.2, 0.3, 0.7),
            "ground": (0.5, 0.4, 0.3),
            "default": (0.5, 0.5, 0.5),
        }

        tmpdir = Path(tempfile.mkdtemp(prefix="sionna_voxel_"))

        # Group triangles by per-face material name
        if materials and len(materials) == len(triangles):
            # Per-face material names
            groups: dict[str, list[int]] = {}
            for i, m in enumerate(materials):
                groups.setdefault(m, []).append(i)
        elif materials and len(materials) == 1:
            groups = {materials[0]: list(range(len(triangles)))}
        else:
            groups = {"concrete": list(range(len(triangles)))}

        import xml.etree.ElementTree as ET

        root = ET.Element("scene", version="2.1.0")

        for mat_name, face_indices in groups.items():
            mat_tris = triangles[face_indices]

            # Compact vertex subset
            unique_idx, inverse = np.unique(mat_tris.ravel(), return_inverse=True)
            local_verts = vertices[unique_idx].astype(np.float32)
            local_faces = inverse.reshape(-1, 3).astype(np.uint32)

            # Write PLY (binary little-endian)
            ply_name = f"{mat_name}.ply"
            ply_path = tmpdir / ply_name
            n_v, n_f = len(local_verts), len(local_faces)
            header = (
                f"ply\nformat binary_little_endian 1.0\n"
                f"element vertex {n_v}\n"
                f"property float x\nproperty float y\nproperty float z\n"
                f"element face {n_f}\n"
                f"property list uchar uint vertex_indices\n"
                f"end_header\n"
            )
            face_parts = []
            for tri in local_faces:
                face_parts.append(struct.pack("<B", 3))
                face_parts.append(struct.pack("<III", int(tri[0]), int(tri[1]), int(tri[2])))
            ply_path.write_bytes(header.encode("ascii") + local_verts.tobytes() + b"".join(face_parts))

            # XML shape element
            shape = ET.SubElement(root, "shape", type="ply", id=f"mesh_{mat_name}")
            ET.SubElement(shape, "string", name="filename", value=ply_name)
            bsdf = ET.SubElement(shape, "bsdf", type="diffuse", id=f"bsdf_{mat_name}")
            r, g, b = mat_colors.get(mat_name, mat_colors["default"])
            ET.SubElement(bsdf, "rgb", name="reflectance", value=f"{r:.3f} {g:.3f} {b:.3f}")

        xml_path = tmpdir / "scene.xml"
        xml_bytes = ET.tostring(root, encoding="unicode", xml_declaration=False)
        xml_path.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + xml_bytes + "\n")

        scene = sionna.rt.load_scene(str(xml_path))
        scene.frequency = freq_hz
        return scene
