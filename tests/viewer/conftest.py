"""Auto-skip viewer tests when Flask (optional dep) is not installed."""

import pytest

flask = pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")
