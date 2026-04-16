"""Compute routes: dosimetry, ray tracing, voxel RT."""

from __future__ import annotations

from flask import Flask

# Helper re-exports for other routes modules and tests that import these
# from `aegis.viewer.routes.compute` directly.
from ._parsing import _parse_bool as _parse_bool
from ._parsing import _parse_freq_and_tissue as _parse_freq_and_tissue
from ._parsing import _parse_mode_or_level as _parse_mode_or_level
from ._parsing import _parse_quantities_and_scenario as _parse_quantities_and_scenario
from ._parsing import _parse_rotation_y as _parse_rotation_y
from ._parsing import _parse_vec3 as _parse_vec3
from ._parsing import _validate_scene_path as _validate_scene_path
from ._responses import _build_binary_response as _build_binary_response
from ._responses import _build_stats_response as _build_stats_response
from ._responses import _inject_curvature_H as _inject_curvature_H
from ._responses import _json_dumps_safe as _json_dumps_safe
from ._responses import _run_dosimetry as _run_dosimetry
from ._responses import _sanitize_for_json as _sanitize_for_json
from ._responses import _stats_label as _stats_label

# Route implementation functions (attached via register())
from .dosimetry import _api_compute_impl, _api_gpu_status_impl, _handle_validate_sinc
from .exports import _export_dosimetry_csv_impl, _export_dosimetry_json_impl, _export_dosimetry_npz_impl
from .misc import _channel_presets_impl, _compliance_report_impl, _lsp_heatmap_impl
from .rt import _api_compute_rt_impl
from .scenes import _api_scene_load_impl, _api_scenes_impl, _api_voxels_hull_mesh_impl
from .sionna_rt import _api_compute_sionna_env_rt_impl, _api_compute_sionna_rt_impl
from .voxel_rt import _api_compute_voxel_rt_impl


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach compute routes to *app*."""

    @app.route("/api/compute", methods=["POST"])
    def api_compute():
        return _api_compute_impl(cache, cache_lock)

    @app.route("/api/scenes")
    def api_scenes():
        return _api_scenes_impl(cache, cache_lock)

    @app.route("/api/scene/load", methods=["POST"])
    def api_scene_load():
        return _api_scene_load_impl(cache, cache_lock)

    @app.route("/api/voxels/hull-mesh", methods=["GET"])
    def api_voxels_hull_mesh():
        return _api_voxels_hull_mesh_impl(cache, cache_lock)

    @app.route("/api/compute/rt", methods=["POST"])
    def api_compute_rt():
        return _api_compute_rt_impl(cache, cache_lock)

    @app.route("/api/compute/sionna-rt", methods=["POST"])
    def api_compute_sionna_rt():
        return _api_compute_sionna_rt_impl(cache, cache_lock)

    @app.route("/api/compute/voxel-rt", methods=["POST"])
    def api_compute_voxel_rt():
        return _api_compute_voxel_rt_impl(cache, cache_lock)

    @app.route("/api/compute/sionna-env-rt", methods=["POST"])
    def api_compute_sionna_env_rt():
        return _api_compute_sionna_env_rt_impl(cache, cache_lock)

    @app.route("/api/export/dosimetry-csv", methods=["GET"])
    def export_dosimetry_csv():
        return _export_dosimetry_csv_impl(cache, cache_lock)

    @app.route("/api/export/dosimetry-json", methods=["GET"])
    def export_dosimetry_json():
        return _export_dosimetry_json_impl(cache, cache_lock)

    @app.route("/api/export/dosimetry-npz", methods=["GET"])
    def export_dosimetry_npz():
        return _export_dosimetry_npz_impl(cache, cache_lock)

    @app.route("/api/compliance/report", methods=["GET"])
    def compliance_report():
        return _compliance_report_impl(cache, cache_lock)

    @app.route("/api/channel-presets", methods=["GET"])
    def channel_presets():
        return _channel_presets_impl(cache, cache_lock)

    @app.route("/api/lsp-heatmap", methods=["POST"])
    def lsp_heatmap():
        return _lsp_heatmap_impl(cache, cache_lock)

    @app.route("/api/gpu/status")
    def api_gpu_status():
        return _api_gpu_status_impl(cache, cache_lock)

    @app.route("/api/validate/sinc", methods=["POST"])
    def api_validate_sinc():
        """Compare AEGIS free-space S_inc against CloudRF link budget."""
        return _handle_validate_sinc(cache, cache_lock)
