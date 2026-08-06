"""Command-line contract for the propagation payload exporter.

The study keeps ``export_propagation_payload.py`` as a published command.  Its
implementation lives in the package so callers can use the same export without
importing a script by path.  The command-line parser is in
:mod:`semantic_twin.cli.export_propagation_payload`; this module owns the
reusable defaults, bundle identity, and export function while :mod:`.exporter`
owns payload assembly and publication.
"""

from __future__ import annotations

from semantic_twin.propagation import DEFAULT_MAX_BOUNCES

from .exporter import DEFAULT_DRAW_RADIUS_M, OUTPUT, export
from .payload import (
    BUNDLE_ARRAY,
    BUNDLE_SCHEMA,
    ProductionFiles,
    manifest_content_sha256,
    payload_content_sha256,
    production_files,
    stamp_bundle_identity,
    verify_bundle_identity,
)

__all__ = [
    "DEFAULT_DRAW_RADIUS_M",
    "DEFAULT_MAX_BOUNCES",
    "BUNDLE_ARRAY",
    "BUNDLE_SCHEMA",
    "manifest_content_sha256",
    "OUTPUT",
    "payload_content_sha256",
    "ProductionFiles",
    "export",
    "production_files",
    "stamp_bundle_identity",
    "verify_bundle_identity",
]
