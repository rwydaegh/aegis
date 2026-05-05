"""Minimal Flask server for the plaza_run replay viewer.

Serves index.html at / and replay_data.json at /replay_data.json. Boots
on port 5050 to avoid conflicts with the main aegis viewer (5000).

Run:
    python -m JSAC.planning.experiments.plaza_run.replay.server
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, send_from_directory

REPLAY_DIR = Path(__file__).resolve().parent
PORT = 5050

app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory(REPLAY_DIR, "index.html")


@app.route("/replay_data.json")
def data():
    return send_from_directory(REPLAY_DIR, "replay_data.json")


def main() -> None:
    if not (REPLAY_DIR / "replay_data.json").exists():
        from . import prepare_data

        prepare_data.main()
    # Bind 0.0.0.0 so VS Code remote port-forwarding and direct LAN access both work.
    print(f"plaza_run replay viewer: http://localhost:{PORT}/   (also LAN-reachable)")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
