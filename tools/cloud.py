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

import json
import os
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
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "ServerAliveInterval=30",
        "-i",
        str(key_path),
        "-p",
        str(state["ssh_port"]),
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
    print("  Try again or destroy: python tools/cloud.py destroy")
    return False


def scp_to_remote(state: dict, local_path: str, remote_path: str) -> None:
    """Copy a file to the remote machine via SCP."""
    key_path = get_ssh_key_path()
    subprocess.run(
        [
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-i",
            str(key_path),
            "-P",
            str(state["ssh_port"]),
            local_path,
            f"{DEFAULT_SSH_USER}@{state['ip']}:{remote_path}",
        ],
        check=True,
    )


def print_ssh_config(state: dict) -> None:
    """Print an SSH config block for easy VS Code Remote-SSH setup."""
    key_path = get_ssh_key_path()
    print("\n--- SSH config (append to ~/.ssh/config) ---")
    print("Host aegis-dev")
    print(f"    HostName {state['ip']}")
    print(f"    Port {state['ssh_port']}")
    print(f"    User {DEFAULT_SSH_USER}")
    print(f"    IdentityFile {key_path}")
    print("---")
