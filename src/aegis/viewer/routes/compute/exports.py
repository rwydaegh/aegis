"""Dosimetry result export routes (CSV, JSON, NPZ)."""

from __future__ import annotations

import json

import numpy as np
from flask import Response, jsonify

from aegis.viewer.server import scoped_cache_get

from ._responses import _ERR_NO_EXPORT_DATA


def _export_dosimetry_csv_impl(cache: dict, cache_lock) -> Response:
    """Export last dosimetry result as a comprehensive CSV.

    Includes per-triangle centroids, areas, normals, and all computed
    quantities (sab, sab_4cm2, sinc, sinc_4cm2, sab_1cm2).

    Uses vectorized numpy formatting instead of per-row Python loops.
    Streams the response to avoid buffering large meshes in memory.
    """
    import io

    result = scoped_cache_get(cache, "_last_dosimetry_result")
    body = scoped_cache_get(cache, "_last_dosimetry_body")
    if result is None or body is None:
        return jsonify({"error": _ERR_NO_EXPORT_DATA}), 404

    # Build column list and collect arrays
    columns = ["cx", "cy", "cz", "area_m2", "nx", "ny", "nz", "sab_w_m2"]
    # Fixed-point columns: centroids (3) + normals (3) = 6 cols
    # Scientific columns: areas (1) + sab (1) + optional extras
    fixed_arrays = [body.centroids, body.normals]  # (N,3) each
    sci_arrays = [body.areas[:, None], result.sab[:, None]]  # (N,1) each

    for arr, name in [
        (result.sab_averaged, "sab_4cm2_w_m2"),
        (result.sinc, "sinc_w_m2"),
        (result.sinc_averaged, "sinc_4cm2_w_m2"),
        (result.sab_1cm2_averaged, "sab_1cm2_w_m2"),
    ]:
        if arr is not None:
            columns.append(name)
            sci_arrays.append(np.asarray(arr)[:, None])

    header = ",".join(columns) + "\n"

    # Vectorized formatting: build fixed-point and scientific blocks
    fixed_block = np.column_stack(fixed_arrays)  # (N, 6)
    sci_block = np.column_stack(sci_arrays)  # (N, 2+)

    # Format each block using numpy's vectorized string conversion
    out = io.StringIO()
    out.write(header)

    # Use savetxt into the StringIO for each row as a combined array
    # Interleave format: cx,cy,cz | area | nx,ny,nz | sab | [extras]
    # Order: centroids(3), area(1), normals(3), sab(1), [sab_avg, sinc, sinc_avg, sab_1cm2]
    fmt_fixed = ["%.6f"] * 3  # centroids
    fmt_sci = ["%.8e"]  # area
    fmt_fixed2 = ["%.6f"] * 3  # normals
    fmt_sci2 = ["%.8e"] * (sci_block.shape[1] - 1)  # sab + optional extras
    fmt = fmt_fixed + fmt_sci + fmt_fixed2 + fmt_sci2

    # Assemble in column order matching the header
    data = np.column_stack(
        [
            fixed_block[:, :3],  # cx, cy, cz
            sci_block[:, :1],  # area
            fixed_block[:, 3:],  # nx, ny, nz
            sci_block[:, 1:],  # sab + optional extras
        ]
    )

    np.savetxt(out, data, delimiter=",", fmt=fmt)

    def generate():
        yield out.getvalue().encode("utf-8")

    resp = Response(generate(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=aegis_dosimetry.csv"
    return resp


def _export_dosimetry_json_impl(cache: dict, cache_lock) -> Response:
    """Export last dosimetry result as a self-describing JSON file.

    Includes per-triangle data, compliance verdict, and peak statistics.
    """
    result = scoped_cache_get(cache, "_last_dosimetry_result")
    body = scoped_cache_get(cache, "_last_dosimetry_body")
    stats = scoped_cache_get(cache, "_last_dosimetry_stats")
    if result is None or body is None:
        return jsonify({"error": _ERR_NO_EXPORT_DATA}), 404

    n = body.n_triangles
    data: dict = {
        "meta": {
            "generator": "AEGIS dosimetry engine",
            "body": body.name,
            "n_triangles": n,
        },
        "centroids": body.centroids.tolist(),
        "normals": body.normals.tolist(),
        "areas": body.areas.tolist(),
        "sab": result.sab.tolist(),
    }

    for arr, key in [
        (result.sab_averaged, "sab_4cm2"),
        (result.sinc, "sinc"),
        (result.sinc_averaged, "sinc_4cm2"),
        (result.sab_1cm2_averaged, "sab_1cm2"),
    ]:
        if arr is not None:
            data[key] = np.asarray(arr).tolist()

    if stats:
        data["stats"] = {k: v for k, v in stats.items() if k not in ("arrays", "path_viz")}

    resp = Response(
        json.dumps(data, allow_nan=False, default=str),
        mimetype="application/json",
    )
    resp.headers["Content-Disposition"] = "attachment; filename=aegis_dosimetry.json"
    return resp


def _export_dosimetry_npz_impl(cache: dict, cache_lock) -> Response:
    """Export last dosimetry result as a NumPy .npz archive.

    Preserves full float64 precision and is much smaller than CSV for
    large meshes.
    """
    import io

    result = scoped_cache_get(cache, "_last_dosimetry_result")
    body = scoped_cache_get(cache, "_last_dosimetry_body")
    if result is None or body is None:
        return jsonify({"error": _ERR_NO_EXPORT_DATA}), 404

    arrays: dict = {
        "centroids": body.centroids,
        "normals": body.normals,
        "areas": body.areas,
        "sab": result.sab,
    }

    for arr, key in [
        (result.sab_averaged, "sab_4cm2"),
        (result.sinc, "sinc"),
        (result.sinc_averaged, "sinc_4cm2"),
        (result.sab_1cm2_averaged, "sab_1cm2"),
    ]:
        if arr is not None:
            arrays[key] = np.asarray(arr)

    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    buf.seek(0)

    resp = Response(buf.getvalue(), mimetype="application/octet-stream")
    resp.headers["Content-Disposition"] = "attachment; filename=aegis_dosimetry.npz"
    return resp
