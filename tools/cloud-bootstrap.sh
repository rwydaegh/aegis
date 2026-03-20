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
