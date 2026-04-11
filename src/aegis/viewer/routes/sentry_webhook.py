"""Sentry webhook handler: creates rich GitHub issues from Sentry error events."""

import hashlib
import hmac
import json
import logging
import os
from urllib.request import Request, urlopen

from flask import Flask, Response, request

log = logging.getLogger(__name__)

GITHUB_REPO = "rwydaegh/aegis"


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach the Sentry webhook route to *app*."""

    @app.route("/api/sentry-webhook", methods=["POST"])
    def sentry_webhook() -> Response:
        # --- Verify signature ---
        client_secret = os.environ.get("SENTRY_CLIENT_SECRET", "")
        if client_secret:
            signature = request.headers.get("Sentry-Hook-Signature", "")
            body = request.get_data()
            expected = hmac.new(client_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                log.warning("Sentry webhook signature mismatch: got=%s expected=%s", signature[:8], expected[:8])
                return Response("Invalid signature", status=401)

        resource = request.headers.get("Sentry-Hook-Resource", "")
        if resource != "issue":
            return Response("OK", status=200)

        payload = request.get_json(silent=True)
        if not payload or payload.get("action") != "created":
            return Response("OK", status=200)

        try:
            _handle_new_issue(payload)
        except Exception:
            log.exception("Failed to create GitHub issue from Sentry webhook")
            # Return 200 to acknowledge receipt. Sentry retries on 5xx, which
            # would create duplicate issues if the failure is transient.
            return Response("Accepted (issue creation failed)", status=200)

        return Response("OK", status=200)


def _handle_new_issue(payload: dict) -> None:
    """Fetch full event from Sentry API, create a GitHub issue."""
    issue_data = payload.get("data", {}).get("issue", {})
    issue_id = issue_data.get("id")
    if not issue_id:
        log.warning("Sentry webhook missing issue ID")
        return

    sentry_token = os.environ.get("SENTRY_API_TOKEN", "")
    github_token = os.environ.get("GITHUB_ISSUES_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
    sentry_org = os.environ.get("SENTRY_ORG", "")
    sentry_project = os.environ.get("SENTRY_PROJECT", "")

    if not all([sentry_token, github_token, sentry_org, sentry_project]):
        log.warning("Missing env vars for Sentry webhook handler")
        return

    # Fetch the latest event for this issue from Sentry API
    event = _fetch_latest_event(sentry_org, sentry_project, issue_id, sentry_token)

    # Format the GitHub issue
    title = f"[Sentry] {issue_data.get('title', 'Unknown error')}"
    body = _format_issue_body(issue_data, event)

    # Create GitHub issue
    _create_github_issue(github_token, title, body)


def _fetch_latest_event(org: str, project: str, issue_id: str, token: str) -> dict | None:
    """GET the latest event for a Sentry issue."""
    api_host = os.environ.get("SENTRY_API_HOST", "https://de.sentry.io")
    url = f"{api_host}/api/0/issues/{issue_id}/events/latest/"
    req = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        log.exception("Failed to fetch Sentry event %s", issue_id)
        return None


def _format_issue_body(issue_data: dict, event: dict | None) -> str:
    """Build a Markdown issue body with all debugging context."""
    lines: list[str] = []

    # Header
    sentry_url = issue_data.get("permalink", "")
    lines.append(f"**Sentry issue:** {sentry_url}")
    lines.append(f"**First seen:** {issue_data.get('firstSeen', 'unknown')}")
    lines.append(f"**Events:** {issue_data.get('count', '?')}")
    lines.append("")

    if not event:
        lines.append("*Could not fetch full event details from Sentry API.*")
        lines.append("")
        lines.append("## Error")
        lines.append(f"```\n{issue_data.get('title', 'Unknown')}\n```")
        return "\n".join(lines)

    # Stack trace
    exception = _extract_exception(event)
    if exception:
        lines.append("## Stack trace")
        lines.append("```")
        lines.append(exception)
        lines.append("```")
        lines.append("")

    # Breadcrumbs (last 15)
    breadcrumbs = _extract_breadcrumbs(event)
    if breadcrumbs:
        lines.append("## Breadcrumbs (recent actions)")
        lines.append("")
        for bc in breadcrumbs:
            lines.append(f"- {bc}")
        lines.append("")

    # Custom contexts (simulation state, UI state, etc.)
    contexts = event.get("contexts", {})
    sim = contexts.get("simulation")
    if sim:
        lines.append("## Simulation state")
        lines.append("")
        pairs = [f"**{k}:** {v}" for k, v in sim.items() if v is not None]
        lines.append(" | ".join(pairs))
        lines.append("")

    ui = contexts.get("ui")
    if ui:
        lines.append("## UI state")
        lines.append("")
        pairs = [f"**{k}:** {v}" for k, v in ui.items() if v is not None]
        lines.append(" | ".join(pairs))
        lines.append("")

    scene = contexts.get("scene")
    if scene:
        lines.append("## Scene")
        lines.append("")
        pairs = [f"**{k}:** {v}" for k, v in scene.items() if v is not None]
        lines.append(" | ".join(pairs))
        lines.append("")

    mimo = contexts.get("mimo")
    if mimo:
        lines.append("## MIMO state")
        lines.append("")
        pairs = [f"**{k}:** {v}" for k, v in mimo.items() if v is not None]
        lines.append(" | ".join(pairs))
        lines.append("")

    # Browser / OS
    browser = contexts.get("browser", {})
    os_ctx = contexts.get("os", {})
    device = contexts.get("device", {})
    env_parts = []
    if browser.get("name"):
        env_parts.append(f"{browser['name']} {browser.get('version', '')}")
    if os_ctx.get("name"):
        env_parts.append(f"{os_ctx['name']} {os_ctx.get('version', '')}")
    if device.get("model"):
        env_parts.append(device["model"])
    if env_parts:
        lines.append("## Environment")
        lines.append("")
        lines.append(" | ".join(env_parts))
        lines.append("")

    # Tags
    tags = event.get("tags", [])
    if tags:
        useful_tags = {t["key"]: t["value"] for t in tags if t["key"] in ("url", "environment", "release", "level")}
        if useful_tags:
            lines.append("## Tags")
            lines.append("")
            for k, v in useful_tags.items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")

    lines.append("---")
    lines.append("*Auto-generated from Sentry. Label: `sentry`*")
    lines.append("")
    lines.append("@claude Fix this bug. The stack trace, breadcrumbs, and simulation state are above.")
    lines.append("Follow `.claude/rules/sentry-issues.md` for the workflow.")

    return "\n".join(lines)


def _extract_exception(event: dict) -> str | None:
    """Pull the formatted stack trace from a Sentry event."""
    entries = event.get("entries", [])
    for entry in entries:
        if entry.get("type") != "exception":
            continue
        values = entry.get("data", {}).get("values", [])
        parts = []
        for val in values:
            exc_type = val.get("type", "Error")
            exc_value = val.get("value", "")
            parts.append(f"{exc_type}: {exc_value}")
            stacktrace = val.get("stacktrace", {})
            frames = stacktrace.get("frames", [])
            for frame in reversed(frames[-10:]):
                filename = frame.get("filename") or frame.get("absPath", "?")
                lineno = frame.get("lineNo", "?")
                func = frame.get("function", "?")
                parts.append(f"    at {func} ({filename}:{lineno})")
        if parts:
            return "\n".join(parts)
    return None


def _extract_breadcrumbs(event: dict) -> list[str]:
    """Pull the last 15 breadcrumbs from a Sentry event."""
    entries = event.get("entries", [])
    for entry in entries:
        if entry.get("type") != "breadcrumbs":
            continue
        crumbs = entry.get("data", {}).get("values", [])
        result = []
        for bc in crumbs[-15:]:
            cat = bc.get("category", "")
            msg = bc.get("message", "")
            data = bc.get("data", {})
            ts = bc.get("timestamp", "")
            if cat == "fetch" or cat == "xhr":
                method = data.get("method", "")
                url = data.get("url", "")
                status = data.get("status_code", "")
                result.append(f"`{ts}` **{cat}:** {method} {url} -> {status}")
            elif cat == "ui.click":
                result.append(f"`{ts}` **click:** {msg}")
            elif cat == "console":
                level = bc.get("level", "")
                result.append(f"`{ts}` **console.{level}:** {msg[:100]}")
            elif cat == "navigation":
                result.append(f"`{ts}` **nav:** {data.get('from', '?')} -> {data.get('to', '?')}")
            else:
                desc = msg or json.dumps(data)[:80] if data else cat
                result.append(f"`{ts}` **{cat}:** {desc}")
        return result
    return []


def _create_github_issue(token: str, title: str, body: str) -> None:
    """Create an issue on GitHub via the REST API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "labels": ["sentry", "bug"],
        }
    ).encode()
    req = Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        log.info("Created GitHub issue #%s: %s", result.get("number"), title)
