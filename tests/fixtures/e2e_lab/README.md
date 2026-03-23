# E2E lab fixture

`e2e_icosahedron.stl` is the same 20-triangle icosahedron as `make_icosahedron()` in `tests/conftest.py` (10 cm sphere, Z-up).

Regenerate after changing the conftest geometry:

```bash
py -3.12 -c "
from pathlib import Path
import sys
sys.path.insert(0, str(Path('tests').resolve()))
from conftest import make_icosahedron
make_icosahedron().save_binary_stl(Path('tests/fixtures/e2e_lab/e2e_icosahedron.stl'))
"
```

Launch the viewer for manual checks or Playwright against this data:

```bash
py -3.12 -m aegis.viewer --config configs/e2e_lab.json --no-open
```
