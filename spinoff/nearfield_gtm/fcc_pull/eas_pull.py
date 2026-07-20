#!/usr/bin/env python3
"""Pull >6 GHz grant lists from the official FCC EAS.

apps.fcc.gov sits behind Akamai bot protection that fingerprints the TLS
handshake, so stdlib urllib/requests/curl get a stalled connection no matter
what IP or User-Agent they use. curl_cffi replays a real Chrome TLS+HTTP2
fingerprint, which the FCC serves normally.

    pip install curl_cffi
    python eas_pull.py --smoke   # single year, prints row count
    python eas_pull.py           # full pull 2019..2026 (resumable)

The search form honours show_records, so one request returns a whole year
(~4.5k rows). fetchfrom / paging does NOT work - the server ignores it and
re-serves row 1..N - so we never paginate; we ask for everything and assert
the page's own "Displaying records 1 through N of N" counter agrees. A year
that somehow exceeds the cap is automatically re-fetched month by month.

Output: eas_dump/YYYY.html (raw) + eas_grants.csv (parsed, deduped).
"""

import argparse
import calendar
import csv
import re
import sys
import time
from pathlib import Path

from curl_cffi import requests as cr

SEARCH = "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
RESULT = ("https://apps.fcc.gov/oetcf/eas/reports/GenericSearchResult.cfm"
          "?RequestTimeout=1800&calledFromFrame=Y")
OUT = Path("eas_dump")
CSV_PATH = Path("eas_grants.csv")

YEARS = range(2019, 2027)
SHOW_RECORDS = "100000"          # ask for the whole window in one page

_BLANK = [
    "grantee_code", "product_code", "applicant_name", "comments",
    "application_purpose", "application_purpose_description",
    "grant_code_1", "grant_code_2", "grant_code_3", "test_firm",
    "application_status_description", "equipment_class",
    "equipment_class_description", "bandwidth_from", "emission_designator",
    "tolerance_from", "tolerance_to", "power_output_from", "power_output_to",
    "rule_part_1", "rule_part_2", "rule_part_3", "product_description",
    "modular_type_description", "tcb_code", "tcb_code_description",
    "tcb_scope", "tcb_scope_description",
]
BASE = dict.fromkeys(_BLANK, "")
BASE.update({
    "application_status": "ALL",
    "tolerance_exact_match": "off",
    "power_exact_match": "off",
    "rule_part_exact_match": "off",
    "calledFromFrame": "Y",
    "outputformat": "HTML",
    "show_records": SHOW_RECORDS,
    # the money filter: grants with a frequency line in 5.925-100 GHz
    "lower_frequency": "5925",
    "upper_frequency": "100000",
})

# Cell offsets within a data row. Data rows carry 16 cells; the header row has
# 17 (it holds an extra leading cell), so header offsets are all +1 from these
# -- read them off a data row, not the header.
COLS = {"applicant": 5, "city": 7, "state": 8, "country": 9, "zip": 10,
        "fcc_id": 11, "purpose": 12, "grant_date": 13,
        "low_mhz": 14, "high_mhz": 15}
NCELLS = 16

COUNTER = re.compile(r"Displaying records (\d+) through ([\d,]+) of ([\d,]+)")
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")


def new_session() -> cr.Session:
    s = cr.Session(impersonate="chrome124")
    s.get(SEARCH, timeout=60)          # seed Akamai cookies
    return s


def fetch(session: cr.Session, d0: str, d1: str) -> str:
    params = dict(BASE, grant_date_from=d0, grant_date_to=d1)
    last = None
    for attempt in range(4):
        try:
            r = session.post(RESULT, data=params, timeout=900,
                             headers={"Referer": SEARCH})
            if r.status_code == 200 and COUNTER.search(r.text):
                return r.text
            if r.status_code == 200 and "results were found" in r.text:
                return r.text          # legitimately zero rows
            last = f"HTTP {r.status_code}, no result counter"
        except Exception as e:                      # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        print(f"    retry {attempt + 1}: {last}", flush=True)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"giving up on {d0}..{d1}: {last}")


