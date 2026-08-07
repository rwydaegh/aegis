"""Send a python file (or -c code) to the live Blender bridge.

  python artloop/bx.py -c "print(len(bpy.data.objects))"
  python artloop/bx.py step_01.py
"""

import json
import pathlib
import socket
import sys

if sys.argv[1] == "-c":
    code = sys.argv[2]
else:
    code = pathlib.Path(sys.argv[1]).read_text()

s = socket.create_connection(("127.0.0.1", 8266), timeout=1200)
s.sendall(json.dumps({"code": code}).encode())
buf = b""
while True:
    chunk = s.recv(65536)
    if not chunk:
        break
    buf += chunk
r = json.loads(buf.decode())
print(r["out"], end="")
if not r["ok"]:
    print("--- ERROR ---", file=sys.stderr)
    print(r["err"], file=sys.stderr)
    sys.exit(1)
