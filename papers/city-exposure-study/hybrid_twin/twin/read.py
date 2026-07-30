"""Run the director over the reference plates and write its readings.

    .venv/bin/python -m twin.read --area graslei --model opus

Until this ran, every building in the scene came from `facade.default_spec`, which
is a regional prior: a Ghent-shaped guess keyed on the OSM id. That is a defensible
default and it is not a reading. This module is what turns the pipeline from
"generate something plausible for Flanders" into "generate this street".

Mechanics, and why they are what they are:

- The model is invoked through the Claude Code CLI in `-p` mode rather than through
  the SDK, because there is no API key on this machine and the CLI carries the OAuth
  session. It also means the director is a thing Robin can run, not a thing that only
  exists inside an agent session.
- `--system-prompt` replaces the default prompt outright, so the director gets
  `director.BRIEF` and nothing else. Running from a scratch directory keeps the
  project's own CLAUDE.md out of the context too. The brief is the whole instruction
  set; anything else leaking in is noise in an experiment.
- `--json-schema` forces the shape at the tool layer, so a malformed answer is
  retried by the CLI rather than parsed hopefully here. What this module still checks
  is the part a schema cannot: that the answer does not contradict measured data.

Every reading is stored with its evidence marks, its confidence, the model that
produced it and the plate it looked at. A reading with no plate is never invented:
the building simply keeps the prior, and says so.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import director
from .anchor import Anchor, Building, load
from .areas import AREAS
from .facade import _seg_dist, street_facing_edges
from .meshkit import oriented_rect

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "twin"


# --------------------------------------------------------------------------
# What the director is allowed to know
# --------------------------------------------------------------------------

def attached_sides(b: Building, anchor: Anchor, *, gap: float = 0.8) -> int:
    """How many neighbours share a party wall.

    A terraced house and a detached villa of the same footprint want completely
    different grammars, and the footprint alone does not distinguish them. This is
    measured, so it belongs in the facts rather than in the director's guess.
    """
    n = 0
    for other in anchor.buildings:
        if other.osm_id == b.osm_id:
            continue
        if np.linalg.norm(other.centroid - b.centroid) > 60.0:
            continue
        d = min(_seg_dist(p, np.vstack([other.ring, other.ring[:1]]))
                for p in b.ring)
        if d < gap:
            n += 1
    return n


def fronting_way(b: Building, anchor: Anchor):
    """The nearest street to the building's front, with its measured character."""
    idx = street_facing_edges(b, anchor)[0]
    ring = b.ring
    mid = (ring[idx] + ring[(idx + 1) % len(ring)]) / 2.0
    best, way = 1e9, None
    for w in anchor.ways:
        if w.kind not in {"carriageway", "walkway", "quay"}:
            continue
        d = _seg_dist(mid, w.line)
        if d < best:
            best, way = d, w
    if way is None:
        return None
    return {"highway": way.tags.get("highway"), "name": way.tags.get("name"),
            "surface": way.surface, "car_access": way.car_access,
            "distance_m": round(best, 1)}


KEEP_TAGS = ("building", "name", "building:material", "building:levels",
             "roof:shape", "roof:material", "start_date", "heritage",
             "historic", "amenity", "shop", "tourism", "addr:street")


def facts_for(b: Building, anchor: Anchor, plate: dict) -> dict:
    """Everything measured about this building, and nothing that is not."""
    rect = oriented_rect(b.ring)
    fronts = street_facing_edges(b, anchor)
    tags = {k: b.tags[k] for k in KEEP_TAGS if k in b.tags}
    f = {
        "osm_id": b.osm_id,
        "city": "Ghent, Belgium",
        "osm_tags": tags or None,
        "frontage_width_m": round(plate.get("facade_width_m", 0.0), 1),
        "footprint_m": [round(2 * rect.half_u, 1), round(2 * rect.half_v, 1)],
        "footprint_area_m2": round(b.area),
        "height_m": round(b.height, 1),
        "height_source": b.decision,
        "street_frontages": len(fronts),
        "attached_neighbours": attached_sides(b, anchor),
        "fronting_street": fronting_way(b, anchor),
        "plate_view": plate.get("view", "street"),
        "street_photos": plate.get("n_photos") or None,
    }
    if plate.get("target_box"):
        f["target_box_normalised"] = plate["target_box"]
    return {k: v for k, v in f.items() if v is not None}


# --------------------------------------------------------------------------
# Talking to the director
# --------------------------------------------------------------------------

def evidence_for(plate: dict, photos: list[dict]) -> tuple[list[str], str]:
    """Image paths in the order the director is told about them, plus the note
    describing what each set can and cannot answer."""
    images = [plate["image"]]
    if plate.get("keyed_image"):
        images.append(plate["keyed_image"])
    notes = [director.EVIDENCE_NOTE[
        "tiles_oblique" if plate.get("view") == "oblique" else "tiles_street"]]
    for p in photos:
        images += [p["file"], p["keyed_file"]]
    if photos:
        notes.append(director.EVIDENCE_NOTE["photo"])
        if any(p.get("is_pano") for p in photos):
            notes.append(director.EVIDENCE_NOTE["photo_pano"])
    else:
        notes.append("There is no street photograph of this building. Everything "
                     "below the resolution of set A is therefore `inferred`.")
    return images, "\n\n".join(notes)


