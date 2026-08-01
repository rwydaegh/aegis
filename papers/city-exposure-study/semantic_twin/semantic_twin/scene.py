"""Scene configuration and credential discovery."""

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


def inhouse_api_key() -> str:
    value = os.environ.get("GOOGLE_API_KEY")
    if value:
        return value
    env_file = pathlib.Path("/home/user/aegis/.env")
    for line in env_file.read_text().splitlines() if env_file.exists() else []:
        if line.startswith("GOOGLE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GOOGLE_API_KEY is not configured")
