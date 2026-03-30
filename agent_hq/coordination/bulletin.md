# Agent bulletin board

Agents: read this at the start of your run. Append findings at the end.
Prune entries older than 7 days.

## Recent findings

<!-- Newest on top. Format: [YYYY-MM-DD HH:MM] agent-name: finding -->

- [2026-03-30] feature-agent: Vectorized multi-stream coherent_sinc (engine.py:68-73) from K-loop to single einsum. Fixed averaging cache from FIFO to LRU eviction. Fixed EventSource leak in ScenePanel (double-click load). Added notification de-duplication (3s window).

## Do not touch

<!-- Things agents have investigated and confirmed are correct or intentional -->

- Curvature_H negative values in level 5 kernel (intentional per monograph eq. 47)
- Fresnel T_avg > T0 near Brewster angle (physically correct, see physics-findings)

## In progress

<!-- Mark what you are working on to avoid collisions. Clear after merge or if stale >6h -->
