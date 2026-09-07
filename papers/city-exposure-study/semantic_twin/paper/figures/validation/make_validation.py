"""Render the controlled one-reflection transport validation figure.

The figure compares three independent estimates of the same diffuse reflected
transfer in a synthetic open square. It uses only the current-compatible
depth-1 transport contract. The input hashes and full experiment structure are
checked before any figure is written.

Run from any directory with:

    uv run --with scienceplots --project /home/user/tools/devpc-python python \
        semantic_twin/paper/figures/validation/make_validation.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import scienceplots  # noqa: E402, F401  # Registers the SciencePlots styles.
from PIL import Image  # noqa: E402


HERE = Path(__file__).resolve().parent
SEMANTIC_TWIN_ROOT = Path(__file__).resolve().parents[3]
CROSS_VALIDATION = SEMANTIC_TWIN_ROOT / "outputs" / "cross_validation"
QUADRATURE_SOURCE = CROSS_VALIDATION / "deterministic_first_bounce_open_square_high.json"
FORWARD_SOURCE = CROSS_VALIDATION / "forward_sionna_open_depth1_50k_open_square.json"

EXPECTED_SOURCE_HASHES = {
    QUADRATURE_SOURCE: "2fd297325ecdc067b66c106be7a3e0f72b5179815f13cceec3fe555b0e9fbee4",
    FORWARD_SOURCE: "9d5f7b039b32db96b06ff32c3fafdb322fa9a3cc532b755d7ae30402d0140f8c",
}
FREQUENCY_HZ = 15_000_000_000.0
SOURCES = 27
RECEIVERS = 6
TRIANGLES = 8
QUADRATURE_SUBDIVISIONS = 512
QUADRATURE_SURFACE_SAMPLES = 2_097_152
ADJOINT_RAYS = 50_000
ADJOINT_SEEDS = 4
SIONNA_SAMPLES_PER_SOURCE = 50_000
SIONNA_SEEDS = 3
RECEIVER_LABELS = tuple(f"R{index}" for index in range(1, RECEIVERS + 1))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, found {actual!r}")


def _load_hash_locked(path: Path) -> tuple[dict[str, Any], str]:
    actual_hash = _sha256(path)
    _require(actual_hash, EXPECTED_SOURCE_HASHES[path], f"{path.name} SHA-256")
    return json.loads(path.read_text(encoding="utf-8")), actual_hash


def _positive_vector(values: Any, label: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64)
    _require(vector.shape, (RECEIVERS,), f"{label} shape")
    if not np.isfinite(vector).all() or not np.all(vector > 0.0):
        raise ValueError(f"{label} must contain six finite positive values")
    return vector


def _db_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(numerator / denominator)


def _summarize_absolute(values: np.ndarray) -> dict[str, float]:
    absolute = np.abs(values)
    return {
        "median": float(np.median(absolute)),
        "maximum": float(np.max(absolute)),
    }


def load_and_validate() -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Authenticate both experiments and extract the plotted values."""
    quadrature, quadrature_hash = _load_hash_locked(QUADRATURE_SOURCE)
    forward, forward_hash = _load_hash_locked(FORWARD_SOURCE)

    _require(
        quadrature.get("method"),
        "equal-area subtriangle centroid quadrature with exact visibility rays",
        "quadrature method",
    )
    _require(quadrature.get("sources"), SOURCES, "quadrature source count")
    _require(quadrature.get("receivers"), RECEIVERS, "quadrature receiver count")
    _require(quadrature.get("frequency_hz"), FREQUENCY_HZ, "quadrature frequency")
    _require(quadrature.get("validation_rms_height_m"), 1.0, "quadrature roughness")
    _require(len(quadrature.get("rows", ())), 3, "quadrature resolution count")
    quadrature_row = quadrature["rows"][-1]
    _require(
        quadrature_row.get("subdivisions"),
        QUADRATURE_SUBDIVISIONS,
        "quadrature subdivisions",
    )
    _require(
        quadrature_row.get("surface_samples"),
        QUADRATURE_SURFACE_SAMPLES,
        "quadrature surface samples",
    )
    quadrature_transfer = _positive_vector(quadrature_row.get("bounced"), "quadrature bounced transfer")
    previous_quadrature_transfer = _positive_vector(
        quadrature["rows"][-2].get("bounced"), "previous quadrature bounced transfer"
    )

    _require(forward.get("environment"), "open-square", "forward environment")
    _require(forward.get("case"), "open_square", "forward case")
    _require(forward.get("frequency_hz"), FREQUENCY_HZ, "forward frequency")
    _require(forward.get("max_depth"), 1, "forward maximum depth")
    _require(
        forward.get("material", {}).get("kind"),
        "fully diffuse near-perfect reflector on every triangle",
        "forward material",
    )
    _require(forward.get("paths", {}).get("diffuse_reflection"), True, "diffuse paths")
    _require(forward.get("paths", {}).get("specular_reflection"), False, "specular paths")
    _require(forward.get("paths", {}).get("refraction"), False, "refracted paths")
    _require(forward.get("paths", {}).get("diffraction"), False, "diffracted paths")
    provenance = forward.get("provenance", {})
    _require(provenance.get("triangles"), TRIANGLES, "controlled triangle count")
    _require(provenance.get("sources_used"), SOURCES, "forward source count")
    _require(provenance.get("receivers_used"), RECEIVERS, "forward receiver count")
    _require(np.asarray(forward.get("sources")).shape, (SOURCES, 3), "source positions")
    _require(np.asarray(forward.get("receivers")).shape, (RECEIVERS, 3), "receiver positions")

    settings = forward.get("settings", {})
    _require(settings.get("adjoint_rays"), ADJOINT_RAYS, "adjoint ray count")
    _require(settings.get("adjoint_connections"), 1, "adjoint connection count")
    _require(settings.get("adjoint_seeds"), ADJOINT_SEEDS, "adjoint seed count")
    _require(
        settings.get("sionna_samples_per_src"),
        SIONNA_SAMPLES_PER_SOURCE,
        "Sionna sample count",
    )
    _require(settings.get("sionna_seeds"), SIONNA_SEEDS, "Sionna seed count")

    adjoint_transfer = _positive_vector(
        forward.get("adjoint", {}).get("bounced", {}).get("mean"),
        "adjoint bounced transfer",
    )
    adjoint_standard_error = np.asarray(forward["adjoint"]["bounced"]["standard_error"], dtype=np.float64)
    _require(adjoint_standard_error.shape, (RECEIVERS,), "adjoint standard-error shape")
    if not np.isfinite(adjoint_standard_error).all() or np.any(adjoint_standard_error < 0.0):
        raise ValueError("adjoint standard errors must be finite and nonnegative")

    sionna_transfer = _positive_vector(
        forward.get("sionna", {}).get("bounced", {}).get("mean"),
        "Sionna bounced transfer",
    )
    sionna_standard_error = np.asarray(forward["sionna"]["bounced"]["standard_error"], dtype=np.float64)
    _require(sionna_standard_error.shape, (RECEIVERS,), "Sionna standard-error shape")
    if not np.isfinite(sionna_standard_error).all() or np.any(sionna_standard_error < 0.0):
        raise ValueError("Sionna standard errors must be finite and nonnegative")
    if any(run.get("path_buffer_saturated") for run in forward["sionna"]["runs"]):
        raise ValueError("Sionna path buffer saturation invalidates the validation")

    adjoint_residual_db = _db_ratio(adjoint_transfer, quadrature_transfer)
    sionna_residual_db = _db_ratio(sionna_transfer, quadrature_transfer)
    adjoint_residual_percent = 100.0 * (adjoint_transfer / quadrature_transfer - 1.0)
    sionna_residual_percent = 100.0 * (sionna_transfer / quadrature_transfer - 1.0)
    recorded_sionna_minus_adjoint = np.asarray(
        forward["comparison"]["bounced"]["sionna_minus_adjoint_db"], dtype=np.float64
    )
    np.testing.assert_allclose(
        recorded_sionna_minus_adjoint,
        _db_ratio(sionna_transfer, adjoint_transfer),
        rtol=1.0e-12,
        atol=1.0e-12,
    )

    values = {
        "quadrature": quadrature_transfer,
        "adjoint": adjoint_transfer,
        "adjoint_standard_error": adjoint_standard_error,
        "sionna": sionna_transfer,
        "sionna_standard_error": sionna_standard_error,
        "adjoint_residual_db": adjoint_residual_db,
        "sionna_residual_db": sionna_residual_db,
        "adjoint_residual_percent": adjoint_residual_percent,
        "sionna_residual_percent": sionna_residual_percent,
    }
    audit = {
        "schema_version": "controlled_depth1_validation_figure_audit_v1",
        "sources": {
            "deterministic_surface_quadrature": {
                "path_from_semantic_twin_root": str(QUADRATURE_SOURCE.relative_to(SEMANTIC_TWIN_ROOT)),
                "sha256": quadrature_hash,
            },
            "adjoint_and_forward_tracer": {
                "path_from_semantic_twin_root": str(FORWARD_SOURCE.relative_to(SEMANTIC_TWIN_ROOT)),
                "sha256": forward_hash,
            },
        },
        "controlled_experiment": {
            "frequency_hz": FREQUENCY_HZ,
            "geometry": "exact ground plane and three rectangular walls",
            "triangles": TRIANGLES,
            "sources": SOURCES,
            "receivers": RECEIVERS,
            "interaction_depth": 1,
            "surface": "fully diffuse near-perfect reflector",
            "excluded_mechanisms": ["specular reflection", "refraction", "diffraction"],
            "quantity": "incoherent bounced transfer in inverse square meters",
        },
        "estimators": {
            "deterministic_surface_quadrature": {
                "subdivisions": QUADRATURE_SUBDIVISIONS,
                "surface_samples": QUADRATURE_SURFACE_SAMPLES,
                "previous_resolution_subdivisions": int(quadrature["rows"][-2]["subdivisions"]),
                "previous_to_final_change_db": _db_ratio(quadrature_transfer, previous_quadrature_transfer).tolist(),
                "previous_to_final_absolute_change_db": _summarize_absolute(
                    _db_ratio(quadrature_transfer, previous_quadrature_transfer)
                ),
            },
            "adjoint_first_diffuse": {
                "primary_rays_per_seed": ADJOINT_RAYS,
                "seeds": ADJOINT_SEEDS,
                "connections_per_vertex": 1,
            },
            "independent_forward_tracer": {
                "engine": "Sionna RT",
                "samples_per_source_per_seed": SIONNA_SAMPLES_PER_SOURCE,
                "seeds": SIONNA_SEEDS,
                "path_buffer_saturated": False,
            },
        },
        "plotted_values": {
            "receiver_labels": list(RECEIVER_LABELS),
            "deterministic_surface_quadrature_m_inv2": quadrature_transfer.tolist(),
            "adjoint_first_diffuse_mean_m_inv2": adjoint_transfer.tolist(),
            "adjoint_first_diffuse_standard_error_m_inv2": adjoint_standard_error.tolist(),
            "independent_forward_tracer_mean_m_inv2": sionna_transfer.tolist(),
            "independent_forward_tracer_standard_error_m_inv2": sionna_standard_error.tolist(),
        },
        "error_against_deterministic_quadrature_db": {
            "adjoint_first_diffuse": {
                "signed_by_receiver": adjoint_residual_db.tolist(),
                "absolute": _summarize_absolute(adjoint_residual_db),
            },
            "independent_forward_tracer": {
                "signed_by_receiver": sionna_residual_db.tolist(),
                "absolute": _summarize_absolute(sionna_residual_db),
            },
        },
        "difference_from_deterministic_quadrature_percent": {
            "adjoint_first_diffuse": {
                "signed_by_receiver": adjoint_residual_percent.tolist(),
                "absolute": _summarize_absolute(adjoint_residual_percent),
            },
            "independent_forward_tracer": {
                "signed_by_receiver": sionna_residual_percent.tolist(),
                "absolute": _summarize_absolute(sionna_residual_percent),
            },
        },
    }
    return values, audit


