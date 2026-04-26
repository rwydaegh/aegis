"""Minimal Sim4Life-side probe to confirm the APD-field data-out path.

Append this BELOW Robin's working "To Python" pipeline (after the
SurfaceViewer block; the SurfaceViewer isn't needed but its presence
forces the evaluator to Update). Drops a sphere_apd_probe.npz and prints
a one-screen summary of what worked.

The two unknowns it resolves:
  1. What is `port.Data` (which `FieldData` subclass) and what's its
     shape / dtype / component count.
  2. How to pull vertex coordinates and triangle connectivity from
     `port.Data.Grid` — the public surface grid attribute names aren't
     in the static rst.

Once this runs, `discover_sapd_outputs.py:dump_per_triangle_apd()` and
`h5_surface_apd.py:load_skin_apd_npz()` are wired for production use.
"""

from pathlib import Path
import numpy as np


def probe(generic_sapd_evaluator, out_dir: str = "/tmp"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log = []

    def say(s):
        print(s)
        log.append(s)

    # ---- 1.  Get the FieldData ------------------------------------------------
    port = generic_sapd_evaluator.Outputs["APD(x,y,z,f0)"]
    port.Update()
    data = port.Data
    say(f"port.Data type:           {type(data).__name__}")
    say(f"  module:                 {type(data).__module__}")
    for attr in (
        "NumberOfComponents",
        "NumberOfTuples",
        "NumberOfSnapshots",
        "IsComplex",
        "Quantity",
        "ValueLocation",
        "RmsFactor",
    ):
        try:
            v = getattr(data, attr, "<missing>")
        except Exception as e:
            v = f"<getattr err: {type(e).__name__}>"
        say(f"  {attr:24s}{v}")

    try:
        field = np.asarray(data.Field(0))
        say(f"data.Field(0).shape:      {field.shape}")
        say(f"data.Field(0).dtype:      {field.dtype}")
        say(f"data.Field(0) min/max:    {float(field.min()):.4e} / {float(field.max()):.4e}")
        say(f"data.Field(0) any NaN:    {bool(np.isnan(field).any())}")
    except Exception as e:
        say(f"data.Field(0) FAILED:     {type(e).__name__}: {e}")
        field = np.array([])

    # If complex, take real and abs for the saved scalar
    if np.iscomplexobj(field):
        scalar = field.real if field.ndim == 1 else np.abs(field).max(axis=-1)
    else:
        scalar = field if field.ndim == 1 else np.linalg.norm(field, axis=-1)

    # ---- 2.  Probe the Grid ---------------------------------------------------
    grid = data.Grid
    say(f"\ngrid type:                {type(grid).__name__}")
    grid_dir = [a for a in dir(grid) if not a.startswith("_")]
    say(f"grid public attrs (first 40): {grid_dir[:40]}")

    candidates = {}
    for attr in (
        "Points",
        "GetPoints",
        "Vertices",
        "GetVertices",
        "Cells",
        "GetCells",
        "Triangles",
        "GetTriangles",
        "Connectivity",
        "GetConnectivity",
        "NumberOfPoints",
        "NumberOfCells",
        "Bounds",
        "Dimensions",
    ):
        v = getattr(grid, attr, None)
        if v is None:
            continue
        try:
            v_eval = v() if callable(v) else v
            candidates[attr] = v_eval
            shape = getattr(v_eval, "shape", None)
            kind = type(v_eval).__name__
            say(f"  {attr:24s}{kind:30s} shape={shape}")
        except Exception as e:
            say(f"  {attr:24s}<call err: {e}>")

    # Try to construct (verts, faces) with a few common interpretations
    verts = None
    for k in ("Points", "GetPoints", "Vertices", "GetVertices"):
        if k in candidates:
            arr = np.asarray(candidates[k])
            if arr.ndim == 2 and arr.shape[1] == 3:
                verts = arr
                say(f"\nverts := {k}, shape {arr.shape}")
                break

    faces = None
    for k in ("Cells", "GetCells", "Triangles", "GetTriangles", "Connectivity", "GetConnectivity"):
        if k in candidates:
            arr = np.asarray(candidates[k])
            if arr.ndim == 2 and arr.shape[1] in (3, 4):
                faces = arr if arr.shape[1] == 3 else arr[:, 1:]
                say(f"faces := {k}, shape {faces.shape}")
                break
            if arr.ndim == 1 and arr.size % 4 == 0:
                rs = arr.reshape(-1, 4)
                if (rs[:, 0] == 3).all():
                    faces = rs[:, 1:]
                    say(f"faces := {k} (VTK-flat decoded), shape {faces.shape}")
                    break

    # ---- 3.  Save what we got -------------------------------------------------
    npz_path = out / "sphere_apd_probe.npz"
    np.savez(
        npz_path,
        apd_native=field,
        apd_scalar=scalar,
        vertices_m=verts if verts is not None else np.array([]),
        faces=faces if faces is not None else np.array([]),
        port_name="APD(x,y,z,f0)",
        algorithm=type(generic_sapd_evaluator).__name__,
        n_components=getattr(data, "NumberOfComponents", -1),
        n_tuples=getattr(data, "NumberOfTuples", -1),
        is_complex=bool(getattr(data, "IsComplex", False)),
    )
    say(f"\nwrote: {npz_path}  ({npz_path.stat().st_size / 1024:.1f} KB)")

    log_path = out / "sphere_apd_probe.log"
    log_path.write_text("\n".join(log))
    say(f"wrote: {log_path}")

    return {
        "field_shape": field.shape,
        "field_dtype": str(field.dtype),
        "n_tuples": getattr(data, "NumberOfTuples", -1),
        "verts_shape": None if verts is None else verts.shape,
        "faces_shape": None if faces is None else faces.shape,
    }


if __name__ == "__main__":
    # When pasted at the bottom of Robin's GUI-exported pipeline:
    #     ... (his existing setup, ending with surface_viewer.UpdateAttributes())
    #     from probe_apd_field import probe
    #     probe(generic_sapd_evaluator, out_dir="/tmp")
    pass
