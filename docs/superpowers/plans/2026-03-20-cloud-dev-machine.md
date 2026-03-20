# Cloud dev machine implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single `tools/cloud.py` script that provisions, wakes, syncs, and tears down a TensorDock GPU dev machine for AEGIS development.

**Architecture:** One Python script with an argparse CLI, a TensorDock API client (using `requests`), SSH helpers via `subprocess`, and a local JSON state file. A separate bash script handles first-boot setup on the remote machine. The Flask viewer gets a small auth hook for remote access.

**Tech Stack:** Python 3.12, requests, subprocess, TensorDock v2 API, SSH, bash

**Spec:** `docs/superpowers/specs/2026-03-20-cloud-dev-machine-design.md`

---

## File map

| File | Action | Responsibility |
|------|--------|----------------|
| `tools/cloud.py` | Create | CLI entry point, TensorDock API client, SSH helpers, state management |
| `tools/cloud-bootstrap.sh` | Create | First-boot setup script (runs on remote Linux machine) |
| `.env` | Modify | Add `TENSORDOCK_API_KEY`, `TENSORDOCK_SSH_KEY_PATH` |
| `.gitignore` | Modify | Add `tools/.cloud-state.json` |
| `pyproject.toml` | Modify | Add `cloud` optional dependency group with `requests` |
| `src/aegis/viewer/server.py` | Modify | Add Basic Auth `@before_request` hook gated on `AEGIS_VIEWER_AUTH` |
| `tests/test_viewer_auth.py` | Create | Test the viewer auth hook |

---

### Task 1: Project scaffolding

**Files:**
- Modify: `.gitignore`
- Modify: `.env`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `tools/.cloud-state.json` to `.gitignore`**

Append to `.gitignore`:
```
# Cloud dev machine state (local, auto-generated)
tools/.cloud-state.json
```

- [ ] **Step 2: Add TensorDock env vars to `.env`**

Append to `.env`:
```
TENSORDOCK_API_KEY=<your-bearer-token-from-tensordock-dashboard>
TENSORDOCK_SSH_KEY_PATH=~/.ssh/tensordock_ed25519
```

- [ ] **Step 3: Add `cloud` optional dependency group to `pyproject.toml`**

Add after the `dev` group:
```toml
cloud = ["requests>=2.31"]
```

Update the `all` group:
```toml
all = ["aegis[gpu,viz,rt,docs,dev,cloud]"]
```

- [ ] **Step 4: Commit scaffolding**

```bash
git add .gitignore .env pyproject.toml
git commit -m "Add cloud dev machine scaffolding (gitignore, env vars, requests dep)"
```

---

### Task 2: TensorDock API client and .env loader in `tools/cloud.py`

**Files:**
- Create: `tools/cloud.py`

This task builds the foundation: env loading, API helpers, and the `status` command.

- [ ] **Step 1: Create `tools/cloud.py` with env loader and API client**

The `.env` loader is a simple stdlib function (no `python-dotenv` dependency). The API client wraps `requests` with the Bearer token.

