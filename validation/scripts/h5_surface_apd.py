"""Extract per-triangle surface absorbed power density from a Sim4Life
`_Output.h5` overall-field dump and a triangulated skin mesh.

This is the linchpin of Tier 1+ NRMSE / 3D-error comparisons. Goliat's stock
`GenericSAPDEvaluator` only reports the peak SAPD value; the user's
preference is integrated NRMSE on the full surface plus a 3D plot of where
the errors live, both of which need a per-triangle field.

Algorithm:
  1. Read complex E(x,y,z,f0) and H(x,y,z,f0) from the h5 file.
  2. Compute time-averaged Poynting vector  S = ½ Re(E × H*)  [W/m²].
  3. Place the field on a single non-staggered grid (Yee → cell centre).
  4. For each surface triangle: sample S at the centroid (offset by ε ·
     n̂_outward into the body so we read the in-tissue field, just below the
     skin), and compute the inward power flux density
              s_apd(t) = − S(centroid) · n̂_outward(t).
     Negative inward fluxes (i.e. wave radiating away from this triangle)
     are clipped to zero, matching the AEGIS ReLU(μ) convention. By energy
     conservation, ∫ s_apd dA = DielLoss to within numerical accuracy.

Tested against synthetic plane-wave data (see `_self_test()` below): given
analytical E, H of a plane wave  E = E_0 ê_E exp(i k · r), the recovered
per-triangle s_apd matches  S_inc · ReLU(n̂ · (−k̂))  to the discretisation
limit.

Usage:
    from h5_surface_apd import load_surface_apd
    s_apd = load_surface_apd("path/_Output.h5", body, freq_hz)

The skin mesh `body` is an aegis BodyMesh; its triangle centroids and
normals are sampled directly. The mesh frame must match the FDTD frame
(both are SI metres, same origin).
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import numpy as np


ETA_0 = 376.730313668


def _read_field(h5_path: str, field_type: str = "E") -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read complex E or H field volume from an S4L `_Output.h5`.

    Returns (Fx, Fy, Fz, axes) where each F* is a complex (Nx-1, Ny-1, Nz-1)
    array on the cell-centre grid (Yee staggering averaged out), and
    axes = (axis_x, axis_y, axis_z) are 1D coordinate arrays in metres.

    The implementation mirrors goliat/extraction/field_reader.py for the
    "Overall Field" sensor, then averages the staggered Yee components onto
    a common cell-centre grid.
    """
    import h5py

    with h5py.File(h5_path, "r") as f:
        # Find "Overall Field" group (mimic goliat/extraction/field_reader.py)
        if "FieldGroups" not in f:
            raise ValueError(f"No FieldGroups in {h5_path}")
        fg_path = None
        for fg_key in f["FieldGroups"].keys():
            obj = f.get(f"FieldGroups/{fg_key}/_Object")
            if obj is None:
                continue
            name = obj.attrs.get("name", b"")
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            if name == "Overall Field":
                fg_path = f"FieldGroups/{fg_key}"
                break
        if fg_path is None:
            raise ValueError(f"No 'Overall Field' in {h5_path}")

        snap = f[f"{fg_path}/AllFields/EM {field_type}(x,y,z,f0)/_Object/Snapshots/0"]
        # Yee staggering: Fx is on (Nx-1, Ny, Nz) edges, Fy on (Nx, Ny-1, Nz),
        # Fz on (Nx, Ny, Nz-1). We need to read all three with their native
        # shapes, then interpolate to a common cell-centre grid (Nx-1, Ny-1, Nz-1).
        comp0 = snap["comp0"][:]  # shape ?x?x?x2 (real, imag)
        comp1 = snap["comp1"][:]
        comp2 = snap["comp2"][:]
        Fx = comp0[..., 0] + 1j * comp0[..., 1]
        Fy = comp1[..., 0] + 1j * comp1[..., 1]
        Fz = comp2[..., 0] + 1j * comp2[..., 1]

        # Find an arbitrary mesh in the file to grab the axes
        if "Meshes" in f:
            for mesh_key in f["Meshes"].keys():
                mesh = f[f"Meshes/{mesh_key}"]
                if "axis_x" in mesh:
                    axis_x = mesh["axis_x"][:]
                    axis_y = mesh["axis_y"][:]
                    axis_z = mesh["axis_z"][:]
                    break
            else:
                raise ValueError(f"No mesh axes in {h5_path}")
        else:
            raise ValueError(f"No Meshes group in {h5_path}")

    # Yee → cell centre. For each component, average the two adjacent
    # samples that lie at the cell faces parallel to that direction.
    def yee_to_cc(F, axis):
        """Average along given axis to bring an Nx face-centred field to
        (Nx-1) cell-centred indices."""
        sl1 = [slice(None)] * F.ndim
        sl2 = [slice(None)] * F.ndim
        sl1[axis] = slice(0, -1)
        sl2[axis] = slice(1, None)
        return 0.5 * (F[tuple(sl1)] + F[tuple(sl2)])

    # Trim to the smallest common shape (Nx-1, Ny-1, Nz-1)
    Nx = min(Fx.shape[0] + 1, Fy.shape[0], Fz.shape[0])  # node count
    Ny = min(Fx.shape[1], Fy.shape[1] + 1, Fz.shape[1])
    Nz = min(Fx.shape[2], Fy.shape[2], Fz.shape[2] + 1)

    # Crop & average to land each component on the (Nx-1, Ny-1, Nz-1)
    # cell-centred grid.
    # Fx is already cell-centred along x but face-centred along y, z.
    # So we average Fx along y and z. Crop first to (Nx-1, Ny, Nz).
    Fx_c = Fx[: Nx - 1, :Ny, :Nz]
    Fx_c = yee_to_cc(yee_to_cc(Fx_c, 1), 2)  # → (Nx-1, Ny-1, Nz-1)

    Fy_c = Fy[:Nx, : Ny - 1, :Nz]
    Fy_c = yee_to_cc(yee_to_cc(Fy_c, 0), 2)

    Fz_c = Fz[:Nx, :Ny, : Nz - 1]
    Fz_c = yee_to_cc(yee_to_cc(Fz_c, 0), 1)

    # Centre-of-cell coordinates
    cx = 0.5 * (axis_x[: Nx - 1] + axis_x[1:Nx])
    cy = 0.5 * (axis_y[: Ny - 1] + axis_y[1:Ny])
    cz = 0.5 * (axis_z[: Nz - 1] + axis_z[1:Nz])

    return Fx_c, Fy_c, Fz_c, (cx, cy, cz)


