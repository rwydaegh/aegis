# Handoff: the materials package

Written 2026-08-04, at the end of the wave that built `semantic_twin/materials/`.
Nothing here is committed. The tree is importable and the tests are green.

The rule that governed the whole wave: `tests/golden/` pins 10,249 traced scalars
at rtol 1e-12, captured before the refactor. Structure moved, physics did not.
No float literal, operation order or RNG draw order was changed, and none of the
findings in `docs/BUGS.md` were fixed, including the ones sitting in files this
wave owns.

## What was completed

`semantic_twin/materials/` is a package, split along one line.

| File | What it holds |
| --- | --- |
| `itu.py` | ITU-R P.2040-4 Table 3 rows, the power law, the uncertainty multiplier |
| `roughness.py` | The Rayleigh closure, the RMS height priors, the two reduction rules |
| `catalogue.py` | `MaterialSpec`, the named materials, `MaterialTable`, `load_table` |
| `binding.py` | `SurfaceBinding`, `Provenance`, the orientation rule |
| `evidence.py` | The three image routes that produce a binding |
| `posterior.py` | The draw-per-face route, and `sample_face_materials` |
| `stack.py` | Facade layers, the transfer matrix, the posterior power mixture |
| `foliage.py` | The canopy as a participating medium |
| `masonry/` | `wall.py`, `floquet.py`, `rcwa.py`, `kirchhoff.py` |

Deleted, each replaced by a shim: `semantic_twin/materials.py` (name clash with
the package), `masonry.py`, `rcwa.py`, `floquet.py`, `kirchhoff.py`, `foliage.py`.

### The line between a material and a surface that has one

This was the question the wave existed to answer, and it is drawn at a file
boundary.

- A **material** is a recipe. `MaterialSpec` names one ITU row and one roughness
  class. No frequency, no triangle. Two squares in two cities that both show
  brick share one spec object. Lives in `catalogue.py`.
- A **material evaluated** is `MaterialTable`: those specs resolved at one
  carrier into permittivity and RMS height arrays. Still no triangles. Same file.
- A **surface that has a material** is `SurfaceBinding`: triangles, the class each
  one carries, its area, and where its class came from. It owns no permittivity
  at all. Lives in `binding.py`.

They meet at exactly one place, the class index. `face_class` indexes the same
tuple `permittivity` does. That shared index is the whole contract, and
`SurfaceBinding.evaluate(config_dir, frequency_hz)` is the only crossing.

The old names were backwards, which is most of why the two ideas were conflated:
`SurfaceBinding` in `propagation/scene.py` held per class permittivity, while
`SemanticBinding` in `propagation/semantic_binding.py` held per triangle classes.
The names are now the other way round, so `SurfaceBinding` means something
different from what it meant last week. That is the one rename most likely to
confuse a reader of old notes.

### Provenance is a type now, not a convention

`SurfaceBinding.face_source` is a per triangle `Provenance` value: `GEOMETRIC`,
`IMAGE_FISHNET`, `IMAGE_WALK_ENTITY`, `IMAGE_WALK_MATERIAL`, `POSTERIOR_DRAW`.
The integers are written into arrays, so they are appended to, never reordered.
`__post_init__` refuses a binding with no provenance, an unknown source value, a
class it has no spec for, or arrays of mismatched length.

Coverage is now measured. `covered_fraction_by_area` counts area whose source is
not `GEOMETRIC`. The eleven city headline reported 0.0 coverage as a literal
typed at `run_exposure.py:533`; `geometric_binding()` reaches the same 0.0 by
counting, and `docs/BUGS.md` records that the literal was a run configuration
fact rather than a bug.

`SurfaceBinding` also has one optional field, `face_station`, which names which
camera decided each triangle as an index into `provenance["image_ids"]`. Nothing
fills it. It is there because the vision layer now exposes
`vision.provenance.station_registrations(site)` keyed on exactly those ids, so
"this material came from a camera we could not place" becomes sayable. Deciding
which station wins a multi station vote is a modelling choice and belongs to the
pass that uses it.

