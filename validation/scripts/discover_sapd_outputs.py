"""Discover the actual output ports exposed by Sim4Life's GenericSAPDEvaluator
and SurfaceFieldFluxEvaluator at runtime, plus dump a per-triangle SAPD field
to a .npz that AEGIS-side `surface_apd_compare.py` can consume.

This is a *Sim4Life-side* script — must be run inside the S4L Python interp
where `s4l_v1` is importable. Paste it into goliat's SAPD extraction pipeline
or run it manually after a project is loaded with results available.

Usage A (goliat-integrated, after `sapd_evaluator.Update()` in
`goliat/extraction/sapd_extractor.py`):

    from aegis_validation.discover_sapd_outputs import (
        dump_outputs_report, dump_per_triangle_apd
    )
    dump_outputs_report(sapd_evaluator, results_dir / "sapd_outputs.txt")
    dump_per_triangle_apd(sapd_evaluator, results_dir / "skin_apd.npz",
                          renorm=753.46)

Usage B (manual, attached to an open S4L document):

    python  -m discover_sapd_outputs <project.smash> <output_dir>

What it produces:
  sapd_outputs.txt   — human-readable enumeration of ports
                       (name, type, NumberOfComponents, NumberOfTuples,
                       Grid summary). Use this once to learn the right port
                       name; commit it to the repo for posterity.
  skin_apd.npz       — vertices (V,3), triangles (T,3), apd_w_m2 (T,) or (V,),
                       and metadata. Sufficient for AEGIS comparison without
                       any further S4L access.
"""

from __future__ import annotations
import sys
from pathlib import Path


def dump_outputs_report(algorithm, out_path: str) -> dict:
    """Enumerate every output port on `algorithm`, return a dict suitable for
    `json.dump`, and also write a human-readable txt to `out_path`. Safe to
    call regardless of whether the algorithm has been Updated."""
    rep = []
    try:
        ports = list(algorithm.Outputs)
    except Exception as e:
        msg = f"<could not iterate Outputs: {e}>"
        Path(out_path).write_text(msg)
        return {"error": str(e)}

    lines = [f"Algorithm: {type(algorithm).__name__}"]
    if hasattr(algorithm, "Name"):
        lines.append(f"  Name: {algorithm.Name}")
    lines.append(f"  Outputs: {len(ports)}")
    for i, port in enumerate(ports):
        try:
            port.Update()
        except Exception:
            pass
        try:
            data = port.Data
            tname = type(data).__name__
        except Exception as e:
            data, tname = None, f"<no Data: {e}>"
        info = {"index": i, "name": getattr(port, "Name", "?"), "type": tname}
        for attr in ("NumberOfComponents", "NumberOfTuples", "NumberOfSnapshots", "IsComplex"):
            try:
                info[attr] = getattr(data, attr, None)
            except Exception:
                info[attr] = None
        try:
            grid = getattr(data, "Grid", None)
            if grid is not None:
                # Try common grid attributes
                gattrs = {}
                for ga in ("Dimensions", "NumberOfPoints", "NumberOfCells", "Bounds"):
                    try:
                        gattrs[ga] = getattr(grid, ga, None)
                    except Exception:
                        pass
                info["Grid"] = gattrs
        except Exception as e:
            info["Grid"] = f"<err: {e}>"
        rep.append(info)
        lines.append(
            f"  [{i}] name={info['name']!r:40s} type={info['type']:30s} "
            f"comps={info.get('NumberOfComponents')} "
            f"tuples={info.get('NumberOfTuples')} "
            f"snaps={info.get('NumberOfSnapshots')}"
        )
    Path(out_path).write_text("\n".join(lines))
    return {"algorithm": type(algorithm).__name__, "ports": rep}


APD_PORT_NAME = "APD(x,y,z,f0)"


def _vtk_grid_to_arrays(vtk_grid):
    """Pull (vertices, faces) from a vtkUnstructuredGrid via vtk_to_numpy.

    Sim4Life ships VTK; this is ~100x faster than iterating GetPoint /
    GetCellPoints in pure Python on a 16k-vertex sphere. Handles both
    legacy (one flat connectivity array prefixed with cell-size counts) and
    modern (separate connectivity + offsets arrays, VTK 9+) cell layouts.
    Asserts the mesh is pure triangles, since that is what
    GenericSAPDEvaluator and ModelToGridFilter produce on a body surface.
    """
    import numpy as np
    from vtk.util import numpy_support as vns

    n_pts = vtk_grid.GetNumberOfPoints()
    n_cells = vtk_grid.GetNumberOfCells()
    verts = vns.vtk_to_numpy(vtk_grid.GetPoints().GetData()).reshape(n_pts, 3)

    cell_array = vtk_grid.GetCells()
    try:
        # VTK 9+ modern API: connectivity + offsets
        conn = vns.vtk_to_numpy(cell_array.GetConnectivityArray())
        offs = vns.vtk_to_numpy(cell_array.GetOffsetsArray())
        sizes = np.diff(offs)
        if not (sizes == 3).all():
            raise ValueError(f"non-triangle cells: sizes={np.unique(sizes).tolist()}")
        faces = conn.reshape(n_cells, 3)
    except (AttributeError, NotImplementedError):
        # Legacy flat layout: [3, i, j, k, 3, i, j, k, ...]
        flat = vns.vtk_to_numpy(cell_array.GetData())
        if flat.size != 4 * n_cells:
            raise ValueError(
                f"flat connectivity size {flat.size} != 4 * n_cells {n_cells} -> mesh is not pure triangles"
            )
        rs = flat.reshape(n_cells, 4)
        if not (rs[:, 0] == 3).all():
            raise ValueError("legacy flat array has non-3 cell sizes")
        faces = rs[:, 1:]
    return verts.astype(np.float64), faces.astype(np.int32)