def poynting_vector(E: tuple, H: tuple) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Time-averaged Poynting vector S = ½ Re(E × H*).  Inputs are 3-tuples
    of complex (Nx, Ny, Nz) arrays. Returns (Sx, Sy, Sz) real arrays."""
    Ex, Ey, Ez = E
    Hx, Hy, Hz = H
    Sx = 0.5 * np.real(Ey * np.conj(Hz) - Ez * np.conj(Hy))
    Sy = 0.5 * np.real(Ez * np.conj(Hx) - Ex * np.conj(Hz))
    Sz = 0.5 * np.real(Ex * np.conj(Hy) - Ey * np.conj(Hx))
    return Sx, Sy, Sz


def sample_at_points(field: np.ndarray, axes: tuple, pts: np.ndarray) -> np.ndarray:
    """Trilinear interpolation of a 3D scalar field at arbitrary (N, 3)
    points in metres. Out-of-domain points are clamped to the boundary."""
    from scipy.interpolate import RegularGridInterpolator

    cx, cy, cz = axes
    interp = RegularGridInterpolator((cx, cy, cz), field, method="linear", bounds_error=False, fill_value=np.nan)
    out = interp(pts)
    # Replace any NaN (out-of-domain) with the nearest valid sample
    if np.any(np.isnan(out)):
        nn = RegularGridInterpolator((cx, cy, cz), field, method="nearest", bounds_error=False, fill_value=0.0)
        bad = np.isnan(out)
        out[bad] = nn(pts[bad])
    return out


def load_skin_apd_npz(npz_path: str, body, *, sinc_ref_w_m2: float = 1.0) -> dict:
    """Load a per-triangle SAPD field dumped goliat-side via
    `discover_sapd_outputs.dump_per_triangle_apd()`. Resamples onto the
    AEGIS body mesh by nearest-neighbour on triangle centroids (goliat's
    surface is Sim4Life's `ModelToGridFilter`-discretised evaluation
    surface; AEGIS's body mesh is the input STL's triangulation, so they
    differ in connectivity but cover the same skin).

    Args:
      npz_path: file written by `dump_per_triangle_apd()`. The schema is:
        `vertices_m (V,3)`, `faces (T,3)`, `apd_w_m2 (V,)` per-vertex
        (kNode) or `(T,)` per-triangle (kCell) — both layouts handled.
      body: aegis BodyMesh (defines the target triangulation).
      sinc_ref_w_m2: reference Sinc against which the peak-APD ratio is
        reported. Use 1.0 if the file was renormed to Sinc=1 W/m² (this
        is the goliat default of `renorm=753.46` for E=1 V/m).

    Returns dict (in addition to `sapd`, `sapd_signed`, `integrated_W`):
      `apd_peak_w_m2` — peak APD on the source mesh (pre-resampling)
      `apd_peak_over_sinc` — peak / sinc_ref_w_m2; useful sanity probe.
        For inward Poynting flux on a perfect absorber this stays ≤ 1.
        On the sphere test we observed ≈ 2.16, suggesting Sim4Life's
        `APD(x,y,z,f0)` is the IEC/IEEE 63195 depth-integrated absorbed
        power density (volumetric, not pure surface flux). Track this
        ratio across phantoms to spot unit/normalisation regressions.

    Always prefer this over `load_surface_apd()` when the npz is present:
    Sim4Life's IEC/IEEE 63195-compliant interpolation is upstream of us.
    """
    d = np.load(npz_path)
    apd = d["apd_w_m2"]
    verts = d["vertices_m"]
    if verts.size == 0 or apd.size == 0:
        raise RuntimeError(f"{npz_path} has no usable mesh; check goliat dump")

    # Map from goliat-side triangulation to AEGIS-body triangulation.
    #  (a) apd length == V:  per-vertex (kNode), average to face via goliat faces
    #  (b) apd length == T:  per-face (kCell), use directly
    faces = d["faces"]
    value_location = str(d.get("value_location", "?"))
    if faces.size and apd.shape[0] == verts.shape[0]:
        face_centroids = verts[faces].mean(axis=1)
        face_apd = apd[faces].mean(axis=1)
        layout = "kNode (per-vertex, averaged to faces)"
    elif faces.size and apd.shape[0] == faces.shape[0]:
        face_centroids = verts[faces].mean(axis=1)
        face_apd = apd
        layout = "kCell (per-face, used directly)"
    else:
        face_centroids = verts
        face_apd = apd
        layout = "fallback (treated verts as point cloud)"

    from scipy.spatial import cKDTree

    tree = cKDTree(face_centroids)
    _, idx = tree.query(body.centroids)
    sapd = face_apd[idx]

    apd_peak = float(apd.max())
    return {
        "sapd": sapd,
        "sapd_signed": sapd,  # already inward by goliat convention
        "integrated_W": float(np.sum(sapd * body.areas)),
        "source": "goliat_dump",
        "port_name": str(d.get("port_name", "?")),
        "value_location": value_location,
        "layout": layout,
        "n_vertices_src": int(verts.shape[0]),
        "n_faces_src": int(faces.shape[0]) if faces.size else 0,
        "apd_peak_w_m2": apd_peak,
        "apd_peak_over_sinc": apd_peak / sinc_ref_w_m2,
        "renorm_in_file": float(d.get("renorm", 1.0)),
    }


def load_surface_apd(h5_path: str, body, *, depth_mm: float = 0.5, renorm: float = 753.46) -> dict:
    """Compute per-triangle surface absorbed power density from a goliat
    `_Output.h5` (overall-field sensor) and a triangulated skin mesh.

    Args:
      h5_path: path to a Sim4Life `_Output.h5` file. The simulation must
        have had `OverallFieldSensorSettings.RecordEField = True` and
        `RecordHField = True` (goliat does this when SAPD extraction is on).
      body: aegis `BodyMesh` for the skin surface (same frame as the FDTD).
      depth_mm: how far inside the body to sample the field. The Yee grid
        cell at the centroid spans the air-tissue boundary on average; we
        sample 0.5 mm deeper to ensure we read the in-tissue field, where
        the Poynting flux is well-defined as "absorbed power into solid".
      renorm: multiplier to scale from goliat's E=1 V/m excitation to
        Sinc=1 W/m² incident. Default 2η₀ ≈ 753.46. Pass 1.0 to keep
        the goliat-native units.

    Returns dict with keys:
      'sapd':  (M,) per-triangle |S · -n̂| in W/m² at Sinc=1 W/m² (clipped >=0)
      'sapd_signed': (M,) S · -n̂  (positive = into body, negative = out)
      'centroids_sampled': (M, 3) the actual sample points in metres
      'integrated_W':  ∫ sapd dA over the mesh; should equal DielLoss×renorm
                       to within ~1 % for a converged FDTD.
    """
    Ex, Ey, Ez, axes_E = _read_field(h5_path, "E")
    Hx, Hy, Hz, axes_H = _read_field(h5_path, "H")
    if axes_E[0].size != axes_H[0].size:
        raise ValueError("E and H grids disagree; check OverallField sensor")

    Sx, Sy, Sz = poynting_vector((Ex, Ey, Ez), (Hx, Hy, Hz))

    # Sample point: centroid offset by `depth_mm` along the INWARD normal
    # (− outward normal). This places us just under the skin in the body.
    eps = depth_mm * 1e-3
    pts = body.centroids - eps * body.normals  # shape (M, 3)

    sx = sample_at_points(Sx, axes_E, pts)
    sy = sample_at_points(Sy, axes_E, pts)
    sz = sample_at_points(Sz, axes_E, pts)
    S_at = np.stack([sx, sy, sz], axis=-1)  # (M, 3)

    # Inward power flux density: − S · n̂_outward.
    s_signed = -np.einsum("md,md->m", S_at, body.normals)
    s_apd = np.maximum(s_signed, 0.0) * renorm
    s_signed_renorm = s_signed * renorm

    integrated = float(np.sum(s_apd * body.areas))

    return {
        "sapd": s_apd,
        "sapd_signed": s_signed_renorm,
        "centroids_sampled": pts,
        "integrated_W": integrated,
        "depth_mm": depth_mm,
        "renorm": renorm,
    }


# ---------------------------------------------------------------------------
# Self-test on synthetic plane-wave h5 data
# ---------------------------------------------------------------------------


def _make_synthetic_h5(
    out_path: str,
    freq_hz: float,
    k_hat: np.ndarray,
    e_E: np.ndarray,
    eps_r: float = 1.0,
    grid_mm: float = 5.0,
    bbox: tuple = (-0.2, 0.2),
):
    """Write a tiny `_Output.h5` containing a free-space plane wave.

    Plane wave:  E(r) = E0 ê_E exp(i k · r),  H(r) = E0 (k̂ × ê_E)/η exp(i k · r)
    with E0 = 1 V/m and η = η₀/√ε_r.

    Used by `_self_test()` to verify the full extraction pipeline against
    analytical surface APD values.
    """
    import h5py

    c0 = 299792458.0
    n = np.sqrt(eps_r)
    k = 2 * np.pi * freq_hz / c0 * n
    eta = ETA_0 / n
    E0 = 1.0

    # Build a regular grid
    x = np.arange(bbox[0], bbox[1] + grid_mm * 1e-3, grid_mm * 1e-3)
    y = np.arange(bbox[0], bbox[1] + grid_mm * 1e-3, grid_mm * 1e-3)
    z = np.arange(bbox[0], bbox[1] + grid_mm * 1e-3, grid_mm * 1e-3)
    Nx, Ny, Nz = len(x), len(y), len(z)

    # Cell-centred sampling for simplicity (skip Yee staggering — we'll
    # write the same values on the staggered nodes since the wave is smooth
    # and the average will reproduce it within O(h²)).
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    phase = np.exp(1j * k * (k_hat[0] * X + k_hat[1] * Y + k_hat[2] * Z))
    Ex = E0 * e_E[0] * phase
    Ey = E0 * e_E[1] * phase
    Ez = E0 * e_E[2] * phase
    h_dir = np.cross(k_hat, e_E) / eta * E0
    Hx = h_dir[0] * phase
    Hy = h_dir[1] * phase
    Hz = h_dir[2] * phase

    def write_comp(g, name, F):
        # Stack as last-axis (real, imag)
        data = np.stack([np.real(F), np.imag(F)], axis=-1).astype(np.float32)
        g.create_dataset(name, data=data)

    with h5py.File(out_path, "w") as f:
        fg = f.create_group("FieldGroups/0")
        obj = fg.create_group("_Object")
        obj.attrs["name"] = "Overall Field"
        for kind, comps in [("E", (Ex, Ey, Ez)), ("H", (Hx, Hy, Hz))]:
            snap = fg.create_group(f"AllFields/EM {kind}(x,y,z,f0)/_Object/Snapshots/0")
            for i, F in enumerate(comps):
                # Yee staggering: shrink each component along its direction
                # so cell-centre averaging reproduces the original. Here we
                # cheat: use cell-centred, with the trim that downstream
                # code expects. Pad to Nx (one larger) along the appropriate axis.
                #   comp0: shape (Nx, Ny, Nz) — cell-centred is fine here.
                #   The downstream Yee → cc averaging will collapse to
                #   (Nx-1, Ny-1, Nz-1).
                if i == 0:
                    # Pad along y, z (face-centre along these dims)
                    Fp = np.pad(F[:-1, :, :], ((0, 0), (0, 0), (0, 0)), mode="edge")
                elif i == 1:
                    Fp = np.pad(F[:, :-1, :], ((0, 0), (0, 0), (0, 0)), mode="edge")
                else:
                    Fp = np.pad(F[:, :, :-1], ((0, 0), (0, 0), (0, 0)), mode="edge")
                write_comp(snap, f"comp{i}", Fp)
        mesh = f.create_group("Meshes/0")
        mesh.create_dataset("axis_x", data=x)
        mesh.create_dataset("axis_y", data=y)
        mesh.create_dataset("axis_z", data=z)


def _self_test():
    """End-to-end test: synthetic plane wave on a sphere, verify the
    recovered per-triangle SAPD matches  Sinc · ReLU(−n̂ · k̂)  to a few %."""
    import sys, tempfile, os

    sys.path.insert(0, "/home/user/aegis/src")
    import trimesh
    from aegis.geometry.mesh import BodyMesh

    print("[h5_surface_apd self-test]")

    # Plane wave: k = +x, E = ẑ (vertical, theta-pol for x_pos), free space
    freq = 1e9
    k_hat = np.array([1.0, 0.0, 0.0])
    e_E = np.array([0.0, 0.0, 1.0])

    with tempfile.TemporaryDirectory() as td:
        h5 = os.path.join(td, "synth_Output.h5")
        _make_synthetic_h5(h5, freq, k_hat, e_E, grid_mm=2.0, bbox=(-0.12, 0.12))

        # Sphere of R=8 cm, free-space surrounded
        sph = trimesh.creation.icosphere(subdivisions=3, radius=0.08)
        stl = os.path.join(td, "sphere.stl")
        sph.export(stl)
        body = BodyMesh.load(stl)

        # Sample IN AIR: depth_mm = 0 → centroid; in vacuum the wave is the
        # full plane wave so the inward Poynting flux density should be
        # exactly Sinc * mu_+ where Sinc = 1/(2η₀) at E0=1 V/m.
        result = load_surface_apd(h5, body, depth_mm=0.0, renorm=1.0)
        sapd = result["sapd"]

        sinc = 1.0 / (2 * ETA_0)
        mu = -np.einsum("md,d->m", body.normals, k_hat)
        expected = sinc * np.maximum(mu, 0.0)

        # Front-facing triangles only (back side has S · n > 0)
        front = mu > 0.05
        rel_err = np.abs(sapd[front] - expected[front]) / (expected[front] + 1e-30)
        med = float(np.median(rel_err))
        worst = float(np.max(rel_err))
        print(f"  median rel_err on front-facing tris: {med:.3%}")
        print(f"  worst                              : {worst:.3%}")
        if med > 0.05:
            raise AssertionError(f"self-test failed: median rel_err {med:.3%} > 5 %")
        # Integrated power: ∫ Sinc * mu_+ dA over a sphere = Sinc * π R²
        target_int = sinc * np.pi * 0.08**2
        rel_int = abs(result["integrated_W"] - target_int) / target_int
        print(
            f"  integrated power: {result['integrated_W']:.3e} W "
            f"(target Sinc·πR² = {target_int:.3e}, err={rel_int:.2%})"
        )
        if rel_int > 0.05:
            raise AssertionError(f"integrated power off by {rel_int:.2%} — check meshing or sample direction")
        print("[h5_surface_apd self-test] PASS")


if __name__ == "__main__":
    _self_test()
