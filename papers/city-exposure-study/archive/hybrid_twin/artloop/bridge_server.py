"""Persistent headless Blender bridge. Run:

  ~/blender-4.5/blender -b --python artloop/bridge_server.py

Listens on 127.0.0.1:8266. Each connection sends one JSON object
{"code": "<python>"} and receives {"ok": bool, "out": str, "err": str}.
State (namespace, bpy scene) persists across calls, like a REPL.
"""

import io
import json
import socket
import traceback
from contextlib import redirect_stdout

import bpy  # noqa: F401

NS = {"bpy": bpy}
HOST, PORT = "127.0.0.1", 8266


def recv_all(conn):
    buf = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        buf += chunk
        try:
            json.loads(buf.decode())
            break
        except Exception:
            continue
    return buf


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[bridge] listening on {HOST}:{PORT}", flush=True)
    while True:
        conn, _ = srv.accept()
        try:
            req = json.loads(recv_all(conn).decode())
            code = req.get("code", "")
            if code == "__quit__":
                conn.sendall(json.dumps({"ok": True, "out": "bye", "err": ""}).encode())
                conn.close()
                break
            out_buf = io.StringIO()
            err = ""
            ok = True
            try:
                with redirect_stdout(out_buf):
                    exec(compile(code, "<bridge>", "exec"), NS)
            except Exception:
                ok = False
                err = traceback.format_exc()
            resp = {"ok": ok, "out": out_buf.getvalue()[-20000:], "err": err[-8000:]}
            conn.sendall(json.dumps(resp).encode())
        except Exception as e:
            try:
                conn.sendall(json.dumps({"ok": False, "out": "", "err": str(e)}).encode())
            except Exception:
                pass
        finally:
            conn.close()


main()