`bind_walk_entities` takes `station_weight`, a dict from image id to a weight,
which scales or drops a station's vote. It is inert by default: the multiply is
skipped entirely at weight one, so the default path is bit identical. Two tests
pin that. `bind_walk_materials` did not get the hook. Its modal branch could take
it, but its `mixture=True` branch reads a per face histogram already summed over
stations, so a station cannot be dropped there at all without changing the file
format.

### Verification that the move is exact

Old and new code were run side by side on real Korenmarkt data. The pre-refactor
implementations were transcribed verbatim into a scratch script and compared:

- `bind_fishnet` on `outputs/korenmarkt_fishnet_vistas`: `face_class`,
  `class_names`, both coverage fractions, `mesh_match` and
  `chosen_material_triangle_counts` all identical.
- `bind_walk_entities` on `outputs/site_semantics/korenmarkt/walk_semantic_130m.npz`:
  identical on every field.
- `effective_rms_height` over all 16 roughness classes: identical.
- Against the golden fixtures themselves: `surface_binding_classes` for both the
  geometric and the semantic case, `semantic_covered_fraction_by_face` and
  `_by_area`, `semantic_mesh_match` and `chosen_material_triangle_counts` all
  reproduce `tests/golden/exposure_korenmarkt_130m_*.json` exactly.

The golden reduction in `tests/golden/cases.py:145-176` reads named keys from
`manifest["semantic_binding"]` and all of `manifest["surface_binding"]["classes"]`.
Adding a key to a provenance dict is therefore safe; adding one to a class block
is not. The new `roughness_rule` key sits in the table's provenance, not in the
class block.

Invariant suites were run as a regression check and stayed green with their
xfails intact. `tests/test_golden_regression.py` was **not** run, because it
writes into `outputs/` and other agents were working in the same tree.

## What is half done

Nothing is half moved. Two things are deliberately incomplete.

1. **The drivers are not rewired.** `run_exposure.py` and `run_next_event.py`
   were off limits this wave, so every old module path survives as a shim that
   re-exports its new home. Each shim carries a one line comment saying it is
   temporary and is removed in the driver rewiring pass.

2. **`face_station` is a shape with nothing behind it.** See above.

## Shims to delete, and the driver lines that must change first

Every shim is a pure re-export. Delete each one only after its importers move.

| Shim | New home |
| --- | --- |
| `semantic_twin/propagation/scene.py` | `semantic_twin.materials` |
| `semantic_twin/propagation/semantic_binding.py` | `semantic_twin.materials.evidence` |
| `semantic_twin/propagation/material_posterior.py` | `semantic_twin.materials.posterior` |
| `semantic_twin/foliage.py` | `semantic_twin.materials.foliage` |
| `semantic_twin/masonry.py` | `semantic_twin.materials.masonry.wall` |
| `semantic_twin/floquet.py` | `semantic_twin.materials.masonry.floquet` |
| `semantic_twin/rcwa.py` | `semantic_twin.materials.masonry.rcwa` |
| `semantic_twin/kirchhoff.py` | `semantic_twin.materials.masonry.kirchhoff` |
| `semantic_twin/mmwave.py` | partial: the roughness names moved to `materials.roughness`, the four frequency scalings stayed |

Old name to new name, which is what the driver edit is:

```
propagation.scene.load_bindings      -> materials.load_table
propagation.scene.CLASS_BINDING      -> materials.SURFACE_CLASSES
propagation.scene.SurfaceBinding     -> materials.MaterialTable   (not SurfaceBinding)
semantic_binding.bind                -> materials.bind_fishnet
semantic_binding.bind_from_walk      -> materials.bind_walk_entities
semantic_binding.bind_from_walk_material -> materials.bind_walk_materials
semantic_binding.SemanticBinding     -> materials.SurfaceBinding
semantic_binding.MATERIAL_BINDING    -> materials.IMAGE_MATERIALS
material_posterior.PosteriorBinding  -> materials.SurfaceBinding
```

