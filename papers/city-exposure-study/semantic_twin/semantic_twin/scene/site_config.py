"""The raw scene JSON of one site, and the credential its imagery needs.

``config/<site>.json`` is where a square's geometry starts: an anchor latitude
and longitude, the ENU origin built from it, and the ground datum every camera
altitude is measured against. :func:`load_scene` is the low level reader and it
checks only that those four keys are present. :mod:`semantic_twin.sites` is the
registry built on top of it and is what most callers want.

:func:`google_api_key` is here because it arrived with the Street View reader
that sits next to :func:`load_scene` in every acquisition script. It is a
credential rather than geometry and belongs under ``acquire/``.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any


def load_scene(path: pathlib.Path) -> dict[str, Any]:
    document = json.loads(path.read_text())
    required = {"name", "location", "enu_origin", "camera_ground_z_m"}
    missing = required - document.keys()
    if missing:
        raise ValueError(f"scene config is missing: {', '.join(sorted(missing))}")
    return document


def google_api_key() -> str:
    value = os.environ.get("GOOGLE_API_KEY")
    if value:
        return value
    env_file = pathlib.Path("/home/user/aegis/.env")
    for line in env_file.read_text().splitlines() if env_file.exists() else []:
        if line.startswith("GOOGLE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_API_KEY is not configured")
