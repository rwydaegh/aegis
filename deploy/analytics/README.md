# Visitor email alerts

The production host checks the app and docs Umami properties every two minutes.
It uses the same Resend sender and recipient as Robin's website watcher.
Visits located in Ghent or Gent, Belgium are excluded. Unknown locations generate
alerts, matching the website watcher. Emails distinguish the app and docs.

The watcher reads Umami's PostgreSQL database through the existing Docker
container. No public analytics share or dashboard credential is needed.
The first run establishes a baseline without sending historical notifications.
Subsequent runs catch up from the last successful check, with a two-hour overlap.
Visit IDs are retained in `/var/lib/aegis-visitor-watcher/state.json` to prevent
repeat notifications. Each successful delivery is saved immediately, and Resend
idempotency keys also protect retries after an interrupted delivery.

Install `visitor_watcher.py` in `/opt/aegis/analytics/` and both units in
`/etc/systemd/system/`. Create `/opt/aegis/visitor-watcher.env` with mode 600,
containing `VISITOR_RESEND_API_KEY`, `VISITOR_EMAIL_FROM`, and `VISITOR_EMAIL_TO`.
Keep this file and the watcher state in private production backups.

```sh
systemctl daemon-reload
systemctl start aegis-visitor-watcher.service
systemctl enable --now aegis-visitor-watcher.timer
journalctl -u aegis-visitor-watcher.service -n 20
```

The docs property is `e068f879-5f00-4ceb-b9f9-dd2c10afb683`, owned by the same
Umami user as the viewer. Its script is in `docs/overrides/main.html` and only
tracks the production docs hostname. Preserve both properties when restoring
the Umami database.

Run the regression checks with:

```sh
python3 -m unittest discover -s deploy/analytics -p 'test_*.py'
```
