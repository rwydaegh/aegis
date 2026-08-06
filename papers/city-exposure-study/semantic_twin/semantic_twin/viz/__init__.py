"""Everything that draws. Blender payloads and scene assembly, and the figures.

Two halves that share one rule, which is that a drawing says what made it.

:mod:`semantic_twin.viz.figures` is the registry. A figure is named by content and
numbered here, at assembly, rather than by whoever wrote the generator. That is
the fix for ``FIGURES/`` having grown two figure 24s and two figure 25s.

:mod:`semantic_twin.viz.provenance` is the record that goes beside every figure and
into its image metadata: the generator, the checkout, and per input file the
illumination law and estimator read out of that run's own manifest. Without it,
answering "which law made this picture" costs a 270 line table of survives-or-not,
which is what ``docs/2026-08-03_161712_LAW_CHANGE.md`` actually is.

Nothing here is imported at package scope, because
:mod:`semantic_twin.viz.blender` runs inside Blender, which has numpy and does not
have matplotlib.
"""

from __future__ import annotations

__all__ = ["blender", "cdf", "figures", "provenance"]