```python
"""TensorDock dev machine manager for AEGIS.

Usage:
    python tools/cloud.py up        # Provision new OR wake stopped machine
    python tools/cloud.py down      # Stop machine (preserves disk)
    python tools/cloud.py destroy   # Delete machine entirely
    python tools/cloud.py sync      # Pull latest code on remote
    python tools/cloud.py ssh       # Open SSH session
    python tools/cloud.py status    # Show machine state
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).parent
STATE_FILE = TOOLS_DIR / ".cloud-state.json"
REPO_ROOT = TOOLS_DIR.parent

API_BASE = "https://dashboard.tensordock.com/api/v2"
DEFAULT_IMAGE = "ubuntu2404"
DEFAULT_VCPUS = 2
DEFAULT_RAM_GB = 4
DEFAULT_STORAGE_GB = 100
DEFAULT_SSH_USER = "user"
SSH_POLL_INTERVAL = 5
SSH_MAX_WAIT = 120

# GPU preference order (cheapest first)
GPU_PREFERENCES = [
    "rtxa4000-pcie-16gb",
    "geforcertx3090-pcie-24gb",
    "geforcertx4090-pcie-24gb",
]


# ---------------------------------------------------------------------------
# .env loader (stdlib only, no python-dotenv)
# ---------------------------------------------------------------------------

def load_dotenv(path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv(REPO_ROOT / ".env")


def get_api_key() -> str:
    key = os.environ.get("TENSORDOCK_API_KEY", "")
    if not key:
        print("Error: TENSORDOCK_API_KEY not set in .env or environment.")
        sys.exit(1)
    return key


def get_ssh_key_path() -> Path:
    raw = os.environ.get("TENSORDOCK_SSH_KEY_PATH", "~/.ssh/tensordock_ed25519")
    return Path(os.path.expanduser(raw))


# ---------------------------------------------------------------------------
# TensorDock API client
# ---------------------------------------------------------------------------

def api_request(method: str, path: str, json_body: dict | None = None) -> dict | list | None:
    """Make an authenticated request to the TensorDock v2 API."""
    import requests

    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = requests.request(method, url, headers=headers, json=json_body, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# State file management
# ---------------------------------------------------------------------------

def load_state() -> dict | None:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def clear_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


# ---------------------------------------------------------------------------
# Instance queries
# ---------------------------------------------------------------------------

def get_instance(instance_id: str) -> dict | None:
    """Fetch instance details from API. Returns None if not found."""
    return api_request("GET", f"/instances/{instance_id}")


def find_cheapest_location() -> tuple[str, str, float]:
    """Find the cheapest available GPU location. Returns (location_id, gpu_name, price)."""
    data = api_request("GET", "/locations")
    locations = data.get("data", {}).get("locations", [])

    best = None
    for loc in locations:
        for gpu in loc.get("gpus", []):
            name = gpu.get("v0Name", "")
            if name not in GPU_PREFERENCES:
                continue
            net = gpu.get("network_features", {})
            if not net.get("port_forwarding_available"):
                continue
            price = gpu.get("price_per_hr", 999)
            pref = GPU_PREFERENCES.index(name)
            candidate = (pref, price, loc["id"], name)
            if best is None or candidate < best:
                best = candidate

    if best is None:
        print("Error: No available location with a supported GPU and port forwarding.")
        sys.exit(1)

    _, price, loc_id, gpu_name = best
    return loc_id, gpu_name, price
```

- [ ] **Step 2: Verify the module loads and API response shapes are correct**

Run: `py -3.12 -c "exec(open('tools/cloud.py').read()); print('OK')"`
Expected: `OK`

Then verify the actual TensorDock API field names match our code by fetching a real response:

Run: `py -3.12 -c "exec(open('tools/cloud.py').read()); import json; print(json.dumps(api_request('GET', '/locations'), indent=2)[:500])"`

Confirm the response contains: `data.locations[].id`, `data.locations[].gpus[].v0Name`, `data.locations[].gpus[].price_per_hr`, `data.locations[].gpus[].network_features.port_forwarding_available`. These field names were verified against actual API responses earlier in development. If any differ, update the parsing code.

- [ ] **Step 3: Commit**

```bash
git add tools/cloud.py
git commit -m "Add cloud.py foundation: env loader, API client, state management"
```

---

### Task 3: SSH helpers

**Files:**
- Modify: `tools/cloud.py`

- [ ] **Step 1: Add SSH key management and SSH helper functions**

Append to `tools/cloud.py`:

