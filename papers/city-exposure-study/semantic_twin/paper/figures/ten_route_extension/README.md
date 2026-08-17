# Ten-route production-contract extension

`ten_route_extension.py` reads the authenticated ten-route report, verifies its
artifact manifest, and writes the supplement figure as vector PDF and a 300-dpi
PNG companion. The left panel shows the route-level normalized whole-body-SAR
quantiles. The right panel shows route-summed additive absorbed-power shares.

Run from `semantic_twin/paper`:

```bash
uv run --project .. python figures/ten_route_extension/ten_route_extension.py
```

The script refuses to plot if the report manifest or any compact report artifact
has changed. `ten_route_extension.audit.json` records the source and output hashes.
