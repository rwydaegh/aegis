"""Material mixtures resolved at hit positions on the common surface atlas.

The panorama fusion keeps material evidence in a small barycentric texture for
each observed support-mesh triangle.  This module is the narrow transport
contract for that evidence.  It maps a hit to one texel and returns a posterior
over material table rows.  Geometry stays unchanged.

Unknown, air, people, vehicles, and vegetation are evidence about something
other than the structural support surface. Their posterior mass is never
renormalised into a certain interface. A structural interface binds only when
its posterior mass strictly exceeds one half. Grass keeps the geometric ground
interface. A woody-canopy cell is non-blocking until registered watertight
canopy geometry supplies entry and exit chords for volume transport. This rule
is recorded in :data:`ATLAS_MATERIAL_RULE` and every atlas material manifest.
"""

from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .binding import extend_classes
from .atlas import FALLBACK_BOUND
from .catalogue import IMAGE_MATERIALS, MATERIAL_SUBSTITUTION, MaterialSpec, MaterialTable, load_table

ATLAS_PREFIX = "atlas:"

# These labels are useful to scene understanding, but they do not describe the
# material of the fixed support surface underneath them.
NON_STRUCTURAL_MATERIALS = frozenset(("unknown", "air", "human_tissue", "vehicle_composite"))

# A strict posterior majority is an interpretable decision boundary. It avoids
# turning a tiny residual interface probability into certainty after unknown,
# object, or volume channels are removed. Exact ties retain the geometric
# fallback, which carries less information but makes no unsupported choice.
MIN_INTERFACE_POSTERIOR = 0.5

ATLAS_MATERIAL_RULE = (
    "At each ray hit, map the support-mesh face and barycentric coordinates to "
    "one common-atlas texel. Remove posterior mass assigned to unknown, air, "
    "people, vehicles, and participating volumes such as vegetation. Bind and "
    "renormalise an interface only when that interface mass is strictly greater "
    "than 0.5 and the joint atlas marks the texel as bound to a "
    "compatible support surface. Compute reflected power as sum(p_m R_m), and compute the specular "
    "sampling probability as sum(p_m R_m S_m) / sum(p_m R_m). If the face or "
    "texel has no decisive structural atlas support, use the geometric face "
    "material. Explicit grass keeps that ground interface. A woody-canopy cell "
    "is non-blocking until registered watertight canopy geometry supplies exact "
    "path chords for P.833 volume transport."
)


def _material_spec(name: str) -> MaterialSpec | None:
    """Return the explicit interface recipe for one atlas material label."""
    if name in NON_STRUCTURAL_MATERIALS:
        return None
    if name in IMAGE_MATERIALS:
        return IMAGE_MATERIALS[name]
    substitute = MATERIAL_SUBSTITUTION.get(name)
    if substitute is not None and substitute in IMAGE_MATERIALS:
        return IMAGE_MATERIALS[substitute]
    raise ValueError(f"surface atlas contains unsupported material name {name!r}")