```python
# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------

def ensure_ssh_key() -> Path:
    """Ensure SSH key exists, generate if missing. Return path to private key."""
    key_path = get_ssh_key_path()
    if not key_path.exists():
        print(f"Generating SSH key at {key_path}...")
        key_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", ""],
            check=True,
            capture_output=True,
        )
        print(f"  Created: {key_path}")
    return key_path


def read_public_key() -> str:
    key_path = ensure_ssh_key()
    pub_path = Path(f"{key_path}.pub")
    return pub_path.read_text().strip()


def ssh_command(state: dict, cmd: str | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a command over SSH. If cmd is None, open interactive session."""
    key_path = get_ssh_key_path()
    base = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ServerAliveInterval=30",
        "-i", str(key_path),
        "-p", str(state["ssh_port"]),
        f"{DEFAULT_SSH_USER}@{state['ip']}",
    ]
    if cmd is None:
        return subprocess.run(base)
    return subprocess.run(
        base + [cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def wait_for_ssh(state: dict) -> bool:
    """Poll until SSH is reachable. Returns True on success, False on timeout."""
    deadline = time.monotonic() + SSH_MAX_WAIT
    print(f"Waiting for SSH at {state['ip']}:{state['ssh_port']}...", end="", flush=True)
    while time.monotonic() < deadline:
        try:
            result = ssh_command(state, "echo ok", timeout=10)
            if result.returncode == 0:
                print(" ready!")
                return True
        except (subprocess.TimeoutExpired, Exception):
            pass
        print(".", end="", flush=True)
        time.sleep(SSH_POLL_INTERVAL)
    print(" timeout!")
    print(f"Error: SSH not reachable after {SSH_MAX_WAIT}s.")
    print(f"  Instance ID: {state.get('instance_id', '?')}")
    print(f"  Try again or destroy: python tools/cloud.py destroy")
    return False


def scp_to_remote(state: dict, local_path: str, remote_path: str) -> None:
    """Copy a file to the remote machine via SCP."""
    key_path = get_ssh_key_path()
    subprocess.run(
        [
            "scp",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-i", str(key_path),
            "-P", str(state["ssh_port"]),
            local_path,
            f"{DEFAULT_SSH_USER}@{state['ip']}:{remote_path}",
        ],
        check=True,
    )


def print_ssh_config(state: dict) -> None:
    """Print an SSH config block for easy VS Code Remote-SSH setup."""
    key_path = get_ssh_key_path()
    print("\n--- SSH config (append to ~/.ssh/config) ---")
    print(f"Host aegis-dev")
    print(f"    HostName {state['ip']}")
    print(f"    Port {state['ssh_port']}")
    print(f"    User {DEFAULT_SSH_USER}")
    print(f"    IdentityFile {key_path}")
    print("---")
```

- [ ] **Step 2: Commit**

```bash
git add tools/cloud.py
git commit -m "Add SSH helpers: key management, wait-for-ssh, scp, config printer"
```

---

### Task 4: Commands - `up`, `down`, `destroy`, `status`

**Files:**
- Modify: `tools/cloud.py`

- [ ] **Step 1: Add the provision, start, stop, destroy functions and `status` command**

Append to `tools/cloud.py`:

