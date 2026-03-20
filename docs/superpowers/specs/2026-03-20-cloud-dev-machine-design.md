# Cloud dev machine manager

**Date:** 2026-03-20
**Status:** Approved

## Problem

AEGIS needs a Linux + GPU machine for development: running tests on Linux, porting kernels to JAX/CUDA, benchmarking, and serving the viewer remotely. No local GPU available. TensorDock provides on-demand cloud GPUs. Currently all interaction with TensorDock is manual curl commands. We need a proper tool.

## Solution

A single Python script `tools/cloud.py` that manages the full lifecycle of a TensorDock dev machine. Draws on patterns from the GOLIAT `cloud_setup/` scripts but cleaner and tailored to AEGIS.

## Commands

```
python tools/cloud.py up        # Provision new OR wake stopped machine
python tools/cloud.py down      # Stop machine (preserves disk, stops compute billing)
python tools/cloud.py destroy   # Delete machine entirely
python tools/cloud.py sync      # Pull latest code + reinstall on running machine
python tools/cloud.py ssh       # Open an SSH session
python tools/cloud.py status    # Show machine state, IP, cost, GPU
```

## State detection (`up` command)

The `up` command checks state and does the right thing:

1. **No machine exists** -> provision new one, wait for SSH, run full bootstrap
2. **Machine exists but stopped** -> start it, wait for SSH, re-query IP/ports (may change on wake), update state file, run sync
3. **Machine already running** -> just run sync

State is tracked in `tools/.cloud-state.json` (gitignored via new `.gitignore` entry). The script validates against the TensorDock API in case someone manually deleted the machine from the dashboard. If the API returns 404 for a stored instance ID, the state file is cleared and the user is prompted.

### SSH wait logic

After provisioning or waking, the script polls SSH readiness:
- Poll interval: 5 seconds
- Max wait: 120 seconds
- On timeout: print error with instance ID, leave machine running (user can retry or destroy manually)

## Configuration

### Secrets (`.env`, already gitignored)

```
TENSORDOCK_API_KEY=<bearer token from TensorDock dashboard>
TENSORDOCK_SSH_KEY_PATH=~/.ssh/tensordock_ed25519
```

The TensorDock v2 API uses a single Bearer token for authentication (not a key+secret pair). Generate one at Dashboard > Developer Settings.

### State file (`tools/.cloud-state.json`, gitignored)

```json
{
  "instance_id": "uuid",
  "ip": "1.2.3.4",
  "ssh_port": 47906,
  "viewer_port": 50123,
  "gpu": "rtxa4000-pcie-16gb",
  "status": "running"
}
```

### Defaults (hardcoded, overridable via CLI flags)

- Image: `ubuntu2404`
- GPU: cheapest available A4000 (fallback to RTX 3090)
- Resources: 2 vCPU, 4GB RAM, 100GB storage
- Ports forwarded: 22 (SSH), 5000 (viewer)
- SSH user: `user` (TensorDock default)

### SSH key

The script checks if `TENSORDOCK_SSH_KEY_PATH` exists. If not, generates a new ed25519 key automatically. The public key is passed inline to the TensorDock create-instance API via the `ssh_key` field (no separate registration step needed).

## Bootstrap (fresh machine)

When `up` provisions a new machine, it SSHes in and runs `tools/cloud-bootstrap.sh`. Each step is guarded by a check so running the script twice skips already-completed steps:

1. **System packages:** `apt update`, `git`, `curl`, `nodejs` (via nodesource). Guard: `which git`, `which node`.
2. **Python 3.12:** Install `python3.12`, `python3.12-venv` from deadsnakes PPA. Guard: `python3.12 --version`.
3. **CUDA verification:** Confirm `nvidia-smi` works (TensorDock images have drivers pre-installed). Fail loudly if missing.
4. **Clone repo:** `git clone` the AEGIS repo from GitHub into `~/aegis`. Guard: `test -d ~/aegis/.git`.
5. **Python env:** Create venv at `~/aegis/.venv`, `pip install -e ".[dev,gpu]"`. The `[gpu]` extra pulls JAX+CUDA (2+ GB, can take several minutes). Guard: `test -d ~/aegis/.venv`. SSH connection uses `ServerAliveInterval` to prevent timeout during long installs.
6. **Firewall:** `ufw allow <ssh_port>/tcp`, `ufw allow <viewer_port>/tcp`, `ufw --force enable`. Deny everything else by default.
7. **Claude Code:** `npm install -g @anthropic-ai/claude-code`. Guard: `which claude`. One-time `claude /login` via SSH port forwarding done manually by user afterward.
8. **Viewer auth:** Generate random password, write to `~/.aegis-viewer-auth`, print to terminal.

