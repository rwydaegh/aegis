# Troubleshooting

## Missing mesh data

Symptoms: tests skipped with “slow” or file-not-found errors, or `BodyMesh.load` raises `FileNotFoundError`.

Phantom meshes ship in `data/` inside the repo. If you moved them, set **`AEGIS_DATA_DIR`** to the directory containing your `.stl` files.

## DiffeRT not installed

Symptoms: `ImportError` when importing `aegis.integration` or running ray-tracer examples.

Install the extra: `pip install -e ".[rt]"`. The core library and most tests run without DiffeRT; integration tests and live tracing need it.

## Port already in use

Symptoms: viewer fails to bind, or Flask reports the address is in use.

Change the server port in your viewer config (`server.port` in JSON) or pass **`--port`** if your CLI supports it. Close other processes using the same port, or pick a high ephemeral port (e.g. 8765).

## Config issues

Symptoms: viewer loads but wrong scenario, missing keys, or merge behaviour surprises you.

Use **`configs/default.json`** as the reference shape. Scenario blocks only override keys present in the file; unknown keys are not supported. For nested objects, deep merge replaces whole sibling branches where you specify overrides. See [Interactive viewer](viewer.md) and the files under `configs/`.

## Wrong Python version

AEGIS targets **Python 3.12**. If imports or typing fail on older versions, switch interpreters or use `py -3.12` on Windows.

## Level-specific errors

Messages like “Level 0 requires `A_ab` and `D_max`” mean the kernel needs precomputed geometry. Either supply those arguments to `DosimetryEngine.compute` or use a level that matches your inputs (e.g. 2 or 3 with only mesh plus `PropagationPaths`).

Coherent levels **7 and 8** need `Precoder` and, for level 8, the UE channel vector `h`. Scalar-power paths alone are not enough.
