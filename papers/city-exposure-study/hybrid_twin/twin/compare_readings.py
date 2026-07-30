"""Compare two director runs over the same buildings.

    .venv/bin/python -m twin.compare_readings mapillary ""

The question this answers is whether better evidence produced a better reading, and
the honest measure is not confidence. The material A/B earlier in this project had
the cheap model reporting *higher* mean confidence than the frontier model while
collapsing 29 of 32 buildings to one material, so confidence tracks fluency rather
than knowledge.

What is measurable is how many schema groups the director was willing to mark
`seen`, per field, plus how far the answers actually moved. A run that sees more and
changes little was already right; a run that sees more and changes a lot was
previously guessing.
"""

from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
GROUPS = ("storeys", "bays", "window", "ground_floor", "roof", "ledges", "material")


def load(area: str, suffix: str) -> dict[int, dict]:
    d = ROOT / "data" / "twin" / (f"readings_{area}_{suffix}" if suffix
                                  else f"readings_{area}")
    out = {}
    for f in d.glob("*.json"):
        rec = json.loads(f.read_text())
        if rec.get("status") == "ok":
            out[int(rec["osm_id"])] = rec
    return out


def seen_count(rec: dict) -> int:
    return sum(1 for k in GROUPS if rec["reading"][k]["evidence"] == "seen")


def summarise(name: str, runs: dict[int, dict]) -> dict:
    n = len(runs)
    per = {k: sum(1 for r in runs.values()
                  if r["reading"][k]["evidence"] == "seen") for k in GROUPS}
    tot = sum(seen_count(r) for r in runs.values())
    print(f"\n{name}: {n} buildings, ${sum(r.get('cost_usd') or 0 for r in runs.values()):.2f}")
    print(f"  mean seen groups   {tot / max(n, 1):.2f} / 7")
    print(f"  mean confidence    {sum(r['reading']['confidence'] for r in runs.values()) / max(n, 1):.3f}")
    print(f"  with a photograph  {sum(1 for r in runs.values() if r['photos'])}/{n}")
    print(f"  audit flags        {sum(len(r['flags']) for r in runs.values())}")
    print("  seen by field      " + "  ".join(f"{k}:{v}" for k, v in per.items()))
    return {"n": n, "per": per, "mean_seen": tot / max(n, 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("suffix_a", help='cache suffix, e.g. "mapillary"')
    ap.add_argument("suffix_b", nargs="?", default="",
                    help="empty for the live cache")
    ap.add_argument("--area", default="graslei")
    args = ap.parse_args()

    a = load(args.area, args.suffix_a)
    b = load(args.area, args.suffix_b)
    sa = summarise(f"A  {args.suffix_a or 'live'}", a)
    sb = summarise(f"B  {args.suffix_b or 'live'}", b)

    print(f"\ndelta mean seen groups  {sb['mean_seen'] - sa['mean_seen']:+.2f}")
    print("delta seen by field     " + "  ".join(
        f"{k}:{sb['per'][k] - sa['per'][k]:+d}" for k in GROUPS))

    both = sorted(set(a) & set(b))
    print(f"\n{len(both)} buildings read by both. What changed:")
    moved = {"roof": 0, "material": 0, "storeys": 0, "bays": 0, "ground_floor": 0}
    for i in both:
        ra, rb = a[i]["reading"], b[i]["reading"]
        bits = []
        if ra["roof"]["form"] != rb["roof"]["form"]:
            moved["roof"] += 1
            bits.append(f"roof {ra['roof']['form']} -> {rb['roof']['form']}")
        if ra["material"]["wall"] != rb["material"]["wall"]:
            moved["material"] += 1
            bits.append(f"wall {ra['material']['wall']} -> {rb['material']['wall']}")
        if ra["storeys"]["count"] != rb["storeys"]["count"]:
            moved["storeys"] += 1
            bits.append(f"storeys {ra['storeys']['count']} -> {rb['storeys']['count']}")
        if ra["bays"]["count"] != rb["bays"]["count"]:
            moved["bays"] += 1
            bits.append(f"bays {ra['bays']['count']} -> {rb['bays']['count']}")
        if ra["ground_floor"]["kind"] != rb["ground_floor"]["kind"]:
            moved["ground_floor"] += 1
            bits.append(f"gf {ra['ground_floor']['kind']} -> "
                        f"{rb['ground_floor']['kind']}")
        if bits:
            print(f"  {i}  " + "; ".join(bits))
    print("\nchanged counts " + "  ".join(f"{k}:{v}/{len(both)}"
                                          for k, v in moved.items()))


if __name__ == "__main__":
    main()