```python
# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------

def provision() -> dict:
    """Provision a new TensorDock VM. Returns state dict."""
    pub_key = read_public_key()
    loc_id, gpu_name, price = find_cheapest_location()
    print(f"Provisioning: {gpu_name} @ ${price:.3f}/hr")

    body = {
        "data": {
            "type": "virtualmachine",
            "attributes": {
                "name": "aegis-dev",
                "type": "virtualmachine",
                "image": DEFAULT_IMAGE,
                "location_id": loc_id,
                "resources": {
                    "vcpu_count": DEFAULT_VCPUS,
                    "ram_gb": DEFAULT_RAM_GB,
                    "storage_gb": DEFAULT_STORAGE_GB,
                    "gpus": {gpu_name: {"count": 1}},
                },
                "ssh_key": pub_key,
                "port_forwards": [
                    {"internal_port": 22, "external_port": 22},
                    {"internal_port": 5000, "external_port": 5000},
                ],
            },
        }
    }

    resp = api_request("POST", "/instances", body)
    if resp is None or "data" not in resp or "id" not in resp["data"]:
        print(f"Error: Unexpected API response during provisioning: {resp}")
        sys.exit(1)
    instance_id = resp["data"]["id"]
    print(f"Instance created: {instance_id}")

    # Fetch full details (IP, actual ports)
    time.sleep(2)
    details = get_instance(instance_id)
    ports = {pf["internal_port"]: pf["external_port"] for pf in details.get("portForwards", [])}

    state = {
        "instance_id": instance_id,
        "ip": details["ipAddress"],
        "ssh_port": ports.get(22, 22),
        "viewer_port": ports.get(5000, 5000),
        "gpu": gpu_name,
        "status": "running",
        "rate_hourly": details.get("rateHourly", price),
        "started_at": time.time(),
    }
    save_state(state)
    return state


def start_instance(state: dict) -> dict:
    """Start a stopped instance and refresh state with new IP/ports."""
    instance_id = state["instance_id"]
    print(f"Starting instance {instance_id}...")
    api_request("POST", f"/instances/{instance_id}/start")

    # Wait a moment, then re-query for possibly changed IP/ports
    time.sleep(5)
    details = get_instance(instance_id)
    if details is None:
        print("Error: Instance not found after start. It may have been deleted.")
        clear_state()
        sys.exit(1)

    ports = {pf["internal_port"]: pf["external_port"] for pf in details.get("portForwards", [])}
    state["ip"] = details["ipAddress"]
    state["ssh_port"] = ports.get(22, state["ssh_port"])
    state["viewer_port"] = ports.get(5000, state["viewer_port"])
    state["status"] = "running"
    state["rate_hourly"] = details.get("rateHourly", state.get("rate_hourly", 0))
    state["started_at"] = time.time()
    save_state(state)
    return state


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_up(args: argparse.Namespace) -> None:
    """Provision new, wake stopped, or sync running machine."""
    state = load_state()

    if state is not None:
        # Validate against API
        details = get_instance(state["instance_id"])
        if details is None:
            print("Stored instance no longer exists. Provisioning new one.")
            clear_state()
            state = None
        else:
            state["status"] = details.get("status", "unknown").lower()
            save_state(state)

    if state is None:
        # Provision new
        state = provision()
        if not wait_for_ssh(state):
            return
        run_bootstrap(state)
        print_ssh_config(state)
        cmd_status(args)
        return

    status = state["status"]
    if status in ("stopped", "stoppeddisassociated"):
        state = start_instance(state)
        if not wait_for_ssh(state):
            return
        run_sync(state)
        print_ssh_config(state)
        cmd_status(args)
        return

    if status == "running":
        print("Machine already running. Syncing...")
        run_sync(state)
        cmd_status(args)
        return

    print(f"Machine is in state '{status}'. Cannot bring up.")
    print("Try: python tools/cloud.py destroy")


def cmd_down(args: argparse.Namespace) -> None:
    """Stop the machine (preserves disk)."""
    state = load_state()
    if state is None:
        print("No machine tracked. Nothing to stop.")
        return

    instance_id = state["instance_id"]
    print(f"Stopping instance {instance_id}...")
    api_request("POST", f"/instances/{instance_id}/stop")
    state["status"] = "stopped"
    save_state(state)
    print("Machine stopped. Disk preserved. Run 'up' to restart.")


def cmd_destroy(args: argparse.Namespace) -> None:
    """Delete the machine entirely."""
    state = load_state()
    if state is None:
        print("No machine tracked. Nothing to destroy.")
        return

    instance_id = state["instance_id"]
    print(f"Deleting instance {instance_id}...")
    try:
        api_request("DELETE", f"/instances/{instance_id}")
    except Exception as e:
        print(f"Warning: API delete failed ({e}). Clearing local state anyway.")
    clear_state()
    print("Machine destroyed.")


def cmd_status(args: argparse.Namespace) -> None:
    """Show current machine status."""
    state = load_state()
    if state is None:
        print("No machine tracked.")
        return

    # Refresh from API
    details = get_instance(state["instance_id"])
    if details is None:
        print("Stored instance no longer exists on TensorDock.")
        clear_state()
        return

    status = details.get("status", "unknown")
    rate = details.get("rateHourly", state.get("rate_hourly", 0))

    print(f"  Instance:  {state['instance_id']}")
    print(f"  Status:    {status}")
    print(f"  IP:        {state['ip']}")
    print(f"  SSH:       ssh -p {state['ssh_port']} {DEFAULT_SSH_USER}@{state['ip']}")
    print(f"  Viewer:    http://{state['ip']}:{state['viewer_port']}")
    print(f"  GPU:       {state['gpu']}")
    print(f"  Rate:      ${rate:.3f}/hr")

    if status.lower() == "running" and rate > 0:
        started_at = state.get("started_at")
        if started_at:
            uptime_hrs = (time.time() - started_at) / 3600
            cost_est = uptime_hrs * rate
            print(f"  Uptime:    {uptime_hrs:.1f}h (est. ${cost_est:.2f})")
            if uptime_hrs > 4:
                print(f"\n  !! WARNING: Machine running for {uptime_hrs:.1f}h. Consider shutting down. !!")
        print(f"\n  ** Machine is running at ${rate:.3f}/hr **")
        print(f"  Run 'python tools/cloud.py down' when done.")
```

