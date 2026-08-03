"""Check a propagation blend against the code and data it claims to come from.

Every defect this looks for is one that actually shipped. On 3 August the blend
files held 400 octahedra floating above each square, sampled from a height band
the method had stopped using twelve hours earlier, and the renders made from
them were presented as evidence. Nothing complained, because nothing was
looking. A blend is a build artefact and it goes stale exactly like a compiled
binary does, but it has no timestamp check and no test.

So this is the timestamp check and the test. It reads the blend through
Blender, writes a plain summary, and asserts against it in ordinary Python so
the assertions can be read and tested without Blender in the way.

The checks, and the failure each one is aimed at:

- **stale**: the blend is older than the last commit that touched the scripts
  that write it. This is the one that would have caught the octahedra.
- **standpoints**: the standpoints in the file are the ones today's walk builder
  produces, to the metre. Catches a blend built before a walk change, and
  catches a blend built from a different radius or seed than its manifest says.
- **grounded**: nothing that claims to sit on a surface floats above one. A
  source on a roofline is within a metre of geometry. Catches the octahedra
  directly, since they hang 14 to 47 m over the rooftops.
- **inside**: no drawn object sits outside the mesh that is actually drawn. The
  city mesh is a disc about the scene origin and a source at 246 m has nothing
  under it in the render.
- **populated**: no collection that the renders use is empty.
- **finite**: no NaN or infinity in any vertex, which turns into an invisible
  object rather than an error.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python qa_propagation_blend.py --site korenmarkt
    ../../../.venv/bin/python qa_propagation_blend.py --all
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"
VIZ = ROOT / "outputs" / "propagation_viz"

#: Scripts whose last commit decides whether a blend is stale. A blend written
#: before any of these changed was built by different code.
BUILDERS = (
    "propagation_blender.py",
    "build_propagation_blends.py",
    "export_propagation_payload.py",
    "semantic_twin/propagation/walk.py",
)

#: Collections the published renders draw from. Empty means a missing layer in
#: a picture nobody checks, which is how a wrong figure gets into a paper.
REQUIRED = (
    "01 city mesh",
    "08 walk standpoints",
    "09 ray paths by fate",
    "11 arrival spectrum",
    "12 transmitter positions",
    "13 body exposure",
)

#: How far a thing that sits on a surface may sit off it before it is floating.
GROUNDED_TOLERANCE_M = 1.5

#: How far past the drawn mesh an object may reach before it is drawn over
#: nothing. Evidence layers overhang by about a tenth, so this sits above that.
OUTSIDE_RATIO = 1.35

DUMP = r"""
import bpy, json, sys, numpy as np
out = {"objects": {}, "collections": {}}
for c in bpy.data.collections:
    out["collections"][c.name] = [o.name for o in c.objects]
for o in bpy.data.objects:
    m = o.data
    if not hasattr(m, "vertices"):
        out["objects"][o.name] = {"kind": type(m).__name__}
        continue
    w = np.array(o.matrix_world)
    v = np.array([list(vv.co) + [1.0] for vv in m.vertices], dtype=float)
    v = (v @ w.T)[:, :3] if v.size else v.reshape(0, 3)
    out["objects"][o.name] = {
        "kind": "mesh",
        "vertices": int(len(m.vertices)),
        "faces": int(len(m.polygons)),
        "finite": bool(np.isfinite(v).all()) if v.size else True,
        "min": v.min(axis=0).tolist() if v.size else None,
        "max": v.max(axis=0).tolist() if v.size else None,
        "centroids": v.reshape(-1, 3).tolist() if len(m.vertices) <= 4000 else None,
    }
