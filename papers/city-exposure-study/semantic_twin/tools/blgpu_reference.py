"""Deterministic tracer fingerprint, for comparing two machines bit for bit.

The adjoint SBR estimator is claimed to be a pure function of its seed, so the
same seed on the same mesh has to give the same float64 out of any host. This
script pins every input, runs the tracer, and prints the results with no
rounding at all: susceptibility comes out as the C99 hexadecimal float literal,
which round trips exactly, and the angular power spectrum comes out as a sha256
over its raw little endian bytes.

Run it on both machines and diff the two outputs. A single differing character
is a real difference, not a formatting artefact.

    python tools/blgpu_reference.py --rays 200000 > local.txt
    tools/blgpu.sh sh "python tools/blgpu_reference.py --rays 200000" > remote.txt
    diff local.txt remote.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import platform
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_twin.propagation import MitsubaGeometry, SbrTracer, TraceConfig  # noqa: E402
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY  # noqa: E402
from semantic_twin.propagation.directions import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL  # noqa: E402

MESH = ROOT / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m_f64.ply"

#: The study's own illumination models, so the fingerprint covers the real
#: reduction and not a stand in. Both machines run the same synced code, so a
#: later edit to this table moves both references together.
MODELS = {
    "isotropic": ISOTROPIC,
    "rooftop": ROOFTOP,
    "street_small_cell": STREET_SMALL_CELL,
}

#: Fixed observation points in the mesh's local ENU frame, at head height above
#: the Korenmarkt ground datum. Hard coded rather than drawn from build_walk so
#: that the fingerprint does not move when the walk sampler changes.
POINTS = np.array(
    [
        [0.0, 0.0, 52.34],
        [12.0, -8.0, 52.34],
        [-15.0, 6.0, 52.34],
    ],
    dtype=np.float64,
)
GROUND_Z_M = 50.83747424667166


def hexfloat(value: float) -> str:
    return float(value).hex()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--local-cells", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260802)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--json", action="store_true", help="machine readable, one object per line")
    args = parser.parse_args()

    geometry = MitsubaGeometry(MESH, variant=args.variant)
    face_class = np.zeros(geometry.face_count, dtype=np.int64)
    permittivity = np.array([complex(5.31, -0.4)])  # ITU-R P.2040 concrete at 15 GHz
    rms_height = np.array([0.0])

    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=args.rays,
        local_cells=args.local_cells,
        exit_bands=18,
        seed=args.seed,
    )
    tracer = SbrTracer(geometry, face_class, permittivity, rms_height, config)

    print(f"# host      {platform.node()}")
    print(f"# python    {platform.python_version()}")
    print(f"# numpy     {np.__version__}")
    print(f"# mesh      {MESH.name}  faces={geometry.face_count}")
    print(f"# vertices  sha256={hashlib.sha256(geometry.vertices.tobytes()).hexdigest()}")
    print(f"# faces     sha256={hashlib.sha256(geometry.faces.tobytes()).hexdigest()}")
    print(f"# config    {json.dumps(config.as_dict(), sort_keys=True)}")
    print(f"# pec       {PEC_PERMITTIVITY}")

    for index, point in enumerate(POINTS):
        result = tracer.trace(point, MODELS, ground_z_m=GROUND_Z_M, seed=args.seed + 1000 * index)
        for name in sorted(result.susceptibility):
            print(f"point{index} chi[{name}]        {hexfloat(result.susceptibility[name])}")
            print(f"point{index} chi_direct[{name}] {hexfloat(result.susceptibility_direct[name])}")
        rho = result.rho if hasattr(result, "rho") else None
        if rho is not None:
            for name in sorted(rho):
                block = np.ascontiguousarray(np.asarray(rho[name], dtype=np.float64))
                digest = hashlib.sha256(block.tobytes()).hexdigest()
                print(f"point{index} rho[{name}]        sha256={digest} sum={hexfloat(float(block.sum()))}")
        for key, value in sorted(result.scalars().items()):
            if isinstance(value, float):
                print(f"point{index} scalar[{key}]      {hexfloat(value)}")
            elif isinstance(value, int):
                print(f"point{index} scalar[{key}]      {value}")


if __name__ == "__main__":
    main()