- [ ] **Step 2: Verify the new functions load without errors**

Run: `py -3.12 -c "exec(open('tools/cloud.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tools/cloud.py
git commit -m "Add up/down/destroy/status commands to cloud.py"
```

---

### Task 5: Commands - `sync`, `ssh`, and `main`

**Files:**
- Modify: `tools/cloud.py`

- [ ] **Step 1: Add bootstrap, sync, ssh commands and argparse main**

Append to `tools/cloud.py`:

```python
# ---------------------------------------------------------------------------
# Bootstrap and sync
# ---------------------------------------------------------------------------

def run_bootstrap(state: dict) -> None:
    """Upload and run the bootstrap script on a fresh machine."""
    bootstrap_script = TOOLS_DIR / "cloud-bootstrap.sh"
    if not bootstrap_script.exists():
        print(f"Error: {bootstrap_script} not found.")
        sys.exit(1)

    print("Running bootstrap on remote machine...")
    scp_to_remote(state, str(bootstrap_script), "/tmp/cloud-bootstrap.sh")
    result = ssh_command(state, "chmod +x /tmp/cloud-bootstrap.sh && sudo bash /tmp/cloud-bootstrap.sh", timeout=600)
    if result.returncode != 0:
        print(f"Bootstrap failed (exit code {result.returncode}):")
        print(result.stderr)
        print(result.stdout)
        print("SSH in manually to debug: python tools/cloud.py ssh")
    else:
        print(result.stdout)
        print("Bootstrap complete.")


def run_sync(state: dict) -> None:
    """Pull latest code and reinstall on the remote machine."""
    # Check if repo exists; fall back to full bootstrap if not
    result = ssh_command(state, "test -d ~/aegis/.git && echo exists", timeout=10)
    if "exists" not in (result.stdout or ""):
        print("Repo not found on remote. Running full bootstrap...")
        run_bootstrap(state)
        return

    print("Syncing remote...")
    sync_cmd = (
        "cd ~/aegis && "
        "git pull --rebase origin master && "
        "source .venv/bin/activate && "
        "pip install -q -e '.[dev,gpu]'"
    )
    result = ssh_command(state, sync_cmd, timeout=300)
    if result.returncode != 0:
        print(f"Sync failed:")
        print(result.stderr)
    else:
        print("Sync complete.")
        if result.stdout.strip():
            # Show only last few lines
            lines = result.stdout.strip().splitlines()
            for line in lines[-5:]:
                print(f"  {line}")


def cmd_sync(args: argparse.Namespace) -> None:
    """Pull latest code on remote machine."""
    state = load_state()
    if state is None:
        print("No machine tracked. Run 'up' first.")
        return
    run_sync(state)


def cmd_ssh(args: argparse.Namespace) -> None:
    """Open interactive SSH session."""
    state = load_state()
    if state is None:
        print("No machine tracked. Run 'up' first.")
        return
    key_path = get_ssh_key_path()
    print(f"Connecting to {state['ip']}:{state['ssh_port']}...")
    # Replace process with SSH (interactive). Use subprocess.run on Windows.
    ssh_args = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ServerAliveInterval=30",
        "-i", str(key_path),
        "-p", str(state["ssh_port"]),
        f"{DEFAULT_SSH_USER}@{state['ip']}",
    ]
    if sys.platform == "win32":
        result = subprocess.run(ssh_args)
        sys.exit(result.returncode)
    else:
        os.execvp("ssh", ssh_args)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="TensorDock dev machine manager for AEGIS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("up", help="Provision, wake, or sync machine")
    sub.add_parser("down", help="Stop machine (preserves disk)")
    sub.add_parser("destroy", help="Delete machine entirely")
    sub.add_parser("sync", help="Pull latest code on remote")
    sub.add_parser("ssh", help="Open SSH session")
    sub.add_parser("status", help="Show machine state")

    args = parser.parse_args()
    commands = {
        "up": cmd_up,
        "down": cmd_down,
        "destroy": cmd_destroy,
        "sync": cmd_sync,
        "ssh": cmd_ssh,
        "status": cmd_status,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI help works**

Run: `py -3.12 tools/cloud.py --help`
Expected: Shows usage with all 6 subcommands

- [ ] **Step 3: Commit**

```bash
git add tools/cloud.py
git commit -m "Add sync, ssh, main CLI to cloud.py"
```

---

### Task 6: Bootstrap script

**Files:**
- Create: `tools/cloud-bootstrap.sh`

- [ ] **Step 1: Write the bootstrap script**

```bash
#!/usr/bin/env bash
# cloud-bootstrap.sh - First-time setup for AEGIS dev machine on TensorDock
# Idempotent: safe to run multiple times.
set -euo pipefail

