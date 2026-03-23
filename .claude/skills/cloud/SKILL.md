---
name: cloud
description: Use when launching, syncing, or troubleshooting the AEGIS viewer on TensorDock cloud GPU machine
user-invocable: true
---

# /cloud - Launch AEGIS on TensorDock

Sync latest code to the TensorDock GPU machine, start the viewer, and provide access.

## Steps

1. **Check status.** Run `py -3.12 tools/cloud.py status`. If stopped, run `py -3.12 tools/cloud.py up`. Note the IP and SSH port from the output.

2. **Sync code.** Run `py -3.12 tools/cloud.py sync`. If npm fails (common after dependency upgrades due to cross-platform native bindings), SSH in and fix manually:
   ```bash
   ssh -i ~/.ssh/tensordock_ed25519 -p <ssh_port> user@<ip> \
     "cd ~/aegis/aegis-web && rm -rf node_modules package-lock.json && npm install && npm run build:copy"
   ```

3. **Kill old viewer.** `ssh <remote> "pkill -f aegis.viewer"`

4. **Start viewer.** Must use `--host 0.0.0.0` and `--no-open` on the remote:
   ```bash
   ssh <remote> 'source ~/aegis/.venv/bin/activate && cd ~/aegis && nohup python -m aegis.viewer --host 0.0.0.0 --no-open > /tmp/aegis.log 2>&1 &'
   ```
   Wait a few seconds, then verify: `ssh <remote> "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/"`

5. **Set up SSH tunnel.** TensorDock rarely forwards port 5000 publicly (only SSH gets NAT-mapped). Use a tunnel:
   ```bash
   ssh -i ~/.ssh/tensordock_ed25519 -L 5000:127.0.0.1:5000 -p <ssh_port> -N -f user@<ip>
   ```

6. **Verify locally.** `curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/` should return 200.

7. **Report to user.** Give them: IP, GPU type, access URL (`http://localhost:5000`), and the tunnel command in case it drops.

## Gotchas

- The viewer binds to `127.0.0.1` by default. Always pass `--host 0.0.0.0` on remote.
- `npm ci` fails when `node_modules` has binaries from a different platform (Windows vs Linux). Fix: nuke `node_modules` and `package-lock.json`, then `npm install`.
- The SSH tunnel command uses `-N -f` to background it. Multiple tunnel processes can pile up; check with `tasklist | grep ssh` on Windows.
- Auth credentials (if enabled) are in `~/.aegis-viewer-auth` on the VM. The env var `AEGIS_VIEWER_AUTH` must be set for auth to activate.
- `py -3.12 tools/cloud.py status` shows whether port 5000 is publicly forwarded. If it is, give the direct URL instead of tunneling.
