import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional

from . import paths


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class SnapshotManager:
    def __init__(self, paper_dir: Path) -> None:
        self.paper_dir = paper_dir
        self.paper_tex = paper_dir / "paper.tex"

    def take_snapshot(self, batch_id: str) -> None:
        dst = paths.snapshots_dir(self.paper_dir) / f"{batch_id}.tex"
        shutil.copy(self.paper_tex, dst)
        sha_pre = _sha256(self.paper_tex)
        with paths.snapshots_ledger(self.paper_dir).open("a") as f:
            f.write(json.dumps({"batch_id": batch_id, "sha256_pre": sha_pre, "sha256_post": None}) + "\n")

    def record_post_sha(self, batch_id: str) -> None:
        sha_post = _sha256(self.paper_tex)
        ledger = paths.snapshots_ledger(self.paper_dir)
        rewritten = []
        for line in ledger.read_text().splitlines():
            if not line:
                continue
            entry = json.loads(line)
            if entry["batch_id"] == batch_id and entry.get("sha256_post") is None:
                entry["sha256_post"] = sha_post
            rewritten.append(json.dumps(entry))
        ledger.write_text("\n".join(rewritten) + "\n")

    def get_post_sha(self, batch_id: str) -> Optional[str]:
        for line in paths.snapshots_ledger(self.paper_dir).read_text().splitlines():
            if not line:
                continue
            entry = json.loads(line)
            if entry["batch_id"] == batch_id:
                return entry.get("sha256_post")
        return None

    def revert(self, batch_id: str, force: bool) -> None:
        if not force:
            current = _sha256(self.paper_tex)
            recorded = self.get_post_sha(batch_id)
            if recorded is None or current != recorded:
                raise RuntimeError(
                    f"paper.tex sha256 differs from recorded sha256_post for batch {batch_id}; use --force"
                )
        snap = paths.snapshots_dir(self.paper_dir) / f"{batch_id}.tex"
        shutil.copy(snap, self.paper_tex)
