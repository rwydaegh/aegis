# Conclusions on `body_aware_channel.tex`

## Recommendation

Adding a body-aware receive channel is doable and scientifically worthwhile.
I would implement it in two steps:

1. **Use body visibility in the production sweep.** Gate every center ray at
   each served-device position using the phantom geometry. Use the existing
   signed-clearance/Fock machinery where it is trustworthy, with a hard
   geometrical-optics visibility gate as the fail-safe model.
2. **Add a deliberately approximate first reflection.** Use a local physical
   optics or two-ray reflection from the body patch nearest the device. Retain
   the complex Fresnel coefficient, outgoing polarization, propagation phase,
   and a bounded curvature/divergence factor. Validate this against a flat
   lossy slab and a small body-in-scene ray-tracing oracle.

That model captures the two effects most likely to change MRT and ECBF:

- paths that currently pass through the torso at full strength are removed or
  attenuated;
- the nearby body produces a coherent reflected copy and therefore a
  separation-dependent channel ripple.

It preserves the paper's main factorization and should be cheap enough for the
full sweep. I would not implement the reaction integral in the note literally
as the first production version.

## What is correct in the note

The central diagnosis is correct. The current signal channel is synthesized
from the body-free ray pack. The body modifies the exposure branch, but it
does not shadow or reflect into the served-device channel. Consequently, MRT
is matched to a channel that a real body-adjacent receiver would not measure.

The proposed first-order split is also reasonable:

```text
h_body = h_direct_with_body_visibility + h_single_body_reflection
Q_body = current Q
```

Keeping Q unchanged is a coherent first-order approximation. The current Q
already describes absorption of the incident environmental paths. Reflection
followed by a second interaction with the body is a higher-order recapture
term and can remain outside the default model.

The factorization is preserved. Body visibility and the reflected coefficient
can be computed for the distinct center paths and served positions, then
lifted through the same array factors to M = 16, 64, and 256. They do not need
to be recomputed per antenna element.

## What should not be accepted literally

### The reaction equation is schematic, not implementation-ready

The integral in the note uses only an electric reflected field and an
unspecified scalar normalization constant. A rigorous Huygens or reciprocity
calculation generally needs consistently normalized tangential electric and
magnetic equivalent currents, the receive antenna field, and the associated
surface-reaction terms. A single overlap

```text
integral u_UE^T R psi dA
```

with a fitted scalar kappa is not yet enough to guarantee the correct phase,
units, polarization, or received power.

This does not invalidate the idea. It means the full reaction route needs a
derivation and an oracle before it can be called the accurate model.

### “Negligible against the exposure kernel” is not established

For Duke, a literal surface reaction over 56,024 triangles, roughly 258
center paths, and 21 served positions is hundreds of millions of complex
interactions per body-ray group. It can be expressed as GPU contractions and
can reuse the body atlas, but it is not automatically free. It needs a real
batched GPU benchmark.

By contrast, a center-path GO visibility/reflection model is only about
21 x 258 path-position interactions and is genuinely small.

### Zero standoff needs a physical convention

At zero mathematical separation, the antenna phase center lies on the mesh.
Neither a free-space spherical wave nor a surface-reflection model is valid
there. Real hardware still has a shell, antenna depth, and tissue clearance.

The clean convention is:

- “0 cm standoff” means zero handset-shell-to-skin gap;
- the receive antenna phase center remains a declared positive distance from
  the surface, for example 3 to 5 mm inside the handset;
- sensitivity to that phase-center depth is reported for the zero-gap ECBF
  figure.

Silently evaluating the reflection formula at d = 0 would be indefensible.

### A body-in-scene Sionna trace is an oracle, not automatically truth

It is useful for a few cases, but only after checking mesh watertightness,
material conventions, polarization, array geometry, path phase, and whether
the tracer's surface model represents the intended lossy tissue interface.
It should validate trends and controlled slab cases, not become the production
sweep by default.

## Recommended production model

### Level B0: current body-free channel

Keep this as a reproducibility baseline.

### Level B1: visibility-aware channel

For every distinct center ray n and served position p:

1. Cast from the served position opposite the arrival propagation direction.
2. Test whether the phantom intersects the incoming half-ray.
3. Set the direct-path gate to 0 or 1 for the strict GO version.
4. Optionally replace the step near the silhouette with the existing complex
   Fock transition, provided the signed clearance and curvature refer to the
   device ray rather than to a surface triangle.
5. Apply the gate before lifting center paths into array elements.

The existing code already contains a Numba BVH any-hit primitive, a signed
directional-clearance representation, curvature estimates, and Fock gates.
The missing part is a device-point query and its path/position batching.

This is the highest-confidence addition. It directly removes rays that pass
through the body and requires no new electromagnetic normalization.

### Level B2: GO-like coherent body reflection

For every center ray and served position:

1. Select the local body patch that can reflect the incoming ray toward the
   device. For the near-chest use case, start from the closest visible patch
   and refine locally rather than searching the complete mesh blindly.
2. Compute the TE/TM Fresnel reflection coefficients from the current tissue
   model.
3. Rotate the outgoing TM basis into the reflected direction.
4. Add the correct optical path phase.
5. Apply a bounded divergence factor based on local curvature. Use D = 1 as
   the planar upper model and a curvature-derived D below 1 as the default.
