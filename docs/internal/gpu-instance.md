# Live GPU instance (shared)

A GPU pod is up on RunPod for AEGIS work. This doc is infra only: what it is and how to reach it. Multiple agents may use it in parallel, so coordinate and do not stop or destroy it without checking.

Last updated: 2026-05-31.

## The box

- Provider: RunPod (community cloud), pod name `aegis-gpu-val`, pod id `b81qnoxslrg64e`
- GPU: NVIDIA RTX A4000, 16 GB VRAM
- CPU/RAM: 14 vCPU, ~62 GB RAM, 40 GB container disk (ephemeral, no persistent volume)
- OS: Ubuntu 24.04.4, Python 3.12.3, NVIDIA driver 550.144 (CUDA 12.4 capable)
- Cost: ~$0.17/hr. RunPod balance is low (was ~$6.45), so be mindful and stop it when idle.

## SSH access (from this dev box)

```bash
ssh -i /home/user/.runpod/ssh/runpodctl-ssh-key -p 1881 \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    root@193.183.22.53
```

Robin's `runpod_april26` key is also injected on the pod, so `ssh -i /home/user/aegis/runpod_april26 -p 1881 root@193.183.22.53` works too (use for Zed over SSH: copy that key to your laptop).

Note: the IP and port can change if the pod is stopped and restarted. Re-read them with `runpodctl ssh info b81qnoxslrg64e`.

## What is already set up on the pod

- AEGIS is at `/workspace/aegis` (rsynced from `/home/user/aegis`, `.git` excluded).
- A venv is at `/workspace/aegis/.venv`, installed with `uv pip install -e ".[gpu,sionna,dev]"`.
  - `jax` 0.10.1 sees `CudaDevice(id=0)`, Sionna RT 2.0.1 defaults to `cuda_ad_mono_polarized`. Both run on the GPU.
- Activate with `cd /workspace/aegis && source .venv/bin/activate`.
- Data: only the small essentials were synced (STL phantoms, `itis_v5.db`). The 36 GB AMASS poses and antenna patterns were NOT synced (would not fit the 40 GB disk).
- Because `.git` was excluded, any `pip install -e .` reinstall needs `SETUPTOOLS_SCM_PRETEND_VERSION=0.33.0` (hatch-vcs has no git to read).

## Running AEGIS on the GPU

- Backend select: `AEGIS_ARRAY_BACKEND=jax` puts the dosimetry kernel on the GPU. Default is `numpy` (CPU).
- Sionna RT uses the GPU automatically (Mitsuba cuda variant).
- Recommended JAX memory flags (Mitsuba and JAX co-reside on the 16 GB):
  ```bash
  export XLA_PYTHON_CLIENT_PREALLOCATE=false
  export XLA_PYTHON_CLIENT_MEM_FRACTION=0.45
  ```

## Memory and the fp64 penalty (read before profiling dosimetry)

The full-resolution coherent dosimetry (duke phantom, 56k triangles) now FITS
in 16 GB as of commit ec1fab91. The level-7 kernel and the static gram build
both materialize a per-triangle intermediate ((paths x triangles x 3) and
(triangles x N_c x 3 x M_ant)) that peaked at tens of GB; both are now chunked
over triangles (additive in Q/M_static, per-triangle in sab, so exact). Tune
the block size with `AEGIS_TRI_CHUNK_MN` (default 6e6 m*n pairs) and
`AEGIS_GRAM_CHUNK_ELEMS` (default 3.2e7 elements). Lower them if you still OOM
while Mitsuba co-resides.

But this card is the WRONG tool for complex128 dosimetry. The A4000 is a
GeForce-class die with gimped fp64 (~1/32 of fp32). Measured full Ghent-core
recompute (85 paths, 64 elements):

| step      | CPU    | GPU (A4000) |
|-----------|--------|-------------|
| ray trace | 0.12 s | 0.27 s      |
| Sab map   | 105 s  | 26.8 s  (3.9x faster) |
| gram      | 5.6 s  | 104.8 s (18.7x SLOWER, fp64-bound) |

So full recompute is CPU 110 s vs GPU 131 s: on this card CPU wins. The gram's
inner c128 matmul is fp64-bound. For the GPU to win you want a real-fp64
datacenter card (A100/H100, fp64 1:2) OR a complex64 gram path (a precision
decision, not yet implemented). The Sab map alone is a clean 3.9x GPU win.

## Managing the box (from this dev box)

The CLIs are installed and authenticated at `~/.local/bin`:

```bash
runpodctl pod get b81qnoxslrg64e      # status and details
runpodctl ssh info b81qnoxslrg64e     # current ip/port
runpodctl pod stop b81qnoxslrg64e     # stop (halt billing; may lose ephemeral disk)
runpodctl pod remove b81qnoxslrg64e   # destroy
```

`vastai` is also installed and authenticated as a fallback provider (`~/.local/bin/vastai`), but no Vast instance is currently running.