def _configure_style() -> None:
    plt.style.use(["science", "ieee", "no-latex"])
    matplotlib.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["STIXGeneral"],
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "xtick.labelsize": 7.3,
            "ytick.labelsize": 7.3,
            "legend.fontsize": 7.2,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.0,
            "lines.markersize": 4.8,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": None,
            "savefig.facecolor": "white",
        }
    )


def draw(values: dict[str, np.ndarray]) -> None:
    """Write the vector figure and its 300 dpi review companion."""
    _configure_style()
    figure, axes = plt.subplots(1, 2, figsize=(7.16, 2.58))
    x = np.arange(RECEIVERS, dtype=np.float64)

    (quadrature_artist,) = axes[0].plot(
        x - 0.13,
        1.0e4 * values["quadrature"],
        color="black",
        marker="o",
        markerfacecolor="white",
        markeredgecolor="black",
        linestyle="none",
        label="Surface quadrature",
        zorder=4,
    )
    adjoint_artist = axes[0].errorbar(
        x,
        1.0e4 * values["adjoint"],
        yerr=1.0e4 * values["adjoint_standard_error"],
        color="#0065BD",
        marker="s",
        markerfacecolor="white",
        capsize=2.0,
        elinewidth=0.8,
        linestyle="none",
        label="Adjoint estimator",
        zorder=3,
    )
    forward_artist = axes[0].errorbar(
        x + 0.13,
        1.0e4 * values["sionna"],
        yerr=1.0e4 * values["sionna_standard_error"],
        color="#D62728",
        marker="^",
        markerfacecolor="white",
        capsize=2.0,
        elinewidth=0.8,
        linestyle="none",
        label="Independent forward",
        zorder=2,
    )
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(RECEIVER_LABELS)
    axes[0].set_xlim(-0.35, RECEIVERS - 0.65)
    axes[0].set_ylim(0.0, 9.8)
    axes[0].set_xlabel("Receiver")
    axes[0].set_ylabel(r"Reflected transfer [$10^{-4}\,\mathrm{m}^{-2}$]")
    axes[0].text(
        0.0,
        1.015,
        "(a)",
        transform=axes[0].transAxes,
        va="bottom",
        fontweight="bold",
    )
    axes[0].grid(axis="y", color="0.86", linewidth=0.5)

    adjoint_percent_se = 100.0 * values["adjoint_standard_error"] / values["quadrature"]
    sionna_percent_se = 100.0 * values["sionna_standard_error"] / values["quadrature"]
    axes[1].axhline(0.0, color="0.35", linewidth=0.7, zorder=1)
    axes[1].errorbar(
        x - 0.07,
        values["adjoint_residual_percent"],
        yerr=adjoint_percent_se,
        color="#0065BD",
        marker="s",
        markerfacecolor="white",
        capsize=2.0,
        elinewidth=0.8,
        linestyle="none",
        zorder=3,
    )
    axes[1].errorbar(
        x + 0.07,
        values["sionna_residual_percent"],
        yerr=sionna_percent_se,
        color="#D62728",
        marker="^",
        markerfacecolor="white",
        capsize=2.0,
        elinewidth=0.8,
        linestyle="none",
        zorder=2,
    )
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(RECEIVER_LABELS)
    axes[1].set_xlim(-0.35, RECEIVERS - 0.65)
    axes[1].set_ylim(-2.5, 2.5)
    axes[1].set_yticks((-2, -1, 0, 1, 2))
    axes[1].set_xlabel("Receiver")
    axes[1].set_ylabel("Difference from quadrature [%]")
    axes[1].text(
        0.0,
        1.015,
        "(b)",
        transform=axes[1].transAxes,
        va="bottom",
        fontweight="bold",
    )
    axes[1].grid(axis="y", color="0.86", linewidth=0.5)

    for axis in axes:
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.tick_params(which="both", top=False, right=False)

    figure.suptitle(
        r"Controlled single-reflection diffuse scene, 15 GHz",
        x=0.5,
        y=0.985,
        fontsize=8.0,
    )
    figure.legend(
        [quadrature_artist, adjoint_artist, forward_artist],
        ["Surface quadrature", "Adjoint estimator", "Independent forward"],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.925),
        ncol=3,
        frameon=False,
        handletextpad=0.45,
        columnspacing=1.4,
    )
    figure.subplots_adjust(left=0.088, right=0.985, bottom=0.20, top=0.76, wspace=0.32)
    pdf_path = HERE / "validation.pdf"
    png_path = HERE / "validation.png"
    figure.savefig(
        pdf_path,
        metadata={"Creator": "make_validation.py", "CreationDate": None, "ModDate": None},
    )
    plt.close(figure)
    subprocess.run(
        [
            "pdftocairo",
            "-png",
            "-singlefile",
            "-r",
            "300",
            str(pdf_path),
            str(png_path.with_suffix("")),
        ],
        check=True,
    )


