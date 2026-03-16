# Testing

## Test categories

AEGIS uses four categories of tests:

- **Golden tests** reproduce monograph tables exactly. Expected values live in `tests/golden/` as JSON files.
- **Property tests** check physics invariants using Hypothesis. These hold for any valid input: Sab >= 0, energy conservation, ReLU bound.
- **E2E tests** run the full pipeline from mesh loading through compliance checking.
- **Regression tests** compare against the Mie theory analytical solution. This is the CI canary.

## Running tests

```bash
pytest tests/ -m "not slow" -x   # fast tests only (~5s)
pytest tests/                     # all tests (~30s, needs mesh data)
pytest tests/ -k "mie"           # just the Mie regression
```

## Mesh data

Tests marked `@pytest.mark.slow` need STL files in `AEGIS_DATA_DIR` (defaults to `../../data`). These are skipped automatically if the data directory is absent.
