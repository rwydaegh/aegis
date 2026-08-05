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

- **stale**: the blend carries a hash over the scripts that write it, and that
  hash is not today's. This is the one that would have caught the octahedra.
- **walk**: the manifest says the standpoints came from the capture route rather
  than from the disc of grid squares, so the two can be told apart without
  opening the file.
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

import json
import pathlib
import subprocess
import sys
from typing import Any

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"
VIZ = ROOT / "outputs" / "propagation_viz"

#: Scripts whose last commit decides whether a blend is stale, used only when a
#: blend predates the fingerprint stamp. A blend written before any of these
#: changed was built by different code.
BUILDERS = (
    "propagation_blender.py",
    "build_propagation_blends.py",
    "export_propagation_payload.py",
    "semantic_twin/walk/grid.py",
    "semantic_twin/walk/route.py",
    "semantic_twin/walk/site.py",
)

#: Collections the published renders draw from. Empty means a missing layer in
#: a picture nobody checks, which is how a wrong figure gets into a paper.
#:
#: A name that is not in the blend at all is a worse fault than an empty one and
#: is reported separately, because it usually means this list went stale rather
#: than that the build broke. That happened on 3 August: the builder renamed
#: "12 transmitter positions" to "11 sources on the facade tips", this list kept
#: the old name, and the floating source check silently stopped running against
#: anything while still reporting a pass.
REQUIRED = (
    "01 city mesh",
    "08 walk standpoints",
    "09 ray paths by fate",
    "11 sources on the facade tips",
    "12 next event estimation",
    "13 arrival spectrum",
    "14 body exposure",
)

#: The collection the sources live in. Named once, because two checks need it
#: and a rename that misses one of them is the fault above all over again.
SOURCES = "11 sources on the facade tips"

#: The exact support outside the close-view mesh. New builds split the support
#: at the display radius so the central mesh stays legible, but both parts are
#: present in the file and together cover the full traced area.
OUTER_SUPPORT = "01B outer traced support"

#: How far a thing that sits on a surface may sit off it before it is floating.
GROUNDED_TOLERANCE_M = 1.5

#: How far past the drawn mesh an object may reach before it is drawn over
#: nothing. Evidence layers overhang by about a tenth, so this sits above that.
OUTSIDE_RATIO = 1.35

#: Numerical slack around a Hair Curves radius when comparing evaluated and
#: control-point bounds. The datablock stores float32 values, so exact equality
#: would turn ordinary rounding at city-scale coordinates into a QA failure.
CURVE_BOUND_TOLERANCE_M = 1.0e-3

