#!/usr/bin/env bash
# Headless Blender studio: Xvfb + GUI Blender + MCP socket server + noVNC.
#
# Blender MCP needs an interactive Blender (its command dispatch runs on
# bpy.app.timers, which never fire in --background). On a GUI-less box we give
# it a virtual X display instead, and expose that display in the browser over
# noVNC so a human can watch the same session the agent is driving.
#
#   ./studio.sh start | stop | status | url | logs
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

BLENDER_BIN=${BLENDER_BIN:-$HOME/blender-4.5/blender}
DISPLAY_NUM=${DISPLAY_NUM:-99}
SCREEN=${SCREEN:-1920x1080x24}
MCP_PORT=${BLENDERMCP_PORT:-9876}
VNC_PORT=${VNC_PORT:-5900}
WEB_PORT=${WEB_PORT:-6080}
RUN_DIR=${RUN_DIR:-/tmp/blender-studio}

mkdir -p "$RUN_DIR"
READY_FILE="$RUN_DIR/ready"

_pidfile() { echo "$RUN_DIR/$1.pid"; }

_alive() {
  local pf
  pf=$(_pidfile "$1")
  [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null
}

_spawn() {
  # _spawn <name> <cmd...>
  local name=$1
  shift
  if _alive "$name"; then
    echo "  $name already running (pid $(cat "$(_pidfile "$name")"))"
    return 0
  fi
  "$@" >"$RUN_DIR/$name.log" 2>&1 &
  echo $! >"$(_pidfile "$name")"
  echo "  $name started (pid $!)"
}

start() {
  if [ ! -x "$BLENDER_BIN" ]; then
    echo "Blender not found at $BLENDER_BIN (set BLENDER_BIN)" >&2
    exit 1
  fi

  rm -f "$READY_FILE"

  echo "Starting virtual display :$DISPLAY_NUM ($SCREEN)"
  _spawn xvfb Xvfb ":$DISPLAY_NUM" -screen 0 "$SCREEN" +extension GLX +render -noreset

  # Xvfb needs to own the socket before anything can connect to it.
  for _ in $(seq 1 30); do
    DISPLAY=":$DISPLAY_NUM" xdpyinfo >/dev/null 2>&1 && break
    sleep 0.3
  done
  if ! DISPLAY=":$DISPLAY_NUM" xdpyinfo >/dev/null 2>&1; then
    echo "Xvfb did not come up, see $RUN_DIR/xvfb.log" >&2
    exit 1
  fi

  if [ -f "$REPO_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$REPO_ROOT/.env"
    set +a
  fi

  echo "Starting Blender with the MCP server on port $MCP_PORT"
  _spawn blender env \
    "DISPLAY=:$DISPLAY_NUM" \
    "BLENDERMCP_PORT=$MCP_PORT" \
    "BLENDERMCP_READY_FILE=$READY_FILE" \
    LIBGL_ALWAYS_SOFTWARE=1 \
    "$BLENDER_BIN" --python "$SCRIPT_DIR/bootstrap.py"

  for _ in $(seq 1 90); do
    [ -f "$READY_FILE" ] && break
    sleep 0.5
  done
  if [ ! -f "$READY_FILE" ]; then
    echo "Blender did not report ready, see $RUN_DIR/blender.log" >&2
    exit 1
  fi

  echo "Starting x11vnc on :$VNC_PORT and noVNC on :$WEB_PORT"
  _spawn x11vnc x11vnc -display ":$DISPLAY_NUM" -rfbport "$VNC_PORT" \
    -localhost -forever -shared -nopw -noxdamage -quiet
  sleep 1
  _spawn novnc websockify --web=/usr/share/novnc "0.0.0.0:$WEB_PORT" \
    "localhost:$VNC_PORT"

  echo
  status
  url
}

stop() {
  for name in novnc x11vnc blender xvfb; do
    local pf
    pf=$(_pidfile "$name")
    if [ -f "$pf" ]; then
      kill "$(cat "$pf")" 2>/dev/null && echo "  stopped $name"
      rm -f "$pf"
    fi
  done
  rm -f "$READY_FILE"
}

status() {
  for name in xvfb blender x11vnc novnc; do
    if _alive "$name"; then
      echo "  up    $name (pid $(cat "$(_pidfile "$name")"))"
    else
      echo "  down  $name"
    fi
  done
  if command -v ss >/dev/null && ss -ltn 2>/dev/null | grep -q ":$MCP_PORT "; then
    echo "  up    mcp socket on $MCP_PORT"
  else
    echo "  down  mcp socket on $MCP_PORT"
  fi
}

url() {
  local ip
  ip=$(hostname -I | awk '{print $1}')
  echo
  echo "Watch the session at: http://$ip:$WEB_PORT/vnc.html?autoconnect=1&resize=scale"
}

logs() { tail -n 40 "$RUN_DIR"/*.log; }

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  restart) stop; sleep 1; start ;;
  status) status ;;
  url) url ;;
  logs) logs ;;
  *) echo "usage: $0 {start|stop|restart|status|url|logs}" >&2; exit 2 ;;
esac
