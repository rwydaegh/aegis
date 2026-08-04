"""One rule for everything acquisition keeps on disk.

Four services grew their own caching independently and two of them disagreed
about what a cached thing is called. Tiles were named by the address they
arrived at. Routes were named by what was asked for. The address turned out to
be worthless: Google serves 3D Tiles payloads at per session paths, so
re-running Krakow produced 91 files whose bytes hashed identically to the 91
already on disk, under 91 different URLs, and every one of them was bought
again.

The rule is one sentence. **A cached thing is named by what it is, never by
where it came from.** For a tile that is where the geometry sits and how coarse
it is. For a walking route it is the waypoints and whether the service was
allowed to reorder them.

Two roundings, because there are two units and one rule would be wrong in one of
them. ECEF metres round to a millimetre, which is far below the metres-across
size of the smallest leaf tile. Latitude and longitude round to seven decimals,
which is about a centimetre and far below any camera position. Both are there to
absorb the last bits of a floating point product without ever merging two things
that are genuinely apart.

The digests are pinned by :mod:`tests.test_acquire_cache`. They name files that
are already on disk and were already paid for, so changing the recipe silently
throws that money away.

What no cache can see is a provider republishing the same thing, at the same
place and the same detail, with new content. That is what a refresh flag is for.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

#: Rounding applied to ECEF metres before they enter a key. A millimetre.
PLACEMENT_ROUNDING_DECIMALS = 3

#: Rounding applied to degrees of latitude and longitude. About a centimetre.
COORDINATE_ROUNDING_DECIMALS = 7


def placement_key(
    bounding_volume: Any,
    transform: np.ndarray,
    geometric_error_m: float,
    order: int,
) -> str:
    """A name for a tile that survives the address it was served at.

    Keys on the bounding volume placed into world coordinates, the geometric
    error, and the payload's position in the tile when a tile carries several.
    That says "this piece of the city at this level of detail", which is a
    property of the data rather than of the delivery.

    ``order`` matters because nothing in the 3D Tiles hierarchy forbids two
    payloads sharing one tile, and two payloads of one tile share a box and an
    error.
    """
    volume: list[float] = []
    if isinstance(bounding_volume, dict):
        for name in ("box", "sphere", "region"):
            value = bounding_volume.get(name)
            if isinstance(value, list):
                volume = [float(v) for v in value]
                break
    digest = hashlib.sha256()
    digest.update(json.dumps([round(v, PLACEMENT_ROUNDING_DECIMALS) for v in volume], sort_keys=True).encode())
    digest.update(np.round(np.asarray(transform, dtype=np.float64), PLACEMENT_ROUNDING_DECIMALS).tobytes())
    digest.update(f"{geometric_error_m:.6f}|{order}".encode())
    return digest.hexdigest()[:32]


def route_key(waypoints: Sequence[tuple[float, float]], optimise: bool) -> str:
    """A name for one routing request, so the same one is never paid for twice.

    The waypoints and the reordering flag are the whole request. Adding a camera
    buys a new route. Asking for the same set again does not.
    """
    digest = hashlib.sha256()
    rounded = [[round(value, COORDINATE_ROUNDING_DECIMALS) for value in point] for point in waypoints]
    digest.update(json.dumps(rounded).encode())
    digest.update(b"optimised" if optimise else b"in order")
    return digest.hexdigest()[:16]


@dataclass(frozen=True)
class ReusedArtefact:
    """One file a previous run already paid for, matched by placement key."""

    key: str
    file: str
    size: int
    record: dict[str, Any]


class ManifestCache:
    """The manifest of a previous run, read back as the cache of that run.

    A download run without this has two in-memory caches that only stop it
    buying the same tile twice inside itself. Across runs there was nothing, so
    re-running a site paid for the whole site again, 155 to 1,178 requests
    depending on the site.

    An entry is spent once. Two things that key the same are a possibility the
    hierarchy does not forbid, and pointing both at one file would leave one of
    them holding bytes that are not its own, quietly.

    Names are the other half. A file kept from a previous run keeps the name it
    was written under, while fresh files count up from the traversal position, so
    the two schemes collide the moment the hierarchy changes. :meth:`free_name`
    is what stops a fresh download landing on top of a kept file.
    """

    def __init__(self, manifest_path: pathlib.Path, *, records_key: str = "tiles") -> None:
        self.manifest_path = manifest_path
        self.directory = manifest_path.parent
        self._available: dict[str, ReusedArtefact] = self._read(records_key)
        self._claimed_names: set[str] = {entry.file for entry in self._available.values()}
        self._spent: set[str] = set()

    def _read(self, records_key: str) -> dict[str, ReusedArtefact]:
        """Prior entries whose file is on disk at the recorded size.

        A size that disagrees is a truncated download, a half written file or an
        edited payload, and reusing any of those would put corrupt geometry into
        every mesh built afterwards without raising anything.

        Manifests written before the key existed match nothing, so a site
        acquired under the old scheme pays once more and then carries it.
        """
        if not self.manifest_path.exists():
            return {}
        try:
            prior = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        found: dict[str, ReusedArtefact] = {}
        for record in prior.get(records_key, []):
            key = record.get("tile_key")
            name = record.get("file")
            if not isinstance(key, str) or not isinstance(name, str):
                continue
            path = self.directory / name
            if path.exists() and path.stat().st_size == record.get("size"):
                found[key] = ReusedArtefact(key, name, int(record["size"]), record)
        return found

    def claim(self, key: str) -> ReusedArtefact | None:
        """Take the prior file for one key, or None when nothing matches."""
        entry = self._available.pop(key, None)
        if entry is not None:
            self._spent.add(key)
        return entry

    def free_name(self, index: int, pattern: str = "tile_{index:04d}.glb") -> str:
        """A name no reused file has already taken, counting up from ``index``."""
        while pattern.format(index=index) in self._claimed_names:
            index += 1
        name = pattern.format(index=index)
        self._claimed_names.add(name)
        return name

    @property
    def reused(self) -> int:
        """How many prior files this run took rather than bought."""
        return len(self._spent)
