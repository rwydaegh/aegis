# Agent prompt — empirical rank of Q on Thelonious at plaza geometry

*PoC, not a finished experiment. I need one plot + one table before I can lock in §II.7 and Remark 4.5 of `JSAC/paper.tex` ("rank-few regime"). This is a coding task inside the AEGIS repo.*

## The question

For a plausible Brussels-plaza geometry at 26 GHz with an $8{\times}8$ BS panel, what does the eigenvalue spectrum of the per-body coherent exposure operator $\mathbf{Q}^{(u)} = \int_\Sigma \tilde{\mathbf{G}}^H \tilde{\mathbf{G}}\,dA$ actually look like on the Thelonious phantom?

I claim in the JSAC paper (§II.7 and §IV Remark 4.5) that $\mathbf{Q}^{(u)}$ has **"$\sim$3–10 dominant eigenmodes"** in the plaza regime, and that this is an empirical regime observation, not a theoretical simplification. Before the paper ships I need to see the actual spectrum. If dominant rank is 3–5, the "rank-few" story in §IV stands. If it's 15+, I rewrite §IV to lead with the coherent operator and mention rank-few only as a niche.

## What I need back

1. **A CDF / scree plot**: $\lambda_k(\mathbf{Q}^{(u)}) / \lambda_1$ on a log scale for $k = 1, \dots, M$, averaged across $\ge 20$ body positions drawn from the scene below. Overlay individual body curves lightly.
2. **A table** with $\varepsilon$-effective rank at $\varepsilon \in \{10^{-1}, 10^{-2}, 10^{-3}\}$, reporting median, 10th, and 90th percentiles across bodies.
3. **One-paragraph written takeaway** — does the spectrum support "rank-few (3–10)" or is it higher? If higher, at what number does the tail fall into the noise floor of AEGIS numerics?

## Scenario

- Carrier: 26 GHz.
- BS: $M = 64$ ($8 \times 8$) panel. Reasonable defaults for mounting height (~8 m) and orientation toward the plaza are fine; if you want to match paper §VI, point down at 10° tilt.
- Phantom: **Thelonious** (default AEGIS phantom). SMPL-X is not required — the static STL pose is enough for a spectrum check. If you want pose variation use a second or third static pose from the monograph's backflip frames; not critical.
- Body positions: spread 20 bodies across a 20–80 m range ring in front of the BS, random azimuth within $\pm 60°$. Vary elevation plausibly (standing adult feet on ground).
- Propagation: whichever ray tracer is most convenient — DiffeRT or Sionna-RT if already wired in, or a hand-rolled LOS + ground-bounce + 2 building-facade specular reflections. The rank claim is robust to the particular ray tracer; we mostly care that there are multiple distinguishable incident paths per body.

## Where to start in the repo

- `src/aegis/coherent/exposure_operator.py` — the canonical $\mathbf{Q}$ assembly from the tissue-weighted field channel. This is the exact operator the paper cites.
- `src/aegis/coherent/field_channel.py` — $\tilde{\mathbf{G}}$ construction.
- `src/aegis/coherent/body_channel.py` — how paths + body surface come together.
- `src/aegis/mimo/compute.py` lines ~110–130 — a full example of `compute_exposure_operator(G_tilde, areas)` in flight.
- `src/aegis/kernels/level7_coherent.py` — level-7 kernel is the coherent-regime one.
- `src/aegis/integration/` — ray tracer bridge (DiffeRT) if you want per-body paths from a scene.
- `src/aegis/_array_backend.py` — JAX / NumPy backend toggle. `AEGIS_ARRAY_BACKEND=jax` for speed if you have JAX + GPU; NumPy is fine for 20 bodies.
- `data/phantoms/` — Thelonious STL lives here. The `AEGIS_DATA_DIR` env var can override if needed.

Look at `tests/test_coherent.py` / `tests/test_exposure_operator.py` for working invocation patterns. The CLI `python -m aegis.viewer --scenario open_ground` can also serve as a jumping-off point for a minimal scene.

## What I do NOT want

- A full simulation pipeline with telemetry, NN, precoder, etc. That is what the paper's §VI does. **This prompt is just: spectrum of $\mathbf{Q}^{(u)}$ for one phantom, one pose, under a realistic plaza path set.**
- Performance optimisation. Slow-but-correct beats fast.
- Novel methods. The goal is to observe what the spectrum looks like, not to design around it.
- To deposit results in the paper. Put the plot + table in `JSAC/experiments/rank_check/` (create if needed) and summarise findings in a markdown there. I'll integrate into the paper myself.

## Output location

- Code → `JSAC/experiments/rank_check/*.py` (or a notebook, your call).
- Plot → `JSAC/experiments/rank_check/rank_cdf.{pdf,png}`.
- Table → `JSAC/experiments/rank_check/rank_table.md`.
- Written takeaway → `JSAC/experiments/rank_check/README.md` with: one paragraph, then the plot, then the table.

## Why this matters

The JSAC paper (`JSAC/paper.tex`) currently has `\TODO{...rank empirical check on Thelonious pending...}` in §II.7. Fixing that TODO either confirms the rank-few framing I've written or forces a small restructure. The coherent operator stays either way — this is about the empirical observation in §VI, not the core theory.
