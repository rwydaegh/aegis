# Blender MCP

This directory carries the repo-local Blender MCP addon and a helper script to
start the socket server without relying on a separately installed copy.

## Setup

1. Copy `.env.example` to `.env` at the repo root if you do not have one yet.
2. Set `BLENDERMCP_HYPER3D_FREE_TRIAL_KEY` in `.env` if you want the Blender UI
   shortcut to populate the Hyper3D free-trial key.
3. Start Blender MCP with:

```bash
bash tools/blender-mcp/start_blender_server.sh
```

The startup script sources the repo `.env` file, adds `tools/blender-mcp/` to
Blender's Python path, and starts the socket server on port `9876`.

## Notes

- The "Set Free Trial API Key" button now reads the key from
  `BLENDERMCP_HYPER3D_FREE_TRIAL_KEY` instead of embedding a secret in source.
- If the env var is unset, you can still paste a private Hyper3D key directly
  into the Blender UI.
