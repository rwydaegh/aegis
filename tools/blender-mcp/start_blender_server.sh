#!/usr/bin/env bash
set -euo pipefail

# Start Blender in background with MCP socket server on port 9876.
# Run this before using the blender-mcp MCP server in Claude Code.
# Usage: bash tools/blender-mcp/start_blender_server.sh

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$REPO_ROOT/.env"
  set +a
fi

export AEGIS_REPO_ROOT="$REPO_ROOT"

blender --background --python-expr "
import bpy
import os
import sys
import time

repo_root = os.environ['AEGIS_REPO_ROOT']
sys.path.insert(0, os.path.join(repo_root, 'tools', 'blender-mcp'))
import addon

# Start the TCP socket server
server = addon.BlenderMCPServer()
server.start()
print('BlenderMCP server started on port 9876')

# Keep Blender alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
    print('Server stopped')
"
