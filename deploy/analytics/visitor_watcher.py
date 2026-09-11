#!/usr/bin/env python3
"""Email Robin once per Umami visit, excluding Ghent, Belgium."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

SITES = {
    "70df2c46-53d1-4717-95fa-4248b4cc8bd6": "AEGIS app",
    "e068f879-5f00-4ceb-b9f9-dd2c10afb683": "AEGIS docs",
}
STATE_PATH = Path(os.environ.get("VISITOR_WATCHER_STATE", "/var/lib/aegis-visitor-watcher/state.json"))


def excluded(visit: dict) -> bool:
    return (visit.get("country") or "").strip().upper() == "BE" and (visit.get("city") or "").strip().casefold() in {
        "gent",
        "ghent",
    }


def recent_visits(start: float, end: float) -> list[dict]:
    sites = ",".join(f"'{site}'" for site in SITES)
    sql = f"""
        SELECT COALESCE(json_agg(v), '[]'::json) FROM (
            SELECT DISTINCT e.website_id, e.visit_id, s.country, s.city
            FROM website_event e
            JOIN session s ON s.session_id = e.session_id AND s.website_id = e.website_id
            WHERE e.website_id IN ({sites}) AND e.event_type = 1
              AND e.created_at >= to_timestamp({float(start)})
              AND e.created_at <= to_timestamp({float(end)})
            ORDER BY e.website_id, e.visit_id
        ) v
    """
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            os.environ.get("UMAMI_DB_CONTAINER", "aegis-umami-db-1"),
            "psql",
            "-X",
            "-U",
            "umami",
            "-d",
            "umami",
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql,
        text=True,
        capture_output=True,
        check=True,
        timeout=60,
    )
    return json.loads(result.stdout)


def notify(visit: dict, key: str) -> None:
    site = SITES[visit["website_id"]]
    location = ", ".join(filter(None, (visit.get("city"), visit.get("country")))) or "unknown location"
    body = json.dumps(
        {
            "from": os.environ["VISITOR_EMAIL_FROM"],
            "to": [os.environ["VISITOR_EMAIL_TO"]],
            "subject": f"New visitor on {site}",
            "text": f"Someone visited {site}.\nLocation: {location}.\n\n"
            "Ghent/Gent, Belgium visits are excluded. Unknown locations are included.\n"
            f"https://analytics.waves-ugent.be/websites/{visit['website_id']}",
        }
    ).encode()
    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {os.environ['VISITOR_RESEND_API_KEY']}",
            "Content-Type": "application/json",
            "User-Agent": "aegis-visitor-watcher/1",
            "Idempotency-Key": f"aegis-visit-{key}",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if not json.load(response).get("id"):
            raise RuntimeError("Email provider did not return a message ID")


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state) + "\n")
    temporary.chmod(0o600)
    temporary.replace(STATE_PATH)


def run() -> None:
    # Missing credentials fail before baselining or advancing state.
    for name in ("VISITOR_EMAIL_FROM", "VISITOR_EMAIL_TO", "VISITOR_RESEND_API_KEY"):
        if not os.environ.get(name):
            raise ValueError(f"{name} is required")
    now = time.time()
    try:
        state = json.loads(STATE_PATH.read_text())
    except FileNotFoundError:
        state = {"checked_at": now, "initialized": False, "visits": []}
    seen = set(state["visits"])
    visits = recent_visits(state["checked_at"] - 7200, now)
    sent = 0
    for visit in visits:
        key = f"{visit['website_id']}-{visit['visit_id']}"
        if key in seen:
            continue
        if state["initialized"] and not excluded(visit):
            notify(visit, key)
            sent += 1
        seen.add(key)
        state["visits"].append(key)
        # Persist each success so a later delivery failure does not repeat it.
        save_state(state)
    state.update(checked_at=now, initialized=True)
    save_state(state)
    print(f"Checked {len(visits)} visits, sent {sent} emails", flush=True)


if __name__ == "__main__":
    run()
