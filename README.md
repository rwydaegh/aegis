# AEGIS

**Adaptive Electromagnetic Geometric Illumination & Safety**

GPU-accelerated geometric dosimetry engine for wireless exposure assessment.

AEGIS computes absorbed power density on human bodies by exploiting the geometric nature of dosimetry. It replaces volumetric EM simulation with surface operations, providing nine fidelity levels from O(1) bounds to coherent MIMO beamforming.

## Installation

```bash
pip install aegis
```

For development:

```bash
git clone https://github.com/rwydaegh/aegis.git
cd aegis
uv pip install -e ".[dev]"
pytest
```

## Documentation and viewer

- [Documentation site source](docs/index.md): run `py -3.12 -m mkdocs serve` after `pip install -e ".[docs]"`.
- **3D viewer**: `py -3.12 -m aegis.viewer` (see [docs/user_guide/viewer.md](docs/user_guide/viewer.md)).

## License

Apache-2.0
