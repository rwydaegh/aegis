"""OpenAPI 3.0.3 specification for the AEGIS viewer HTTP API.

Scope: the five route groups covered by Wave 3F integration tests
(``/api/compute``, ``/api/compute/rt``, ``/api/optimize``, ``/api/analysis`` /
``/api/compliance``, and the non-external ``/api/environment`` endpoints).
External endpoints that require network (OSM, 3D Tiles, GeoJSON upload) are
deliberately omitted - they belong to a separate follow-up because they depend
on third-party availability.

The spec is exposed at ``/api/openapi.json`` so Schemathesis can consume it
directly. Request bodies use ``additionalProperties: true`` where the route
accepts many optional tuning parameters; the documented properties are the
ones the fuzzer should drive.

Response representations:
- ``/api/compute`` returns ``application/octet-stream`` with a JSON document
  inside an ``X-Stats`` HTTP header. That cannot be expressed faithfully in
  vanilla OpenAPI 3.0, so we document the header schema and mark the body as
  ``binary`` - Schemathesis then validates the status + content-type, not the
  inner statistics JSON.
- ``/api/optimize`` streams ``text/event-stream`` SSE events. OpenAPI has no
  native SSE support; we represent the response as a text/event-stream body
  and describe the event envelope shape in the response description.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Reusable component schemas
# ---------------------------------------------------------------------------

_SCHEMAS: dict[str, Any] = {
    "Vec3": {
        "type": "array",
        "items": {"type": "number", "format": "double"},
        "minItems": 3,
        "maxItems": 3,
        "description": "3-component vector [x, y, z] in engine (Z-up) coordinates.",
    },
    "Error": {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "ComputeRequest": {
        "type": "object",
        "description": (
            "Dosimetry request. Either ``mode`` (``bound``/``aggregate``/``spatial``) "
            "or legacy ``level`` (0-8) must be supplied or defaulted."
        ),
        "properties": {
            "level": {"type": "integer", "minimum": 0, "maximum": 8},
            "mode": {"type": "string", "enum": ["bound", "aggregate", "spatial"]},
            "fresnel": {"type": "boolean"},
            "polarisation": {"type": "boolean"},
            "curvature": {"type": "boolean"},
            "diffraction": {"type": "boolean"},
            "power_dbm": {"type": "number"},
            "freq_hz": {"type": "number", "minimum": 0},
            "antenna_pos": {"$ref": "#/components/schemas/Vec3"},
            "body_offset": {"$ref": "#/components/schemas/Vec3"},
            "body_rotation_y": {"type": "number"},
            "body_name": {"type": "string"},
            "stochastic": {"type": "boolean"},
            "stochastic_preset": {"type": "string"},
            "stochastic_seed": {"type": "integer"},
            "antennas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "position": {"$ref": "#/components/schemas/Vec3"},
                        "power_dbm": {"type": "number"},
                        "array_config": {"type": "object", "additionalProperties": True},
                    },
                    "additionalProperties": True,
                },
            },
        },
        "additionalProperties": True,
    },
    "RTConfig": {
        "type": "object",
        "properties": {
            "max_depth": {"type": "integer", "minimum": 0, "maximum": 10},
            "method": {"type": "string", "enum": ["exhaustive", "sbr"]},
            "rays_per_source": {"type": "integer", "minimum": 1},
            "chunk_size": {"type": "integer", "minimum": 1},
            "reflection_loss_per_order": {"type": "number"},
        },
        "additionalProperties": True,
    },
    "ComputeRTRequest": {
        "type": "object",
        "description": "Ray-traced dosimetry. Extends ComputeRequest with ray tracer configuration.",
        "properties": {
            "antenna_pos": {"$ref": "#/components/schemas/Vec3"},
            "power_dbm": {"type": "number"},
            "freq_hz": {"type": "number", "minimum": 0},
            "level": {"type": "integer", "minimum": 0, "maximum": 8},
            "mode": {"type": "string", "enum": ["bound", "aggregate", "spatial"]},
            "body_name": {"type": "string"},
            "rt_config": {"$ref": "#/components/schemas/RTConfig"},
            "scene_path": {"type": "string"},
            "use_modal": {"type": "boolean"},
            "session_id": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "OptimizeRequest": {
        "type": "object",
        "required": ["mode"],
        "properties": {
            "mode": {"type": "string", "enum": ["mimo_peak", "tilt_power", "placement"]},
            "freq_hz": {"type": "number", "minimum": 0},
            "power_dbm": {"type": "number"},
            "antenna_pos": {"$ref": "#/components/schemas/Vec3"},
            "body_name": {"type": "string"},
            "max_iter": {"type": "integer", "minimum": 1, "maximum": 10000},
            "session_id": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "ComplianceLimitsResponse": {
        "type": "object",
        "properties": {
            "limits": {"type": "object", "additionalProperties": True},
        },
        "additionalProperties": True,
    },
    "ComplianceSummaryResponse": {
        "type": "object",
        "additionalProperties": True,
    },
    "ComplianceSpatialRequest": {
        "type": "object",
        "description": "Spatially averaged compliance check.",
        "properties": {
            "antenna_pos": {"$ref": "#/components/schemas/Vec3"},
            "power_dbm": {"type": "number"},
            "freq_hz": {"type": "number", "minimum": 0},
            "body_name": {"type": "string"},
            "averaging_area_cm2": {"type": "number", "minimum": 0},
        },
        "additionalProperties": True,
    },
    "TissueSpectrumResponse": {
        "type": "object",
        "properties": {
            "freq_hz": {"type": "array", "items": {"type": "number"}},
            "eps_r": {"type": "array", "items": {"type": "number"}},
            "sigma": {"type": "array", "items": {"type": "number"}},
        },
        "additionalProperties": True,
    },
    "EnvironmentMaterialsResponse": {
        "type": "object",
        "required": ["materials"],
        "properties": {
            "materials": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "eps_r": {"type": "number", "nullable": True},
                        "sigma": {"type": "number", "nullable": True},
                    },
                },
            },
        },
    },
    "EnvironmentFromVoxelsRequest": {
        "type": "object",
        "description": "Build an EnvironmentMesh from the cached voxel grid.",
        "properties": {
            "lat": {"type": "number"},
            "lon": {"type": "number"},
            "session_id": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "EnvironmentCombineRequest": {
        "type": "object",
        "description": "Combine per-source cached meshes into one.",
        "properties": {
            "sources": {
                "type": "array",
                "items": {"type": "string"},
            },
            "session_id": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "EnvironmentExportSceneRequest": {
        "type": "object",
        "properties": {
            "format": {"type": "string", "enum": ["differt", "sionna"]},
            "session_id": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "AnalysisSweepParams": {
        "type": "object",
        "description": "Query parameters for compliance sweeps. Accepted as query string on GET routes.",
        "properties": {
            "freq_hz": {"type": "number"},
            "level": {"type": "integer", "minimum": 0, "maximum": 8},
            "body_name": {"type": "string"},
            "n_points": {"type": "integer", "minimum": 2, "maximum": 500},
        },
        "additionalProperties": True,
    },
}


# Standard error responses
_COMMON_ERROR_RESPONSES = {
    "400": {
        "description": "Malformed request.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "404": {
        "description": "Missing required resource (e.g. cached body, env mesh).",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
    "500": {
        "description": "Unhandled server error.",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
    },
}


def _octet_stats_response(description: str) -> dict[str, Any]:
    """Response spec for routes returning raw binary with a JSON ``X-Stats`` header."""
    return {
        "description": description,
        "headers": {
            "X-Stats": {
                "description": "JSON document with per-triangle summary stats.",
                "schema": {"type": "string"},
            },
        },
        "content": {
            "application/octet-stream": {
                "schema": {"type": "string", "format": "binary"},
            },
        },
    }


def _octet_meta_response(description: str) -> dict[str, Any]:
    """Response spec for environment mesh routes returning binary + JSON ``X-Meta``."""
    return {
        "description": description,
        "headers": {
            "X-Meta": {
                "description": "JSON document describing the returned mesh (n_triangles, bbox, ...).",
                "schema": {"type": "string"},
            },
        },
        "content": {
            "application/octet-stream": {
                "schema": {"type": "string", "format": "binary"},
            },
        },
    }


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


_PATHS: dict[str, Any] = {
    # ------------------------------------------------------------------
    # /api/compute and /api/compute/rt
    # ------------------------------------------------------------------
    "/api/compute": {
        "post": {
            "operationId": "compute_dosimetry",
            "summary": "Run dosimetry on the cached body mesh.",
            "description": (
                "Returns ``application/octet-stream`` containing float32 Sab values "
                "concatenated per triangle, with a JSON document in the ``X-Stats`` header."
            ),
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ComputeRequest"},
                    },
                    "application/octet-stream": {
                        "schema": {"type": "string", "format": "binary"},
                        "description": "Inline mesh upload (rare path).",
                    },
                },
            },
            "responses": {
                "200": _octet_stats_response("Dosimetry succeeded."),
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/compute/rt": {
        "post": {
            "operationId": "compute_rt",
            "summary": "Run ray-traced dosimetry.",
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ComputeRTRequest"},
                    },
                },
            },
            "responses": {
                "200": _octet_stats_response("Ray-traced dosimetry succeeded."),
                "502": {
                    "description": "Upstream ray tracer (Modal / local GPU) unavailable.",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}},
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    # ------------------------------------------------------------------
    # /api/optimize (SSE)
    # ------------------------------------------------------------------
    "/api/optimize": {
        "post": {
            "operationId": "optimize",
            "summary": "Start an optimization run (server-sent events).",
            "description": (
                "Streams `text/event-stream` frames of the form ``data: {json}\\n\\n``. "
                "Each JSON payload is either ``{iteration, value, sab_b64, ...}`` or "
                "``{error: true, message: ...}`` on failure. OpenAPI cannot express SSE "
                "natively; the response body schema here is the raw stream."
            ),
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/OptimizeRequest"},
                    },
                },
            },
            "responses": {
                "200": {
                    "description": "Stream started.",
                    "content": {
                        "text/event-stream": {
                            # Each ``data:`` frame is a JSON object — either an
                            # iteration payload or ``{error: true, message}``.
                            # Schemathesis parses the frames and validates
                            # against this schema; ``string`` would be wrong.
                            "schema": {"type": "object", "additionalProperties": True},
                        },
                    },
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/optimize/cancel": {
        "post": {
            "operationId": "optimize_cancel",
            "summary": "Cancel the running optimization for the current session.",
            "responses": {
                "200": {
                    "description": "Cancellation flag state.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["cancelled"],
                                "properties": {"cancelled": {"type": "boolean"}},
                            },
                        },
                    },
                },
            },
        },
    },
    # ------------------------------------------------------------------
    # /api/compliance and /api/tissue (analysis group)
    # ------------------------------------------------------------------
    "/api/compliance/limits": {
        "get": {
            "operationId": "compliance_limits",
            "summary": "ICNIRP 2020 limits for the current tissue / frequency.",
            "responses": {
                "200": {
                    "description": "Limit values.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ComplianceLimitsResponse"},
                        },
                    },
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/compliance/summary": {
        "get": {
            "operationId": "compliance_summary",
            "summary": "Whole-body compliance summary at the current operating point.",
            "responses": {
                "200": {
                    "description": "Summary.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ComplianceSummaryResponse"},
                        },
                    },
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/compliance/power-sweep": {
        "get": {
            "operationId": "compliance_power_sweep",
            "summary": "Compliance margin vs transmit power.",
            "responses": {
                "200": {
                    "description": "Sweep results.",
                    "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/compliance/frequency-sweep": {
        "get": {
            "operationId": "compliance_frequency_sweep",
            "summary": "Compliance margin vs frequency.",
            "responses": {
                "200": {
                    "description": "Sweep results.",
                    "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/compliance/heatmap": {
        "get": {
            "operationId": "compliance_heatmap",
            "summary": ("2D compliance heatmap. Infinite margins are intentionally serialized as null."),
            "responses": {
                "200": {
                    "description": "Heatmap grid.",
                    "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/compliance/spatial": {
        "post": {
            "operationId": "compliance_spatial",
            "summary": "Spatially averaged compliance check.",
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ComplianceSpatialRequest"},
                    },
                },
            },
            "responses": {
                "200": {
                    "description": "Spatial compliance result.",
                    "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}},
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    "/api/tissue/spectrum": {
        "get": {
            "operationId": "tissue_spectrum",
            "summary": "Tissue EM spectrum for the currently selected tissue.",
            "responses": {
                "200": {
                    "description": "Spectrum values.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TissueSpectrumResponse"},
                        },
                    },
                },
                **_COMMON_ERROR_RESPONSES,
            },
        },
    },
    # ------------------------------------------------------------------
    # /api/environment (non-external subset)
    # ------------------------------------------------------------------
    "/api/environment/materials": {
        "get": {
            "operationId": "environment_materials",
            "summary": "Material catalog (EM properties per building material).",
            "responses": {
                "200": {
                    "description": "Materials.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/EnvironmentMaterialsResponse"},
                        },
                    },
                },
            },
        },
    },
    "/api/environment/mesh": {
        "get": {
            "operationId": "environment_mesh_get",
            "summary": "Return the most recently cached environment mesh (any source).",
            "responses": {
                "200": _octet_meta_response("Cached environment mesh."),
                "404": _COMMON_ERROR_RESPONSES["404"],
            },
        },
    },
    "/api/environment/from-voxels": {
        "post": {
            "operationId": "environment_from_voxels",
            "summary": "Build an EnvironmentMesh from the cached voxel grid.",
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/EnvironmentFromVoxelsRequest"},
                    },
                },
            },
            "responses": {
                "200": _octet_meta_response("Environment mesh built and cached."),
                "404": _COMMON_ERROR_RESPONSES["404"],
                "400": _COMMON_ERROR_RESPONSES["400"],
                "500": _COMMON_ERROR_RESPONSES["500"],
            },
        },
    },
    "/api/environment/combine": {
        "post": {
            "operationId": "environment_combine",
            "summary": "Combine cached per-source environment meshes into one.",
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/EnvironmentCombineRequest"},
                    },
                },
            },
            "responses": {
                "200": _octet_meta_response("Combined environment mesh."),
                "404": _COMMON_ERROR_RESPONSES["404"],
                "400": _COMMON_ERROR_RESPONSES["400"],
                "500": _COMMON_ERROR_RESPONSES["500"],
            },
        },
    },
    "/api/environment/export-scene": {
        "post": {
            "operationId": "environment_export_scene",
            "summary": "Export the cached environment mesh to DiffeRT or Sionna scene format.",
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/EnvironmentExportSceneRequest"},
                    },
                },
            },
            "responses": {
                "200": {
                    "description": "Exported scene files (zip or json).",
                    "content": {
                        "application/octet-stream": {"schema": {"type": "string", "format": "binary"}},
                        "application/json": {"schema": {"type": "object", "additionalProperties": True}},
                    },
                },
                "404": _COMMON_ERROR_RESPONSES["404"],
                "400": _COMMON_ERROR_RESPONSES["400"],
                "500": _COMMON_ERROR_RESPONSES["500"],
            },
        },
    },
    "/api/cache/environments": {
        "delete": {
            "operationId": "clear_environment_cache",
            "summary": "Clear the file-based environment cache.",
            "responses": {
                "200": {
                    "description": "Cache cleared.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["ok"],
                                "properties": {"ok": {"type": "boolean"}},
                            },
                        },
                    },
                },
            },
        },
    },
}


def build_openapi_spec() -> dict[str, Any]:
    """Assemble the full OpenAPI 3.0.3 document for the viewer API."""
    try:
        from aegis._version import __version__ as aegis_version
    except Exception:  # pragma: no cover - version import is trivial
        aegis_version = "0.0.0"

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "AEGIS viewer API",
            "version": aegis_version,
            "description": (
                "HTTP surface of the AEGIS viewer Flask app. Covers dosimetry, ray tracing, "
                "optimization, compliance analysis, and non-external environment routes."
            ),
        },
        "servers": [{"url": "http://localhost:5000", "description": "Local dev server."}],
        "paths": _PATHS,
        "components": {"schemas": _SCHEMAS},
    }
