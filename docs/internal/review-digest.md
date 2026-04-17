# Review digest

Tier-3 findings from code-review-swarm runs. One line per entry. These
are **faint unease** items -- things a reviewer noticed but couldn't
articulate well enough to file an issue. Most are noise. A few compound
into something actionable over time.

## How to use

- Read weekly. It takes 2-3 minutes.
- If two entries point at the same file/concern, that's worth a real
  look.
- Stale entries (> 1 month, area since reworked) can be pruned.

## Format

```
- YYYY-MM-DD | <file:line> | <one sentence of unease> | reviewer #N, run <id>
```

## Entries

<!-- newest first -->

- 2026-04-17 | src/aegis/coherent/ecbf.py:130 | Slack-regime guard is eigenvalues[0] > NUMERICAL_FLOOR (=1e-30), effectively "eigenvalue != 0"; a true-singular Q with h perpendicular to null(Q) skips the slack branch and falls through to the infeasibility warning, returning the null-direction (objective=0) instead of the pseudo-inverse slack optimum. Constructable but unlikely in production (Q from MIMO channel is typically full-rank). | reviewer #5, run 24565798246
- 2026-04-17 | src/aegis/viewer/routes/compute/dosimetry.py:281 and 234 | antennas[i].power_dbm and main power_dbm floats are parsed without math.isfinite guards; float("nan") succeeds, NaN < min and NaN > max are both False, so NaN bypasses the range check. Downstream _sanitize_for_json masks the NaN in JSON but raw binary Sab bytes can contain NaN. Pre-existing gap (not introduced by #541) similar to the one #461 closed for freq_hz. | reviewer #5, run 24565798246