Exact lines, as of this writing:

- `run_exposure.py:47` and `:48` are the two imports.
- `run_exposure.py:310`, `:442`, `:472`, `:510`, `:533` call `load_bindings`.
- `run_exposure.py:431` calls `bind`, `:465` calls `bind_from_walk`, `:500` calls
  `bind_from_walk_material`.
- `run_exposure.py:534` writes the hand typed `covered_fraction 0.0`. Replacing
  the geometric branch with `materials.geometric_binding(...)` makes that a
  measurement. It returns the same 0.0, so no number moves.
- `run_next_event.py:45` and `:49` are the imports, `:188` calls `load_bindings`.

Also still on old paths, and read only for this wave: `tests/test_determinism.py:207`,
`tests/test_propagation.py:48`, `tests/golden/capture.py:299`, and
`tests/test_invariant_audit.py` at lines 95, 834, 921, 972, 1034, 1070, 1071,
1101 and 1135. `tests/test_invariant_audit.py:1135` imports the private
`_effective_rms_height`, which `propagation/scene.py` keeps aliased for it.
Two prose references also point at the old module: `semantic_twin/vision/__init__.py:57`
and `semantic_twin/illumination/sources.py:169`.

## Orphan decisions

The standing instruction was to wire an orphan back in unless there is a real
reason not to. Both were examined; the calls differ.

### Foliage: wired in at the material layer, not at the tracer

`foliage.py` was 926 lines of which roughly 20 reached anything. What made it
unreachable was not the code, it was the type: the catalogue had no way to say
"this class is a volume, not a surface". It does now. `MaterialSpec.medium`
names a participating medium, `MaterialTable.media` lists the classes that are
volumes, and `foliage.medium_for_spec(spec, frequency_hz)` turns one into a
P.833 medium. Only `vegetation_effective` sets it.

That is as far as the wiring goes on purpose. Making `SbrTracer` carry a volume
means editing `propagation/tracer.py`, which was another agent's file this wave
and, more importantly, would move every number in the study. The vegetation
faces of a live run still take the P.2040 vacuum row, which removes a spurious
71.8 dB of canopy reflection and keeps a false block. That trade is recorded in
`VEGETATION_NOTE` and written into every manifest.

### Masonry: keep it out until findings 5 and 10 are fixed, with one exception

The stack is 1,790 lines and carries three findings of its own: 5 (Laurent's rule
where Li's inverse rule is required), 6 (an angle compared against a direction
cosine width), and 10 (a lossless passive grating returning reflectances of 54,
56.7 and 58, non-monotone in the truncation).

The stack splits cleanly in two, and the two halves deserve different answers.

**The rigorous solver stays out.** `rcwa.py` and the Kirchhoff order machinery
should not be wired to any result until 5 and 10 are fixed. Finding 10 is the
decisive one: it is wrong by a factor of 58 without raising, and it is not
monotone in the truncation, so the usual defence of running a convergence sweep
does not work. A larger `M` is as likely to land on a bad value as a good one.
Under Laurent's rule the across-stripe series does not usefully converge either:
increments halve as truncation doubles, a clean 1/M tail, and M=16 to M=32 still
moves 4.4 percent of itself, against 3 parts in a million under the inverse rule.
"Wire it in as-is" is not an option I would defend.

**The closed form half is offered, and is not the default.**
`kirchhoff.equivalent_rms_height_m` with the `wall.py` geometry is pure algebra
over construction documents. It touches neither `rcwa.py` nor the order
machinery, so it carries none of the three findings.
`roughness.masonry_equivalent_rms_height` is the wiring point and
`load_table(..., roughness_rule=MASONRY_RULE)` is how a caller asks for it. The
default stays `QUADRATURE_RULE`, which is what every published number ran.

