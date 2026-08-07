# Ten-city cohort manifest

`config/city_cohort_manifest.json` is the authoritative identity of the next
ten-city campaign:

> **Current-contract notice.** Comparable-city v2 contains ten intended
> atlas-backed sites with exact cached registered-span pedestrian routes. Nine
> have panorama acquisitions, while Krakow is pending Street View quota. Each
> site must pass input readiness before execution. Times Square remains
> excluded for invalid geometry. See
> [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md) for the
> active production boundary.

- Korenmarkt, Prague, Brussels, Madrid, Mexico City, Tokyo Hachiko, London
  Trafalgar, Milan Duomo, Krakow Rynek, and Toulouse Capitole are the intended
  comparable cohort. Every primary result uses the semantic atlas.
- Every site uses the same `registered_span_street_v1` route contract. The
  endpoints are the furthest pair in its current admitted station report, and
  the route is the exact waypoint-keyed cached Google walking response.
- Times Square is explicitly excluded because the current geometry contains
  mirror-glass reconstruction artefacts and sub-street geometry. It is not the
  tenth site and must not silently re-enter a run.

The manifest intentionally contains no latitude/longitude waypoint arrays. A
registered-span route derives its two waypoints from the admitted station
report, then reads the one exact request-keyed file from
`data/street_routes/{site}_*.json`. This makes route preparation an explicit
acquisition step and makes a missing or stale cache a visible preflight failure,
not an implicit straight-line fallback.

## Readiness check

From the semantic-twin directory, run:

```bash
python -m semantic_twin.cli.cohort
python -m semantic_twin.cli.cohort --json
```

The command is read-only. It validates the manifest, then reports one row per
included city. `ready` means the admitted station report is valid and the exact
cache selected by its current endpoints exists with matching waypoints. It does
not assert that semantic material inference, mesh coverage, or the exposure
estimator is ready. Those remain separate campaign gates.

For a staged checkout, pass the study root explicitly:

```bash
python -m semantic_twin.cli.cohort --root /path/to/semantic_twin --json
```

No command in this utility contacts Google, writes a cache, or manufactures
route coordinates.