def audit_outputs(audit: dict[str, Any]) -> None:
    """Record the rendered dimensions, hashes, and embedded vector fonts."""
    pdf_path = HERE / "validation.pdf"
    png_path = HERE / "validation.png"
    pdf_info = subprocess.run(["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True).stdout
    fonts_output = subprocess.run(["pdffonts", str(pdf_path)], check=True, capture_output=True, text=True).stdout
    images_output = subprocess.run(
        ["pdfimages", "-list", str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    font_rows = [re.split(r"\s{2,}", line.strip()) for line in fonts_output.splitlines()[2:] if line.strip()]
    if not font_rows:
        raise ValueError("validation.pdf contains no fonts")
    embedded = all(len(row) >= 4 and row[3].split()[0] == "yes" for row in font_rows)
    if not embedded:
        raise ValueError("validation.pdf contains a non-embedded font")
    font_types = sorted({row[1] for row in font_rows})
    if "Type 3" in font_types:
        raise ValueError("validation.pdf contains a Type 3 font")
    image_rows = [line for line in images_output.splitlines()[2:] if line.strip()]
    if image_rows:
        raise ValueError("validation.pdf unexpectedly contains a raster image")

    image = Image.open(png_path)
    _require(image.size, (2148, 774), "300 dpi PNG dimensions")
    page_match = re.search(r"^Page size:\s+(.+)$", pdf_info, flags=re.MULTILINE)
    if page_match is None:
        raise ValueError("pdfinfo did not report a page size")
    if not page_match.group(1).startswith("515.52 x "):
        raise ValueError(f"validation.pdf is not exactly 7.16 in wide: {page_match.group(1)}")

    audit["outputs"] = {
        "pdf": {
            "path": pdf_path.name,
            "sha256": _sha256(pdf_path),
            "page_size": page_match.group(1),
            "contains_raster_images": False,
            "fonts_embedded": embedded,
            "contains_type3_fonts": False,
            "font_types": font_types,
            "fonts": sorted({row[0] for row in font_rows}),
        },
        "png": {
            "path": png_path.name,
            "sha256": _sha256(png_path),
            "dimensions_pixels": list(image.size),
            "rasterization_dpi": 300,
        },
    }
    audit["generator"] = {
        "path": Path(__file__).name,
        "sha256": _sha256(Path(__file__)),
        "style": ["science", "ieee", "no-latex"],
        "width_inches": 7.16,
    }
    (HERE / "validation.audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    values, audit = load_and_validate()
    draw(values)
    audit_outputs(audit)
    print(f"wrote {HERE / 'validation.pdf'}")
    print(f"wrote {HERE / 'validation.png'}")
    print(f"wrote {HERE / 'validation.audit.json'}")


if __name__ == "__main__":
    main()
