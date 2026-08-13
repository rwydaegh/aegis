# Numerical claims audit

The claim functions in `claims/current_results.py` authenticate the current
five-city aggregate, all five campaign manifests and replica shards, the
controlled validation sidecars, the convergence audit, and both paired
material-control reports. They then recompute the manuscript headline values
from those files, including the pooled body-component shares and the retained
directional atom/cell representation.

Run the audit from the repository root:

```bash
uv run --project /home/user/PaperMaker9000 papermaker claims run \
  --code-root semantic_twin/paper/code --banner-on-fail
```

The generated record is `results/claims.json`. Run the focused tests with:

```bash
PYTHONPATH=/home/user/PaperMaker9000 uv run --project semantic_twin pytest -q \
  semantic_twin/paper/code/tests
```

The validation claim keeps three comparators separate. The maximum bounced
adjoint-to-quadrature error is 0.061565 dB. The maximum bounced
adjoint-to-forward difference is 0.062140 dB. The maximum total
adjoint-to-forward difference is 0.034439 dB. These values answer different
questions and must not be substituted for one another in the paper.