echo "=== AEGIS dev machine bootstrap ==="

# --- System packages ---
if ! command -v git &>/dev/null || ! command -v curl &>/dev/null; then
    echo "Installing system packages..."
    apt-get update -qq
    apt-get install -y -qq git curl software-properties-common
else
    echo "System packages: OK"
fi

# --- Python 3.12 ---
if ! command -v python3.12 &>/dev/null; then
    echo "Installing Python 3.12..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
else
    echo "Python 3.12: $(python3.12 --version)"
fi

# --- Node.js (for Claude Code) ---
if ! command -v node &>/dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y -qq nodejs
else
    echo "Node.js: $(node --version)"
fi

# --- CUDA verification ---
if command -v nvidia-smi &>/dev/null; then
    echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader)"
else
    echo "WARNING: nvidia-smi not found. GPU may not be available."
fi

# --- Clone repo ---
AEGIS_DIR="/home/user/aegis"
if [ ! -d "$AEGIS_DIR/.git" ]; then
    echo "Cloning AEGIS repo..."
    sudo -u user git clone https://github.com/rwydaegh/aegis.git "$AEGIS_DIR"
else
    echo "Repo: already cloned"
fi

# --- Python venv + deps ---
VENV_DIR="$AEGIS_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python venv and installing deps (this may take a few minutes)..."
    sudo -u user python3.12 -m venv "$VENV_DIR"
    sudo -u user "$VENV_DIR/bin/pip" install --upgrade pip
    sudo -u user "$VENV_DIR/bin/pip" install -e "$AEGIS_DIR[dev,gpu]"
else
    echo "Venv: already exists, updating deps..."
    sudo -u user "$VENV_DIR/bin/pip" install -q -e "$AEGIS_DIR[dev,gpu]"
fi

# --- Claude Code ---
if ! command -v claude &>/dev/null; then
    echo "Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code
else
    echo "Claude Code: $(claude --version 2>/dev/null || echo 'installed')"
fi

# --- Firewall ---
if command -v ufw &>/dev/null; then
    echo "Configuring firewall..."
    ufw default deny incoming
    ufw default allow outgoing
    # Allow SSH and viewer (actual external ports are handled by TensorDock NAT)
    ufw allow 22/tcp
    ufw allow 5000/tcp
    ufw --force enable
    echo "Firewall: enabled"
fi

