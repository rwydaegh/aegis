"""Blender-side bootstrap: register the MCP addon and start its socket server.

Run via: blender --python bootstrap.py
Requires a GUI Blender (real or on Xvfb). Background mode does not work because
the addon dispatches every command through bpy.app.timers, which only fire
inside Blender's interactive event loop.
"""

import os
import sys

import bpy

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import addon  # noqa: E402

PORT = int(os.environ.get("BLENDERMCP_PORT", "9876"))


def _dismiss_splash():
    """Reload the home file so the splash popup is not covering the viewport."""
    try:
        bpy.ops.wm.read_homefile(use_empty=False)
    except Exception as exc:
        print(f"[bootstrap] could not reload homefile: {exc}")


def _prepare_viewport():
    """Give the 3D viewport as much of the window as possible, in solid shading."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                space.shading.type = "SOLID"
                space.overlay.show_overlays = True
                space.region_3d.view_perspective = "PERSP"


def _start_server():
    if getattr(bpy.types, "blendermcp_server", None):
        print("[bootstrap] server already present")
        return
    server = addon.BlenderMCPServer(port=PORT)
    server.start()
    bpy.types.blendermcp_server = server
    for scene in bpy.data.scenes:
        scene.blendermcp_server_running = True
    print(f"[bootstrap] BlenderMCP server listening on port {PORT}")


def main():
    try:
        addon.register()
        print("[bootstrap] addon registered")
    except Exception as exc:
        print(f"[bootstrap] addon.register() failed: {exc}")
        raise

    _dismiss_splash()
    _prepare_viewport()
    _start_server()

    # Touch a readiness marker so the shell launcher can wait on us.
    marker = os.environ.get("BLENDERMCP_READY_FILE")
    if marker:
        with open(marker, "w") as handle:
            handle.write(str(PORT))


main()
