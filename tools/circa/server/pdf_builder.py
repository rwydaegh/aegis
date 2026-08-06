from __future__ import annotations
import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BuildResult:
    ok: bool
    error_tail: str = ""
    timed_out: bool = False


class PdfBuilder:
    def __init__(self, paper_dir: Path, build_timeout_s: int = 120, tex_name: str = "paper.tex") -> None:
        self.paper_dir = paper_dir
        self.timeout = build_timeout_s
        self.tex_name = tex_name
        self.stem = Path(tex_name).stem
        self._lock = asyncio.Lock()

    async def build(self) -> BuildResult:
        async with self._lock:
            return await asyncio.to_thread(self._blocking)

    def _blocking(self) -> BuildResult:
        cmd = ["pdflatex", "-interaction=nonstopmode", "-file-line-error", self.tex_name]
        try:
            for _ in range(2):
                r = subprocess.run(
                    cmd, cwd=self.paper_dir, capture_output=True, text=True, timeout=self.timeout
                )
                if r.returncode != 0:
                    return BuildResult(ok=False, error_tail=self._tail_log())
            return BuildResult(ok=True)
        except subprocess.TimeoutExpired:
            return BuildResult(ok=False, error_tail="pdflatex timed out", timed_out=True)

    def _tail_log(self) -> str:
        log = self.paper_dir / f"{self.stem}.log"
        if not log.exists():
            return ""
        return "\n".join(log.read_text(errors="replace").splitlines()[-50:])
