"""Compatibility facade for the city exposure command.

The implementation lives in :mod:`semantic_twin.cli.exposure`.  This root file
stays importable because published captures, notebooks, and reproduction
scripts still refer to ``run_exposure`` directly.
"""

from __future__ import annotations

import sys
from typing import Any

from semantic_twin.cli import exposure as _command
from semantic_twin.exposure import study as _study

# Explicit historical exports.  Keep these assignments visible rather than
# relying on a broad module-level ``__getattr__`` for names that callers use.
CONFIG = _command.CONFIG
COVERAGE_LADDER = _command.COVERAGE_LADDER
CROP_BOUND_NOTE = _command.CROP_BOUND_NOTE
GROUND_DATUM_M = _command.GROUND_DATUM_M
LADDER_MODELS = _command.LADDER_MODELS
MODELS = _command.MODELS
OUTPUT = _command.OUTPUT
PHANTOM = _command.PHANTOM
PHANTOM_MASS_KG = _command.PHANTOM_MASS_KG
REFERENCE_S0_W_M2 = _command.REFERENCE_S0_W_M2
ROOT = _command.ROOT
SEMANTICS = _command.SEMANTICS
SITES = _command.SITES
SITE_SEMANTICS = _command.SITE_SEMANTICS
WALK_SEMANTIC = _command.WALK_SEMANTIC
ExecutionConfig = _command.ExecutionConfig
LegacyReplay = _command.LegacyReplay
CitySweepConfig = _command.CitySweepConfig
LadderSweepConfig = _command.LadderSweepConfig
RunConfig = _command.RunConfig
DEFAULT_MAX_BOUNCES = _command.DEFAULT_MAX_BOUNCES

_escape_config = _command._escape_config
arguments = _command.arguments
coverage_ladder = _command.coverage_ladder
coverage_ladder_report = _command.coverage_ladder_report
coverage_report = _command.coverage_report
cross_city_report = _command.cross_city_report
fishnet_rests_on_an_admitted_pose = _command.fishnet_rests_on_an_admitted_pose
ground_datum = _command.ground_datum
ladder_key = _command.ladder_key
ladder_markdown = _command.ladder_markdown
ladder_sites = _command.ladder_sites
ladder_tag = _command.ladder_tag
measure_ground_datum = _command.measure_ground_datum
report = _command.report
reusable = _command.reusable
run = _command.run
run_all_sites = _command.run_all_sites
run_coverage_ladder = _command.run_coverage_ladder
site_fishnet = _command.site_fishnet
site_mesh = _command.site_mesh
site_walk_semantics = _command.site_walk_semantics
_against_baseline = _command._against_baseline
_one_value = _command._one_value
_spread = _command._spread


def validate(rays: int = 400_000) -> dict[str, object]:
    """Run validation while honoring the historical mutable ``MODELS`` name."""
    original_models = _command.MODELS
    original_config = _command.CONFIG
    _command.MODELS = MODELS
    _command.CONFIG = CONFIG
    try:
        return _command.validate(rays)
    finally:
        _command.MODELS = original_models
        _command.CONFIG = original_config


_CALLBACK_NAMES = (
    "run",
    "run_all_sites",
    "run_coverage_ladder",
)


def main(argv: list[str] | None = None) -> int:
    """Delegate command parsing and dispatch to the package-owned boundary.

    The temporary bindings retain the established sweep hook: scripts and
    tests may replace one of the three root-level run functions before calling
    ``main``. Package callers use the package module directly and do not need
    this compatibility bridge.
    """
    saved = {name: getattr(_command, name) for name in _CALLBACK_NAMES}
    try:
        for name in _CALLBACK_NAMES:
            setattr(_command, name, globals()[name])
        return _command.main(argv)
    finally:
        for name, value in saved.items():
            setattr(_command, name, value)


def __getattr__(name: str) -> Any:
    """Expose legacy study attributes while callers migrate to the package."""
    return getattr(_study, name)


if __name__ == "__main__":
    sys.exit(main())
