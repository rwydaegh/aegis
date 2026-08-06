"""What the payload holds, and everything derived from it. No Blender in here.

This is the half of the blend builder that is arithmetic, and separating it is the
point of the split. ``propagation_blender.py`` opened with ``import bpy``, so a
function that decides where the rim breaks or which bundle a ray belongs to could
only run inside Blender, and a function that can only run inside Blender does not
get a test. ``tests/test_propagation_viz.py`` covers the exporter that writes the
payload and covered none of this, which is the stage that reads it.

Everything here takes numpy arrays or a mapping that behaves like an ``npz`` and
returns numpy arrays. The one Blender-adjacent thing it does is
:func:`camera_rotation`, and that is trigonometry with a Blender convention in it
rather than a Blender call.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import pathlib
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np

from .style import MODEL_BANDS, RIM_LIFT_RADII, RIM_RAMP_FLOOR, colour_ramp

#: The sources a blend is built from. A blend whose fingerprint over these does
#: not match today's is a build artefact from different code, exactly the way a
#: compiled binary is, and on 3 August every blend in the tree was one.
#:
#: Lives here rather than in the runner because ``qa_propagation_blend.py`` has to
#: compute the same hash outside Blender and used to keep a hand copy of the list
#: with a comment explaining that importing the real one would pull in ``bpy``.
#: That is no longer true, so there is one list.
BUILDER_SOURCES: tuple[str, ...] = (
    "propagation_blender.py",
    "export_propagation_payload.py",
    "semantic_twin/viz/blender/exporter.py",
    "semantic_twin/viz/blender/payload.py",
    "semantic_twin/viz/blender/style.py",
    "semantic_twin/viz/blender/scene.py",
    "semantic_twin/viz/blender/estimator.py",
    "semantic_twin/viz/blender/animation.py",
    "semantic_twin/viz/blender/panorama.py",
    "semantic_twin/viz/blender/views.py",
    "semantic_twin/viz/blender/evidence.py",
    "semantic_twin/viz/blender/renders.py",
    "semantic_twin/vision/surface_atlas.py",
    "semantic_twin/walk/__init__.py",
    "semantic_twin/walk/builders.py",
    "semantic_twin/walk/grid.py",
    "semantic_twin/walk/ground.py",
    "semantic_twin/walk/links.py",
    "semantic_twin/walk/model.py",
    "semantic_twin/walk/ordering.py",
    "semantic_twin/walk/route.py",
    "semantic_twin/walk/site.py",
)


BUNDLE_SCHEMA = "semantic-twin-blender-bundle-v1"
BUNDLE_ARRAY = "bundle_identity_sha256"


def payload_content_sha256(payload: Mapping[str, Any]) -> str:
    """Hash all payload arrays except the identity stamp itself.

    The hash is over names, types, shapes, and values. It does not depend on the
    ZIP metadata in an NPZ file, so it is stable across safe rewrites.
    """
    digest = hashlib.sha256()
    for name in sorted(key for key in payload if key != BUNDLE_ARRAY):
        value = np.asarray(payload[name])
        if value.dtype.hasobject:
            raise TypeError(f"payload array {name!r} has object dtype and cannot receive a stable bundle hash")
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(value.dtype.str.encode("ascii") + b"\0")
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii") + b"\0")
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def manifest_content_sha256(manifest: Mapping[str, Any]) -> str:
    """Hash a manifest without its bundle stamp."""
    content = {key: value for key, value in manifest.items() if key != "bundle"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), default=float).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stamp_bundle_identity(payload: dict[str, Any], manifest: dict[str, Any]) -> str:
    """Give a payload and manifest one checked identity before publication."""
    payload.pop(BUNDLE_ARRAY, None)
    manifest.pop("bundle", None)
    payload_hash = payload_content_sha256(payload)
    manifest_hash = manifest_content_sha256(manifest)
    identity = hashlib.sha256(f"{BUNDLE_SCHEMA}\0{payload_hash}\0{manifest_hash}".encode()).hexdigest()
    payload[BUNDLE_ARRAY] = np.array(identity)
    manifest["bundle"] = {
        "schema": BUNDLE_SCHEMA,
        "identity_sha256": identity,
        "payload_content_sha256": payload_hash,
        "manifest_content_sha256": manifest_hash,
    }
    return identity


def verify_bundle_identity(payload: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    """Reject a missing, partial, or crossed payload and manifest pair."""
    record = manifest.get("bundle")
    if not isinstance(record, Mapping) or record.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("payload and manifest do not carry a supported shared bundle identity")
    if BUNDLE_ARRAY not in payload:
        raise ValueError("payload is missing the shared bundle identity")
    stamped = str(np.asarray(payload[BUNDLE_ARRAY]).item())
    expected = record.get("identity_sha256")
    payload_hash = payload_content_sha256(payload)
    manifest_hash = manifest_content_sha256(manifest)
    if payload_hash != record.get("payload_content_sha256"):
        raise ValueError("payload content does not match its manifest bundle hash")
    if manifest_hash != record.get("manifest_content_sha256"):
        raise ValueError("manifest content does not match its bundle hash")
    identity = hashlib.sha256(f"{BUNDLE_SCHEMA}\0{payload_hash}\0{manifest_hash}".encode()).hexdigest()
    if stamped != expected or identity != expected:
        raise ValueError("payload and manifest bundle identities disagree")
    return identity


@dataclass(frozen=True)
class ProductionFiles:
    """The three files that together make one streamed exposure result."""

    locations: pathlib.Path
    spectra: pathlib.Path
    manifest: pathlib.Path

    def hashes(self) -> dict[str, dict[str, str]]:
        """Exact input identity written into the visualization manifest."""
        return {
            name: {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in (
                ("locations_jsonl", self.locations),
                ("spectra_npz", self.spectra),
                ("manifest_json", self.manifest),
            )
        }


@dataclass(frozen=True)
class ProductionData:
    """Validated arrays and rows read from one production exposure result."""

    files: ProductionFiles
    input_identity: dict[str, dict[str, str]]
    manifest: dict[str, Any]
    rows: tuple[dict[str, Any], ...]
    index: np.ndarray
    rho_rooftop: np.ndarray
    local_grid: np.ndarray
    solid_angle: float


@dataclass(frozen=True)
class DrawableRayLegs:
    """Straight display legs derived from recorded transport paths.

    Each row in ``points`` is one endpoint and every pair is one physical leg.
    ``leg_throughput`` belongs to the whole leg. It is never interpolated across
    a reflection. An escaped last leg is still a ray to infinity in the model.
    Its recorded endpoint is only a finite display proxy.
    """

    points: np.ndarray
    lengths: np.ndarray
    leg_throughput: np.ndarray
    path_index: np.ndarray
    leg_index: np.ndarray
    escaped_final: np.ndarray
    paths_requested: int
    paths_drawn: int
    paths_left_out_beyond_drawn_support: np.ndarray
    paths_trimmed_at_zero_throughput: np.ndarray
    outgoing_legs_after_zero_left_out: int
    degenerate_legs_left_out: int


@dataclass(frozen=True)
class _DrawablePath:
    """One path after applying only display-domain filters."""

    points: np.ndarray
    power: np.ndarray
    depth: np.ndarray
    outside_support: bool
    trimmed_at_zero: bool
    zero_legs_left_out: int
    degenerate_legs_left_out: int


def production_files(
    *,
    stem: pathlib.Path | None,
    locations: pathlib.Path | None,
    spectra: pathlib.Path | None,
    manifest: pathlib.Path | None,
    default_directory: pathlib.Path,
) -> ProductionFiles | None:
    """Resolve a named stem or three exact paths, and reject mixed input."""
    exact = (locations, spectra, manifest)
    if stem is not None and any(path is not None for path in exact):
        raise ValueError("use --production-stem or the three exact production paths, not both")
    if stem is not None:
        base = stem if stem.parent != pathlib.Path(".") else default_directory / stem
        return ProductionFiles(
            base.with_name(f"{base.name}_locations.jsonl"),
            base.with_name(f"{base.name}_spectra.npz"),
            base.with_name(f"{base.name}_manifest.json"),
        )
    if not any(path is not None for path in exact):
        return None
    if not all(path is not None for path in exact):
        raise ValueError(
            "production input needs --production-locations, --production-spectra, and --production-manifest"
        )
    return ProductionFiles(
        cast(pathlib.Path, locations),
        cast(pathlib.Path, spectra),
        cast(pathlib.Path, manifest),
    )


def read_production_data(files: ProductionFiles) -> ProductionData:
    """Read the three files without deciding whether they describe this model."""
    missing = [str(path) for path in (files.locations, files.spectra, files.manifest) if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"production exposure input does not exist: {', '.join(missing)}")
    content = {
        "locations_jsonl": files.locations.read_bytes(),
        "spectra_npz": files.spectra.read_bytes(),
        "manifest_json": files.manifest.read_bytes(),
    }
    identity = {
        name: {"path": str(path.resolve()), "sha256": hashlib.sha256(content[name]).hexdigest()}
        for name, path in (
            ("locations_jsonl", files.locations),
            ("spectra_npz", files.spectra),
            ("manifest_json", files.manifest),
        )
    }
    manifest = json.loads(content["manifest_json"])
    if not isinstance(manifest, dict):
        raise TypeError(f"{files.manifest} must contain one JSON object")
    text = content["locations_jsonl"].decode()
    if text and not text.endswith("\n"):
        raise ValueError(f"{files.locations} ends with an incomplete JSONL row")
    rows = tuple(json.loads(line) for line in text.splitlines())
    with np.load(io.BytesIO(content["spectra_npz"])) as saved:
        arrays = {
            name: np.array(saved[name], copy=True) for name in ("index", "rho_rooftop", "local_grid", "solid_angle")
        }
    return ProductionData(
        files=files,
        input_identity=identity,
        manifest=manifest,
        rows=rows,
        index=arrays["index"],
        rho_rooftop=arrays["rho_rooftop"],
        local_grid=arrays["local_grid"],
        solid_angle=float(arrays["solid_angle"]),
    )


def builder_fingerprint(root: pathlib.Path | None = None) -> str:
    """A hash over the code that writes a blend, stamped into the blend.

    A timestamp cannot answer "was this built by today's code". Committing an
    unchanged file moves its commit time forward and makes a perfectly current
    blend look stale, which is what happened the first time this was checked.
    Hashing the bytes answers it exactly and says nothing about when.
    """
    if root is None:
        from ... import paths

        root = paths.root()
    digest = hashlib.sha256()
    for name in BUILDER_SOURCES:
        path = root / name
        digest.update(path.read_bytes() if path.exists() else b"")
    return digest.hexdigest()[:16]


def _mapping_at(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    return value if isinstance(value, Mapping) else {}


def _named_strings(record: Mapping[str, Any], names: Sequence[tuple[str, str]]) -> dict[str, str]:
    return {
        property_name: value
        for source_name, property_name in names
        if isinstance((value := record.get(source_name)), str)
    }


def _production_input_hashes(production: Mapping[str, Any]) -> dict[str, str]:
    inputs = _mapping_at(production, "inputs")
    names = (
        ("locations_jsonl", "production_locations_sha256"),
        ("spectra_npz", "production_spectra_sha256"),
        ("manifest_json", "production_manifest_sha256"),
    )
    return {
        property_name: digest
        for source_name, property_name in names
        if isinstance((digest := _mapping_at(inputs, source_name).get("sha256")), str)
    }


def _surface_hashes(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Flatten the canonical hit atlas and its whole-face fallback separately."""
    fallback = _mapping_at(manifest, "support_surface_fallback")
    atlas = _mapping_at(manifest, "surface_atlas")
    properties = _named_strings(
        fallback,
        (
            ("mesh_sha256", "support_mesh_sha256"),
            ("face_class_sha256", "support_fallback_face_class_sha256"),
            ("face_source_sha256", "support_fallback_face_source_sha256"),
        ),
    )
    properties.update(
        _named_strings(
            atlas,
            (
                ("content_sha256", "surface_atlas_content_sha256"),
                ("mesh_sha256", "surface_atlas_mesh_sha256"),
            ),
        )
    )
    for source_name, property_name in (
        ("npz", "surface_atlas_npz_sha256"),
        ("manifest", "surface_atlas_manifest_sha256"),
    ):
        digest = _mapping_at(atlas, source_name).get("sha256")
        if isinstance(digest, str):
            properties[property_name] = digest

    # Read old visualization manifests without preserving their false claim
    # that one whole-face class map was the final hit-position atlas.
    if not properties:
        legacy = _mapping_at(manifest, "final_surface_atlas")
        properties.update(
            _named_strings(
                legacy,
                (
                    ("mesh_sha256", "support_mesh_sha256"),
                    ("face_class_sha256", "support_fallback_face_class_sha256"),
                    ("face_source_sha256", "support_fallback_face_source_sha256"),
                ),
            )
        )
    return properties