DUMP = r"""
import bpy, json, sys, numpy as np
out = {"objects": {}, "collections": {}, "scene": {}}
depsgraph = bpy.context.evaluated_depsgraph_get()
depsgraph.update()

def world_points(values, matrix):
    if not values.size:
        return values.reshape(0, 3)
    homogeneous = np.column_stack([values, np.ones(values.shape[0])])
    return (homogeneous @ matrix.T)[:, :3]

def bounds(values):
    if not values.size or not np.isfinite(values).all():
        return None, None
    return values.min(axis=0).tolist(), values.max(axis=0).tolist()

for key in bpy.context.scene.keys():
    value = bpy.context.scene[key]
    out["scene"][key] = value if isinstance(value, (str, int, float, bool)) else str(value)
for c in bpy.data.collections:
    out["collections"][c.name] = [o.name for o in c.objects]
for o in bpy.data.objects:
    m = o.data
    w = np.array(o.matrix_world, dtype=float)
    if o.type == "CURVES":
        positions = np.empty((len(m.points), 3), dtype=float)
        m.attributes["position"].data.foreach_get("vector", positions.ravel())
        positions = world_points(positions, w)
        radii = np.empty(len(m.points), dtype=float)
        radius_attribute = m.attributes.get("radius")
        if radius_attribute is None:
            radii.fill(np.nan)
        else:
            radius_attribute.data.foreach_get("value", radii)
        curve_type_attribute = m.attributes.get("curve_type")
        curve_types = None
        if curve_type_attribute is not None:
            values = np.empty(len(m.curves), dtype=np.int8)
            curve_type_attribute.data.foreach_get("value", values)
            curve_types = sorted(set(int(value) for value in values))
        display_proxy_attribute = m.attributes.get("value_is_escaped_display_proxy")
        support_positions = positions
        display_proxy_points = 0
        if display_proxy_attribute is not None:
            display_proxy = np.empty(len(m.points), dtype=np.int32)
            display_proxy_attribute.data.foreach_get("value", display_proxy)
            display_proxy_points = int(np.count_nonzero(display_proxy))
            support_positions = positions[display_proxy == 0]
        evaluated = o.evaluated_get(depsgraph)
        evaluated_bounds = world_points(np.asarray(evaluated.bound_box, dtype=float), np.array(evaluated.matrix_world))
        control_min, control_max = bounds(positions)
        support_min, support_max = bounds(support_positions)
        evaluated_min, evaluated_max = bounds(evaluated_bounds)
        linear_scale = float(np.linalg.norm(w[:3, :3], ord=2))
        out["objects"][o.name] = {
            "kind": "curves",
            "hidden": bool(o.hide_render and o.hide_viewport),
            "points": int(len(m.points)),
            "curves": int(len(m.curves)),
            "control_positions_finite": bool(np.isfinite(positions).all()),
            "radii_finite": bool(np.isfinite(radii).all()),
            "finite": bool(np.isfinite(positions).all() and np.isfinite(radii).all()),
            "curve_types": curve_types,
            "min": control_min,
            "max": control_max,
            "support_min": support_min,
            "support_max": support_max,
            "escaped_display_proxy_points": display_proxy_points,
            "max_radius": float(radii.max() * linear_scale) if radii.size and np.isfinite(radii).all() else None,
            "evaluated_bounds_finite": bool(np.isfinite(evaluated_bounds).all()),
            "evaluated_min": evaluated_min,
            "evaluated_max": evaluated_max,
        }
        continue
    if not hasattr(m, "vertices"):
        out["objects"][o.name] = {"kind": type(m).__name__}
        continue
    v = np.array([list(vv.co) + [1.0] for vv in m.vertices], dtype=float)
    v = (v @ w.T)[:, :3] if v.size else v.reshape(0, 3)
    out["objects"][o.name] = {
        "kind": "mesh",
        "hidden": bool(o.hide_render and o.hide_viewport),
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


def check_stale(blend: pathlib.Path, summary: dict, newest: int) -> list[str]:
    """The blend was written by the code that is on disk right now.

    The blend carries a hash over its builder sources, so this compares hashes
    and is exact. The timestamp path below is the fallback for a blend written
    before the stamp existed, and it is only an approximation: committing an
    unchanged file moves its commit time forward and makes a current blend look
    stale. That false alarm is why the stamp exists.
    """
    stamped = summary.get("scene", {}).get("builder_fingerprint")
    if stamped:
        current = builder_fingerprint()
        if stamped != current:
            return [f"stale: built by code fingerprinted {stamped}, the tree now fingerprints {current}"]
        return []
    if newest and blend.stat().st_mtime < newest:
        age_h = (newest - blend.stat().st_mtime) / 3600.0
        return [f"stale: written {age_h:.1f} h before the last change to the scripts that write it, no fingerprint"]
    return ["stale: no builder fingerprint, so this blend predates the stamp"]


def builder_fingerprint() -> str:
    """The same hash the blend builder stamps, computed here.

    Imported rather than copied. This used to be a hand kept duplicate of the
    source list with a comment saying that importing the real one would pull in
    ``bpy``. That is no longer true: the list lives in
    ``semantic_twin.viz.blender.payload``, which is the half of the builder that
    has no Blender in it, so the two lists cannot drift.
    """
    from semantic_twin.viz.blender.payload import builder_fingerprint as fingerprint

    return fingerprint(ROOT)


def check_populated(summary: dict) -> list[str]:
    """Every collection the renders draw from is present, and holds something."""
    problems = []
    for name in REQUIRED:
        if name not in summary["collections"]:
            problems.append(f"no such collection: {name}, so every check that reads it did nothing")
        elif not summary["collections"][name]:
            problems.append(f"empty collection: {name}")
    return problems


def check_finite(summary: dict) -> list[str]:
    problems = []
    for name, obj in summary["objects"].items():
        if obj.get("kind") == "curves":
            if obj.get("control_positions_finite") is False:
                problems.append(f"non finite curve control positions: {name}")
            if obj.get("radii_finite") is False:
                problems.append(f"non finite curve radii: {name}")
            if obj.get("evaluated_bounds_finite") is False:
                problems.append(f"non finite evaluated curve bounds: {name}")
        elif obj.get("finite") is False:
            problems.append(f"non finite vertices: {name}")
    return problems


def check_hair_curves(summary: dict) -> list[str]:
    """Hair Curves are straight, finite tubes around their recorded points."""
    problems = []
    for name, obj in summary["objects"].items():
        if obj.get("kind") != "curves":
            continue
        curve_types = obj.get("curve_types")
        if curve_types != [1]:
            rendered = "missing" if curve_types is None else repr(curve_types)
            problems.append(f"non-POLY Hair Curves: {name} has curve types {rendered}")
        control_min = obj.get("min")
        control_max = obj.get("max")
        evaluated_min = obj.get("evaluated_min")
        evaluated_max = obj.get("evaluated_max")
        radius = obj.get("max_radius")
        if None in (control_min, control_max, evaluated_min, evaluated_max, radius):
            continue
        lower = np.asarray(control_min, dtype=float) - float(radius) - CURVE_BOUND_TOLERANCE_M
        upper = np.asarray(control_max, dtype=float) + float(radius) + CURVE_BOUND_TOLERANCE_M
        below = np.maximum(lower - np.asarray(evaluated_min, dtype=float), 0.0)
        above = np.maximum(np.asarray(evaluated_max, dtype=float) - upper, 0.0)
        overshoot = float(max(below.max(), above.max()))
        if overshoot > 0.0:
            problems.append(
                f"evaluated Hair Curves overshoot: {name} reaches {overshoot:.3f} m beyond its controls and radius"
            )
    return problems


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
    for name in summary["collections"].get(SOURCES) or []:
        o = summary["objects"][name]
        if o.get("min") is None or o.get("hidden"):
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

    An object hidden in both the render and the viewport is skipped. The blend
    keeps the superseded 400 marker source set on purpose, hidden, because the
    numbers in the same payload integrated it. Nobody sees it, so it cannot be
    drawn over nothing.
    """
    mesh = summary["objects"].get(city)
    if mesh is None or mesh.get("max") is None:
        return []
    reach = max(abs(v) for v in (mesh["min"][0], mesh["max"][0], mesh["min"][1], mesh["max"][1]))
    problems = []
    for name, o in summary["objects"].items():
        if name == city or o.get("max") is None or o.get("hidden"):
            continue
        lower = o.get("support_min", o["min"])
        upper = o.get("support_max", o["max"])
        if lower is None or upper is None:
            continue
        out = max(abs(v) for v in (lower[0], upper[0], lower[1], upper[1]))
        if out > OUTSIDE_RATIO * reach:
            problems.append(
                f"outside the drawn mesh: {name} reaches {out:.0f} m, "
                f"{out / reach:.1f} times the drawn mesh's {reach:.0f} m"
            )
    return problems


