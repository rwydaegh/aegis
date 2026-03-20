# Batch tasks for parallel agents

Small, self-contained tasks for fast AI agents to execute independently. Each touches 1-3 files with a clear deliverable.

## Ground rules

- **You have discretion.** If a task is unnecessary (thing already exists, design doesn't fit, code moved on), say so and skip it. "No, because X" is a valid output. "No, but here's what I did instead" is even better.
- **Read before writing.** Every task assumes you read the relevant files first. If reality contradicts the spec, trust reality.
- **Don't over-build.** Minimum that makes sense. No extra abstractions, no bonus features.
- **Run checks after code changes:** `py -3.12 -m ruff check src/ tests/` and `py -3.12 -m pytest tests/ -m "not slow" -x`.
- **Frozen dataclasses.** Core types (`BodyMesh`, `PropagationPaths`, `DosimetryResult`, `TissueModel`, `Precoder`) are all frozen. You cannot add mutable state. Return new instances if needed.
- **No circular imports.** `result.py` imports from `compliance`. Do not make `compliance` import from `result`.
- **Style:** No em dashes, no semicolons, sentence case headings. See `.claude/rules/docs-style.md`.

---

## Tests

### 1. Test `constants.py`

Create `tests/test_constants.py`. Verify `C_0`, `MU_0`, `EPS_0`, `Z_0` from `src/aegis/constants.py` satisfy `C_0 == 1/sqrt(MU_0 * EPS_0)` and `Z_0 == sqrt(MU_0 / EPS_0)` within float precision (`math.isclose`).

### 2. Test `PropagationPaths.from_powers()`

Create `tests/test_paths.py`. Test that `from_powers(k_hat, power)` produces paths where `paths.power` round-trips to the input powers (within float tolerance). Test single-path input (1D k_hat). Test zero power gives zero psi magnitude. Test that `k_hat` gets normalized.

### 3. Test `Precoder` factories

Create `tests/test_precoder.py`. Read `src/aegis/precoder.py` first to see the actual API. Test `Precoder.mrt(h, P)`: verify `precoder.power` equals `P`, verify shape matches `h`. Test that zero-channel edge case doesn't crash. Test `__post_init__` rejects 2D arrays.

### 4. Test each kernel independently

Create `tests/test_kernels.py`. For levels 0-6, call each kernel function directly (not through `DosimetryEngine`) with synthetic input. Read `src/aegis/kernels/` to understand each function's actual signature (they vary). Assert: correct output shape, non-negativity.

Note: levels 0 and 1 require extra inputs (`A_ab`, `D_max`, `sh_coeffs`). Levels 5-6 require `curvature_H` and `freq_hz`. Read the code.

### 5. Test `cauchy.py` with `compute_projected_area`

Create `tests/test_cauchy.py`. The interesting test is: generate normals and areas for a simple convex body (e.g., an icosahedron approximation of a sphere), compute `A_perp` over many directions using `compute_projected_area` from `projected_area.py`, then verify `mean_projected_area(A_perp)` matches `cauchy_projected_area(total_area)` within a few percent. Testing `cauchy_projected_area` alone is pointless (it's just division by 4).

### 6. Test `fibonacci_sphere`

Add to `tests/test_geometry.py`. Verify `fibonacci_sphere(N)` returns shape `(N, 3)`, all points on the unit sphere (`np.allclose(norms, 1.0)`). For uniformity: check that the z-coordinates are approximately uniformly distributed over [-1, 1] using a KS test or just checking the mean is near 0 and std is near `1/sqrt(3)`.

### 7. Test Cole-Cole at known frequencies

Add to `tests/test_tissue.py`. Use the Cole-Cole model to compute skin properties at 28 GHz. Compare against the hardcoded `SKIN_28GHZ` preset (eps_r=17.0, sigma=25.0). These should roughly agree (within 10-20%, since presets are from literature and Cole-Cole is from the IT'IS database fit). Mark as `@pytest.mark.slow` if it needs the database file.

### 8. Test compliance module

Create `tests/test_compliance.py`. Test `is_compliant_sab(9.0)` returns True, `is_compliant_sab(11.0)` returns False. Same for `is_compliant_sar`. Verify `ICNIRP_2020` constants: `sab_peak == 10.0`, `sar_wb == 0.08`, `averaging_area_cm2 == 4.0`.

### 9. Test viewer config deep merge edge cases

In `tests/test_viewer_config.py`, add tests: nested override preserves unmentioned sibling keys, list values get replaced (not appended), empty override dict is a no-op. Read `src/aegis/viewer/config.py` to understand the merge function first.

---

## CLI improvements

### 10. Add `--version` flag

In `src/aegis/viewer/__main__.py`, add `parser.add_argument("--version", action="version", version=...)`. Import `__version__` from `aegis`.

### 11. Add `--port` flag

In `src/aegis/viewer/__main__.py`, add `--port` argument (int). When provided, override `config["server"]["port"]` before server launch. Read the file to see how config flows into the server.

### 12. Add `--level` flag

In `src/aegis/viewer/__main__.py`, add `--level` argument (int, 0-8). Override `config["dosimetry"]["default_level"]`.

### 13. Create `src/aegis/__main__.py`

Make `py -3.12 -m aegis` work. Print version, one-line description, usage hint for viewer. Under 20 lines. Include a `main()` function so it can be used as a console script entry point.

### 14. Add `[project.scripts]` to `pyproject.toml`

Add `[project.scripts]` with `aegis = "aegis.__main__:main"`. Depends on task 13 existing. If `__main__.py` doesn't exist yet, create it (combine with task 13).

---

## API additions (core library)

### 15. Add `DosimetryResult.to_dict()` and `to_json()`

In `src/aegis/result.py`, add both methods together (no reason to split them). `to_dict()` returns all fields as a plain dict, converting numpy arrays via `.tolist()`, skipping `None` fields. `to_json(indent=2)` calls `to_dict()` and returns `json.dumps(...)`.

### 16. Add `PropagationPaths.__len__`

In `src/aegis/paths.py`, add `def __len__(self) -> int: return self.n_paths`. One-liner. Makes `len(paths)` work.

### 17. Add `PropagationPaths.subset(indices)`

In `src/aegis/paths.py`, add a method that returns a new `PropagationPaths` with only the paths at given indices. Example use: `los_paths = paths.subset(np.where(paths.is_los)[0])`. Index all 5 arrays with `self.k_hat[indices]`, etc.

### 18. Add `PropagationPaths.total_power` property

Return `float(np.sum(self.power))`. One-liner.

### 19. Add `DosimetryResult.peak_triangle_index` property

Return `int(np.argmax(self.sab))`. One-liner. Locates the hotspot triangle.

### 20. Add `DosimetryResult.mean_sab` property

Return `float(np.mean(self.sab))`. One-liner.

### 21. Add `BodyMesh.center` property

Return `(bmin + bmax) / 2` using the existing `bounding_box` property. One-liner.

### 22. Add `BodyMesh.height` property

Return `bmax[2] - bmin[2]` (Z-extent). AEGIS uses Z-up in Python.

---

## Module hygiene

### 23. `compliance/__init__.py` missing `__all__`

Add `__all__ = ["ICNIRPLimits", "ICNIRP_2020", "is_compliant_sab", "is_compliant_sar"]`.

### 24. `integration/__init__.py` missing `__all__`

Read `src/aegis/integration/differt.py` and add `__all__` listing the public functions.

### 25. Export `plot_dashboard` from `viz/__init__.py`

`src/aegis/viz/dashboard.py` defines `plot_dashboard` but `viz/__init__.py` only exports `plot_heatmap` and `plot_level_comparison`. Add the missing import and `__all__` entry.

---

## Compliance module

### 26. Add `margin_db()`

In `src/aegis/compliance/__init__.py`, add a function: compliance margin in dB = `10 * log10(limit / peak_sab)`. Positive means compliant. Use `import math` and `math.log10` (the module currently doesn't import numpy). Add a test in `tests/test_compliance.py`.

### 27. Add `summary_text()`

In `src/aegis/compliance/__init__.py`, add a function that takes primitive values (peak_sab, sar_wb=None) and returns a formatted multi-line string: peak S_ab, ICNIRP limit, margin in dB, PASS/FAIL. Do NOT accept a `DosimetryResult` parameter (that would create a circular import since `result.py` already imports from `compliance`). Plain text output, no external dependencies.

---

## Visualization

### 28. Add `plot_frequency_sweep`

Create a new function in `src/aegis/viz/` (new file or add to existing). Signature: `plot_frequency_sweep(freqs_hz, peak_sab_values, limit=10.0)`. X-axis in GHz, Y-axis in W/m^2 (log scale). Horizontal dashed red line at limit. Matplotlib only. Add to `viz/__init__.py` exports.

### 29. Add `plot_tissue_spectrum`

New function in `src/aegis/viz/`. Signature: `plot_tissue_spectrum(tissue_name, freq_min_hz, freq_max_hz, n_points=200)`. Use the Cole-Cole model + IT'IS database to compute eps_r and sigma across frequency. Two y-axes: permittivity left, conductivity right. Read `src/aegis/tissue/cole_cole.py` and `database.py` first. This function will require the IT'IS database at runtime. Add to exports.

---

## Viewer API

### 30. Add `GET /api/health`

In `src/aegis/viewer/server.py`, return `{"status": "ok", "version": "<version>"}`.

### 31. Add `GET /api/levels`

Return JSON array: `[{"level": 0, "name": "Bound", "description": "..."}, ...]` for all 9 levels. Read `src/aegis/kernels/` for accurate names and descriptions.

### 32. Add `GET /api/tissues`

Return available tissue presets as JSON. Read `src/aegis/tissue/dielectric.py` for preset names (SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ) and their eps_r, sigma, freq_hz values.

### 33. Add `GET /api/body/info`

Return body metadata as JSON: n_triangles, total_area, bounding_box, name. No binary data. Read from the module-level `_cache` dict.

### 34. Add request validation to `/api/compute`

In the compute endpoint, validate incoming JSON before processing. Check `power_dbm` is in a sane range, `level` is in the allowed set, `n_paths` is in the allowed set. Return HTTP 400 with `{"error": "description"}` instead of letting bad input produce a 500.

---

## Caching

### 35. Memoize `fibonacci_sphere`

In `src/aegis/geometry/projected_area.py`. The function is pure (deterministic for given N). Cache with a module-level dict (`_fib_cache = {}`) since the numpy array output isn't hashable for `lru_cache`. Return a read-only view (`result.flags.writeable = False`) to prevent cache corruption.

### 36. Cache `TissueModel.from_database()` lookups

In `src/aegis/tissue/dielectric.py`. The method calls `get_tissue_properties(tissue_name, freq_hz)` which reads an SQLite database. Cache at the module level keyed on `(tissue_name, freq_hz)`. Don't try to `lru_cache` the classmethod directly (the `cls` argument and `Path` argument make it awkward). Cache the inner lookup result instead.

---

## Configuration presets

### 37. Create `configs/indoor_office.json`

Read `configs/default.json` and `configs/README.md` first to understand the actual config structure and how scenarios work. Create a scenario config for an indoor office: 28 GHz, 23 dBm power, appropriate defaults. Only override keys that differ from defaults. Do NOT invent config keys that don't exist (e.g., antenna position is set interactively in the viewer, not in config).

### 38. Create `configs/outdoor_urban.json`

Same approach. 3.5 GHz, 43 dBm. Read the config structure first. Only use keys that actually exist.

### 39. Create `configs/mmwave_close.json`

60 GHz, 10 dBm. Read the config structure first.

---

## Documentation

### 40. Create `docs/user_guide/quickstart.md`

A quickstart with copy-pasteable Python: install AEGIS, create synthetic BodyMesh data (or load STL), create `PropagationPaths` with `from_powers()`, compute at level 2, print peak S_ab. Read the actual API first. Add to `mkdocs.yml` nav.

Follow `.claude/rules/docs-style.md` strictly: no em dashes, sentence case headings, concise, no AI buzzwords.

### 41. Create `docs/user_guide/faq.md`

Answer (with accurate info from reading the code):
- Which fidelity level should I use?
- How do I add a custom tissue type?
- What coordinate system does the viewer use? (Z-up in Python, Y-up in Three.js)
- How do I export dosimetry results?

Add to `mkdocs.yml` nav. Follow docs style guide.

### 42. Create `docs/user_guide/troubleshooting.md`

Common errors: missing mesh data, DiffeRT not installed, port in use, config issues. Add to nav. Follow style guide.

### 43. Create `docs/developer_guide/adding_a_kernel.md`

Read the existing kernels first. Document the actual pattern: file naming, function signature, registration in `__init__.py`, dispatch in `engine.py`, testing. Follow style guide.

---

## Project boilerplate

### 44. Create `CONTRIBUTING.md`

Under 50 lines. Dev setup, how to test, lint, format. Key rules from CLAUDE.md rewritten for human contributors. Follow style guide.

### 45. Create `Makefile`

Common commands using `py -3.12`. Targets: test, test-all, lint, format, docs, viewer. All `.PHONY`. This project runs on Windows with Git Bash, so `make` works but keep commands cross-platform.

### 46. Create `CITATION.cff`

Citation File Format. Read `git log` for author name(s), `__init__.py` for version. Title: "AEGIS". Include DOI placeholder.

### 47. Create `.github/ISSUE_TEMPLATE/bug_report.md`

Standard template with YAML frontmatter. Sections: Description, Steps to reproduce, Expected vs actual behavior, Environment.

### 48. Create `.github/ISSUE_TEMPLATE/feature_request.md`

Standard template. Sections: Description, Use case, Proposed solution, Alternatives.
