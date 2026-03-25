# Tutorials

Hands-on Python tutorials for the AEGIS dosimetry engine. Each tutorial is a self-contained script that runs after `pip install -e ".[viz]"` with no STL files or external data required. Synthetic meshes (spheres, cylinders) stand in for human body phantoms.

## Formats

Every tutorial is available in two formats:

- **Documentation pages** (you are here) - read the tutorials with rendered equations and explanations
- **Jupyter notebooks** in the [`notebooks/`](https://github.com/rwydaegh/aegis/tree/master/notebooks) directory - run the tutorials interactively, cell by cell

The markdown files in `docs/tutorials/` are the source of truth. Notebooks are generated from them using [Jupytext](https://jupytext.readthedocs.io/) via a sync script. To regenerate after editing a tutorial:

```bash
python tools/sync_notebooks.py
```

The notebooks are numbered (`01_quickstart.ipynb`, `02_fidelity_levels.ipynb`, ...) to reflect the recommended reading order.

## Contents

1. **[The geometric absorption law](quickstart.md)** -- Core equation, single plane wave, ReLU projection, multipath superposition
2. **[Fidelity levels and convergence](fidelity_levels.md)** -- The nine-level computational hierarchy, sweep_levels, level comparison plots
3. **[Tissue physics and Fresnel transmission](tissue_and_fresnel.md)** -- Cole-Cole model, pseudo-Brewster compensation, angle-dependent transmission
4. **[ICNIRP 2020 compliance](compliance.md)** -- Regulatory limits, compliance evaluation, power sweeps, link budget analysis
5. **[Coherent MIMO and ECBF](coherent_mimo.md)** -- Field channel, exposure operator Q, MRT beamforming, exposure-constrained precoding

Each tutorial references equations from the AEGIS monograph and explains the underlying physics alongside the code.