def _admission_properties(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Flatten the two linked registration gates and the atlas cohort."""
    atlas = _mapping_at(manifest, "surface_atlas")
    atlas_admission = _mapping_at(atlas, "admission")
    registration = _mapping_at(_mapping_at(manifest, "evidence"), "registration")
    registration_admission = _mapping_at(registration, "admission")
    properties: dict[str, str] = {}
    for prefix, admission in (
        ("surface_atlas", atlas_admission),
        ("registration", registration_admission),
    ):
        version = admission.get("version")
        if isinstance(version, str):
            properties[f"{prefix}_admission_version"] = version
            properties[f"{prefix}_admission_json"] = json.dumps(admission, sort_keys=True, separators=(",", ":"))
    camera_ids = atlas.get("camera_ids")
    if isinstance(camera_ids, list) and all(isinstance(value, str) for value in camera_ids):
        properties["surface_atlas_admitted_captures_json"] = json.dumps(camera_ids, separators=(",", ":"))
    admitted = registration.get("admitted_captures")
    if isinstance(admitted, list) and all(isinstance(value, str) for value in admitted):
        properties["registration_admitted_captures_json"] = json.dumps(admitted, separators=(",", ":"))
    return properties


def _production_transport(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    arms = _mapping_at(manifest, "estimator_arms")
    exposure = _mapping_at(arms, "exposure")
    return _mapping_at(exposure, "transport")


def production_scene_properties(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Flatten production identity into Blender-supported scene properties.

    Blender custom properties cannot hold nested dictionaries. The production
    visualization manifest keeps the complete nested record, while the scene
    receives the fields needed to identify the exact exposure run without
    opening a second file. Standalone visualization manifests have no
    ``production_exposure`` block and therefore receive only the shared bundle
    identity when one is present.
    """
    bundle = _mapping_at(manifest, "bundle")
    properties = _named_strings(bundle, (("identity_sha256", "visualization_bundle_sha256"),))
    production = _mapping_at(manifest, "production_exposure")
    if not production:
        return properties

    transport = _production_transport(manifest)
    properties.update(_named_strings(production, (("run_digest", "production_run_digest"),)))
    properties.update(_production_input_hashes(production))
    properties.update(_surface_hashes(manifest))
    properties.update(_admission_properties(manifest))
    properties.update(
        _named_strings(
            transport,
            (
                ("kernel", "transport_kernel"),
                ("variant", "transport_variant"),
                ("floating_point", "transport_floating_point"),
            ),
        )
    )
    properties.update(
        _named_strings(
            _mapping_at(transport, "rng"),
            (("family", "transport_rng_family"), ("algorithm", "transport_rng_algorithm")),
        )
    )
    properties.update(
        _named_strings(
            _mapping_at(transport, "versions"),
            (("mitsuba", "mitsuba_version"), ("drjit", "drjit_version")),
        )
    )
    return properties


def has(payload: Any, prefix: str) -> bool:
    """Does the payload carry any array whose name starts with this?

    Every evidence layer is optional, and the test for whether a site has one is
    whether its arrays are in the file. A site with no panorama is not an error
    and never has been.
    """
    return any(key.startswith(prefix) for key in payload.files)


def available_spectrum_models(payload: Any, candidates: Sequence[str]) -> tuple[str, ...]:
    """Models whose angular spectrum is actually present in this payload."""
    keys = payload.files if hasattr(payload, "files") else payload
    return tuple(name for name in candidates if f"rho_{name}" in keys)


def connection_render_layers(layers: Mapping[str, str], object_names: Collection[str]) -> dict[str, str]:
    """Select the correctly named connection object for this payload family."""
    resolved = dict(layers)
    if "estimator_connections" in resolved and "source_evidence_connections" in object_names:
        channel = resolved.pop("estimator_connections")
        resolved["source_evidence_connections"] = channel
    return resolved


def elevation_deg(directions: np.ndarray) -> np.ndarray:
    return np.degrees(np.arcsin(np.clip(np.asarray(directions, dtype=np.float64)[:, 2], -1.0, 1.0)))


def ray_bundles(payload: Any, terminations: Sequence[str]) -> dict[str, np.ndarray]:
    """Sort recorded paths into five exclusive bundles.

    The split is by what happened to the ray, not by how it looks. A ray either
    left the scene or died in it, and if it left, it either left into the
    elevation band the rooftop model illuminates from or it did not. That last
    distinction is the one worth drawing: an escape outside the band contributes
    nothing under that model no matter how far it travelled.
    """
    sky = list(terminations).index("sky")
    escaped = payload["path_termination"] == sky
    keys = payload.files if hasattr(payload, "files") else payload
    if "path_offsets" in keys and "path_throughput" in keys:
        offsets = np.asarray(payload["path_offsets"], dtype=np.int64)
        throughput = np.asarray(payload["path_throughput"], dtype=np.float64)
        absorbed = np.array(
            [np.any(np.equal(throughput[offsets[i] : offsets[i + 1] - 1], 0.0)) for i in range(offsets.size - 1)]
        )
        escaped = escaped & ~absorbed
    bounced = payload["path_bounces"] > 0
    low, high = MODEL_BANDS["rooftop"]
    exit_elevation = elevation_deg(payload["path_exit_direction"])
    band = (exit_elevation >= low) & (exit_elevation <= high)
    return {
        "direct_sky_in_rooftop_band": escaped & ~bounced & band,
        "direct_sky_elsewhere": escaped & ~bounced & ~band,
        "multipath_to_rooftop_band": escaped & bounced & band,
        "multipath_elsewhere": escaped & bounced & ~band,
        "stopped_in_the_scene": ~escaped,
    }


def path_slice(offsets: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Vertex indices of a chosen set of paths, concatenated in path order.

    The paths are stored as one vertex array with a start offset per path, so
    picking a subset is a gather rather than a slice. Empty in gives empty out
    with the right dtype, which matters because an empty float index array cannot
    index anything.
    """
    indices = np.asarray(indices, dtype=np.int64)
    if indices.size == 0:
        return np.zeros(0, dtype=np.int64)
    return np.concatenate([np.arange(offsets[i], offsets[i + 1]) for i in indices])


def _validate_ray_record(
    vertices: np.ndarray,
    offsets: np.ndarray,
    throughput: np.ndarray,
    bounces: np.ndarray,
    termination: np.ndarray,
    selected: np.ndarray,
    drawn_radius_m: float,
) -> None:
    if offsets.ndim != 1 or offsets.size != bounces.size + 1:
        raise ValueError("path offsets must contain one start per path and one final stop")
    if vertices.shape != (throughput.size, 3) or offsets[-1] != vertices.shape[0]:
        raise ValueError("path vertices and throughput must match the recorded offsets")
    if termination.shape != bounces.shape:
        raise ValueError("path termination must contain one value per path")
    if np.any((selected < 0) | (selected >= bounces.size)):
        raise IndexError("selected path index is outside the recorded path table")
    if drawn_radius_m <= 0.0:
        raise ValueError("drawn_radius_m must be positive")


def _drawable_path(
    path_points: np.ndarray,
    path_power: np.ndarray,
    bounce_count: int,
    drawn_radius_m: float,
) -> _DrawablePath:
    if path_points.shape[0] < 2 or bounce_count < 0 or bounce_count > path_points.shape[0] - 2:
        raise ValueError("path has an invalid vertex or bounce count")
    bounce_points = path_points[1 : bounce_count + 1]
    outside = bool(bounce_points.size and np.any(np.linalg.norm(bounce_points[:, :2], axis=1) > drawn_radius_m))
    if outside:
        return _DrawablePath(np.zeros((0, 3)), np.zeros(0), np.zeros(0, dtype=np.int64), True, False, 0, 0)

    total = path_points.shape[0] - 1
    zero = np.flatnonzero(np.equal(path_power[:total], 0.0))
    stop = int(zero[0]) if zero.size else total
    pairs = np.stack([path_points[:stop], path_points[1 : stop + 1]], axis=1)
    live = np.linalg.norm(pairs[:, 1] - pairs[:, 0], axis=1) > 1.0e-12
    return _DrawablePath(
        points=pairs[live].reshape(-1, 3),
        power=path_power[:stop][live],
        depth=np.arange(stop, dtype=np.int64)[live],
        outside_support=False,
        trimmed_at_zero=bool(zero.size),
        zero_legs_left_out=total - stop,
        degenerate_legs_left_out=int(np.count_nonzero(~live)),
    )


def drawable_ray_legs(
    payload: Any,
    indices: np.ndarray,
    terminations: Sequence[str],
    *,
    drawn_radius_m: float,
) -> DrawableRayLegs:
    """Turn recorded paths into straight, constant-throughput display legs.

    A recorded surface vertex separates two physical legs. Duplicating that
    vertex gives each leg one constant radius and makes the power loss at the
    reflection discontinuous, as it is in the transport record. The final leg
    of a sky path is marked as a finite display proxy for a semi-infinite ray.

    The displayed support mesh is smaller than the mesh used for transport.
    Paths with a reflection outside that displayed disc are left out in full,
    otherwise they appear to turn in empty space. This is a display filter only.

    Throughput is stored on the segment leaving a vertex. Once an exact zero is
    reached, that vertex remains as the end of the incoming leg and no outgoing
    leg is drawn. Duplicate terminal vertices used to record roulette and
    truncation are also left out because they have no physical length.
    """
    vertices = np.asarray(payload["path_vertices"], dtype=np.float64)
    offsets = np.asarray(payload["path_offsets"], dtype=np.int64)
    throughput = np.asarray(payload["path_throughput"], dtype=np.float64)
    bounces = np.asarray(payload["path_bounces"], dtype=np.int64)
    termination = np.asarray(payload["path_termination"], dtype=np.int64)
    selected = np.asarray(indices, dtype=np.int64)
    sky = list(terminations).index("sky")

    _validate_ray_record(vertices, offsets, throughput, bounces, termination, selected, drawn_radius_m)

    points: list[np.ndarray] = []
    leg_power: list[float] = []
    path_index: list[int] = []
    leg_index: list[int] = []
    escaped_final: list[bool] = []
    drawn_paths: set[int] = set()
    outside: list[int] = []
    zero_trimmed: list[int] = []
    zero_legs = 0
    degenerate = 0

    for index in selected:
        path = int(index)
        start, stop = int(offsets[path]), int(offsets[path + 1])
        selected_path = _drawable_path(
            vertices[start:stop],
            throughput[start:stop],
            int(bounces[path]),
            drawn_radius_m,
        )
        if selected_path.outside_support:
            outside.append(path)
            continue
        if selected_path.trimmed_at_zero:
            zero_trimmed.append(path)
        zero_legs += selected_path.zero_legs_left_out
        degenerate += selected_path.degenerate_legs_left_out
        if selected_path.power.size:
            points.extend(selected_path.points)
            leg_power.extend(selected_path.power.tolist())
            path_index.extend([path] * selected_path.power.size)
            leg_index.extend(selected_path.depth.tolist())
            final_depth = stop - start - 2
            escaped_final.extend((termination[path] == sky) & (selected_path.depth == final_depth))
            drawn_paths.add(path)

    count = len(leg_power)
    return DrawableRayLegs(
        points=np.asarray(points, dtype=np.float64).reshape(-1, 3),
        lengths=np.full(count, 2, dtype=np.int32),
        leg_throughput=np.asarray(leg_power, dtype=np.float64),
        path_index=np.asarray(path_index, dtype=np.int64),
        leg_index=np.asarray(leg_index, dtype=np.int64),
        escaped_final=np.asarray(escaped_final, dtype=bool),
        paths_requested=int(selected.size),
        paths_drawn=len(drawn_paths),
        paths_left_out_beyond_drawn_support=np.asarray(outside, dtype=np.int64),
        paths_trimmed_at_zero_throughput=np.asarray(zero_trimmed, dtype=np.int64),
        outgoing_legs_after_zero_left_out=zero_legs,
        degenerate_legs_left_out=degenerate,
    )


def supported_live_scattering_vertices(
    payload: Any,
    path_index: np.ndarray,
    vertex_index: np.ndarray,
    unsupported_paths: np.ndarray,
) -> np.ndarray:
    """Which next-event origins still have power and visible bounce support.

    A truncated path may end with a duplicate terminal marker and therefore have
    no drawable outgoing leg. Its last scattering vertex is still a valid
    next-event origin when its throughput is positive.
    """
    path_index = np.asarray(path_index, dtype=np.int64)
    vertex_index = np.asarray(vertex_index, dtype=np.int64)
    offsets = np.asarray(payload["path_offsets"], dtype=np.int64)
    throughput = np.asarray(payload["path_throughput"], dtype=np.float64)
    if path_index.shape != vertex_index.shape:
        raise ValueError("next-event path and vertex indices must have the same shape")
    if np.any((path_index < 0) | (path_index >= offsets.size - 1) | (vertex_index < 0)):
        raise IndexError("next-event origin is outside the recorded path table")
    record_index = offsets[path_index] + vertex_index
    if np.any(record_index >= offsets[path_index + 1] - 1):
        raise ValueError("next-event origin must be a scattering vertex, not a terminal marker")
    supported = ~np.isin(path_index, np.asarray(unsupported_paths, dtype=np.int64))
    return supported & ~np.equal(throughput[record_index], 0.0)


def octahedra(centres: np.ndarray, radius: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
    """A marker mesh: one eight sided diamond per centre, in one triangle soup."""
    unit = np.array(
        [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]]
    )
    template = np.array(
        [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]], dtype=np.int64
    )
    centres = np.asarray(centres, dtype=np.float64)
    count = centres.shape[0]
    scale = np.full(count, radius) if np.isscalar(radius) else np.asarray(radius, dtype=np.float64)
    vertices = (centres[:, None, :] + scale[:, None, None] * unit[None, :, :]).reshape(-1, 3)
    faces = (template[None, :, :] + 6 * np.arange(count)[:, None, None]).reshape(-1, 3)
    return vertices, faces


def unit_sphere(subdivisions: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """A sphere by subdividing an octahedron, so no external primitive is needed."""
    vertices = np.array(
        [[1.0, 0, 0], [-1.0, 0, 0], [0, 1.0, 0], [0, -1.0, 0], [0, 0, 1.0], [0, 0, -1.0]], dtype=np.float64
    )
    faces = np.array(
        [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]], dtype=np.int64
    )
    for _ in range(subdivisions):
        a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
        base = vertices.shape[0]
        count = faces.shape[0]
        midpoints = np.concatenate([(a + b) / 2.0, (b + c) / 2.0, (c + a) / 2.0])
        vertices = np.concatenate([vertices, midpoints])
        ab = base + np.arange(count)
        bc = ab + count
        ca = bc + count
        faces = np.concatenate(
            [
                np.column_stack([faces[:, 0], ab, ca]),
                np.column_stack([ab, faces[:, 1], bc]),
                np.column_stack([ca, bc, faces[:, 2]]),
                np.column_stack([ab, bc, ca]),
            ]
        )
    return vertices / np.linalg.norm(vertices, axis=1, keepdims=True), faces


# ---------------------------------------------------------------------------
# The skyline rim
# ---------------------------------------------------------------------------


def rim_tube(slant: np.ndarray, width_scale: float) -> tuple[np.ndarray, np.ndarray]:
    """Drawn radius of the rim at a slant range, and how far above the tip it goes.

    The radius rises as the square root of the range, which is between constant
    world size and constant angular size, so the far rim neither swells nor
    vanishes. It carries no flux, so there is no second reading of that number to
    reconcile with the colour.
    """
    radius = width_scale * np.sqrt(np.maximum(np.asarray(slant, dtype=np.float64), 1.0e-6))
    return radius, RIM_LIFT_RADII * radius


def rim_shading(weight: np.ndarray, found: np.ndarray) -> tuple[Callable[[np.ndarray], np.ndarray], float, float]:
    """The flux ramp, and the two logarithms it spans. Shared, so nothing drifts.

    The rim and the connections that land on it are shaded by the same call, or a
    bright line could arrive at a dark roofline and the reader would have no way to
    know which of the two was lying.

    The ramp spans the middle eight tenths of the azimuths rather than the whole
    range, so a tenth of the rim saturates at each end. A single tip a metre and a
    half away carries eighty times the median at Korenmarkt, and shading to it
    leaves every other roofline in one dark colour. Most rooflines deliver within a
    factor of three of each other, so what is left after the tails are cut is 1.07
    decades at Korenmarkt rather than 1.58. The true range and the span shaded are
    both on the object.
    """
    live = np.asarray(weight)[np.asarray(found, dtype=bool)]
    low, high = (float(np.log10(value)) for value in np.percentile(live, [10, 90]))

    def shade(values: np.ndarray) -> np.ndarray:
        scaled = np.log10(np.maximum(np.asarray(values, dtype=np.float64), 1.0e-12))
        step = np.clip((scaled - low) / max(high - low, 1.0e-9), 0.0, 1.0)
        return colour_ramp(RIM_RAMP_FLOOR + (1.0 - RIM_RAMP_FLOOR) * step, 0.0, 1.0)

    return shade, low, high


def contiguous_runs(mask: np.ndarray) -> list[np.ndarray]:
    """Runs of consecutive true indices, joined across the wrap at azimuth zero.

    The rim closes on itself, so a run ending at the last azimuth and one starting
    at the first are one run through the seam rather than two.
    """
    index = np.flatnonzero(mask)
    if index.size == 0:
        return []
    runs = np.split(index, np.flatnonzero(np.diff(index) > 1) + 1)
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == mask.size - 1:
        runs = [np.concatenate([runs[-1], runs[0]])] + runs[1:-1]
    return runs


def rim_polylines(found: np.ndarray, offset: np.ndarray, *, break_fraction: float) -> list[np.ndarray]:
    """The rim as drawable polylines: index runs with a tip, cut where it steps.

    Two cuts, and they are different questions. An azimuth with no tip is open to
    the horizon and carries no source, so the rim has a hole there. An azimuth
    whose tip jumps is a corner: the silhouette has moved onto a facade behind the
    one it was on, and the two tips are both real and are not joined by a roofline.
    """
    pieces: list[np.ndarray] = []
    for run in contiguous_runs(found):
        if run.size == found.size:
            run = np.append(run, run[0])
        reach = np.linalg.norm(offset[run], axis=1)
        step = np.linalg.norm(np.diff(offset[run], axis=0), axis=1)
        cut = np.flatnonzero(step > break_fraction * np.minimum(reach[:-1], reach[1:])) + 1
        pieces += [piece for piece in np.split(run, cut) if piece.size >= 2]
    return pieces


def shorten_sky_legs(
    points: np.ndarray,
    lengths: np.ndarray,
    *,
    reach: float,
    escaped_final: np.ndarray | None = None,
) -> np.ndarray:
    """Pull the last vertex of each polyline back to ``reach`` metres.

    Only the last one, and only along its own direction. A recorded path that
    escaped ends on a sky sphere 176 m out, which in a close view runs off the
    frame and takes the connections with it. A path that stopped in the scene has
    its last vertex sitting on the previous one and is left alone.
    """
    moved = np.array(points, dtype=np.float64, copy=True)
    end = np.cumsum(lengths) - 1
    if escaped_final is not None:
        escaped_final = np.asarray(escaped_final, dtype=bool)
        if escaped_final.shape != end.shape:
            raise ValueError("escaped_final must contain one flag per polyline")
        end = end[escaped_final]
    if end.size == 0:
        return moved
    span = moved[end] - moved[end - 1]
    distance = np.linalg.norm(span, axis=1)
    live = distance > 1.0e-9
    moved[end[live]] = moved[end[live] - 1] + reach * span[live] / distance[live, None]
    return moved


def camera_rotation(location: np.ndarray, target: np.ndarray) -> tuple[float, float, float]:
    """XYZ Euler angles aiming a Blender camera from ``location`` at ``target``.

    A Blender camera looks down its own -Z with +Y up, so this solves
    ``Rz(rz) Rx(rx) (0, 0, -1) = d``. That gives ``rx`` from ``-dz`` and ``rz``
    from ``(-dx, dy)``. Every other arrangement of those signs aims somewhere
    plausible looking and wrong, and the failure is a black frame or a view of the
    inside of a roof rather than an error.
    """
    direction = np.asarray(target, dtype=np.float64) - np.asarray(location, dtype=np.float64)
    direction = direction / max(float(np.linalg.norm(direction)), 1.0e-12)
    return (
        math.acos(float(np.clip(-direction[2], -1.0, 1.0))),
        0.0,
        math.atan2(-direction[0], direction[1]),
    )


def place_body(vertices: np.ndarray, hero: np.ndarray, ground_z: float) -> np.ndarray:
    """Stand the phantom on the local ground at the hero standpoint.

    The mesh arrives in metres with its own origin, so it is placed by its own feet
    rather than by assuming where that origin sits. Getting this wrong buries the
    phantom or floats it, and both look deliberate.
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    centre = vertices.mean(axis=0)
    origin = np.array([centre[0], centre[1], vertices[:, 2].min()])
    return vertices - origin + np.array([hero[0], hero[1], ground_z])
