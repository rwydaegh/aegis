"""Antenna pattern library with SQLite index over MSI zip archives.

Indexes MSI antenna pattern files from zip archives (as shipped by
Kathrein, Commscope, Huawei, etc.) into a local SQLite database.
Provides search by manufacturer, model, frequency, and gain, and loads
full 2D patterns on demand via ``msi_to_antenna_pattern``.

Handles two layouts found in the wild:
1. Direct MSI files inside the outer zip (HUAWEI, Kathrein, etc.)
2. Inner zip files inside the outer zip that contain MSI files (Commscope)
"""

from __future__ import annotations

import gzip
import io
import logging
import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from pathlib import Path

from aegis.basestation.antenna import AntennaPattern
from aegis.basestation.msi import msi_to_antenna_pattern, parse_msi

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PatternSearchResult:
    """A single row from the antenna pattern index."""

    id: str  # e.g. "Kathrein/1800MHz/731620X7.MSI"
    source: str  # "local" or "cloudrf"
    manufacturer: str
    model: str  # filename stem
    frequency_mhz: float
    gain_dbi: float
    tilt_deg: float


class AntennaPatternLibrary:
    """Index and query antenna patterns stored as MSI files in zip archives.

    Parameters
    ----------
    data_dir:
        Root data directory (contains ``antenna_patterns/msi_raw/*.zip``).
    cloudrf_api_key:
        Reserved for future CloudRF provider integration.
    """

    def __init__(self, data_dir: str, cloudrf_api_key: str | None = None) -> None:
        self._data_dir = Path(data_dir)
        self._db_path = self._data_dir / "antenna_patterns" / "index.sqlite"
        self._msi_dir = self._data_dir / "antenna_patterns" / "msi_raw"

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def build_index(self) -> int:
        """Scan all .zip files in msi_raw/, parse MSI headers, write SQLite.

        Drops and rebuilds the index from scratch.  Returns the count of
        indexed patterns.
        """
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("DROP TABLE IF EXISTS patterns")
        conn.execute("""
            CREATE TABLE patterns (
                id TEXT PRIMARY KEY,
                manufacturer TEXT NOT NULL,
                model TEXT NOT NULL,
                frequency_mhz REAL,
                gain_dbi REAL,
                tilt_deg REAL,
                source_zip TEXT NOT NULL,
                source_path TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_manufacturer ON patterns(manufacturer)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_freq ON patterns(frequency_mhz)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON patterns(model)")

        count = 0
        for zip_path in sorted(self._msi_dir.glob("*.zip")):
            manufacturer = zip_path.stem
            with zipfile.ZipFile(zip_path) as zf:
                count += self._index_zipfile(conn, zf, manufacturer, zip_path.name, prefix="")

        conn.commit()
        conn.close()
        logger.info("Indexed %d antenna patterns", count)
        return count

    def _index_zipfile(
        self,
        conn: sqlite3.Connection,
        zf: zipfile.ZipFile,
        manufacturer: str,
        source_zip: str,
        prefix: str,
    ) -> int:
        """Index all MSI files in a zipfile, including nested inner zips."""
        count = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            name_lower = info.filename.lower()

            # Handle inner zip files (e.g. Commscope nested zips)
            if name_lower.endswith(".zip"):
                try:
                    inner_bytes = zf.read(info.filename)
                    inner_zf = zipfile.ZipFile(io.BytesIO(inner_bytes))
                    inner_prefix = prefix + info.filename + "/"
                    count += self._index_zipfile(conn, inner_zf, manufacturer, source_zip, inner_prefix)
                except Exception as exc:
                    logger.debug(
                        "Failed to read inner zip %s in %s: %s",
                        info.filename,
                        source_zip,
                        exc,
                    )
                continue

            if not name_lower.endswith(".msi"):
                continue

            try:
                raw = zf.read(info.filename)
                text = raw.decode("utf-8", errors="replace")
                meta, _, _ = parse_msi(
                    text,
                    manufacturer=manufacturer,
                    source_zip=source_zip,
                    source_path=info.filename,
                )
                pattern_id = f"{manufacturer}/{prefix}{info.filename}"
                model = Path(info.filename).stem
                conn.execute(
                    "INSERT OR REPLACE INTO patterns VALUES (?,?,?,?,?,?,?,?)",
                    (
                        pattern_id,
                        manufacturer,
                        model,
                        meta.frequency_mhz,
                        meta.gain_dbi,
                        meta.tilt_deg,
                        source_zip,
                        prefix + info.filename,
                    ),
                )
                count += 1
            except Exception as exc:
                logger.debug(
                    "Failed to parse %s in %s: %s",
                    info.filename,
                    source_zip,
                    exc,
                )
        return count

    # ------------------------------------------------------------------
    # Auto-build
    # ------------------------------------------------------------------

    def _ensure_index(self) -> None:
        """Build the index automatically on first access if it does not exist.

        Priority:
        1. Use existing index.sqlite if present.
        2. Decompress shipped index.sqlite.gz (committed to git).
        3. Build from MSI zip archives if available.
        4. Log a warning and return (search will return empty results).
        """
        if self._db_path.exists():
            return
        gz_path = self._db_path.with_suffix(".sqlite.gz")
        if gz_path.exists():
            logger.info("Decompressing shipped antenna pattern index from %s", gz_path)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(gz_path, "rb") as f_in, open(self._db_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            return
        if self._msi_dir.exists() and any(self._msi_dir.glob("*.zip")):
            self.build_index()
        else:
            logger.warning(
                "No antenna pattern index and no MSI zips at %s. Pattern search will return empty results.",
                self._msi_dir,
            )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str = "",
        manufacturer: str | None = None,
        freq_min_mhz: float | None = None,
        freq_max_mhz: float | None = None,
        gain_min_dbi: float | None = None,
        gain_max_dbi: float | None = None,
        source: str = "all",
        limit: int = 50,
    ) -> list[PatternSearchResult]:
        """Search the index by free-text query and/or structured filters.

        Returns up to *limit* matching ``PatternSearchResult`` rows.
        """
        self._ensure_index()
        if not self._db_path.exists():
            return []
        conn = sqlite3.connect(str(self._db_path))
        conditions: list[str] = []
        params: list[object] = []

        if query:
            conditions.append("(manufacturer LIKE ? OR model LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if manufacturer:
            conditions.append("manufacturer LIKE ?")
            params.append(f"%{manufacturer}%")
        if freq_min_mhz is not None:
            conditions.append("frequency_mhz >= ?")
            params.append(freq_min_mhz)
        if freq_max_mhz is not None:
            conditions.append("frequency_mhz <= ?")
            params.append(freq_max_mhz)
        if gain_min_dbi is not None:
            conditions.append("gain_dbi >= ?")
            params.append(gain_min_dbi)
        if gain_max_dbi is not None:
            conditions.append("gain_dbi <= ?")
            params.append(gain_max_dbi)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = (
            "SELECT id, manufacturer, model, frequency_mhz, gain_dbi, tilt_deg "
            f"FROM patterns WHERE {where} ORDER BY manufacturer, model LIMIT ?"
        )
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [
            PatternSearchResult(
                id=r[0],
                source="local",
                manufacturer=r[1],
                model=r[2],
                frequency_mhz=r[3] or 0,
                gain_dbi=r[4] or 0,
                tilt_deg=r[5] or 0,
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_pattern(self, source: str, pattern_id: str) -> AntennaPattern:
        """Load a full 2D antenna pattern by source and ID.

        Parameters
        ----------
        source:
            ``"local"`` for MSI zip patterns. Other sources reserved.
        pattern_id:
            The ``id`` field from a ``PatternSearchResult``.
        """
        if source == "local":
            return self._load_local(pattern_id)
        raise ValueError(f"Unknown source: {source}")

    def _load_local(self, pattern_id: str) -> AntennaPattern:
        """Extract an MSI file from its zip and parse the full 2D pattern."""
        self._ensure_index()
        conn = sqlite3.connect(str(self._db_path))
        row = conn.execute(
            "SELECT source_zip, source_path, manufacturer, gain_dbi FROM patterns WHERE id = ?",
            (pattern_id,),
        ).fetchone()
        conn.close()
        if row is None:
            raise KeyError(f"Pattern not found: {pattern_id}")

        source_zip, source_path, manufacturer, _gain_dbi = row
        zip_path = self._msi_dir / source_zip

        text = self._read_msi_from_zip(zip_path, source_path)
        meta, h_atten, v_atten = parse_msi(
            text,
            manufacturer=manufacturer,
            source_zip=source_zip,
            source_path=source_path,
        )
        return msi_to_antenna_pattern(
            h_atten,
            v_atten,
            meta.gain_dbi,
            vertical_convention=meta.vertical_convention,
        )

    @staticmethod
    def _read_msi_from_zip(zip_path: Path, source_path: str) -> str:
        """Read an MSI file from a zip, handling nested inner zips.

        *source_path* may contain an inner-zip boundary indicated by a
        ``/`` segment ending in ``.zip/``.  For example::

            Commscope/2CPX208M-V1_Msi.zip/2CPX208M-V1_Port 1 - +45_00DT_0824.msi

        In that case we open the outer zip, extract the inner zip bytes,
        then read the MSI file from the inner zip.
        """
        with zipfile.ZipFile(zip_path) as zf:
            # Try direct read first (covers HUAWEI-style flat layouts)
            if source_path in zf.namelist():
                raw = zf.read(source_path)
                return raw.decode("utf-8", errors="replace")

            # Look for an inner-zip boundary in the path
            parts = source_path.split("/")
            for idx, part in enumerate(parts):
                if part.lower().endswith(".zip"):
                    inner_zip_path = "/".join(parts[: idx + 1])
                    inner_msi_path = "/".join(parts[idx + 1 :])
                    inner_bytes = zf.read(inner_zip_path)
                    inner_zf = zipfile.ZipFile(io.BytesIO(inner_bytes))
                    raw = inner_zf.read(inner_msi_path)
                    return raw.decode("utf-8", errors="replace")

            raise KeyError(f"Cannot locate {source_path} in {zip_path}")