### Sync (wake or manual)

On wake (stopped machine restarted) or explicit `sync` command:

```bash
cd ~/aegis && git pull --rebase origin master
source .venv/bin/activate && pip install -e ".[dev,gpu]"
```

The `sync` command checks that `~/aegis/.git` exists. If not (e.g., bootstrap failed partway), it falls back to running the full bootstrap.

## Viewer auth

When the env var `AEGIS_VIEWER_AUTH` is set (format: `user:password`), the Flask viewer adds a `@before_request` hook that checks HTTP Basic Auth on all routes. Unset locally so no change to local dev workflow. The bootstrap script sets it on the remote machine.

Note: Basic Auth sends credentials in cleartext over HTTP. Acceptable for a dev tool on a non-sensitive viewer. Not suitable for production.

### SSH config convenience

The `up` command prints an SSH config block that can be appended to `~/.ssh/config`:

```
Host aegis-dev
    HostName 1.2.3.4
    Port 47906
    User user
    IdentityFile ~/.ssh/tensordock_ed25519
```

This lets VS Code Remote-SSH pick up the machine automatically (connect to host "aegis-dev").

## Interaction patterns

### Developer (VS Code Remote-SSH)

1. Run `python tools/cloud.py up`
2. VS Code Remote-SSH connects to "aegis-dev" (auto-configured in SSH config)
3. Work normally: edit, test, run viewer
4. VS Code auto-tunnels ports (Flask viewer accessible at localhost:5000)
5. Run `python tools/cloud.py down` when done

### Claude Code on remote machine

1. Machine already running (via `up`)
2. SSH in with port forwarding: `ssh -L 8080:localhost:8080 aegis-dev`
3. Run `claude /login` once, open the localhost URL in local browser
4. Claude Code uses Max subscription (not API key billing)
5. Subsequent sessions: just SSH in, `claude` works

### Quick test cycle

1. Push changes locally
2. `python tools/cloud.py sync` (pulls on remote, reinstalls)
3. SSH in and run tests: `pytest tests/ -m "not slow" -x`

### Remote viewer access

1. Machine running with viewer port forwarded
2. Open `http://<ip>:<viewer_port>` in local browser
3. HTTP Basic Auth prompt (credentials from bootstrap)
4. Full 3D viewer in browser, compute running on GPU

## Cost awareness

The `status` command shows uptime and estimated cost since last start. If the machine has been running for more than 4 hours, it prints a warning.

## Files

| File | Description |
|------|-------------|
| `tools/cloud.py` | CLI: up/down/destroy/sync/ssh/status |
| `tools/cloud-bootstrap.sh` | First-time machine setup (runs on remote) |
| `.env` (additions) | `TENSORDOCK_API_KEY`, `TENSORDOCK_SSH_KEY_PATH` |
| `tools/.cloud-state.json` | Instance state (gitignored, auto-generated) |
| `.gitignore` (addition) | `tools/.cloud-state.json` entry |
| `src/aegis/viewer/server.py` | Add `@before_request` Basic Auth hook gated on `AEGIS_VIEWER_AUTH` env var |

## Dependencies

- `requests` - HTTP client for TensorDock API. Not currently in `pyproject.toml`. Add to a new `[cloud]` optional group.
- `subprocess` - SSH commands (stdlib, no install needed)
- `.env` loading - use stdlib (`open` + `str.split`), no `python-dotenv` dependency

## Future evolution

If this outgrows one file, split into `tools/cloud/` with `api.py`, `cli.py`, `bootstrap.sh`. For now, a single file is sufficient. Long term, the remote machine could become a persistent backend server, but that is out of scope for this design.
