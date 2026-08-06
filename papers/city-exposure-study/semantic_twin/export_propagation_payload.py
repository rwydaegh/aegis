"""Compatibility command for the propagation payload exporter."""

from __future__ import annotations

import sys

from semantic_twin.cli.export_propagation_payload import (  # noqa: F401
    DEFAULT_DRAW_RADIUS_M,
    DEFAULT_MAX_BOUNCES,
    EXPOSURE_OUTPUT,
    OUTPUT,
    ProductionFiles,
    arguments,
    export,
    main,
    production_files,
    stamp_bundle_identity,
    verify_bundle_identity,
)


if __name__ == "__main__":
    sys.exit(main())