def build_prompt(b: Building, anchor: Anchor, plate: dict,
                 photos: list[dict]) -> str:
    images, evidence = evidence_for(plate, photos)
    task = director.facade_task(osm_id=b.osm_id,
                                facts=facts_for(b, anchor, plate),
                                images=images, evidence=evidence)
    n_plate = 2 if plate.get("keyed_image") else 1
    lines = []
    for i, p in enumerate(images):
        label = "set A" if i < n_plate else "set B"
        mark = "annotated" if i % 2 else "clean"
        lines.append(f"  {label}, {mark}: {pathlib.Path(p).resolve()}")
    return ("Read these images with the Read tool:\n" + "\n".join(lines)
            + f"\n\n{task.prompt}")


def call(prompt: str, *, model: str, schema_path: pathlib.Path,
         brief_path: pathlib.Path, img_dir: pathlib.Path,
         cwd: pathlib.Path, timeout: int = 420) -> dict:
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--system-prompt-file", str(brief_path),
        "--json-schema", schema_path.read_text(),
        "--allowedTools", "Read",
        "--add-dir", str(img_dir),
        "--output-format", "json",
    ]
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        # Uncaught, this propagates out of the worker and `list(ex.map(...))`
        # re-raises it, so one slow building throws away the other 31 readings
        # after twenty minutes of work. One building failing is a data point;
        # losing the run is not.
        return {"ok": False, "error": f"timed out after {timeout}s"}
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout)[-400:]}
    env = json.loads(proc.stdout)
    if env.get("is_error"):
        return {"ok": False, "error": str(env.get("result"))[-400:]}
    try:
        payload = json.loads(env["result"])
    except (KeyError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"unparseable result: {exc}"}
    return {"ok": True, "reading": payload,
            "cost_usd": env.get("total_cost_usd"),
            "model": next(iter(env.get("modelUsage", {"?": None})))}


# --------------------------------------------------------------------------
# Checks a schema cannot make
# --------------------------------------------------------------------------

