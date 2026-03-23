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


def api_request(method: str, path: str, json_body: dict | None = None, timeout: int = 30) -> dict | list | None:
    """Make an authenticated request to the TensorDock v2 API."""
    import requests

    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = requests.request(method, url, headers=headers, json=json_body, timeout=timeout)
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
# SSH option constants (avoid duplicate literals)
# ---------------------------------------------------------------------------

_SSH_STRICT_HOST = "StrictHostKeyChecking=no"
_SSH_KNOWN_HOSTS = "UserKnownHostsFile=/dev/null"

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
        _SSH_STRICT_HOST,
        "-o",
        _SSH_KNOWN_HOSTS,
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
            _SSH_STRICT_HOST,
            "-o",
            _SSH_KNOWN_HOSTS,
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
    api_request("POST", f"/instances/{instance_id}/start", timeout=120)

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
    ip = details.get("ipAddress", state["ip"])
    port_forwards = details.get("portForwards", [])
    by_internal = {pf["internal_port"]: pf["external_port"] for pf in port_forwards}
    ssh_ext = by_internal.get(22, state["ssh_port"])
    viewer_ext = by_internal.get(5000)
    key_path = get_ssh_key_path()

    print(f"  Instance:  {state['instance_id']}")
    print(f"  Status:    {status}")
    print(f"  IP:        {ip}")
    print(f"  SSH:       ssh -i {key_path} -p {ssh_ext} {DEFAULT_SSH_USER}@{ip}")
    if viewer_ext is not None:
        print(f"  Viewer:    http://{ip}:{viewer_ext}")
    else:
        print("  Viewer:    not publicly port-forwarded (TensorDock API has no mapping for :5000)")
        print(f"             Tunnel: ssh -i {key_path} -L 5000:127.0.0.1:5000 -p {ssh_ext} {DEFAULT_SSH_USER}@{ip}")
        print("             Then open http://localhost:5000")
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
        print("  Run 'python tools/cloud.py down' when done.")


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
        "cd ~/aegis && git pull --rebase origin master && "
        "source .venv/bin/activate && pip install -q -e '.[dev,gpu,rt]' && "
        "cd ~/aegis/aegis-web && npm ci && npm run build:copy"
    )
    result = ssh_command(state, sync_cmd, timeout=900)
    if result.returncode != 0:
        print("Sync failed:")
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
        "-o",
        _SSH_STRICT_HOST,
        "-o",
        _SSH_KNOWN_HOSTS,
        "-o",
        "ServerAliveInterval=30",
        "-i",
        str(key_path),
        "-p",
        str(state["ssh_port"]),
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
