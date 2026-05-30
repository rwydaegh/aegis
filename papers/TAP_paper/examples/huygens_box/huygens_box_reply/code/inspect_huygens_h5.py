"""
Quick inspector for the binary Huygens .h5 file that Sim4Life writes
as <simulation_id>_Input.h5. Useful if you want to confirm what
Sim4Life produced and what its internal Yee-grid layout looks like.

This is not the recommended path for importing data from a different
simulator (use write_huygens_txt.py for that), but it is helpful for
sanity checks and for understanding what Sim4Life does internally.

The structure was reverse-engineered during a research stay at the
IT'IS Foundation (Zurich, May 2023). The format is proprietary and
may change between Sim4Life versions.

Expected groups:
    /Meshes/<mesh_key>/axis_x, axis_y, axis_z              (Yee node coords, in m)
    /Meshes/<mesh_key>/_Object attrs.mesh_name             == b"Mesh Huygens_box ..."
    /FieldGroups/<field_key>/_Object attrs.name            == b"Incident Huygens Field"
    /FieldGroups/<field_key>/AllFields/EM E(x,y,z,f0)/_Object/Snapshots/0/comp{0,1,2}
    /FieldGroups/<field_key>/AllFields/EM H(x,y,z,f0)/_Object/Snapshots/0/comp{0,1,2}

Each component dataset is 4-D, with shape (Nx', Ny', Nz', 2). The
last axis holds [real, imag]. The first three axes are reduced by
one element in directions where the Yee staggering drops a sample:

    E_i (i = 0, 1, 2): dimension i has length (N_i - 1), others N_j
    H_i (i = 0, 1, 2): dimensions j, k transverse to i have length
                       (N_j - 1), (N_k - 1); dimension i has length N_i
"""

from __future__ import annotations

import sys

import h5py
import numpy as np


def inspect(path: str) -> None:
    with h5py.File(path, "r") as f:
        print(f"=== {path} ===\n")

        print("Meshes:")
        for mkey in f["Meshes"]:
            obj = f[f"Meshes/{mkey}/_Object"]
            name = obj.attrs.get("mesh_name", b"").decode("ascii", errors="replace")
            x = f[f"Meshes/{mkey}/axis_x"][:]
            y = f[f"Meshes/{mkey}/axis_y"][:]
            z = f[f"Meshes/{mkey}/axis_z"][:]
            print(f"  /{mkey}  name={name!r}")
            print(f"     axis_x: {len(x)} pts  [{x[0]:.4g}, {x[-1]:.4g}] m")
            print(f"     axis_y: {len(y)} pts  [{y[0]:.4g}, {y[-1]:.4g}] m")
            print(f"     axis_z: {len(z)} pts  [{z[0]:.4g}, {z[-1]:.4g}] m")

        print("\nFieldGroups:")
        for fkey in f["FieldGroups"]:
            obj = f[f"FieldGroups/{fkey}/_Object"]
            name = obj.attrs.get("name", b"").decode("ascii", errors="replace")
            print(f"  /{fkey}  name={name!r}")
            try:
                fields = list(f[f"FieldGroups/{fkey}/AllFields"].keys())
            except KeyError:
                fields = []
            for fld in fields:
                print(f"    field: {fld}")
                snap_root = f[f"FieldGroups/{fkey}/AllFields/{fld}/_Object/Snapshots/0"]
                for cname in snap_root:
                    arr = snap_root[cname]
                    print(f"      {cname}: shape={arr.shape}, dtype={arr.dtype}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python inspect_huygens_h5.py <simulation_id>_Input.h5")
        sys.exit(1)
    inspect(sys.argv[1])
