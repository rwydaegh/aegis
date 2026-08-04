"""Screen candidate sites for the ten-city rollout on Street View metadata alone.

Screening has to be cheap, because its whole purpose is to decide where the
expensive acquisition goes. This script never downloads a tile and never
downloads an image. It walks the Street View link graph outwards from each
candidate centre with metadata requests, probes points the walk never visited,
and writes one row per candidate to ``outputs/city_screening/screening.json``
with a markdown table beside it.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python screen_cities.py --out outputs/city_screening

Set ``GOOGLE_API_KEY`` first. Request counts are reported per candidate and in
total, because the study has to be able to account for what it spent.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.scene.site_config import google_api_key  # noqa: E402
from semantic_twin.screening import (  # noqa: E402
    DEFAULT_MAX_PANORAMAS,
    DEFAULT_SCREEN_RADIUS_M,
    Candidate,
    rank,
    screen,
)

CREATE_SESSION = "https://tile.googleapis.com/v1/createSession"
METADATA = "https://tile.googleapis.com/v1/streetview/metadata"

# Candidate sites. Two are already acquired and are screened anyway, as the only
# way to know what the numbers mean: Ghent is a car track through a square and
# Milan is a trekker capture of one, and the screening has to reproduce that
# difference before any of the other rows can be believed. The rest span built
# forms on purpose, since an exposure distribution over eight identical arcaded
# piazzas would describe one building type rather than a population.
CANDIDATES = [
    Candidate(
        "korenmarkt", "Korenmarkt", "Belgium", 51.055, 3.722, "medieval brick square, car track capture, acquired"
    ),
    Candidate(
        "milan_duomo",
        "Piazza del Duomo",
        "Italy",
        45.4642,
        9.19,
        "monumental stone piazza, cathedral pinnacle field, acquired",
    ),
    Candidate(
        "brussels_grandplace",
        "Grand-Place",
        "Belgium",
        50.84673,
        4.35247,
        "fully enclosed guildhall square, gilded stone, high aspect ratio",
    ),
    Candidate(
        "madrid_plazamayor",
        "Plaza Mayor",
        "Spain",
        40.41552,
        -3.70744,
        "closed arcaded rectangle, uniform painted render, four gated entries",
    ),
    Candidate(
        "krakow_rynek",
        "Rynek Glowny",
        "Poland",
        50.06166,
        19.93727,
        "very large medieval square with a free-standing hall in the middle",
    ),
    Candidate(
        "prague_staromestske",
        "Staromestske namesti",
        "Czechia",
        50.08758,
        14.42134,
        "irregular medieval square, gothic towers, plaster and stone mix",
    ),
    Candidate(
        "venice_sanmarco",
        "Piazza San Marco",
        "Italy",
        45.43418,
        12.33875,
        "car-free trapezoid, brick campanile, arcaded on three sides",
    ),
    Candidate(
        "london_trafalgar",
        "Trafalgar Square",
        "United Kingdom",
        51.508,
        -0.12805,
        "open terraced square, Portland stone, traffic on one side",
    ),
    Candidate(
        "toulouse_capitole",
        "Place du Capitole",
        "France",
        43.60447,
        1.44422,
        "brick city, single monumental facade, otherwise low arcades",
    ),
    Candidate(
        "lisbon_comercio",
        "Praca do Comercio",
        "Portugal",
        38.70751,
        -9.13646,
        "three-sided square open to water, uniform arcade, tiled render",
    ),
    Candidate("amsterdam_dam", "Dam", "Netherlands", 52.37307, 4.89252, "narrow-fronted brick square crossed by trams"),
    Candidate(
        "vienna_stephansplatz",
        "Stephansplatz",
        "Austria",
        48.20849,
        16.37301,
        "cathedral standing in the middle, very narrow residual square",
    ),
    Candidate(
        "berlin_alexanderplatz",
        "Alexanderplatz",
        "Germany",
        52.52194,
        13.41319,
        "post-war modernist plaza, curtain wall and concrete, very open",
    ),
    Candidate(
        "rome_navona",
        "Piazza Navona",
        "Italy",
        41.89921,
        12.47308,
        "long narrow stadium plan, baroque render, fountains",
    ),
    Candidate(
        "copenhagen_kongensnytorv",
        "Kongens Nytorv",
        "Denmark",
        55.67854,
        12.58527,
        "circular plaza, mixed brick and stucco, northern latitude sun",
    ),
    Candidate(
        "barcelona_placareial",
        "Placa Reial",
        "Spain",
        41.37977,
        2.17503,
        "small enclosed arcaded courtyard, palms, very high enclosure",
    ),
    Candidate(
        "istanbul_sultanahmet",
        "Sultanahmet Meydani",
        "Turkey",
        41.00553,
        28.97688,
        "wide open park square between two large domed masses",
    ),
    Candidate(
        "zagreb_jelacic",
        "Trg bana Jelacica",
        "Croatia",
        45.81311,
        15.97719,
        "tram-crossed square, mixed nineteenth century and modern fronts",
    ),
    Candidate(
        "newyork_timessquare",
        "Times Square",
        "United States",
        40.75797,
        -73.98554,
        "deep glass and LED canyon, tallest aspect ratio in the set",
    ),
    Candidate(
        "tokyo_hachiko",
        "Hachiko square, Shibuya",
        "Japan",
        35.65947,
        139.70046,
        "dense glass canyon with a scramble crossing, heavy signage",
    ),
    Candidate(
        "mexico_zocalo",
        "Plaza de la Constitucion",
        "Mexico",
        19.43264,
        -99.13321,
        "very large open plaza, volcanic stone, low surrounding blocks",
    ),
    Candidate(
        "melbourne_federation",
        "Federation Square",
        "Australia",
        -37.81796,
        144.96907,
        "faceted modern facades, sandstone and zinc, southern hemisphere",
    ),
    Candidate(
        "singapore_raffles",
        "Raffles Place",
        "Singapore",
        1.28381,
        103.85152,
        "tropical high-rise financial core, glass towers around a small park",
    ),
    Candidate(
        "capetown_greenmarket",
        "Greenmarket Square",
        "South Africa",
        -33.92418,
        18.42003,
        "small cobbled market square, low painted facades",
    ),
]


class MapTilesMetadata:
    """One Map Tiles Street View session, used for metadata lookups only.

    A single session token is reused for every request in the run, and the
    connection pool is a plain opener so that repeated lookups do not each pay
    for a fresh TLS handshake.
    """

    def __init__(self, api_key: str, *, tries: int = 4, timeout_s: float = 30.0) -> None:
        self.api_key = api_key
        self.tries = tries
        self.timeout_s = timeout_s
        self.requests = 0
        self.opener = urllib.request.build_opener()
        body = json.dumps({"mapType": "streetview", "language": "en-US"}).encode()
        request = urllib.request.Request(
            f"{CREATE_SESSION}?{urllib.parse.urlencode({'key': api_key})}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        self.session = json.loads(self.opener.open(request, timeout=timeout_s).read())["session"]
        self.requests += 1

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        params = dict(params, session=self.session, key=self.api_key)
        url = f"{METADATA}?{urllib.parse.urlencode(params)}"
        last: Exception | None = None
        for attempt in range(self.tries):
            self.requests += 1
            try:
                with self.opener.open(url, timeout=self.timeout_s) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return {}
                if exc.code < 500 and exc.code != 429:
                    raise RuntimeError(f"Street View metadata HTTP {exc.code}") from exc
                last = exc
            except OSError as exc:
                last = exc
            time.sleep(1.0 * (attempt + 1))
        raise RuntimeError("Street View metadata request failed") from last

    def by_pano_id(self, pano_id: str) -> dict[str, Any]:
        return self._get({"panoId": pano_id})

    def by_location(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]:
        return self._get({"lat": lat, "lng": lon, "radius": int(round(radius_m))})


def markdown_table(rows: list[dict[str, Any]]) -> str:
    """Render the ranked screening rows as a markdown table."""
    header = (
        "| Rank | Site | Country | Panoramas | Dates | Walk date | Walk panoramas | Median spacing | Span | Azimuth | Coverage | Passes | Newest usable walk | Requests |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    lines = []
    for row in rows:
        spacing = "n/a" if row["walk_spacing_m"] is None else f"{row['walk_spacing_m']:.1f} m"
        newest = row["recent_walk"]
        recent = "none" if newest is None else f"{newest['date']}, {newest['walk_count']} panoramas"
        lines.append(
            f"| {row['rank']} | {row['name']} | {row['country']} | {row['panorama_count']} | {row['distinct_dates']} | "
            f"{row['walk_date'] or 'n/a'} | {row['walk_count']} | {spacing} | {row['walk_span_m']:.0f} m | "
            f"{row['walk_azimuth_spread'] * 100:.0f}% | {row['walk_coverage'] * 100:.0f}% | "
            f"{'yes' if row['connected'] else 'no'} | {recent} | {row['requests']} |"
        )
    return header + "\n".join(lines) + "\n"


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("outputs/city_screening"))
    parser.add_argument("--radius-m", type=float, default=DEFAULT_SCREEN_RADIUS_M)
    parser.add_argument("--max-panoramas", type=int, default=DEFAULT_MAX_PANORAMAS)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--only", nargs="*", default=None, help="Screen only these candidate keys")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    candidates = [c for c in CANDIDATES if args.only is None or c.key in args.only]
    if not candidates:
        print("No candidate matched --only", file=sys.stderr)
        return 2

    source = MapTilesMetadata(google_api_key())
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        started = time.time()
        row = screen(
            source,
            candidate,
            radius_m=args.radius_m,
            max_panoramas=args.max_panoramas,
            workers=args.workers,
        )
        row["seconds"] = round(time.time() - started, 1)
        rows.append(row)
        spacing = "n/a" if row["walk_spacing_m"] is None else f"{row['walk_spacing_m']:.1f} m"
        print(
            f"[screen] {candidate.key:26s} panoramas={row['panorama_count']:4d} dates={row['distinct_dates']:2d} "
            f"walk={row['walk_count']:4d} on {str(row['walk_date']):8s} spacing={spacing:>7s} "
            f"span={row['walk_span_m']:5.0f} m azim={row['walk_azimuth_spread'] * 100:3.0f}% cover={row['walk_coverage'] * 100:3.0f}% ok={str(row['connected']):5s} "
            f"recent={str(row['recent_walk']['date'] if row['recent_walk'] else 'none'):8s} "
            f"requests={row['requests']:4d} {row['seconds']:.1f}s",
            flush=True,
        )

    ranked = rank(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    document = {
        "generator": "semantic_twin/screen_cities.py",
        "screen_radius_m": args.radius_m,
        "max_panoramas": args.max_panoramas,
        "total_metadata_requests": source.requests,
        "candidates_screened": len(rows),
        "rows": ranked,
    }
    (args.out / "screening.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "screening_table.md").write_text(markdown_table(ranked), encoding="utf-8")
    print(f"[done] {len(rows)} candidates, {source.requests} metadata requests -> {args.out / 'screening.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