def find_field_port(algorithm) -> tuple:
    """Find an APD/SAPD field port on `algorithm`.

    Preference order:
      1. The exact name `APD(x,y,z,f0)` (set by SetAPD=True on
         GenericSAPDEvaluator; this is what we want for production).
      2. Any port whose Data has a `.Field()` method, preferring scalar
         (1-component) over vector fields and most tuples first. Used as a
         fallback when the evaluator is a SurfaceFieldFluxEvaluator or a
         differently-named port.
    """
    # 1. Direct port-name lookup — cheap and decisive when SetAPD=True
    try:
        port = algorithm.Outputs[APD_PORT_NAME]
        port.Update()
        if hasattr(port.Data, "Field"):
            return port, port.Data
    except Exception:
        pass

    # 2. Generic search
    candidates = []
    for port in algorithm.Outputs:
        try:
            port.Update()
            data = port.Data
        except Exception:
            continue
        if not hasattr(data, "Field"):
            continue
        n_comp = getattr(data, "NumberOfComponents", None) or 0
        n_tup = getattr(data, "NumberOfTuples", None) or 0
        candidates.append((n_comp, n_tup, port))
    if not candidates:
        return None, None
    candidates.sort(key=lambda t: (abs(t[0] - 1), -t[1]))
    _, _, port = candidates[0]
    return port, port.Data


def dump_per_triangle_apd(algorithm, out_path: str, *, renorm: float = 753.46, quantity_label: str = "SAPD"):
    """Pull the per-vertex APD field from `algorithm` and write a portable
    .npz that AEGIS-side `h5_surface_apd.load_skin_apd_npz()` consumes.

    Side effect: if `algorithm` is a GenericSAPDEvaluator and `SetAPD` is
    not already True, this enables it and re-runs `UpdateAttributes()`.
    The caller's `Spatial-Averaged Power Density Report` port stays valid.

    Output schema (kNode per-vertex APD, validated on a sphere test case):
      vertices_m   : (V, 3) float64 — surface mesh nodes, metres
      faces        : (T, 3) int32   — triangle vertex indices
      apd_w_m2     : (V,)   float32 — APD at each node, scaled by `renorm`
      port_name    : str             "APD(x,y,z,f0)"
      value_location: str            "kNode"
      renorm       : float           multiplier applied to apd_w_m2
      algorithm    : str             type(algorithm).__name__
    """
    import numpy as np

    # 1. Toggle the SAPD-field output if the evaluator supports it
    if hasattr(algorithm, "SetAPD") and not getattr(algorithm, "SetAPD", False):
        algorithm.SetAPD = True
        if hasattr(algorithm, "UpdateAttributes"):
            algorithm.UpdateAttributes()

    port, data = find_field_port(algorithm)
    if port is None:
        raise RuntimeError(
            f"No FieldData output found on {type(algorithm).__name__}; run dump_outputs_report() to enumerate ports."
        )

    field = np.asarray(data.Field(0))
    apd = field if field.ndim == 1 else np.linalg.norm(field, axis=-1)
    apd = apd.astype(np.float32, copy=False)

    # 2. Pull mesh via VTK → numpy
    grid = data.Grid
    if grid is None or not hasattr(grid, "GetVtkUnstructuredGrid"):
        raise RuntimeError(
            f"port.Data.Grid lacks GetVtkUnstructuredGrid(); type={type(grid).__name__ if grid else 'None'}"
        )
    verts, faces = _vtk_grid_to_arrays(grid.GetVtkUnstructuredGrid())

    # 3. Sanity check: APD length matches vertex count for kNode fields
    value_location = str(getattr(data, "ValueLocation", "?"))
    if apd.size != len(verts) and apd.size != len(faces):
        raise RuntimeError(
            f"APD has {apd.size} entries but mesh has V={len(verts)}, T={len(faces)}; ValueLocation={value_location!r}"
        )

    np.savez(
        out_path,
        apd_w_m2=apd * renorm,
        vertices_m=verts,
        faces=faces,
        port_name=getattr(port, "Name", APD_PORT_NAME),
        value_location=value_location,
        algorithm=type(algorithm).__name__,
        quantity=quantity_label,
        renorm=renorm,
        n_vertices=len(verts),
        n_faces=len(faces),
    )
    return out_path


# ---------------------------------------------------------------------------
# Stand-alone main: open a project, run all SAPD evaluators it contains,
# dump everything. Useful for retroactive analysis of saved projects.
# ---------------------------------------------------------------------------


def main(project_path: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    import s4l_v1.document as document

    document.Open(project_path)

    found = 0
    for algo in document.AllAlgorithms:
        cls = type(algo).__name__
        if "SAPD" in cls or "SurfaceFieldFlux" in cls:
            stem = algo.Name.replace(" ", "_") if hasattr(algo, "Name") else cls
            dump_outputs_report(algo, out / f"{stem}_outputs.txt")
            try:
                dump_per_triangle_apd(algo, out / f"{stem}_skin_apd.npz")
                found += 1
            except Exception as e:
                (out / f"{stem}_dump_err.txt").write_text(str(e))
    print(f"Wrote {found} per-triangle dumps to {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m discover_sapd_outputs <project.smash> <out_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
