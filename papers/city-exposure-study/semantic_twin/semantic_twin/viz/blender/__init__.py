"""Building the propagation walkthrough blend, split along the three jobs it does.

``propagation_blender.py`` was 2,116 lines and the largest single file in the
study. Reading it, it is three things stacked on top of each other, and the
stacking is why none of it could be tested: line one is ``import bpy``, so the
whole file including its arithmetic was unimportable outside Blender.

So the split is by what needs Blender, not by subject.

:mod:`~semantic_twin.viz.blender.payload` is the arithmetic. What the payload
holds, and everything derived from it: which bundle a ray belongs to, where the
rim breaks, how a marker mesh is built, where a camera has to point. Pure numpy,
no ``bpy``, and therefore testable in the ordinary interpreter, which is what
``tests/test_blender_payload.py`` does.

:mod:`~semantic_twin.viz.blender.scene` is the Blender vocabulary. Collections,
meshes, colour attributes, materials, point clouds, cameras, lighting and the
saved viewport. Nothing in it knows what a ray is.

:mod:`~semantic_twin.viz.blender.estimator` draws the estimator: the mesh, the
recorded paths twice over, the arrival spectrum, the sources on the facade tips,
the next event connections, the walk and the phantom.

:mod:`~semantic_twin.viz.blender.evidence` draws the image evidence layers, every
one of which is skipped when the payload lacks it, and
:mod:`~semantic_twin.viz.blender.renders` holds the figure table and renders it.

The style constants live in :mod:`~semantic_twin.viz.blender.style` because two of
those four modules read them and a constant in the file that happens to use it
first is how a palette ends up with two versions.

Nothing is imported here. ``payload`` has to stay importable without Blender and
the rest cannot be imported without it.
"""

from __future__ import annotations

__all__ = ["estimator", "evidence", "payload", "renders", "scene", "style"]
