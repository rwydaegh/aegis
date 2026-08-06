#!/usr/bin/env python3
"""Attach equipment class to the grants pulled by eas_pull.py.

The result table has no equipment-class column, and fetching it per grant would
be ~3,900 detail requests. But equipment_class is a *search input*, so we can
instead run the same 5925-100000 MHz / 2019-2026 query once per class (97 of
them) and label every FCC ID we get back. ~97 requests instead of ~3,900.

    python eas_classes.py        # -> eas_grants_classed.csv  (resumable)

A grant can hold several classes (a phone is both a 6 GHz client and a UWB
device), so classes are joined with "|" per FCC ID.
"""

import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from curl_cffi import requests as cr

from eas_pull import (BASE, COUNTER, RESULT, SEARCH, clean, counts, new_session,
                      parse)

CACHE = Path("eas_dump/classes")
IN_CSV = Path("eas_grants.csv")
OUT_CSV = Path("eas_grants_classed.csv")
D0, D1 = "01/01/2019", "12/31/2026"


def class_list(session) -> list[tuple[str, str]]:
    html = session.get(SEARCH, timeout=60).text
    sel = re.search(r'name=["\']equipment_class["\'].*?</select>', html, re.S | re.I)
    if not sel:
        raise RuntimeError("equipment_class dropdown not found on search form")
    out = []
    for val, desc in re.findall(
            r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>(.*?)</option>',
            sel.group(0), re.S | re.I):
        if val.strip():
            out.append((val.strip(), clean(desc)))
    return out


def fetch_class(session, code: str, desc: str) -> str:
    f = CACHE / f"{code}.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    params = dict(BASE, grant_date_from=D0, grant_date_to=D1,
                  equipment_class=code, equipment_class_description=desc)
    for attempt in range(4):
        try:
            r = session.post(RESULT, data=params, timeout=900,
                             headers={"Referer": SEARCH})
            # a class with no in-band grants renders the results page with
            # neither the counter nor the "results were found" line, so the
            # page title is the only reliable "the server answered us" signal
            if r.status_code == 200 and "Authorization Search Results" in r.text:
                f.write_text(r.text, encoding="utf-8")
                return r.text
            last = f"HTTP {r.status_code}, unrecognised page"
        except Exception as e:                      # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        print(f"    retry {attempt + 1}: {last}", flush=True)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"giving up on class {code}")


def main() -> None:
    if not IN_CSV.exists():
        sys.exit("run eas_pull.py first (eas_grants.csv missing)")
    CACHE.mkdir(parents=True, exist_ok=True)
    session = new_session()

    classes = class_list(session)
    print(f"{len(classes)} equipment classes to sweep\n")

    by_id = defaultdict(set)
    label = {}
    for i, (code, desc) in enumerate(classes, 1):
        html = fetch_class(session, code, desc)
        served, total = counts(html)
        rows = parse(html)
        ids = {r["fcc_id"] for r in rows}
        for fid in ids:
            by_id[fid].add(desc.split("-", 1)[0].strip() or code)
        label[code] = desc
        flag = "" if served == total else f"  !! CAPPED {served}/{total}"
        if ids:
            print(f"  [{i:2d}/{len(classes)}] {desc[:46]:46s} {len(ids):5d} ids{flag}",
                  flush=True)
        if not (CACHE / f"{code}.html").stat().st_size == 0:
            time.sleep(1)

    rows = list(csv.DictReader(IN_CSV.open(encoding="utf-8")))
    fields = list(rows[0]) + ["equipment_class"]
    hit = 0
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            cls = sorted(by_id.get(r["fcc_id"], []))
            if cls:
                hit += 1
            r["equipment_class"] = "|".join(cls)
            w.writerow(r)

    ids = {r["fcc_id"] for r in rows}
    covered = {i for i in ids if by_id.get(i)}
    print(f"\ndone: {hit}/{len(rows)} rows labelled; "
          f"{len(covered)}/{len(ids)} FCC IDs got a class -> {OUT_CSV}")


if __name__ == "__main__":
    sys.exit(main())
