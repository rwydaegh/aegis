import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

# Make tools/circa/ root importable so tests can `from server import ...` and `from cli import ...`.
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Alias `circa_cli` -> the cli module so tests can import either name.
_cli_path = _ROOT / "cli.py"
if _cli_path.exists() and "circa_cli" not in sys.modules:
    spec = importlib.util.spec_from_file_location("circa_cli", str(_cli_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["circa_cli"] = mod
    spec.loader.exec_module(mod)


@pytest.fixture
def paper_dir(tmp_path: Path) -> Path:
    """A temporary paper directory with a tiny.tex copied as paper.tex."""
    src = Path(__file__).parent / "fixtures" / "tiny.tex"
    dst_dir = tmp_path / "paper"
    dst_dir.mkdir()
    shutil.copy(src, dst_dir / "paper.tex")
    return dst_dir
