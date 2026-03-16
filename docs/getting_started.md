# Getting started

## Installation

```bash
pip install aegis
```

For development:

```bash
git clone https://github.com/rwydaegh/aegis.git
cd aegis
uv pip install -e ".[dev]"
```

## Optional dependencies

```bash
uv pip install -e ".[viz]"   # matplotlib, pyvista, trame
uv pip install -e ".[gpu]"   # JAX with CUDA
uv pip install -e ".[docs]"  # mkdocs
uv pip install -e ".[all]"   # everything
```
