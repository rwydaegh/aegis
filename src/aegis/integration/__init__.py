"""Ray tracer integration: load propagation paths from external tools."""

from aegis.integration.differt import paths_from_differt, paths_from_differt_scene

__all__ = [
    "paths_from_differt",
    "paths_from_differt_scene",
]
