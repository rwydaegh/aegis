"""Named production contracts for fixed-route CDF campaigns."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


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
class BodySourcePin:
    """Body source and coupling law used by a production campaign."""

    model: str
    phantom: str
    mass_kg: float
    sha256: str
    frequency_hz: float
    level: int
    triangles: int
    transmission_coefficient: float

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
    model_names: tuple[str, ...]
    seed_stream_stride: int
    seed_stream_rule: str
    identity_hashes: tuple[tuple[str, str], ...]
    run_settings: tuple[tuple[str, Any], ...]
    point_kind_counts: tuple[tuple[str, int], ...]
    tissue_database: TissueDatabasePin
    archived_rooftop_run_dir: str | None = None

    def threshold_values(self) -> dict[str, float]:
        return dict(self.thresholds)

    def identity_hash_values(self) -> dict[str, str]:
        return dict(self.identity_hashes)

    def run_setting_values(self) -> dict[str, Any]:
        values = dict(self.run_settings)
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
        mass_kg=72.4,
        sha256="781e65ef3882f1347669e0ddca5dafa82cd6368dddd6b9e801dc49613822fe3b",
        frequency_hz=15.0e9,
        level=2,
        triangles=56_024,
        transmission_coefficient=0.5001397541911426,
    ),
    model_names=("isotropic", "rooftop", "street_small_cell"),
    seed_stream_stride=1000,
    seed_stream_rule="base seed + 1000 * frozen production standpoint index",
    identity_hashes=(
        ("mesh_sha256", "bfbdba0657a1dd4b8b819e7e611dbfd4eea919e5c08538078ff1948599957264"),
        (
            "material_evidence_sha256",
            "c452c34e1d9422022d55fc758d228c22a39b80d9a770042e89e13f9110f43a76",
        ),
        (
            "standpoint_array_sha256",
            "d373e65c769017c5309db17c2035adf2178641d421fc5fbbdf92356e424b6f5c",
        ),
    ),
    run_settings=(
        ("site", "korenmarkt"),
        ("crop_m", 250),
        ("law", "band"),
        ("models", ("isotropic", "rooftop", "street_small_cell")),
        ("estimator", "escape"),
        ("walk", "route"),
        ("walk_path", "links"),
        ("walk_stride_m", 6.0),
        ("locations", 0),
        ("frequency_hz", 15.0e9),
        ("max_bounces", 3),
        ("roulette_start", 4),
        ("materials", "atlas"),
        ("rays", 1_600_000),
        ("batch", 400_000),
        ("local_cells", 4096),
        ("exit_bands", 18),
        ("seed", 7),
        ("variant", "cuda_ad_rgb"),
        ("transport_kernel", "drjit"),
    ),
    point_kind_counts=(("camera_registered", 5), ("stride_interpolated", 8)),
    tissue_database=TissueDatabasePin(
        sha256="51dc983da2fa4e40bde9ca4e9830ecd6b41739c2b92b28b5efbdc5d5e556aa8f",
        bytes=7_094_272,
    ),
    archived_rooftop_run_dir="outputs/angular_convergence_4096_atlas_v2/runs",
)


PRODUCTION_CDF_CONTRACTS: Mapping[str, CdfProductionContract] = MappingProxyType(
    {KORENMARKT_CDF_STOPPING_4096_V1.name: KORENMARKT_CDF_STOPPING_4096_V1}
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
        filename = f"{contract.body.phantom}.stl"
        previous = sources.setdefault(filename, contract.body.sha256)
        if previous != contract.body.sha256:
            raise ValueError(f"conflicting production body hashes for {filename}: {previous} != {contract.body.sha256}")
    return tuple(sorted(sources.items()))


def registered_body_sources() -> tuple[tuple[str, str], ...]:
    """Return each phantom file and exact hash needed by named contracts."""
    return body_sources(PRODUCTION_CDF_CONTRACTS.values())
