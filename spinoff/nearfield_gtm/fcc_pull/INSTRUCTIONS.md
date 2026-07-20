# Route B: official EAS pull — DONE

The pull is complete. No residential IP, no browser, no Claude for Chrome needed.
`eas_grants.csv` (15,611 rows) and `eas_dump/YYYY.html` (raw pages) are in this folder.

## What the old plan got wrong

The old note assumed apps.fcc.gov blocks *datacenter IPs* and that running from a
home connection would fix it. It doesn't. Akamai fingerprints the **TLS handshake**,
not the IP: TCP and TLS both complete instantly, then the HTTP response never
arrives. stdlib `urllib`, `requests`, and `curl` all hang from any machine.

`curl_cffi` replays a real Chrome TLS+HTTP2 fingerprint, and the FCC serves
normally — HTTP 200, full result table. That is the entire fix.

Two silent data-loss bugs in the old script, worth knowing about because both
would have produced a truncated corpus that *looked* successful:

- `count_rows()` counted the string `"ViewGrant"`, which appears nowhere in the
  result page. It returned 0 for every month.
- **`fetchfrom` is ignored by the server.** `fetchfrom=500` re-serves rows 1–500.
  The paging loop could never advance past the first page.

Together those would have capped every month at 500 rows and printed "done".

## What actually works

`show_records` *is* honoured, and the page states its own completeness:
"Displaying records 1 through N of N". So one request returns a whole year
(2025 = 4,452 rows in a single response). The pull is ~8 requests, not 91.

`eas_pull.py` asks for the full year, then asserts `served == total == parsed`,
and automatically re-fetches that year month-by-month if the server ever caps it.

```bash
pip install curl_cffi
python eas_pull.py --smoke   # one year, prints row count
python eas_pull.py           # full 2019..2026, resumable (~4 min)
```

Delete `eas_dump/YYYY.html` to force a refetch of that year; anything cached and
complete is reused.

## The data

`eas_grants.csv` — one row per (FCC ID × frequency line):
`applicant, city, state, country, zip, fcc_id, purpose, grant_date, low_mhz, high_mhz`

- 15,611 unique rows, **3,900 distinct FCC IDs**, 2019-01-02 → 2026-07-13, no gaps.
- Per year: 340 / 479 / 902 / 1717 / 2087 / 3758 / 4452 / 3414 (2026 partial).
- Band mix by FCC ID: ~2,235 touch 6 GHz (WiFi 6E/7), ~1,909 sit above 7.125 GHz
  (UWB/mmWave). These overlap — a phone is in both.
- Top applicants: Apple (220), Samsung (213), Google (74), Motorola (59),
  Zebra (50), LG (50), ASUS (48), Ubiquiti (42).

**Note on out-of-band rows.** 356 rows fall outside 5925–100000 MHz. They belong to
133 FCC IDs that *also* have an in-band line — the FCC matches the **grant** (any
line in range) and the table then lists **every** frequency line of that device,
including e.g. 13.56 MHz NFC. Every FCC ID in the file has at least one in-band
line, so there is no contamination. Filter on
`high_mhz >= 5925 and low_mhz <= 100000` if you want in-band lines only.

## Equipment class — `eas_classes.py` -> `eas_grants_classed.csv`

The result table has no equipment-class column, and a per-grant detail fetch would
be ~3,900 requests. But `equipment_class` is a *search input*, so `eas_classes.py`
re-runs the same query once per class (97 of them) and labels every FCC ID it gets
back — 97 requests instead of 3,900.

```bash
python eas_classes.py        # -> eas_grants_classed.csv (resumable, ~3 min)
```

**3,862 / 3,900 FCC IDs get a class.** A grant can hold several (a phone is both a
6 GHz client and a UWB device), so classes are joined with `|`. The 38 unlabelled
IDs hold no class that appears in the search dropdown.

Class mix that matters for the Stage 1 spine:

| Class | Meaning | FCC IDs |
|-------|---------|---------|
| 6XD | 6 GHz Low Power Indoor Client | 705 |
| UWB | Ultra Wideband Transmitter | 672 |
| 6CD | 6 GHz Low Power Dual Client | 497 |
| 6ID | 6 GHz Low Power Indoor Access Point | 470 |
| 6VL | 6 GHz Very Low Power Device | 241 |
| 6PP | 6 GHz Subordinate Indoor Device | 128 |
| 6SD | 6 GHz Standard Power Access Point | 113 |
| 6FC / 6FX | 6 GHz Fixed / Standard Client | 16 / 9 |

## Coverage validation (independent source)

The FCC's own EAS Web API (KDB 953436, base `https://apps.fcc.gov/OETLabServices/`)
is unauthenticated and needs no key. `getAFCAuthorizations?beginDate=&endDate=`
returns 6 GHz standard-power grants with equipment class and freqMin/freqMax —
a source completely independent of the HTML search.

Checked against it: **118/118 of its FCC IDs are in our corpus, and 118/118 of our
equipment_class labels agree with it.** No gaps, no disagreements.

Note the API is *not* an alternative route for the main pull: `getFCCIDList` takes
only an FCC ID prefix — no frequency filter, no date filter, and it returns no
frequency data at all. `getAFCAuthorizations` is the only endpoint with
frequencies and it covers just 6SD/6FC (118 devices). Hence the HTML scrape.

## Routes that do NOT work (checked, so nobody re-checks them)

- **No bulk dump of EAS grants with frequencies exists** — not on data.gov /
  Socrata (grantee registry only, stale since 2021), GitHub, Kaggle, HuggingFace,
  data.world, or Academic Torrents.
- **fccid.io `/frequency-explorer`** caps at 1,000 rows and filters by *containment*,
  not overlap. `5955–6415` is one exact frequency line shared by thousands of Wi-Fi
  6E devices, so no query window can subdivide that population — you can only ever
  see the most recent ~1,000. Fine for sparse bands, useless for 6 GHz.
- A Zenodo set (347k FCC IDs, 1981–2023) has equipment class but **no frequencies**
  and stops mid-2023.