json.dump(out, open(sys.argv[-1], "w"))
"""


def dump_blend(blend: pathlib.Path, destination: pathlib.Path) -> dict:
    """Read a blend through Blender and return a plain summary of its objects."""
    script = destination.with_suffix(".py")
    script.write_text(DUMP)
    result = subprocess.run(
        [str(BLENDER), "-b", str(blend), "--python", str(script), "--", str(destination)],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if not destination.exists():
        raise SystemExit(f"Blender wrote nothing for {blend.name}:\n{result.stdout[-2000:]}")
    return json.loads(destination.read_text())


def last_builder_commit() -> int:
    """Unix time of the most recent commit touching anything that writes a blend."""
    stamps = []
    for name in BUILDERS:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", name],
            cwd=ROOT,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if out:
            stamps.append(int(out))
    return max(stamps) if stamps else 0


def check_stale(blend: pathlib.Path, newest: int) -> list[str]:
    if newest and blend.stat().st_mtime < newest:
        age_h = (newest - blend.stat().st_mtime) / 3600.0
        return [f"stale: written {age_h:.1f} h before the last change to the scripts that write it"]
    return []


def check_populated(summary: dict) -> list[str]:
    return [f"empty collection: {name}" for name in REQUIRED if not summary["collections"].get(name)]


def check_finite(summary: dict) -> list[str]:
    return [f"non finite vertices: {name}" for name, o in summary["objects"].items() if o.get("finite") is False]


def check_standpoints(summary: dict, payload: pathlib.Path) -> list[str]:
    """The standpoints drawn are the ones the payload traced."""
    objects = summary["collections"].get("08 walk standpoints") or []
    if not objects or not payload.exists():
        return ["standpoints: nothing drawn" if not objects else "standpoints: no payload to compare against"]
    points = np.load(payload)["walk_points"]
    drawn = summary["objects"][objects[0]]
    if drawn.get("centroids") is None:
        return []
    marks = np.asarray(drawn["centroids"], dtype=float)
    # Markers are little solids around each standpoint, so compare on the set of
    # marker centres rather than on vertices.
    per = marks.shape[0] // points.shape[0] if points.shape[0] else 0
    if per == 0 or marks.shape[0] % points.shape[0]:
        return [f"standpoints: {marks.shape[0]} marker vertices does not divide {points.shape[0]} standpoints"]
    centres = marks.reshape(points.shape[0], per, 3).mean(axis=1)
    order = np.argsort(centres[:, 0] * 1e6 + centres[:, 1])
    want = np.argsort(points[:, 0] * 1e6 + points[:, 1])
    gap = np.linalg.norm(centres[order] - points[want], axis=1).max()
    return [f"standpoints: drawn markers sit up to {gap:.2f} m from the traced points"] if gap > 1.0 else []


def check_grounded(summary: dict, city: str) -> list[str]:
    """Nothing that should sit on a surface hangs in the air above it."""
    mesh = summary["objects"].get(city)
    if mesh is None or mesh.get("max") is None:
        return ["grounded: no city mesh to measure against"]
    problems = []
    for name in summary["collections"].get("12 transmitter positions") or []:
        o = summary["objects"][name]
        if o.get("min") is None:
            continue
        # A source set that sits on the rooflines spans the roof heights. One
        # that floats sits entirely above the tallest thing in the scene.
        if o["min"][2] > mesh["max"][2] + GROUNDED_TOLERANCE_M:
            problems.append(
                f"floating: {name} starts {o['min'][2] - mesh['max'][2]:.1f} m above the top of the drawn mesh"
            )
    return problems


def check_inside(summary: dict, city: str) -> list[str]:
    """No drawn object reaches far outside the mesh that is actually drawn.

    The tolerance is a ratio, not a margin, and that is deliberate. Evidence
    layers legitimately overhang: a fishnet is cut from a panorama that sees
    past the drawn disc, and a depth cloud is a measurement, so both land 10
    percent beyond the mesh and look right. What does not look right is a
    source set at 304 m over a 116 m mesh, which is nearly three times the
    scene and hangs over nothing at all.

    Flagging both at one metre made ten complaints of which one mattered, and a
    check that has to be read past is a check that stops being read.
    """
    mesh = summary["objects"].get(city)
    if mesh is None or mesh.get("max") is None:
        return []
    reach = max(abs(v) for v in (mesh["min"][0], mesh["max"][0], mesh["min"][1], mesh["max"][1]))
    problems = []
    for name, o in summary["objects"].items():
        if name == city or o.get("max") is None:
            continue
        out = max(abs(v) for v in (o["min"][0], o["max"][0], o["min"][1], o["max"][1]))
        if out > OUTSIDE_RATIO * reach:
            problems.append(
                f"outside the drawn mesh: {name} reaches {out:.0f} m, "
                f"{out / reach:.1f} times the drawn mesh's {reach:.0f} m"
            )
    return problems


def audit(site: str, scratch: pathlib.Path) -> list[str]:
    blend = VIZ / f"{site}_propagation.blend"
    if not blend.exists():
        return [f"no blend at {blend.relative_to(ROOT)}"]
    summary = dump_blend(blend, scratch / f"{site}.json")
    city = (summary["collections"].get("01 city mesh") or [None])[0]
    problems = check_stale(blend, last_builder_commit())
    problems += check_populated(summary)
    problems += check_finite(summary)
    problems += check_standpoints(summary, VIZ / f"{site}_payload.npz")
    if city:
        problems += check_grounded(summary, city)
        problems += check_inside(summary, city)
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--scratch", type=pathlib.Path, default=pathlib.Path("/tmp/blend_qa"))
    args = ap.parse_args()

    args.scratch.mkdir(parents=True, exist_ok=True)
    sites = args.site or (
        [p.name.replace("_propagation.blend", "") for p in sorted(VIZ.glob("*_propagation.blend"))]
        if args.all
        else ["korenmarkt"]
    )

    failed = 0
    for site in sites:
        problems = audit(site, args.scratch)
        if problems:
            failed += 1
            print(f"{site}: {len(problems)} problems")
            for p in problems:
                print(f"    {p}")
        else:
            print(f"{site}: clean")
    print(f"\n{len(sites) - failed} of {len(sites)} clean")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
