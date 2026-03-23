# Cloud GPU machine

AEGIS runs on Windows locally, but GPU acceleration (JAX/CUDA) and Linux testing require a remote machine. The `tools/cloud.py` script manages an on-demand TensorDock VM with a single command.

## Setup

Add your TensorDock API key and SSH key path to `.env`:

```bash
TENSORDOCK_API_KEY=<bearer-token-from-tensordock-dashboard>
TENSORDOCK_SSH_KEY_PATH=~/.ssh/tensordock_ed25519
```

Generate a bearer token at Dashboard > Developer Settings on [TensorDock](https://dashboard.tensordock.com). The SSH key is created automatically on first use if it doesn't exist.

### SSH identity (read this)

TensorDock installs the **public** half of `TENSORDOCK_SSH_KEY_PATH` on the VM. Every manual `ssh` command must use the matching **private** key with **`-i`**, or you get `Permission denied (publickey)`:

```bash
ssh -i ~/.ssh/tensordock_ed25519 -p <ssh_port> user@<ip>
```

Use the path from `.env` if you changed it. On Windows (Git Bash), if `~` does not resolve, use `$USERPROFILE/.ssh/tensordock_ed25519`.

**Easiest:** run `python tools/cloud.py ssh` from the repo. It loads `.env` and passes the key for you.

## Commands

```bash
python tools/cloud.py up        # provision, wake, or sync
python tools/cloud.py down      # stop (disk preserved, ~$0.005/hr)
python tools/cloud.py destroy   # delete everything
python tools/cloud.py sync      # git pull + pip install on remote
python tools/cloud.py ssh       # open interactive session
python tools/cloud.py status    # IP, GPU, cost, uptime
```

The `up` command detects state automatically. If no machine exists, it provisions one (Ubuntu 24.04, cheapest available GPU, 2 vCPU, 4 GB RAM, 100 GB disk). If the machine is stopped, it wakes it. If already running, it syncs.

## First boot

On a fresh machine, `up` runs `tools/cloud-bootstrap.sh` which installs:

- Python 3.12 with venv
- The AEGIS repo (cloned from GitHub) with `.[dev,gpu,rt]` extras
- The React frontend (`cd aegis-web && npm ci && npm run build:copy`) so Flask serves the modern UI, not the legacy HTML fallback
- JAX with CUDA support (2+ GB download, takes a few minutes)
- Node.js and the `nodejs-voxelearth` pipeline (for location loading)
- Claude Code CLI
- UFW firewall (only SSH and viewer ports open)
- Viewer HTTP Basic Auth credentials (printed once, save them)

The venv activates on login and `cd`s into `~/aegis` automatically.

## Typical workflow

```bash
python tools/cloud.py up         # ~30s to wake, ~5min to provision
# work via VS Code Remote-SSH or terminal
python tools/cloud.py down       # stop when done
```

After `up`, the output includes an SSH config block you can paste into `~/.ssh/config` for VS Code Remote-SSH. Connect to host `aegis-dev`.

VS Code tunnels ports automatically, so Flask on the remote machine appears at `localhost:5000` in your local browser once you forward port 5000 (or use "Forward a Port" for 5000).

## Running tests on the remote

```bash
python tools/cloud.py ssh
# now on the remote machine:
pytest tests/ -m "not slow" -x -q
```

Or without an interactive session:

```bash
ssh aegis-dev "cd ~/aegis && pytest tests/ -m 'not slow' -x -q"
```

## Claude Code on the remote

Claude Code uses your Max subscription, not API credits. First-time setup requires SSH port forwarding for the OAuth login:

```bash
ssh -L 8080:localhost:8080 aegis-dev
claude /login
# copy the localhost URL to your local browser, authenticate
```

After that, `claude` works on the remote machine using your subscription.

## Viewer access

**Always run** `python tools/cloud.py status` **first.** It asks the TensorDock API which ports are forwarded and prints either a public `http://` URL or an SSH tunnel command. Do not assume `http://<ip>:5000` works: many instances only forward **SSH**, not port 5000, so a direct browser request fails with connection refused.

### When status shows a public viewer URL

Open that URL. If bootstrap enabled HTTP Basic Auth, use the username `aegis` and the password stored in `~/.aegis-viewer-auth` on the VM (printed once during first bootstrap).

### When status says the viewer is not publicly forwarded (typical)

The Flask app still listens on `0.0.0.0:5000` **inside** the VM. Reach it through a **local** port forward using the **same key as in `.env`**:

```bash
ssh -i ~/.ssh/tensordock_ed25519 \
  -L 5000:127.0.0.1:5000 \
  -p <ssh_port> \
  user@<ip>
```

Copy `<ssh_port>` and `<ip>` from `status` output. Leave the session open, then open **`http://localhost:5000`** in your browser.

Other options: VS Code Remote-SSH and forward port 5000, or add a port-5000 forward in the TensorDock dashboard if you need a public URL without a tunnel.

The Server section at the bottom of the panel shows the hostname, GPU name, utilization, VRAM, and temperature. It updates every 5 seconds.

## Cost

The script picks the cheapest available GPU with port forwarding. Typical cost is $0.10-0.20/hr for an RTX A4000 or RTX 3090. Stopped machines cost about $0.005/hr for disk storage.

The `status` command shows current rate and uptime. After 4 hours of continuous running, it prints a warning.

## State file

Machine state (instance ID, IP, ports) is stored in `tools/.cloud-state.json` (gitignored). The script validates this against the TensorDock API on every command. If someone deletes the machine from the dashboard, the script detects it and offers to provision a replacement.
