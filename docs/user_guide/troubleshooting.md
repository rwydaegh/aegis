# Troubleshooting

## Missing mesh data

Symptoms: tests skipped with “slow” or file-not-found errors, or `BodyMesh.load` raises `FileNotFoundError`.

Phantom meshes ship in `data/` inside the repo. If you moved them, set **`AEGIS_DATA_DIR`** to the directory containing your `.stl` files.

## DiffeRT not installed

Symptoms: `ImportError` when calling `paths_from_differt()` or running ray-tracer examples. The module imports fine, but functions raise at call time if the backend is missing.

Install the extra: `pip install -e ".[rt]"`. The core library and most tests run without DiffeRT. Integration tests and live tracing need it.

## Port already in use

Symptoms: viewer fails to bind, or Flask reports the address is in use.

Change the server port in your viewer config (`server.port` in JSON) or pass **`--port`** if your CLI supports it. Close other processes using the same port, or pick a high ephemeral port (e.g. 8765).

## Config issues

Symptoms: viewer loads but wrong scenario, missing keys, or merge behaviour surprises you.

Use **`configs/default.json`** as the reference shape. Scenario blocks only override keys present in the file. For nested objects, deep merge is recursive: it only replaces the specific keys you override, preserving sibling keys you did not mention. See [Interactive viewer](viewer.md) and the files under `configs/`.

## Wrong Python version

AEGIS targets **Python 3.12**. If imports or typing fail on older versions, switch interpreters or use `py -3.12` on Windows.

## Level-specific errors

Messages like “Level 0 requires `A_ab` and `D_max`” mean the kernel needs precomputed geometry. Either supply those arguments to `DosimetryEngine.compute` or use a level that matches your inputs (e.g. 2 or 3 with only mesh plus `PropagationPaths`).

Level **7** requires a `Precoder`. Level **8** requires the UE channel vector `h` (the precoder is optional, defaulting to unit power). Both need full complex `psi` paths, not scalar power.

## TensorDock: connection refused or SSH permission denied

Symptoms: browser cannot open `http://<instance-ip>:5000`, or `ssh user@<ip>` returns **`Permission denied (publickey)`**.

See [Cloud GPU machine](../developer_guide/cloud_machine.md). Run **`python tools/cloud.py status`**: it shows whether port 5000 is public or you need a tunnel. For SSH, pass **`-i`** with the same path as **`TENSORDOCK_SSH_KEY_PATH`** in `.env`, or run **`python tools/cloud.py ssh`** from the repo so the key is picked up automatically.
