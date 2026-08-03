# City exposure study

Radio-frequency exposure of people in city squares. Three pieces of work sit
here. They share a subject and almost nothing else, so read this before you go
looking for something.

| Directory | State | What it is |
| --- | --- | --- |
| `semantic_twin/` | live | The current paper. Eleven photogrammetric city squares at 15 GHz, surface materials read out of street-level panoramas, and an adjoint SBR estimator that runs the trace outward from the pedestrian. Start at `semantic_twin/README.md`. |
| `report/` | finished | The older arm, from June. Ten cities at 28 GHz, agents walking, the deterministic ray-traced channel from `aegis.study.run_cities`, and a short LaTeX report. Start at `report/README.md`. |
| `hybrid_twin/` | mostly finished | The sister project. Google and Inhouse 3D tiles plus OSM, assembled in headless Blender, focused on Graslei in Ghent. Shares no code with the other two. Start at `hybrid_twin/README.md`. |
| `archive/` | keep, do not read | Finished material and things nothing reads any more, including a 5.9 GB mirror of a rented GPU box. Described in `archive/README.md`. |

`INVENTORY.md` is the full map: every directory, what it holds, what reads it,
and what was moved where during the 2026-08-03 tidy-up.

## Building the two papers

```bash
# The current paper, 21 pages
cd semantic_twin/paper && latexmk -pdf -interaction=nonstopmode paper.tex

# The older report, 2 pages
cd report && latexmk -pdf -interaction=nonstopmode report.tex
```

## Running the tests

Only `semantic_twin/` has a test suite. It has to be run from that directory,
because the tests import the run scripts sitting next to the package.

```bash
cd semantic_twin
/home/user/aegis/.venv/bin/python -m pytest tests/ -q -p no:randomly
```