def counts(html: str) -> tuple[int, int]:
    """(rows served on this page, total rows matching) -- (0, 0) if none."""
    m = COUNTER.search(html)
    if not m:
        return (0, 0)
    return (int(m.group(2).replace(",", "")), int(m.group(3).replace(",", "")))


def clean(cell: str) -> str:
    return (TAG.sub("", cell)
            .replace("&nbsp;", " ").replace("&amp;", "&")
            .replace("&#x2f;", "/").replace("&#x27;", "'")
            .replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
            .strip())


def parse(html: str) -> list[dict]:
    out = []
    for raw in ROW.finditer(html):
        cells = [clean(c) for c in CELL.findall(raw.group(1))]
        if len(cells) < NCELLS:
            continue
        fcc_id = cells[COLS["fcc_id"]]
        date = cells[COLS["grant_date"]]
        # the 17-cell header row lands "Zip Code"/"ApplicationPurpose" in these
        # slots, so requiring a real date here is what filters it out
        if not fcc_id or not re.fullmatch(r"\d\d/\d\d/\d{4}", date):
            continue
        out.append({k: cells[i] for k, i in COLS.items()})
    return out


def windows(year: int):
    """One window for the whole year; caller splits to months on overflow."""
    return (f"{year}", f"01/01/{year}", f"12/31/{year}")


def months(year: int):
    for m in range(1, 13):
        last = calendar.monthrange(year, m)[1]
        yield (f"{year}-{m:02d}", f"{m:02d}/01/{year}", f"{m:02d}/{last}/{year}")


def grab(session, tag, d0, d1) -> list[dict]:
    """Fetch one window, cache the raw HTML, verify completeness."""
    f = OUT / f"{tag}.html"
    if f.exists():
        html = f.read_text(encoding="utf-8")
        served, total = counts(html)
        if served == total:
            rows = parse(html)
            print(f"{tag}: cached, {total} rows", flush=True)
            return rows
        print(f"{tag}: cached page incomplete ({served}/{total}), refetching")

    html = fetch(session, d0, d1)
    f.write_text(html, encoding="utf-8")
    served, total = counts(html)
    rows = parse(html)
    ok = "OK" if served == total == len(rows) else "MISMATCH"
    print(f"{tag}: served={served} total={total} parsed={len(rows)} "
          f"{len(html)//1024}KB {ok}", flush=True)

    if served < total:
        # server capped us: fall back to month windows for this year
        print(f"{tag}: capped at {served}/{total}, splitting into months")
        f.unlink()
        rows = []
        for mtag, m0, m1 in months(int(tag)):
            rows += grab(session, mtag, m0, m1)
            time.sleep(2)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="fetch a single year and stop")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    session = new_session()

    if args.smoke:
        rows = grab(session, *windows(2025))
        print(f"\nsmoke: parsed {len(rows)} grants for 2025")
        for r in rows[:5]:
            print("   ", r["grant_date"], r["fcc_id"],
                  f'{r["low_mhz"]}-{r["high_mhz"]} MHz', r["applicant"][:34])
        return

    all_rows = []
    for year in YEARS:
        all_rows += grab(session, *windows(year))
        time.sleep(2)

    # one grant can match on several frequency lines -> dedupe
    seen, uniq = set(), []
    for r in all_rows:
        key = (r["fcc_id"], r["grant_date"], r["low_mhz"], r["high_mhz"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(COLS))
        w.writeheader()
        w.writerows(uniq)

    ids = {r["fcc_id"] for r in uniq}
    print(f"\ndone: {len(all_rows)} rows -> {len(uniq)} unique "
          f"({len(ids)} distinct FCC IDs) -> {CSV_PATH}")


if __name__ == "__main__":
    sys.exit(main())
