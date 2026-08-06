"""Compose the support-mesh remeshing comparison panel."""

from semantic_twin import paths
from semantic_twin.viz import figures
from semantic_twin.viz.remesh_panel import compose_remesh_panel

# Kept at command scope for the output-routing regression test.
ROOT = paths.root()
out = figures.get("remesh_visual").path()


def main() -> None:
    compose_remesh_panel()


if __name__ == "__main__":
    main()