@dataclass(frozen=True)
class AtlasMaterialBinding:
    """Fixed-resolution atlas data needed by NumPy and Dr.Jit transport.

    ``material_probability`` contains only structural material channels and is
    already renormalised within each supported texel. ``material_class`` maps those
    channels to the shared :class:`MaterialTable`.  A supported texel therefore
    has a posterior that sums to one and can be mixed directly in reflected
    power.
    """

    face_to_atlas_row: np.ndarray
    material_probability: np.ndarray
    supported: np.ndarray
    valid_texels: np.ndarray
    material_names: tuple[str, ...]
    material_class: np.ndarray
    provenance: dict[str, Any]
    nonblocking: np.ndarray | None = None

    def __post_init__(self) -> None:
        face_to_row = np.asarray(self.face_to_atlas_row)
        probability = np.asarray(self.material_probability)
        supported = np.asarray(self.supported)
        valid = np.asarray(self.valid_texels)
        material_class = np.asarray(self.material_class)
        if face_to_row.ndim != 1 or not np.issubdtype(face_to_row.dtype, np.integer):
            raise ValueError("face_to_atlas_row must be a one-dimensional integer array")
        if probability.ndim != 4:
            raise ValueError("material_probability must have shape (atlas rows, height, width, materials)")
        rows, height, width, materials = probability.shape
        if supported.shape != (rows, height, width):
            raise ValueError("supported must match the atlas row and texel dimensions")
        nonblocking = (
            np.zeros((rows, height, width), dtype=bool) if self.nonblocking is None else np.asarray(self.nonblocking)
        )
        if nonblocking.shape != (rows, height, width):
            raise ValueError("nonblocking must match the atlas row and texel dimensions")
        object.__setattr__(self, "nonblocking", nonblocking.astype(bool, copy=False))
        if valid.shape != (height, width):
            raise ValueError("valid_texels must match the atlas texel dimensions")
        if len(self.material_names) != materials or material_class.shape != (materials,):
            raise ValueError("material names and material classes must match the probability channels")
        if len(set(self.material_names)) != len(self.material_names):
            raise ValueError("material names must be unique")
        if np.any(face_to_row < -1) or np.any(face_to_row >= rows):
            raise ValueError("face_to_atlas_row contains an atlas row outside [-1, rows)")
        if not np.all(np.isfinite(probability)) or np.any(probability < 0.0):
            raise ValueError("material probabilities must be finite and nonnegative")
        if not np.issubdtype(material_class.dtype, np.integer):
            raise ValueError("material_class must contain integer table indices")
        if np.any(material_class < 0):
            raise ValueError("material_class cannot contain negative table indices")
        totals = probability.sum(axis=-1)
        if np.any(np.asarray(supported, dtype=bool) & ~np.isclose(totals, 1.0, atol=2e-6)):
            raise ValueError("every supported atlas texel must carry a material posterior that sums to one")
        if np.any(~np.asarray(supported, dtype=bool) & (totals != 0.0)):
            raise ValueError("unsupported atlas texels must have an exact zero posterior")
        if np.any(np.asarray(supported, dtype=bool) & ~valid[None, ...]):
            raise ValueError("texels outside the canonical triangle cannot be supported")
        if np.any(nonblocking & ~valid[None, ...]):
            raise ValueError("texels outside the canonical triangle cannot be non-blocking")
        if np.any(nonblocking & np.asarray(supported, dtype=bool)):
            raise ValueError("a texel cannot be both an interface and non-blocking")
        if not self.provenance:
            raise ValueError("an atlas material binding must record its provenance")

    @property
    def resolution(self) -> tuple[int, int]:
        return tuple(int(value) for value in self.material_probability.shape[1:3])

    @property
    def face_count(self) -> int:
        return int(self.face_to_atlas_row.size)

    def lookup(
        self,
        face: np.ndarray,
        barycentric_uv: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return ``(posterior, supported, nonblocking)`` for NumPy ray hits.

        ``barycentric_uv`` stores the weights of triangle vertices one and two.
        This is the same convention as Mitsuba's ``prim_uv`` and the vision
        ledger's canonical triangle chart.
        """
        face = np.asarray(face, dtype=np.int64)
        uv = np.asarray(barycentric_uv, dtype=np.float64)
        if face.ndim != 1 or uv.shape != (face.size, 2):
            raise ValueError("face and barycentric_uv must have shapes (hits,) and (hits, 2)")
        if np.any(face < 0) or np.any(face >= self.face_count):
            raise ValueError("face contains an index outside the support mesh")
        if not np.all(np.isfinite(uv)):
            raise ValueError("barycentric coordinates must be finite")
        if np.any(uv < -1e-5) or np.any(uv.sum(axis=1) > 1.0 + 1e-5):
            raise ValueError("barycentric coordinates must lie in the canonical triangle")

        row = self.face_to_atlas_row[face].astype(np.int64, copy=False)
        height, width = self.resolution
        texel_row, texel_column = _texel_indices(uv[:, 1], uv[:, 0], height, width)
        present = row >= 0
        probability = np.zeros((face.size, len(self.material_names)), dtype=np.float64)
        use = np.zeros(face.size, dtype=bool)
        pass_through = np.zeros(face.size, dtype=bool)
        if np.any(present):
            index = np.flatnonzero(present)
            probability[index] = self.material_probability[row[index], texel_row[index], texel_column[index]]
            use[index] = self.supported[row[index], texel_row[index], texel_column[index]]
            pass_through[index] = self.nonblocking[row[index], texel_row[index], texel_column[index]]
        return probability, use, pass_through


def bind_surface_atlas(
    atlas: Any,
    config_dir: pathlib.Path,
    frequency_hz: float,
    *,
    geometric_class: np.ndarray,
    source_npz: pathlib.Path | None = None,
    source_manifest: pathlib.Path | None = None,
) -> tuple[MaterialTable, AtlasMaterialBinding]:
    """Build one transport table and binding from a loaded surface atlas."""
    names = tuple(str(name) for name in atlas.material_names)
    if len(set(names)) != len(names):
        raise ValueError("surface-atlas material names must be unique")

    structural_names: list[str] = []
    structural_specs: dict[str, MaterialSpec] = {}
    source_channels: list[int] = []
    ignored: list[str] = []
    volume_materials: list[str] = []
    for channel, name in enumerate(names):
        spec = _material_spec(name)
        if spec is None:
            ignored.append(name)
            continue
        if not spec.is_interface:
            volume_materials.append(name)
            continue
        structural_names.append(name)
        structural_specs[name] = spec
        source_channels.append(channel)

    if not structural_names:
        raise ValueError("surface atlas has no structural material channels")
    class_names, spec = extend_classes(structural_names, ATLAS_PREFIX, structural_specs)
    table = load_table(
        pathlib.Path(config_dir),
        frequency_hz,
        class_names=class_names,
        class_binding=spec,
        class_rule=ATLAS_MATERIAL_RULE,
    )

    geometric_class = _integral_indices(geometric_class, "geometric_class")
    if geometric_class.shape != (np.asarray(atlas.face_to_atlas_row).size,):
        raise ValueError("geometric_class must have one entry per support-mesh face")
    compatible_marginal = getattr(atlas, "host_compatible_material_probability", None)
    if compatible_marginal is None:
        raw = np.asarray(atlas.material_probability, dtype=np.float64)
        compatible_support = np.asarray(atlas.material_support, dtype=np.float64) > 0.0
        posterior_source = "material marginal supplied by a legacy atlas without paired host filtering"
    else:
        raw, compatible_support = compatible_marginal(geometric_class)
        raw = np.asarray(raw, dtype=np.float64)
        compatible_support = np.asarray(compatible_support, dtype=bool)
        posterior_source = "material marginal of host-compatible joint entity-material entries only"
    if raw.ndim != 4 or raw.shape[-1] != len(names):
        raise ValueError("surface-atlas material_probability does not match material_names")
    if compatible_support.shape != raw.shape[:-1]:
        raise ValueError("surface-atlas compatible support does not match material_probability")
    probability = raw[..., np.asarray(source_channels, dtype=np.intp)].copy()
    structural_mass = probability.sum(axis=-1)
    original_support = np.asarray(atlas.material_support, dtype=np.float64)
    if original_support.shape != raw.shape[:-1]:
        raise ValueError("surface-atlas material_support does not match material_probability")
    valid_texels = np.asarray(atlas.valid_texels, dtype=bool)
    fallback_state = getattr(atlas, "fallback_state_dense", None)
    if fallback_state is None:
        fallback_bound = np.ones(raw.shape[:-1], dtype=bool)
    else:
        fallback_state = np.asarray(fallback_state)
        if fallback_state.shape != raw.shape[:-1]:
            raise ValueError("surface-atlas fallback_state_dense does not match material_probability")
        fallback_bound = fallback_state == int(FALLBACK_BOUND)
    observed = (original_support > 0.0) & valid_texels[None, ...]
    nonblocking, vegetation_provenance = _nonblocking_vegetation(atlas, raw.shape[:-1], observed)
    decisive_structural = structural_mass > MIN_INTERFACE_POSTERIOR
    structural_support = compatible_support & observed & decisive_structural
    supported = structural_support & fallback_bound & ~nonblocking
    probability = np.divide(
        probability,
        structural_mass[..., None],
        out=np.zeros_like(probability),
        where=supported[..., None],
    ).astype(np.float32)

    face_to_row = np.asarray(atlas.face_to_atlas_row)
    if face_to_row.ndim != 1:
        raise ValueError("surface-atlas face_to_atlas_row must be one-dimensional")
    material_class = np.arange(len(structural_names), dtype=np.int32) + len(table.class_names) - len(structural_names)
    provenance = {
        "rule": ATLAS_MATERIAL_RULE,
        "atlas_material_names": list(names),
        "transport_material_names": list(structural_names),
        "ignored_non_structural_material_names": ignored,
        "excluded_volume_material_names": volume_materials,
        "resolution": list(probability.shape[1:3]),
        "observed_faces": int(np.count_nonzero(face_to_row >= 0)),
        "supported_texels": int(np.count_nonzero(supported)),
        "structural_support_texels": int(np.count_nonzero(structural_support)),
        "minimum_interface_posterior": MIN_INTERFACE_POSTERIOR,
        "interface_decision": "strict majority; exact 0.5 ties use geometric fallback",
        "fallback_bound_texels": int(np.count_nonzero(fallback_bound & valid_texels[None, ...])),
        "refused_by_host_compatibility": int(np.count_nonzero(observed & ~compatible_support & ~nonblocking)),
        "refused_by_atlas_fallback_state": int(
            np.count_nonzero(observed & compatible_support & ~fallback_bound & ~nonblocking)
        ),
        "refused_by_insufficient_structural_mass": int(
            np.count_nonzero(observed & compatible_support & fallback_bound & ~decisive_structural & ~nonblocking)
        ),
        "nonblocking_vegetation_texels": int(np.count_nonzero(nonblocking)),
        "transport_states": {
            "atlas_interface": int(np.count_nonzero(supported)),
            "nonblocking_woody_vegetation": int(np.count_nonzero(nonblocking)),
            "geometric_fallback": int(np.count_nonzero(observed & ~supported & ~nonblocking)),
        },
        "vegetation": vegetation_provenance,
        "fallback_state_gate_present": fallback_state is not None,
        "transport_posterior": posterior_source,
    }
    mesh_sha = getattr(atlas, "mesh_sha256", None)
    if mesh_sha is not None:
        provenance["mesh_sha256"] = str(mesh_sha)
    for key, path in (("atlas_npz", source_npz), ("atlas_manifest", source_manifest)):
        if path is not None:
            resolved = pathlib.Path(path)
            provenance[key] = str(resolved)
            if resolved.exists():
                provenance[f"{key}_sha256"] = _file_sha256(resolved)

    binding = AtlasMaterialBinding(
        face_to_atlas_row=np.asarray(face_to_row, dtype=np.int32),
        material_probability=probability,
        supported=supported,
        valid_texels=valid_texels,
        material_names=tuple(structural_names),
        material_class=material_class,
        provenance=provenance,
        nonblocking=nonblocking,
    )
    return table, binding


def _integral_indices(values: np.ndarray, name: str) -> np.ndarray:
    raw = np.asarray(values)
    if raw.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not (np.issubdtype(raw.dtype, np.integer) or np.issubdtype(raw.dtype, np.floating)):
        raise ValueError(f"{name} must contain finite integer indices")
    numeric = raw.astype(np.float64)
    if np.any(~np.isfinite(numeric)) or np.any(numeric != np.floor(numeric)):
        raise ValueError(f"{name} must contain finite integer indices")
    return numeric.astype(np.int64)


def _nonblocking_vegetation(
    atlas: Any,
    dense_shape: tuple[int, int, int],
    observed: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Resolve woody volume evidence without confusing it with grass.

    Explicit form and subtype posteriors take priority. If they are absent for
    a cell, the dense Vistas ``Vegetation`` entity is the fallback evidence for
    a woody canopy. Vistas ``Terrain`` is deliberately not treated as woody.
    This lets ordinary dense semantics distinguish canopy from possible grass
    while SAM-derived form evidence can make the distinction more precise.
    """
    form_names = tuple(str(value) for value in getattr(atlas, "vegetation_form_names", ()))
    subtype_names = tuple(str(value) for value in getattr(atlas, "vegetation_subtype_names", ()))
    form = _sparse_evidence_dense(
        atlas,
        getattr(atlas, "vegetation_form_posterior", None),
        len(form_names),
        dense_shape,
        "vegetation_form_posterior",
    )
    subtype = _sparse_evidence_dense(
        atlas,
        getattr(atlas, "vegetation_subtype_posterior", None),
        len(subtype_names),
        dense_shape,
        "vegetation_subtype_posterior",
    )

    def channel(values: np.ndarray, names: tuple[str, ...], label: str) -> np.ndarray:
        if label not in names:
            return np.zeros(dense_shape, dtype=np.float64)
        return values[..., names.index(label)]

    ground = np.maximum(
        channel(form, form_names, "ground_vegetation"),
        channel(subtype, subtype_names, "grass"),
    )
    woody_subtype = sum(
        (channel(subtype, subtype_names, label) for label in ("shrub", "tree", "forest")),
        start=np.zeros(dense_shape, dtype=np.float64),
    )
    woody = np.maximum(channel(form, form_names, "woody_canopy"), woody_subtype)
    explicit = (ground + woody) > 0.0

    entity_names = tuple(str(value) for value in getattr(atlas, "entity_names", ()))
    entity_probability = getattr(atlas, "entity_probability", None)
    if entity_probability is None or "Vegetation" not in entity_names:
        vistas_woody = np.zeros(dense_shape, dtype=np.float64)
    else:
        entity_probability = np.asarray(entity_probability, dtype=np.float64)
        expected = dense_shape + (len(entity_names),)
        if entity_probability.shape != expected:
            raise ValueError(
                f"surface-atlas entity_probability has shape {entity_probability.shape}, expected {expected}"
            )
        vistas_woody = entity_probability[..., entity_names.index("Vegetation")]

    explicit_woody = (woody > MIN_INTERFACE_POSTERIOR) & (woody > ground)
    explicit_ground = (ground > MIN_INTERFACE_POSTERIOR) & (ground >= woody)
    inferred_woody = ~explicit & (vistas_woody > MIN_INTERFACE_POSTERIOR)
    nonblocking = observed & ~explicit_ground & (explicit_woody | inferred_woody)
    return nonblocking, {
        "policy": (
            "explicit grass or ground vegetation keeps the geometric ground interface; explicit woody canopy, "
            "shrub, tree, or forest is non-blocking without registered watertight volume chords; where explicit "
            "form evidence is absent, strict-majority Vistas Vegetation is treated as woody and Terrain is not"
        ),
        "decision_threshold": MIN_INTERFACE_POSTERIOR,
        "form_vocabulary": list(form_names),
        "subtype_vocabulary": list(subtype_names),
        "explicit_ground_texels": int(np.count_nonzero(observed & explicit_ground)),
        "explicit_woody_texels": int(np.count_nonzero(observed & explicit_woody)),
        "vistas_woody_texels": int(np.count_nonzero(observed & inferred_woody)),
        "canopy_geometry": "absent from surface atlas; P.833 requires registered watertight volume chords",
    }


def _sparse_evidence_dense(
    atlas: Any,
    values: Any,
    channels: int,
    dense_shape: tuple[int, int, int],
    name: str,
) -> np.ndarray:
    if channels == 0:
        return np.zeros(dense_shape + (0,), dtype=np.float64)
    sparse = np.asarray(values, dtype=np.float64)
    if sparse.ndim == 4:
        expected = dense_shape + (channels,)
        if sparse.shape != expected:
            raise ValueError(f"surface-atlas {name} has shape {sparse.shape}, expected {expected}")
        return sparse
    triangle_ids = np.asarray(getattr(atlas, "triangle_ids", ()), dtype=np.int64)
    offsets = np.asarray(getattr(atlas, "texel_offsets", ()), dtype=np.int64)
    rows = np.asarray(getattr(atlas, "texel_row", ()), dtype=np.int64)
    columns = np.asarray(getattr(atlas, "texel_column", ()), dtype=np.int64)
    if offsets.shape != (triangle_ids.size + 1,) or sparse.shape != (rows.size, channels):
        raise ValueError(f"surface-atlas sparse {name} does not match its texel index")
    if columns.shape != rows.shape or int(offsets[-1]) != rows.size:
        raise ValueError(f"surface-atlas sparse {name} has an invalid texel index")
    dense = np.zeros(dense_shape + (channels,), dtype=np.float64)
    owner = np.repeat(np.arange(triangle_ids.size, dtype=np.int64), np.diff(offsets))
    dense[owner, rows, columns] = sparse
    return dense


def _texel_indices(v: np.ndarray, u: np.ndarray, height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    """Match the vision atlas's nearest valid canonical-triangle texel."""
    v = np.clip(v, 0.0, 1.0)
    u = np.clip(u, 0.0, 1.0)
    rows = np.floor(v * (height - 1) + 0.5)
    columns = np.floor(u * (width - 1) + 0.5)
    row_excess = rows - v * (height - 1)
    column_excess = columns - u * (width - 1)
    outside = rows / (height - 1) + columns / (width - 1) > 1.0 + 1e-12
    while np.any(outside):
        step_row = outside & (row_excess >= column_excess)
        step_column = outside & ~step_row
        rows[step_row] -= 1.0
        columns[step_column] -= 1.0
        row_excess[step_row] -= 1.0
        column_excess[step_column] -= 1.0
        outside = rows / (height - 1) + columns / (width - 1) > 1.0 + 1e-12
    return rows.astype(np.intp), columns.astype(np.intp)


def _file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "ATLAS_MATERIAL_RULE",
    "ATLAS_PREFIX",
    "MIN_INTERFACE_POSTERIOR",
    "NON_STRUCTURAL_MATERIALS",
    "AtlasMaterialBinding",
    "bind_surface_atlas",
]