6. Suppress the term if the reflected segment is occluded.

This is an approximation, but it is an explicit and understandable one. It
should reproduce the flat-slab two-ray limit and the correct several-dB ripple
scale without paying for a full surface reaction.

Near a silhouette, use either the Fock transition or a smooth visibility
blend. Do not combine two independently normalized edge corrections.

### Level B3: physical-optics reaction

Treat this as a validation/refinement level, not the initial campaign model.
Derive the equivalent electric and magnetic currents, establish port
normalization, implement the triangle integral as a streamed GPU contraction,
and compare it with B2 and body-in-scene oracle cases. Promote it only if it
changes the paper conclusions enough to justify its cost.

## Expected coding work

These are engineering estimates, not measured completion times.

| Work item | Coding and tests | Scientific risk |
|---|---:|---|
| B1 hard body visibility | 2 to 4 days | Low |
| B1 smooth/Fock device gate | another 2 to 5 days | Medium |
| B2 local GO reflection | 4 to 8 days | Medium |
| Flat-slab and two-ray oracle suite | 2 to 4 days | Low |
| Small body-in-scene oracle set | 3 to 7 days | Medium to high |
| B3 full reaction derivation and GPU kernel | 2 to 4 weeks | High |

The first useful result is therefore about one focused week: B1 plus a simple
B2 and controlled validation. The full reaction model is a separate research
task.

## Expected compute and storage overhead

### B1 and B2

The expensive unit is a body-ray group, not an antenna element. With about 258
center rays and 21 positions, B1/B2 create about 5,400 small geometric/path
queries per group. Their outputs are tiny:

- one real or complex gate per path and position;
- one complex reflected coefficient per path and position;
- less than a megabyte per body-ray group;
- shared exactly across M = 16, 64, and 256.

The target should be less than 10 percent additional warm wall time for B1 and
less than 25 percent for B1+B2. If a GPU implementation misses those gates,
the implementation is wrong for the campaign even if the physics is useful.

Across 9,216 body-ray groups, 0.1 seconds of overhead per group is about 15
minutes. One second per group is about 2.6 hours. These figures make a GO-like
model entirely plausible and make a literal surface reaction something that
must be benchmarked.

### B3

The body atlas already stores the large triangle-by-center-ray response. A
reaction implementation can stream the UE receive field and contract it with
that atlas, so storage need not explode. Retaining all device-position fields
for Duke would add on the order of tens of megabytes per active group, while
the existing Duke response atlas is about 694 MB. The risk is computation and
memory traffic, not permanent storage.

## Validation gates

The approximate model is acceptable if its approximation is explicit and it
passes the following gates:

1. **No-body limit.** Moving or disabling the phantom recovers the current h.
2. **Visibility geometry.** Rays crossing a slab or closed mesh are blocked;
   unobstructed rays are unchanged.
3. **Flat-interface reflection.** B2 matches the complex two-ray coefficient
   over angle, polarization, frequency, and 1 to 20 cm separation.
4. **Phase continuity.** The channel varies continuously with position when a
   smooth silhouette gate is enabled.
5. **Array factorization.** Center-ray lifting matches an independently
   expanded M = 16/64/256 channel to near floating-point tolerance.
6. **Body-in-scene spot checks.** A small set spanning LOS/NLOS, chest/head,
   1/3/10 cm, 28/60/100 GHz, and two bodies agrees in the sign and scale of
   received-power and MRT-direction changes.
7. **Paper sensitivity.** Recompute the MRT table slice and ECBF Pareto slice
   under B0, B1, and B2. The paper must state which conclusions are stable and
   which depend on body-aware CSI.
8. **Performance.** Measure batched A6000/H100 throughput over a miniature
   campaign. Reject an implementation that defeats grouping across arrays.

## How this fits the two-block paper

The body-aware channel should be applied consistently to both blocks:

- MRT uses x proportional to the conjugate of h_body.
- Whole-body ECBF uses the pair (h_body, Q), with Q unchanged.

The large MRT table should state explicitly that its beam is body-aware MRT
under the selected B level. The ECBF figure should compare ECBF and MRT built
from the same h_body. Otherwise some apparent ECBF gain could merely be the
cost of using a body-free MRT baseline.

The zero-standoff ECBF figure is exactly where B2 matters most. It also has the
greatest modeling uncertainty, so the antenna phase-center convention and the
B0/B1/B2 sensitivity should appear in the figure method or caption.

## Final decision

Implement B1 and B2. Keep B0 for comparison. Do not block the campaign on B3.

The deliberately imperfect GO-like model is a good trade if we:

- call it first-order body-aware CSI rather than a full-wave channel;
- retain complex phase and polarization rather than using a scalar dB loss;
- share center-path work across all arrays;
- define zero standoff physically;
- validate controlled cases and show B0/B1/B2 sensitivity;
- keep the complete exposure maps and Q calculation unchanged.

This would materially improve the realism of the baseline for modest compute
cost. It is more valuable than adding another large sweep dimension, and much
more practical than implementing the note's full reaction integral before we
know whether reflection changes the conclusions.