# --- Viewer auth ---
AUTH_FILE="/home/user/.aegis-viewer-auth"
if [ ! -f "$AUTH_FILE" ]; then
    VIEWER_PASS=$(head -c 16 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 16)
    echo "aegis:$VIEWER_PASS" > "$AUTH_FILE"
    chown user:user "$AUTH_FILE"
    chmod 600 "$AUTH_FILE"
    echo ""
    echo "============================================"
    echo "  Viewer credentials (save these!)"
    echo "  Username: aegis"
    echo "  Password: $VIEWER_PASS"
    echo "============================================"
    echo ""
else
    echo "Viewer auth: already configured"
fi

# --- Shell convenience: activate venv on login ---
BASHRC="/home/user/.bashrc"
if ! grep -q "aegis/.venv" "$BASHRC" 2>/dev/null; then
    cat >> "$BASHRC" << 'BASHRC_APPEND'

# AEGIS dev environment
if [ -d "$HOME/aegis/.venv" ]; then
    source "$HOME/aegis/.venv/bin/activate"
    cd "$HOME/aegis"
    export AEGIS_VIEWER_AUTH=$(cat "$HOME/.aegis-viewer-auth" 2>/dev/null || true)
fi
BASHRC_APPEND
fi

echo ""
echo "=== Bootstrap complete ==="
echo "SSH in and run: pytest tests/ -m 'not slow' -x"
echo "To use Claude Code: claude /login (with SSH port forwarding)"
```

- [ ] **Step 2: Verify the script has no syntax errors**

Run: `bash -n tools/cloud-bootstrap.sh`
Expected: No output (no syntax errors)

- [ ] **Step 3: Commit**

```bash
git add tools/cloud-bootstrap.sh
git commit -m "Add cloud bootstrap script for remote machine first-boot setup"
```

---

### Task 7: Viewer Basic Auth

**Files:**
- Modify: `src/aegis/viewer/server.py`
- Create: `tests/test_viewer_auth.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_viewer_auth.py`:

```python
"""Tests for viewer HTTP Basic Auth."""

import base64
import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clean_auth_env():
    """Ensure AEGIS_VIEWER_AUTH is cleaned up after each test."""
    yield
    os.environ.pop("AEGIS_VIEWER_AUTH", None)


def _make_app(auth_env: str | None = None):
    """Create a minimal Flask test app with auth configured.

    Uses the e2e_lab fixture data dir so body loading succeeds.
    """
    if auth_env:
        os.environ["AEGIS_VIEWER_AUTH"] = auth_env
    else:
        os.environ.pop("AEGIS_VIEWER_AUTH", None)

    from aegis.viewer.server import create_app

    # Use the test fixture directory which has a small STL
    data_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    app = create_app(
        data_dir=data_dir,
        body_name="e2e_icosahedron",
        config={"server": {"host": "127.0.0.1", "port": 5099}},
    )
    app.config["TESTING"] = True
    return app


def test_no_auth_when_unset():
    """Without AEGIS_VIEWER_AUTH, all routes are open."""
    app = _make_app(auth_env=None)
    with app.test_client() as c:
        resp = c.get("/api/health")
        assert resp.status_code == 200


def test_auth_rejects_without_credentials():
    """With AEGIS_VIEWER_AUTH set, requests without credentials get 401."""
    app = _make_app(auth_env="aegis:testpass123")
    with app.test_client() as c:
        resp = c.get("/api/health")
        assert resp.status_code == 401