def audit(reading: dict, b: Building, facts: dict) -> list[str]:
    """Flag readings that contradict the measured layer.

    Not a filter. The reading is kept either way and the complaints are stored with
    it, because the interesting failure is systematic (every building gets four
    storeys) and that is only visible across the set.
    """
    out = []
    st = reading["storeys"]
    modelled = st["ground_height_m"] + max(0, st["count"] - 1) * st["upper_height_m"]
    if modelled > b.height + 1.0:
        out.append(f"storeys imply {modelled:.1f} m of wall above a measured "
                   f"{b.height:.1f} m envelope")
    if modelled < 0.45 * b.height:
        out.append(f"storeys fill only {modelled / b.height:.0%} of the envelope")
    tag = b.material_tag()
    if tag and reading["material"]["wall"] != tag:
        out.append(f"wall {reading['material']['wall']!r} contradicts OSM "
                   f"building:material={tag!r}")
    levels = (facts.get("osm_tags") or {}).get("building:levels")
    if levels and str(st["count"]) != str(levels):
        out.append(f"storeys {st['count']} against OSM building:levels={levels}")
    bays = reading["bays"]["count"]
    width = facts["frontage_width_m"]
    if width > 2.0 and not (1.4 <= width / max(bays, 1) <= 9.0):
        out.append(f"{bays} bays across {width} m is {width / max(bays, 1):.1f} m "
                   f"of frontage each")
    if reading["material"]["evidence"] == "seen" and \
            facts["plate_view"] == "oblique" and not facts.get("street_photos"):
        out.append("material marked `seen` from an aerial plate alone")
    if reading["roof"]["evidence"] == "seen" and facts["plate_view"] == "street" \
            and reading["roof"]["form"] != "flat":
        out.append("roof form marked `seen`, but no view here looks down on it")
    return out


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--plates", default="data/twin/plates.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", default=None)
    ap.add_argument("--refresh", action="store_true",
                    help="discard the per-building cache and re-read")
    args = ap.parse_args()

    anchor = load()
    cx, cy, radius = AREAS[args.area]
    centre = np.array([cx, cy])
    plates = {int(p["id"]): p
              for p in json.loads((ROOT / args.plates).read_text())["plates"]
              if p.get("status") == "rendered"}
    # The merged manifest if `twin.streetview` has run, else Mapillary alone. The
    # merged one is preferred because an aimed Street View shot beats a drive-by
    # frame that happened to point the right way, and it carries the Mapillary
    # records anyway for the buildings Google cannot see.
    sv_path = next((p for p in (ROOT / "data" / "twin" / f"photos_{args.area}.json",
                                ROOT / "data" / "twin"
                                / f"streetview_{args.area}.json") if p.exists()),
                   None)
    photos = ({int(k): v for k, v in
               json.loads(sv_path.read_text())["photos"].items()}
              if sv_path else {})
    if sv_path:
        srcs: dict[str, int] = {}
        for recs in photos.values():
            for r in recs:
                s = r.get("source", "mapillary")
                srcs[s] = srcs.get(s, 0) + 1
        print(f"[read] photo sources {srcs}")
    for osm_id, plate in plates.items():
        plate["n_photos"] = len(photos.get(osm_id, []))

    targets = [b for b in anchor.buildings
               if b.osm_id in plates
               and np.linalg.norm(b.centroid - centre) <= radius]
    if args.only:
        keep = {int(s) for s in args.only.split(",")}
        targets = [b for b in targets if b.osm_id in keep]

    # One file per building, written the moment it lands. A twenty-minute fan-out
    # that keeps everything in memory until the end is one bad building away from
    # returning nothing, and resuming is then free rather than another eight
    # dollars of re-reading the same walls.
    cache = OUT / f"readings_{args.area}"
    cache.mkdir(parents=True, exist_ok=True)
    if args.refresh:
        for f in cache.glob("*.json"):
            f.unlink()
    done = {int(f.stem) for f in cache.glob("*.json")}
    todo = [b for b in targets if b.osm_id not in done]
    covered = sum(1 for b in targets if photos.get(b.osm_id))
    print(f"[read] {len(targets)} buildings, {covered} with a street photo, "
          f"{len(done)} already cached, {len(todo)} to read, model {args.model}")

    work = pathlib.Path(tempfile.mkdtemp(prefix="director-"))
    brief_path = work / "brief.txt"
    brief_path.write_text(director.BRIEF)
    schema_path = work / "facade_schema.json"
    schema_path.write_text(json.dumps(director.FACADE_SCHEMA))
    img_dir = (ROOT / "renders").resolve()

    def one(b: Building) -> dict:
        plate = plates[b.osm_id]
        pics = photos.get(b.osm_id, [])
        facts = facts_for(b, anchor, plate)
        prompt = build_prompt(b, anchor, plate, pics)
        res = call(prompt, model=args.model, schema_path=schema_path,
                   brief_path=brief_path, img_dir=img_dir, cwd=work)
        if not res["ok"]:
            print(f"  {b.osm_id}  FAILED  {res['error'][:120]}")
            return {"osm_id": b.osm_id, "status": "failed",
                    "error": res["error"]}
        r = res["reading"]
        flags = audit(r, b, facts)
        seen = sum(1 for k in ("storeys", "bays", "window", "ground_floor", "roof",
                               "ledges", "material")
                   if r[k]["evidence"] == "seen")
        print(f"  {b.osm_id}  {r['roof']['form']:14s} {r['storeys']['count']}st "
              f"{r['bays']['count']}bay {r['material']['wall']:12s} "
              f"conf {r['confidence']:.2f}  seen {seen}/7  "
              f"{len(pics)} photo" + (f"  [{len(flags)} flag]" if flags else ""))
        for f in flags:
            print(f"       ! {f}")
        rec = {"osm_id": b.osm_id, "status": "ok", "reading": r,
               "flags": flags, "facts": facts, "plate": plate["image"],
               "photos": [p["file"] for p in pics],
               "view": plate.get("view", "street"),
               "cost_usd": res["cost_usd"], "model": res["model"]}
        (cache / f"{b.osm_id}.json").write_text(json.dumps(rec, indent=1))
        return rec

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(one, todo))

    results = []
    for b in targets:
        f = cache / f"{b.osm_id}.json"
        results.append(json.loads(f.read_text()) if f.exists()
                       else {"osm_id": b.osm_id, "status": "failed",
                             "error": "no reading"})
    ok = [r for r in results if r["status"] == "ok"]
    cost = sum(r.get("cost_usd") or 0.0 for r in ok)
    out = pathlib.Path(args.out) if args.out else OUT / f"facades_{args.area}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    # hashlib, not hash(): Python salts string hashing per process, so the built-in
    # would stamp a different brief id on every run and identify nothing.
    brief_sha = hashlib.sha256(director.BRIEF.encode()).hexdigest()[:12]
    out.write_text(json.dumps({"area": args.area, "model": args.model,
                               "brief_sha": brief_sha,
                               "readings": results}, indent=1))
    forms: dict[str, int] = {}
    mats: dict[str, int] = {}
    for r in ok:
        forms[r["reading"]["roof"]["form"]] = \
            forms.get(r["reading"]["roof"]["form"], 0) + 1
        mats[r["reading"]["material"]["wall"]] = \
            mats.get(r["reading"]["material"]["wall"], 0) + 1
    print(f"\n[read] {len(ok)}/{len(results)} read, ${cost:.2f}")
    print(f"[read] roof forms {dict(sorted(forms.items(), key=lambda kv: -kv[1]))}")
    print(f"[read] materials  {dict(sorted(mats.items(), key=lambda kv: -kv[1]))}")
    print(f"[read] flagged    {sum(1 for r in ok if r['flags'])}")
    print(f"[read] -> {out}")


if __name__ == "__main__":
    sys.exit(main())
