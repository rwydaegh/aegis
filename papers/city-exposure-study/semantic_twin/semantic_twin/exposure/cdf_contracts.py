"""Named production contracts for fixed-route CDF campaigns."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

from semantic_twin.runconfig import RunConfig


@dataclass(frozen=True)
class ReferenceFiles:
    """One sealed exposure generation used as a CDF reference."""

    manifest: str
    locations: str
    spectra: str
    manifest_sha256: str
    locations_sha256: str
    spectra_sha256: str

    def paths(self) -> tuple[str, str, str]:
        return self.manifest, self.locations, self.spectra

    def hashes(self) -> dict[str, str]:
        return {
            "manifest": self.manifest_sha256,
            "locations": self.locations_sha256,
            "spectra": self.spectra_sha256,
        }


@dataclass(frozen=True)
class TissueDatabasePin:
    """Exact tissue database bytes accepted by a production campaign."""

    sha256: str
    bytes: int


@dataclass(frozen=True)
class ArtifactPin:
    """Exact path and bytes of one contract artifact."""

    path: str
    sha256: str


@dataclass(frozen=True)
class MaterialEvidencePin:
    """Material evidence and its canonical JSON sidecar, when required."""

    role: str
    artifact: ArtifactPin | None
    atlas_json_sidecar: ArtifactPin | None

    def identity_fields(self) -> dict[str, str | None]:
        return {
            "material_evidence_role": self.role,
            "material_evidence_path": self.artifact.path if self.artifact is not None else None,
            "material_evidence_sha256": self.artifact.sha256 if self.artifact is not None else None,
            "atlas_json_sidecar_path": (self.atlas_json_sidecar.path if self.atlas_json_sidecar is not None else None),
            "atlas_json_sidecar_sha256": (
                self.atlas_json_sidecar.sha256 if self.atlas_json_sidecar is not None else None
            ),
        }


@dataclass(frozen=True)
class RoutePin:
    """Canonical route geometry behind a fixed standpoint sample."""

    canonical_walk_provenance_sha256: str
    geometry: str
    path: str
    stride_m: float
    registered_standpoints: int
    road_length_m: float

    def identity_fields(self) -> dict[str, str | float | int]:
        return {
            "canonical_walk_provenance_sha256": self.canonical_walk_provenance_sha256,
            "route_geometry": self.geometry,
            "route_path": self.path,
            "route_stride_m": self.stride_m,
            "route_registered_standpoints": self.registered_standpoints,
            "route_road_length_m": self.road_length_m,
        }


@dataclass(frozen=True)
class ReferenceIdentityPin:
    """Exact scene, route, and reference-run identity of one campaign."""

    mesh_sha256: str
    standpoint_array_sha256: str
    standpoints: int
    surface_binding_sha256: str
    reference_run_digest: str
    material_evidence: MaterialEvidencePin
    route: RoutePin

    def identity_fields(self) -> dict[str, Any]:
        return {
            "mesh_sha256": self.mesh_sha256,
            "standpoint_array_sha256": self.standpoint_array_sha256,
            "standpoints": self.standpoints,
            "surface_binding_sha256": self.surface_binding_sha256,
            "reference_run_digest": self.reference_run_digest,
            **self.material_evidence.identity_fields(),
            **self.route.identity_fields(),
        }


@dataclass(frozen=True)
class BodySourcePin:
    """Body source and coupling law used by a production campaign."""

    model: str
    phantom: str
    filename: str
    data_dir: str
    mass_kg: float
    sha256: str
    frequency_hz: float
    level: int
    triangles: int
    transmission_coefficient: float

    def __post_init__(self) -> None:
        if self.filename != f"{self.phantom}.stl":
            raise ValueError("production body filename must match its phantom name")
        if PurePosixPath(self.data_dir).is_absolute():
            raise ValueError("production body data_dir must be repository-relative")

    def manifest_fields(self) -> dict[str, Any]:
        return {
            "phantom": self.phantom,
            "frequency_hz": self.frequency_hz,
            "level": self.level,
            "triangles": self.triangles,
            "T0": self.transmission_coefficient,
        }


@dataclass(frozen=True)
class CdfProductionContract:
    """Every pinned input that gives a named CDF campaign its meaning."""

    name: str
    config_path: str
    output_dir: str
    reference: ReferenceFiles
    base_seeds: tuple[int, ...]
    diagnostic_look: int
    looks: tuple[int, ...]
    bootstrap_replicates: int
    bootstrap_seed: int
    confidence: float
    bootstrap_alpha_allocation: str
    body_chunk_cells: int
    body_peak_selection_min_fraction: float
    thresholds: tuple[tuple[str, float], ...]
    body: BodySourcePin
    seed_stream_stride: int
    seed_stream_rule: str
    reference_identity: ReferenceIdentityPin
    run: RunConfig
    point_kind_counts: tuple[tuple[str, int], ...]
    tissue_database: TissueDatabasePin
    archived_rooftop_run_dir: str | None = None

    def __post_init__(self) -> None:
        evidence = self.reference_identity.material_evidence
        route = self.reference_identity.route
        point_kinds = [kind for kind, _count in self.point_kind_counts]
        if len(point_kinds) != len(set(point_kinds)):
            raise ValueError("reference point-kind pins must be unique")
        if self.reference_identity.standpoints != sum(count for _kind, count in self.point_kind_counts):
            raise ValueError("reference standpoint count differs from its point-kind counts")
        if route.path != self.run.walk_path or route.stride_m != self.run.walk_stride_m:
            raise ValueError("reference route pin differs from its RunConfig path or stride")
        if self.run.materials == "atlas":
            if evidence.role != "joint_surface_atlas" or evidence.artifact is None:
                raise ValueError("an atlas production run requires a joint surface atlas artifact pin")
            if evidence.atlas_json_sidecar is None:
                raise ValueError("an atlas production run requires its canonical JSON sidecar pin")
            if self.run.atlas_npz != evidence.artifact.path:
                raise ValueError("RunConfig and material evidence pin name different surface atlases")

    def threshold_values(self) -> dict[str, float]:
        return dict(self.thresholds)

    def reference_identity_values(self) -> dict[str, Any]:
        return self.reference_identity.identity_fields()

    def run_setting_values(self) -> dict[str, Any]:
        values = self.run.as_dict()
        values["models"] = list(values["models"])
        return values

    def point_kind_count_values(self) -> dict[str, int]:
        return dict(self.point_kind_counts)


KORENMARKT_CDF_STOPPING_4096_V1 = CdfProductionContract(
    name="korenmarkt_cdf_stopping_4096_v1",
    config_path="config/cdf_convergence_4096.json",
    output_dir="outputs/cdf_convergence_4096_atlas_v1",
    reference=ReferenceFiles(
        manifest=("outputs/exposure_korenmarkt/final_korenmarkt_walk_drjit_atlas_4096_v2_15ghz_manifest.json"),
        locations=("outputs/exposure_korenmarkt/final_korenmarkt_walk_drjit_atlas_4096_v2_15ghz_locations.jsonl"),
        spectra=("outputs/exposure_korenmarkt/final_korenmarkt_walk_drjit_atlas_4096_v2_15ghz_spectra.npz"),
        manifest_sha256="e87bd8e5db0308cfa9ad445c179a8464b19a7aaa8eaf2242fb1492c0eee75a9d",
        locations_sha256="66b4e5c70494dc653a8d99ab33d4551fac99d70029114995ef9523d831e34534",
        spectra_sha256="1186e952d4edc65046e69940a54c1024cb29c1fee6e6ae72acbe95b76f59b90b",
    ),
    base_seeds=tuple(range(7, 39)),
    diagnostic_look=8,
    looks=(16, 24, 32),
    bootstrap_replicates=20_000,
    bootstrap_seed=20260805,
    confidence=0.95,
    bootstrap_alpha_allocation="equal Bonferroni allocation over formal looks 16, 24, and 32",
    body_chunk_cells=512,
    body_peak_selection_min_fraction=0.95,
    thresholds=(
        ("point_p90_db", 0.10),
        ("point_max_db", 0.15),
        ("cdf_q50_db", 0.05),
        ("cdf_q10_q90_db", 0.10),
        ("cdf_endpoint_db", 0.15),
        ("stability_wasserstein_db", 0.03),
        ("stability_q50_db", 0.03),
        ("stability_q10_q90_db", 0.05),
        ("stability_endpoint_db", 0.10),
        ("body_peak_max_db", 0.15),
    ),
    body=BodySourcePin(
        model="rooftop",
        phantom="duke",
        filename="duke.stl",
        data_dir="../../../data",
        mass_kg=72.4,
        sha256="781e65ef3882f1347669e0ddca5dafa82cd6368dddd6b9e801dc49613822fe3b",
        frequency_hz=15.0e9,
        level=2,
        triangles=56_024,
        transmission_coefficient=0.5001397541911426,
    ),
    seed_stream_stride=1000,
    seed_stream_rule="base seed + 1000 * frozen production standpoint index",
    reference_identity=ReferenceIdentityPin(
        mesh_sha256="bfbdba0657a1dd4b8b819e7e611dbfd4eea919e5c08538078ff1948599957264",
        standpoint_array_sha256="d373e65c769017c5309db17c2035adf2178641d421fc5fbbdf92356e424b6f5c",
        standpoints=13,
        surface_binding_sha256="2441abf4bc3e9d7190e45ef3de154fbc7507e82cf5d5f64f77f4320e58b9a0aa",
        reference_run_digest="af8b9fc7cf3e",
        material_evidence=MaterialEvidencePin(
            role="joint_surface_atlas",
            artifact=ArtifactPin(
                path="outputs/site_semantics/korenmarkt/joint_atlas_250m_r8.npz",
                sha256="c452c34e1d9422022d55fc758d228c22a39b80d9a770042e89e13f9110f43a76",
            ),
            atlas_json_sidecar=ArtifactPin(
                path="outputs/site_semantics/korenmarkt/joint_atlas_250m_r8.json",
                sha256="80d8f0bb448d6677fc29c9c51e81036e9b54913d52f1480030095ac16f08d783",
            ),
        ),
        route=RoutePin(
            canonical_walk_provenance_sha256=("b347e8c0346b751f30e808178100e85a36660be1776c43ae3e0f0631a9e87531"),
            geometry="registered_road_v1",
            path="links",
            stride_m=6.0,
            registered_standpoints=5,
            road_length_m=49.20198618693214,
        ),
    ),
    run=RunConfig(
        site="korenmarkt",
        crop_m=250,
        law="band",
        models=("isotropic", "rooftop", "street_small_cell"),
        estimator="escape",
        next_event=None,
        walk="route",
        walk_path="links",
        walk_radius_m=90.0,
        walk_spacing_m=3.0,
        walk_stride_m=6.0,
        head_height_m=1.5,
        locations=0,
        frequency_hz=15.0e9,
        max_bounces=3,
        roulette_start=4,
        roulette_floor=0.05,
        ray_epsilon_m=1.0e-3,
        range_weighted_escape=False,
        materials="atlas",
        walk_npz=None,
        atlas_npz="outputs/site_semantics/korenmarkt/joint_atlas_250m_r8.npz",
        rays=1_600_000,
        batch=400_000,
        local_cells=4096,
        exit_bands=18,
        seed=7,
        variant="cuda_ad_rgb",
        transport_kernel="drjit",
        tag="final_korenmarkt_walk_drjit_atlas_4096_v2",
    ),
    point_kind_counts=(("camera_registered", 5), ("stride_interpolated", 8)),
    tissue_database=TissueDatabasePin(
        sha256="51dc983da2fa4e40bde9ca4e9830ecd6b41739c2b92b28b5efbdc5d5e556aa8f",
        bytes=7_094_272,
    ),
    archived_rooftop_run_dir="outputs/angular_convergence_4096_atlas_v2/runs",
)


PRAGUE_CDF_STOPPING_4096_V1 = CdfProductionContract(
    name="prague_cdf_stopping_4096_v1",
    config_path="config/cdf_convergence_prague_4096.json",
    output_dir="outputs/cdf_convergence_prague_4096_atlas_v1",
    reference=ReferenceFiles(
        manifest=("outputs/exposure_korenmarkt/final_prague_walk_drjit_atlas_4096_v1_15ghz_manifest.json"),
        locations=("outputs/exposure_korenmarkt/final_prague_walk_drjit_atlas_4096_v1_15ghz_locations.jsonl"),
        spectra=("outputs/exposure_korenmarkt/final_prague_walk_drjit_atlas_4096_v1_15ghz_spectra.npz"),
        manifest_sha256="4a0b6753b512d1e18fc26efcbf01a68d2d60b97b960b4fed23e541549ae93189",
        locations_sha256="9a513fd8f70112124e0d9721b740a7c2ff5c2bd5ffc0b5b004a54bdd6e67289b",
        spectra_sha256="f8c763660bd1f5453505c2263591935adc58d64a167a47c22e1b38dc4aa16cea",
    ),
    base_seeds=tuple(range(7, 39)),
    diagnostic_look=8,
    looks=(16, 24, 32),
    bootstrap_replicates=20_000,
    bootstrap_seed=20260806,
    confidence=0.95,
    bootstrap_alpha_allocation="equal Bonferroni allocation over formal looks 16, 24, and 32",
    body_chunk_cells=512,
    body_peak_selection_min_fraction=0.95,
    thresholds=(
        ("point_p90_db", 0.10),
        ("point_max_db", 0.15),
        ("cdf_q50_db", 0.05),
        ("cdf_q10_q90_db", 0.10),
        ("cdf_endpoint_db", 0.15),
        ("stability_wasserstein_db", 0.03),
        ("stability_q50_db", 0.03),
        ("stability_q10_q90_db", 0.05),
        ("stability_endpoint_db", 0.10),
        ("body_peak_max_db", 0.15),
    ),
    body=BodySourcePin(
        model="rooftop",
        phantom="duke",
        filename="duke.stl",
        data_dir="../../../data",
        mass_kg=72.4,
        sha256="781e65ef3882f1347669e0ddca5dafa82cd6368dddd6b9e801dc49613822fe3b",
        frequency_hz=15.0e9,
        level=2,
        triangles=56_024,
        transmission_coefficient=0.5001397541911426,
    ),
    seed_stream_stride=1000,
    seed_stream_rule="base seed + 1000 * frozen production standpoint index",
    reference_identity=ReferenceIdentityPin(
        mesh_sha256="a2533b5d589f3604b63e905a5673873df2db7a41d396c8cef03389e72d08b6f4",
        standpoint_array_sha256="f1761deb913aa772f7e68189b1fdaa04b64cd55b18e31e4b4e1260243484240b",
        standpoints=68,
        surface_binding_sha256="2441abf4bc3e9d7190e45ef3de154fbc7507e82cf5d5f64f77f4320e58b9a0aa",
        reference_run_digest="2daef0c8931a",
        material_evidence=MaterialEvidencePin(
            role="joint_surface_atlas",
            artifact=ArtifactPin(
                path="outputs/site_semantics/prague_staromestske/joint_atlas_250m_r8.npz",
                sha256="323b6c3f371c711cb81d287325c4ae8b3790bcc8b77d6cd5013819cb08080023",
            ),
            atlas_json_sidecar=ArtifactPin(
                path="outputs/site_semantics/prague_staromestske/joint_atlas_250m_r8.json",
                sha256="8ec1ab2485545abd0ddeaf461dc6ce01ff319fb994b4c12e4ec9cb1be70d2b5d",
            ),
        ),
        route=RoutePin(
            canonical_walk_provenance_sha256=("0a983775a019cf351daf0ec927b299c0ffbc1e389bf604b3acdc2fac45d7e9e8"),
            geometry="registered_road_v1",
            path="links",
            stride_m=6.0,
            registered_standpoints=12,
            road_length_m=339.7173561271683,
        ),
    ),
    run=RunConfig(
        site="prague_staromestske",
        crop_m=250,
        law="band",
        models=("isotropic", "rooftop", "street_small_cell"),
        estimator="escape",
        next_event=None,
        walk="route",
        walk_path="links",
        walk_radius_m=90.0,
        walk_spacing_m=3.0,
        walk_stride_m=6.0,
        head_height_m=1.5,
        locations=0,
        frequency_hz=15.0e9,
        max_bounces=3,
        roulette_start=4,
        roulette_floor=0.05,
        ray_epsilon_m=1.0e-3,
        range_weighted_escape=False,
        materials="atlas",
        walk_npz=None,
        atlas_npz="outputs/site_semantics/prague_staromestske/joint_atlas_250m_r8.npz",
        rays=1_600_000,
        batch=400_000,
        local_cells=4096,
        exit_bands=18,
        seed=7,
        variant="cuda_ad_rgb",
        transport_kernel="drjit",
        tag="final_prague_walk_drjit_atlas_4096_v1",
    ),
    point_kind_counts=(("camera_registered", 12), ("stride_interpolated", 56)),
    tissue_database=TissueDatabasePin(
        sha256="51dc983da2fa4e40bde9ca4e9830ecd6b41739c2b92b28b5efbdc5d5e556aa8f",
        bytes=7_094_272,
    ),
)


PRODUCTION_CDF_CONTRACTS: Mapping[str, CdfProductionContract] = MappingProxyType(
    {
        KORENMARKT_CDF_STOPPING_4096_V1.name: KORENMARKT_CDF_STOPPING_4096_V1,
        PRAGUE_CDF_STOPPING_4096_V1.name: PRAGUE_CDF_STOPPING_4096_V1,
    }
)


def production_contract(name: str) -> CdfProductionContract | None:
    """Resolve a named contract, while keeping ``custom`` visibly unpinned."""
    if name == "custom":
        return None
    try:
        return PRODUCTION_CDF_CONTRACTS[name]
    except KeyError as error:
        raise ValueError(f"unknown production CDF contract: {name}") from error


def registered_reference_triples() -> tuple[tuple[str, tuple[str, str, str]], ...]:
    """Return each production config and the exact reference files it requires."""
    return tuple((contract.config_path, contract.reference.paths()) for contract in PRODUCTION_CDF_CONTRACTS.values())


def body_sources(
    contracts: Iterable[CdfProductionContract],
) -> tuple[tuple[str, str], ...]:
    """Deduplicate named phantom files and reject conflicting hash pins."""
    sources: dict[str, str] = {}
    for contract in contracts:
        filename = contract.body.filename
        previous = sources.setdefault(filename, contract.body.sha256)
        if previous != contract.body.sha256:
            raise ValueError(f"conflicting production body hashes for {filename}: {previous} != {contract.body.sha256}")
    return tuple(sorted(sources.items()))


def registered_body_sources() -> tuple[tuple[str, str], ...]:
    """Return each phantom file and exact hash needed by named contracts."""
    return body_sources(PRODUCTION_CDF_CONTRACTS.values())