That route is also the only thing in the tree that reads `unit_scatter_mm`, the
3 mm brick to brick tolerance that finding 2 drops. It is not a fix for finding
2 and must not be treated as one: it is a second opinion, reachable by an
explicit argument, and it moves the facade RMS height from 1.155 mm to 3.119 mm.

If you write tests for this stack, do not lean on `R + T`. That identity has now
failed to catch two separate defects, because R and T blow up together.

## Findings

`docs/BUGS.md` finding 14 is new from this wave: **the default tree species is
decided by the order of a source tuple.** At 15 GHz seven species tie exactly in
`ret_parameters`, `min()` returns whichever row is written first, and that picks
the extinction. Reversing `_RET_ROWS` changes a 10 m canopy crossing by a factor
of 20; across every species the module accepts, by a factor of 2,300. Not
currently fired, because nothing live calls it. Code untouched.

Two smaller things noticed and not written up as findings, because neither is
currently wrong in a run:

- `materials/binding.py:162`, `class_area_fractions` iterates only the four
  geometric classes, so on an extended class table it returns a partition that
  does not sum to one. Nothing calls it: `run_exposure.py:575` inlines its own
  version over `binding.class_names`, which is correct. It is a trap rather than
  a defect.
- `SurfaceRoughnessPrior.specular_power_fraction` refuses periodic classes,
  because a mortar joint grid diffracts into orders that a smooth coherent
  fraction cannot describe. The live path applies that same closure to those same
  classes anyway, through `load_table` and the tracer's `specular_share`, with no
  guard. The manifest does record `roughness_structure` per class, so the fact is
  recoverable. It is the same physics as finding 2 rather than a new one.

## What I would do next, in order

1. **Rewire the two drivers** and delete the nine shims. The lines are listed
   above. Do it as its own commit and check the golden suite after, because it is
   the change most likely to look harmless and not be.
2. **Replace the geometric branch** at `run_exposure.py:533-534` with
   `materials.geometric_binding(...)`. Same 0.0, measured instead of typed. This
   is the smallest change that retires the finding the whole wave was named for.
3. **Fix finding 2**, the roughness quadrature, as its own commit with its own
   before and after number. `masonry_equivalent_rms_height` is a second reading
   to check the fix against, not the fix.
4. **Fill `face_station`** in `bind_walk_entities`, then join it to
   `vision.provenance.station_registrations`. Decide first what "which station
   decided this triangle" means when several voted. Argmax of the per station
   contribution is the obvious answer and is not the only one.
5. **Findings 5 and 10** in `rcwa.py`, in that order, before anything in
   `masonry/` is wired to a number.

## Things I am not sure about

- **`stack.py`'s boundary.** `MATERIAL_VOCABULARY` moved from `vision/vlm.py`
  into `catalogue.py`, on the reasoning that the list is defined by what the
  catalogue can ground rather than by what a prompt says. `FACADE_FINISHES` and
  `RELIEF_PATTERNS` stayed in vision, because they are about what a model is
  asked to say. That line is arguable and I would not fight for it.
- **Whether `sample_face_materials` belongs in `posterior.py`.** It draws a
  material per face from a distribution, which is that module's subject, but it
  is used only by the vision analysis scripts. It is re-exported from `vlm.py`,
  so nothing broke.
- **Whether `class_area_fractions` should have been fixed rather than moved.** It
  is not on the golden path and no caller uses it, so the move was faithful and
  the trap survives. A fresh reader may reasonably decide the rule against fixing
  findings did not cover a function nobody calls.
- **`brick_face` vs `brick_wall_with_mortar_joints`.** The masonry rule takes the
  nominal unit dimension from `brick.width_m`, matching the convention at
  `run_masonry_grating.py:363` and `plot_masonry_grating.py:186`. I checked that
  against the study's own scripts, not against BS EN 771-1 itself.