def test_auth_accepts_correct_credentials():
    """Correct Basic Auth credentials pass through."""
    app = _make_app(auth_env="aegis:testpass123")
    creds = base64.b64encode(b"aegis:testpass123").decode()
    with app.test_client() as c:
        resp = c.get("/api/health", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200


def test_auth_rejects_wrong_credentials():
    """Wrong credentials get 401."""
    app = _make_app(auth_env="aegis:testpass123")
    creds = base64.b64encode(b"aegis:wrongpass").decode()
    with app.test_client() as c:
        resp = c.get("/api/health", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_viewer_auth.py -v`
Expected: `test_auth_rejects_without_credentials` and `test_auth_rejects_wrong_credentials` FAIL (no auth implemented yet). The others may pass or fail depending on body load.

- [ ] **Step 3: Add `import os` to `server.py`**

Add `import os` to the imports at the top of `src/aegis/viewer/server.py` (after `import threading`).

- [ ] **Step 4: Add Basic Auth hook to `server.py`**

Add this right after `app = Flask(...)` in `create_app()` (around line 190 of `server.py`):

```python
    # Optional HTTP Basic Auth for remote access
    _viewer_auth = os.environ.get("AEGIS_VIEWER_AUTH")
    if _viewer_auth and ":" in _viewer_auth:
        _auth_user, _, _auth_pass = _viewer_auth.partition(":")

        @app.before_request
        def _check_basic_auth():
            from flask import request, Response

            auth = request.authorization
            if not auth or auth.username != _auth_user or auth.password != _auth_pass:
                return Response(
                    "Authentication required.",
                    401,
                    {"WWW-Authenticate": 'Basic realm="AEGIS Viewer"'},
                )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_viewer_auth.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Run existing viewer tests to verify no regression**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -q`
Expected: All pass

- [ ] **Step 7: Lint**

Run: `py -3.12 -m ruff check src/aegis/viewer/server.py tests/test_viewer_auth.py`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
git add src/aegis/viewer/server.py tests/test_viewer_auth.py
git commit -m "Add optional HTTP Basic Auth to viewer for remote access"
```

---

### Task 8: Integration test with the running TensorDock machine

**Files:** None new (manual verification)

The aegis-dev machine is currently running at `84.50.156.8:47906`. Use it to verify the full flow.

- [ ] **Step 1: Point `.cloud-state.json` at the running machine**

Create `tools/.cloud-state.json` manually from the current running instance:

```json
{
  "instance_id": "ee47e606-c81f-4d1a-8548-8048ba3b9df6",
  "ip": "84.50.156.8",
  "ssh_port": 47906,
  "viewer_port": 5000,
  "gpu": "rtxa4000-pcie-16gb",
  "status": "running",
  "rate_hourly": 0.109
}
```

Note: The SSH key is at `/tmp/tensordock_hello` from the earlier session. Copy it to the proper location first:

```bash
mkdir -p ~/.ssh
cp /tmp/tensordock_hello ~/.ssh/tensordock_ed25519
cp /tmp/tensordock_hello.pub ~/.ssh/tensordock_ed25519.pub
```

- [ ] **Step 2: Verify `status` command works**

Run: `py -3.12 tools/cloud.py status`
Expected: Shows instance details, IP, SSH command, viewer URL

- [ ] **Step 3: Run bootstrap on the live machine**

Run: `py -3.12 tools/cloud.py sync`
Expected: Since no repo exists yet, falls back to bootstrap. Installs Python, clones repo, creates venv, prints viewer credentials.

Note: This will take several minutes (JAX+CUDA download). Watch for timeout issues.

- [ ] **Step 4: Verify remote tests pass**

SSH in and run:
```bash
ssh -i ~/.ssh/tensordock_ed25519 -p 47906 user@84.50.156.8 \
  "cd ~/aegis && source .venv/bin/activate && pytest tests/ -m 'not slow' -x -q"
```
Expected: All fast tests pass on Linux + GPU

- [ ] **Step 5: Verify `down` and `up` cycle**

```bash
py -3.12 tools/cloud.py down    # Stop machine
py -3.12 tools/cloud.py status  # Should show "stopped"
py -3.12 tools/cloud.py up      # Wake it, should sync not re-bootstrap
```

---

### Task 9: Final cleanup

- [ ] **Step 1: Run full lint and test suite**

```bash
py -3.12 -m ruff check src/ tests/ tools/
py -3.12 -m ruff format --check src/ tests/ tools/
py -3.12 -m pytest tests/ -m "not slow" -x
```

- [ ] **Step 2: Shut down or keep machine based on user preference**

Run: `py -3.12 tools/cloud.py status` to remind cost, then ask user.

- [ ] **Step 3: Final commit and push**

```bash
git push origin master
```
