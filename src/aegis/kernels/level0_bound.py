"""Level 0: Worst-case power bound."""

from __future__ import annotations

from functools import partial

from aegis._array_backend import jit, xp


@partial(jit, static_argnums=(0, 1, 2, 4, 5))
def level0_bound(total_area, A_ab, D_max, power, T0, n_triangles):
    """Compute worst-case absorbed power bound."""
    S_total = xp.sum(power)
    p_abs_bound = T0 * (A_ab * D_max / 4.0) * S_total
    sab_uniform = p_abs_bound / total_area if total_area > 0 else 0.0
    sab = xp.full(n_triangles, sab_uniform)
    return sab, p_abs_bound