def select_inside_support(summary: dict, city: str) -> str:
    """Choose the displayed support object with the greatest XY reach.

    Current blends split exact support geometry between the strong inner city
    mesh and a muted outer annulus. The inside check must therefore use the
    outer annulus when it extends farther. Legacy blends have no such
    collection and continue to use the inner city mesh.
    """
    candidates = [city, *(summary.get("collections", {}).get(OUTER_SUPPORT) or [])]

    def displayed_reach(name: str) -> float:
        obj = summary.get("objects", {}).get(name, {})
        if obj.get("hidden") or obj.get("min") is None or obj.get("max") is None:
            return -1.0
        return max(abs(v) for v in (obj["min"][0], obj["max"][0], obj["min"][1], obj["max"][1]))

    return max(candidates, key=displayed_reach)


def check_walk_builder(manifest: pathlib.Path) -> list[str]:
    """The standpoints came from the capture route, not from the disc of grid squares.

    The grid builder is still there and still reproduces the published numbers,
    so a blend built from it is not wrong, it is just answering an older
    question. What is wrong is not being able to tell which one you are looking
    at, which is the state every blend was in until the manifest started saying.
    """
    if not manifest.exists():
        return ["walk: no manifest, so how the standpoints were chosen is unrecorded"]
    provenance = json.loads(manifest.read_text()).get("walk_provenance")
    if not provenance:
        return ["walk: the manifest does not say how the standpoints were chosen"]
    if provenance.get("builder") != "panorama route":
        return [f"walk: built by {provenance.get('builder')!r}, not by the capture route"]
    return []


def audit(site: str, scratch: pathlib.Path) -> list[str]:
    blend = VIZ / f"{site}_propagation.blend"
    if not blend.exists():
        return [f"no blend at {blend.relative_to(ROOT)}"]
    summary = dump_blend(blend, scratch / f"{site}.json")
    city = (summary["collections"].get("01 city mesh") or [None])[0]
    problems = check_stale(blend, summary, last_builder_commit())
    problems += check_populated(summary)
    problems += check_finite(summary)
    problems += check_hair_curves(summary)
    problems += check_standpoints(summary, VIZ / f"{site}_payload.npz")
    problems += check_walk_builder(VIZ / f"{site}_manifest.json")
    if city:
        problems += check_grounded(summary, city)
        problems += check_inside(summary, select_inside_support(summary, city))
    return problems


def run_audit(args: Any) -> None:
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
