#!/usr/bin/env python3
"""Thin client for the Blender MCP socket, for driving Blender from a shell.

The MCP server that Claude Code talks to is a wrapper around this same JSON
line protocol on port 9876, so anything reachable here is reachable from the
MCP tools. Having a CLI is useful for scripted iteration and for sessions where
the MCP server was configured after startup.

    bmcp.py info                       scene summary
    bmcp.py obj <name>                 object detail
    bmcp.py code path/to/script.py     run a script inside Blender, print stdout
    bmcp.py code -                     same, reading the script from stdin
    bmcp.py shot out.png [max_size]    viewport screenshot (see note)
    bmcp.py look out.png [w] [h]       viewport-style render, offscreen
    bmcp.py render out.png [w] [h] [spp]   full Cycles render

Note on `shot`: the addon's get_viewport_screenshot reads back the window front
buffer, which comes out black under Xvfb because nothing drives redraws. Use
`look` instead - bpy.ops.render.opengl draws the viewport into an offscreen
buffer, needs no window events, and takes about 0.3s at 800x450.
"""

import json
import socket
import sys

HOST = "localhost"
PORT = 9876
# Cycles renders on CPU take minutes; the default has to tolerate that.
TIMEOUT = 1800.0


RENDER_SNIPPET = """
import bpy, time
scene = bpy.context.scene
scene.render.resolution_x = {width}
scene.render.resolution_y = {height}
scene.render.resolution_percentage = 100
scene.render.filepath = "{path}"
start = time.time()
if {viewport}:
    area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(area=area, region=region):
        bpy.ops.render.opengl(write_still=True)
    print(f"viewport render -> {path} in {{time.time() - start:.1f}}s")
else:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = {samples}
    bpy.ops.render.render(write_still=True)
    print(f"cycles render ({samples} spp) -> {path} in {{time.time() - start:.1f}}s")
"""


def call(command_type, params=None, timeout=TIMEOUT):
    """Send one command and return the parsed response."""
    payload = json.dumps({"type": command_type, "params": params or {}})
    sock = socket.create_connection((HOST, PORT), timeout=30)
    sock.settimeout(timeout)
    try:
        sock.sendall(payload.encode("utf-8"))
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            # The server writes one JSON object per command and does not frame
            # it, so completeness is "does it parse yet".
            try:
                return json.loads(b"".join(chunks).decode("utf-8"))
            except json.JSONDecodeError:
                continue
        raise RuntimeError("connection closed before a complete response")
    finally:
        sock.close()


def run_code(code, timeout=TIMEOUT):
    """Execute Python inside Blender. Returns captured stdout."""
    response = call("execute_code", {"code": code}, timeout=timeout)
    if response.get("status") != "success":
        raise RuntimeError(response.get("message", response))
    return response["result"].get("result", "")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    action = sys.argv[1]

    if action == "info":
        print(json.dumps(call("get_scene_info")["result"], indent=2))

    elif action == "obj":
        result = call("get_object_info", {"name": sys.argv[2]})
        print(json.dumps(result, indent=2))

    elif action == "code":
        if sys.argv[2] == "-":
            source = sys.stdin.read()
        else:
            with open(sys.argv[2]) as handle:
                source = handle.read()
        sys.stdout.write(run_code(source))

    elif action == "shot":
        path = sys.argv[2]
        max_size = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
        result = call("get_viewport_screenshot", {"filepath": path, "max_size": max_size})
        print(json.dumps(result, indent=2))

    elif action in ("look", "render"):
        path = sys.argv[2]
        width = int(sys.argv[3]) if len(sys.argv) > 3 else 800
        height = int(sys.argv[4]) if len(sys.argv) > 4 else 450
        samples = int(sys.argv[5]) if len(sys.argv) > 5 else 32
        viewport = action == "look"
        print(
            run_code(
                RENDER_SNIPPET.format(
                    path=path,
                    width=width,
                    height=height,
                    samples=samples,
                    viewport=viewport,
                )
            )
        )

    else:
        print(f"unknown action: {action}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
