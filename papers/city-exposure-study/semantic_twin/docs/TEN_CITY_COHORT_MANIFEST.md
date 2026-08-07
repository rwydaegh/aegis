# Ten-city cohort manifest

`config/city_cohort_manifest.json` is the authoritative identity of the next
ten-city campaign:

- Korenmarkt, Prague, Brussels, Madrid, Mexico City, and Tokyo Hachiko are the
  primary semantic-route cohort. Their route is the registered panorama/link
  path, so the route coordinates come from the frozen capture evidence.
- London Trafalgar, Milan Duomo, Krakow Rynek, and Toulouse Capitole are the
  geometric-extension cohort. Their route is a cached Google walking response
  and is not considered present until the cache contains a valid response.
- Times Square is explicitly excluded because the current geometry contains
  mirror-glass reconstruction artefacts and sub-street geometry. It is not the
  tenth site and must not silently re-enter a run.

The manifest intentionally contains no latitude/longitude waypoint arrays. A
panorama route reads positions from the registered station report and link
graph. A street route reads `data/street_routes/{site}_*.json`, which is a
cached response from the Google Routes API. This makes route preparation an
explicit acquisition step and makes a missing cache a visible preflight failure,
not an implicit straight-line fallback.

## Readiness check

From the semantic-twin directory, run:

```bash
python -m semantic_twin.cli.cohort
python -m semantic_twin.cli.cohort --json
```

The command is read-only. It validates the manifest, then reports one row per
included city. `ready` means every required panorama evidence file exists for a
panorama route, or at least one syntactically valid cached route exists for a
street route. It does not assert that semantic material inference, mesh
coverage, or the exposure estimator is ready. Those remain separate campaign
gates.

For a staged checkout, pass the study root explicitly:

```bash
python -m semantic_twin.cli.cohort --root /path/to/semantic_twin --json
```

No command in this utility contacts Google, writes a cache, or manufactures
route coordinates.
