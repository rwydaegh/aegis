# plaza_run NPZ replay viewer

A standalone Three.js + Flask scene that replays the trajectories and per-slot P_abs from a brief 08 NPZ. Hacky on purpose; bypasses the main aegis viewer to keep the contract simple.

## Run

```bash
python -m JSAC.code.experiments.plaza_run.replay.server
```

Open <http://127.0.0.1:5050/>.

The server auto-runs `prepare_data.py` on first launch to bake `replay_data.json` from the canonical NPZ (`specular_aware`). Re-run `prepare_data.py` directly to swap to a different NPZ (edit the `npz_label` arg).

## What it shows

- A synthetic plaza ring (matches the path generator's facade assumptions; not the real Brussels OSM scrape, since Overpass was unreachable when this was built)
- The BS panel as a small backplane with an 8x8 grid of glowing red dots, plus a yellow broadside arrow
- 50 capsule bodies sized ~1.7 m tall, colored each frame by P_abs / L_RL on a log scale (legend top-right)
- Faint orange beam lines from the BS to each of the 25 served (tier A) bodies, updated per frame
- HUD top-left with current slot, time, precoder, sum-rate, max P_abs/L
- Bottom controls bar: Play / time slider / precoder dropdown / playback speed

## Files

| File | Purpose |
|---|---|
| `prepare_data.py` | Bakes the NPZ + synthetic plaza geometry into `replay_data.json` |
| `index.html` | Self-contained Three.js page (importmap to unpkg CDN) |
| `server.py` | 25-line Flask app, port 5050 |
| `replay_data.json` | Bundled scene + decimated trajectories (~950 KB) |
| `preview.png` | Static screenshot for paper / promotor handoff |

The NPZ is decimated by 5 slots → 120 keyframes from the 600-slot run. Replay speed is configurable via the dropdown.

## Limitations

- Plaza geometry is synthetic (4 facade rings + ground), not real OSM. Replace `synthetic_plaza_buildings()` in `prepare_data.py` with a load of `data/scenes/brussels_grand_place/mesh.npz` once the OSM scrape lands.
- Bodies are uniform capsules, not posed SMPL-X meshes. The pose stream isn't visualized; only the root translation animates.
- No per-vertex P_abs colormap on the body surface. P_abs is shown via whole-body capsule color.
- The first 30 slots have sumrate ~ 0.1 Mbps because the channel is degenerate before the first pose-cadence rebuild. The page defaults to keyframe 15 (slot 75) so it doesn't open on the cold-start.
