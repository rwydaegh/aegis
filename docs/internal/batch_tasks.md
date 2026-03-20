# Batch tasks for parallel agents

These are small, self-contained tasks intended for fast AI agents to execute independently. Each task touches 1-3 files and has a clear deliverable.

## Ground rules for executing agents

- **You have discretion.** If a task turns out to be unnecessary (the thing already exists, the design doesn't fit, the code has moved on), say so and skip it. "No, because X" is a valid output.
- **Read before writing.** Every task assumes you will read the relevant files first. If reality contradicts the spec, trust reality.
- **Don't over-build.** Do the minimum that makes sense. No extra abstractions, no bonus features.
- **Run tests.** After any code change: `py -3.12 -m ruff check src/ tests/` and `py -3.12 -m pytest tests/ -m "not slow" -x`.
- **Frozen dataclasses.** Many core types are frozen. You cannot add mutable state. If you need to return modified data, return a new instance.

---

## 1. `compliance/__init__.py` missing `__all__`

Add `__all__ = ["ICNIRPLimits", "ICNIRP_2020", "is_compliant_sab", "is_compliant_sar"]` to `src/aegis/compliance/__init__.py`. The module defines these public symbols but doesn't export them.

## 2. `integration/__init__.py` missing `__all__`

Add `__all__` to `src/aegis/integration/__init__.py` listing the public functions from `differt.py`. Read `differt.py` first to see what makes sense to export.

## 3. Test `constants.py`

Create `tests/test_constants.py`. Verify that `C_0`, `MU_0`, `EPS_0`, `Z_0` satisfy the physical relationships: `C_0 == 1/sqrt(MU_0 * EPS_0)` and `Z_0 == sqrt(MU_0 / EPS_0)` within float precision. Use `np.isclose` or `math.isclose`.

## 4. Test `PropagationPaths.from_powers()` factory

Create `tests/test_paths.py`. Verify that `from_powers(k_hat, power)` produces paths where `paths.power` matches the input powers. Verify shapes. Verify single-path input (1D k_hat) works. Verify that zero power produces zero psi magnitude.

## 5. Test `Precoder` factories

Create `tests/test_precoder.py`. Read `src/aegis/precoder.py` first. Test that `Precoder.mrt()` returns a precoder whose vector is conjugate-transpose of the channel, normalized to unit power. Test shape and norm constraints.

## 6. Test each kernel function independently

Create `tests/test_kernels.py`. For each of levels 0-6, call the kernel function directly (not through `DosimetryEngine`) with a minimal synthetic input (e.g., 3 triangles, 1 path). Assert: output shape matches number of triangles, all values non-negative, higher levels are not identical to lower levels (they incorporate more physics).

Read `src/aegis/kernels/` first to understand each function's signature.

## 7. Test `geometry/cauchy.py`

Create `tests/test_cauchy.py`. Read `src/aegis/geometry/cauchy.py` first. For a synthetic convex body (e.g., unit cube vertices), verify the Cauchy projected area formula returns the known value (for a convex body: `total_surface_area / 4`).

## 8. Test Fibonacci sphere uniformity

Add tests to `tests/test_geometry.py` (or create `tests/test_projected_area.py`). Verify `fibonacci_sphere(N)` returns exactly N points, all on the unit sphere (norm == 1). For N >= 100, verify rough uniformity: mean pairwise distance should decrease as N increases.

## 9. Test Cole-Cole model at known frequencies

Add tests to `tests/test_tissue.py`. Use the Cole-Cole model (`src/aegis/tissue/cole_cole.py`) to compute skin permittivity and conductivity at 10 GHz and 28 GHz. Compare against IT'IS published values (look them up in the database module or the monograph). Tolerance: 5% for a sanity check.

## 10. Add `--version` flag to viewer CLI

In `src/aegis/viewer/__main__.py`, add `parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")` where `__version__` is imported from `aegis`.

## 11. Add `--port` flag to viewer CLI

In `src/aegis/viewer/__main__.py`, add a `--port` argument. When provided, override `config["server"]["port"]` before launching the Flask server. Read the file first to see how config flows into the server.

## 12. Add `--level` flag to viewer CLI

In `src/aegis/viewer/__main__.py`, add a `--level` argument (int, choices 0-8). When provided, override `config["dosimetry"]["default_level"]`. Read the file to see how config is built before passing to the server.

## 13. Create `src/aegis/__main__.py`

Make `py -3.12 -m aegis` work. Print the version, the one-line project description ("AEGIS computes absorbed power density on human bodies in wireless environments"), and usage hints (`py -3.12 -m aegis.viewer` to launch the viewer). Keep it under 20 lines.

## 14. Add `DosimetryResult.to_dict()` method

In `src/aegis/result.py`, add a `to_dict()` method that returns all fields as a plain dict. Convert numpy arrays to nested lists via `.tolist()`. Skip fields that are `None`. This enables JSON serialization of results.

## 15. Add `DosimetryResult.to_json()` method

Depends on task 14. Add `to_json(indent=2)` that calls `to_dict()` and returns `json.dumps(...)`. Import json at the top of the file.

## 16. Add `PropagationPaths.__len__`

In `src/aegis/paths.py`, add `__len__` returning `self.n_paths`. This is a one-liner but makes `len(paths)` work naturally.

## 17. Add `BodyMesh.center` property

In `src/aegis/geometry/mesh.py`, add a `center` property returning the midpoint of the bounding box: `(bmin + bmax) / 2`. The `bounding_box` property already exists.

## 18. Add `plot_frequency_sweep`

In `src/aegis/viz/`, add a function `plot_frequency_sweep(freqs_hz, peak_sab_values, limit=10.0)`. Line plot: X-axis in GHz, Y-axis in W/m^2 (log scale). Horizontal dashed red line at the ICNIRP limit. Matplotlib only. Add to `__init__.py` exports.

## 19. Add `plot_tissue_spectrum`

In `src/aegis/viz/`, add a function `plot_tissue_spectrum(tissue_name, freq_min_hz, freq_max_hz, n_points=200)`. Use the Cole-Cole model to compute eps_r and sigma across the frequency range. Two y-axes: permittivity (left), conductivity (right). Matplotlib. Add to `__init__.py` exports.

Read `src/aegis/tissue/cole_cole.py` and `src/aegis/tissue/database.py` first to understand how to get Cole-Cole parameters for a named tissue.

## 20. Add `compliance.margin_db()`

In `src/aegis/compliance/__init__.py`, add:
```python
def margin_db(peak_sab: float, limits: ICNIRPLimits = ICNIRP_2020) -> float:
    """Compliance margin in dB. Positive = compliant."""
    return 10.0 * np.log10(limits.sab_peak / peak_sab)
```
Add a test for it: margin_db(5.0) should be ~3.01 dB, margin_db(20.0) should be ~-3.01 dB.

## 21. Add `compliance.summary_table()`

In `src/aegis/compliance/__init__.py`, add a function that takes a `DosimetryResult` and returns a formatted multi-line string showing: peak S_ab, ICNIRP limit, margin in dB, PASS/FAIL. If SAR is available, include that too. Plain text, no dependencies.

## 22. Create `configs/indoor_office.json`

A viewer scenario config: single antenna at (0, 3, 0) in Z-up coords (ceiling height), 28 GHz, 23 dBm EIRP. Set appropriate body position, voxel settings for an indoor scene. Read `configs/default.json` first to understand the config structure. Only override what differs from defaults.

## 23. Create `configs/outdoor_urban.json`

Viewer scenario config: antenna at (50, 0, 10) in Z-up (macro cell 50m away, 10m height), 3.5 GHz, 43 dBm. Body at origin. Override only what differs from defaults.

## 24. Create `configs/mmwave_close.json`

Viewer scenario: antenna at (0.5, 0, 2) in Z-up, 60 GHz, 10 dBm. Close-range mmWave exposure. Use `SKIN_60GHZ` tissue preset if the config supports tissue selection. Override only what differs.

## 25. Validate `DosimetryEngine.compute()` inputs

In `src/aegis/engine.py`, at the top of `compute()`, add validation:
- `level` must be 0-8 (raise `ValueError`)
- `body.n_triangles` must be >= 1
- `paths.n_paths` must be >= 1
- For levels 7-8, `precoder` must not be None

Read the existing code first. Some of these checks might already exist in the kernel dispatch logic.

## 26. Add request validation to `/api/compute`

In `src/aegis/viewer/server.py`, in the compute endpoint, validate incoming JSON:
- `power_dbm` in [-30, 60] range
- `level` in allowed set (read from config)
- `n_paths` in allowed set (read from config)

Return HTTP 400 with a JSON error body `{"error": "description"}` instead of letting it crash to 500.

## 27. Add `GET /api/health` endpoint

In `src/aegis/viewer/server.py`, add a health check endpoint returning `{"status": "ok", "version": "<aegis version>"}`. Import `__version__` from aegis.

## 28. Add `GET /api/levels` endpoint

In `src/aegis/viewer/server.py`, add an endpoint returning a JSON array describing the 9 fidelity levels: `[{"level": 0, "name": "Bound", "description": "..."}, ...]`. Read `src/aegis/kernels/` to get accurate names and one-line descriptions.

## 29. Add `GET /api/tissues` endpoint

In `src/aegis/viewer/server.py`, add an endpoint returning available tissue presets as JSON. Read `src/aegis/tissue/dielectric.py` for the preset names and their properties.

## 30. Add `GET /api/body/info` endpoint

In `src/aegis/viewer/server.py`, add an endpoint returning body metadata as JSON: `{"n_triangles": ..., "total_area": ..., "bounding_box": [[xmin,ymin,zmin],[xmax,ymax,zmax]], "name": ...}`. No binary data. Read from `_cache`.

## 31. Add `[project.scripts]` entry to `pyproject.toml`

Add a console script entry point so `aegis` works after `pip install`. This requires that `src/aegis/__main__.py` exists (task 13) with a `main()` function. Add: `[project.scripts]` with `aegis = "aegis.__main__:main"`.

## 32. Create `CONTRIBUTING.md`

Minimal contributing guide: how to set up dev environment (`pip install -e ".[dev]"`), run tests, lint, format, and the key testing rules (never weaken assertions, Mie test is the canary). Under 50 lines. Pull info from CLAUDE.md but write for human contributors.

## 33. Create `Makefile`

Aliases for common commands using `py -3.12`:
- `make test` - run fast tests
- `make test-all` - run all tests
- `make lint` - ruff check
- `make format` - ruff format
- `make docs` - mkdocs serve
- `make viewer` - launch viewer

Use `.PHONY` for all targets.

## 34. Add `@functools.lru_cache` to `TissueModel.from_database()`

In `src/aegis/tissue/dielectric.py`, read the `from_database` classmethod. If it reads from disk or does computation that's a pure function of its arguments, wrap it with `@functools.lru_cache`. Note: the method might take unhashable arguments, in which case use a module-level dict cache instead.

## 35. Memoize `fibonacci_sphere`

In `src/aegis/geometry/projected_area.py`, read the `fibonacci_sphere` function. If it's a pure function of N, add caching (lru_cache or module-level dict). The function always returns the same points for the same N, so this avoids redundant recomputation.

## 36. Create `docs/user_guide/quickstart.md`

A 20-line quickstart: install AEGIS, create a BodyMesh from synthetic data (or load STL), create PropagationPaths with `from_powers()`, run `DosimetryEngine.compute()` at level 2, print peak S_ab. Must be copy-pasteable Python. Read the actual API first to get the code right.

Also add it to the mkdocs nav. Read `mkdocs.yml` to see how pages are organized.

## 37. Create `docs/user_guide/faq.md`

Answer these questions (read the code to get accurate answers):
- Which fidelity level should I use?
- How do I add a custom tissue type?
- What coordinate system does the viewer use?
- How do I export dosimetry results?
- What does each fidelity level add?

Add to mkdocs nav.

## 38. Create `docs/user_guide/troubleshooting.md`

Common errors and fixes:
- Missing mesh data (AEGIS_DATA_DIR not set)
- DiffeRT not installed (levels 7-8 or RT viewer)
- Port already in use (viewer)
- Config key typos (silent failures)

Add to mkdocs nav.

## 39. Create `docs/developer_guide/adding_a_kernel.md`

Step-by-step guide for adding a new fidelity level kernel:
1. Create `src/aegis/kernels/levelN_name.py` following `_base.py` pattern
2. Register in `kernels/__init__.py`
3. Add dispatch case in `engine.py`
4. Add test in `tests/test_kernels.py`
5. Add to viewer dropdown in config

Read the existing kernels first to describe the actual pattern accurately.

## 40. Add docstrings to `geometry/__init__.py` exports

Read `src/aegis/geometry/__init__.py`. For each exported function/class that lacks a docstring, add a one-line docstring. If they all already have docstrings, skip this task.

## 41. Create `CITATION.cff`

Create a Citation File Format file in the project root. Fields: title ("AEGIS: Absorbed Power Density on Human Bodies"), authors (read git log for author names), version (read from `__init__.py`), license, DOI placeholder. Follow the CFF spec.

## 42. Create `.github/ISSUE_TEMPLATE/bug_report.md`

Standard GitHub bug report template with sections: Description, Steps to reproduce, Expected behavior, Actual behavior, Environment (OS, Python version, AEGIS version). Use YAML frontmatter for the template metadata.

## 43. Create `.github/ISSUE_TEMPLATE/feature_request.md`

Standard feature request template: Description, Use case, Proposed solution, Alternatives considered.

## 44. Add `DosimetryResult.peak_triangle_index` property

In `src/aegis/result.py`, add a property returning `int(np.argmax(self.sab))`. Useful for locating the hotspot on the body mesh.

## 45. Add `DosimetryResult.mean_sab` property

Return `float(np.mean(self.sab))`. Useful alongside peak for understanding distribution shape.

## 46. Add `BodyMesh.height` property

Return the Z-extent of the bounding box: `bmax[2] - bmin[2]`. AEGIS uses Z-up coordinates in Python. Read `mesh.py` to confirm coordinate conventions.

## 47. Test viewer config deep merge

In `tests/test_viewer_config.py`, add tests for edge cases of config deep merge: nested override, list replacement (not append), missing keys preserved from defaults, empty override dict is no-op. Read `src/aegis/viewer/config.py` to understand the merge function.

## 48. Test compliance module

Create `tests/test_compliance.py`. Test `is_compliant_sab` and `is_compliant_sar` with values above and below limits. Test the `ICNIRP_2020` constants match the published values (sab_peak=10.0 W/m^2, sar_wb=0.08 W/kg, averaging_area=4.0 cm^2).

## 49. Add `PropagationPaths.subset(indices)` method

In `src/aegis/paths.py`, add a method that returns a new `PropagationPaths` with only the paths at the given indices. Useful for filtering (e.g., LOS-only paths): `los_paths = paths.subset(np.where(paths.is_los)[0])`. Since the dataclass is frozen, this returns a new instance.

## 50. Add `PropagationPaths.total_power` property

Return `float(np.sum(self.power))`. The total incident power density from all paths combined.
