"""In-app bug report endpoint: saves screenshot locally and creates a GitHub issue."""

import base64
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from flask import Flask, Response, jsonify, request, send_from_directory

log = logging.getLogger(__name__)

GITHUB_REPO = "rwydaegh/aegis"
SCREENSHOT_DIR = Path(os.environ.get("BUG_SCREENSHOT_DIR", "/tmp/bug-screenshots"))


def register(app: Flask, cache: dict, cache_lock) -> None:
    """Attach the bug report routes to *app*."""

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    @app.route("/bug-screenshots/<path:filename>")
    def serve_bug_screenshot(filename: str) -> Response:
        return send_from_directory(str(SCREENSHOT_DIR), filename)

    @app.route("/api/bug-report", methods=["POST"])
    def bug_report() -> Response:
        payload = request.get_json(silent=True) or {}

        description = payload.get("description", "").strip()
        screenshot = payload.get("screenshot", "")
        state = payload.get("state") or {}

        if not description:
            return jsonify({"error": "description is required"}), 400

        token = os.environ.get("GITHUB_ISSUES_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
        if not token:
            log.warning("Bug report received but no GitHub token configured")
            return jsonify({"error": "GitHub token not configured on server"}), 503

        # Save screenshot locally and build a public URL
        screenshot_url = ""
        if screenshot:
            screenshot_b64 = screenshot.split(",", 1)[1] if "," in screenshot else screenshot
            try:
                screenshot_bytes = base64.b64decode(screenshot_b64)
            except Exception:
                return jsonify({"error": "screenshot must be a valid base64 image"}), 400

            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            ext = "png" if "image/png" in screenshot else "jpg"
            filename = f"{timestamp}.{ext}"
            filepath = SCREENSHOT_DIR / filename
            filepath.write_bytes(screenshot_bytes)

            # Build public URL from the request host
            base_url = request.host_url.rstrip("/")
            screenshot_url = f"{base_url}/bug-screenshots/{filename}"
            log.info("Saved bug screenshot: %s", screenshot_url)

        title = f"[User report] {description[:72]}"
        body = _format_issue_body(description, screenshot_url, state)

        try:
            issue = _create_github_issue(token, title, body)
        except Exception:
            log.exception("Failed to create GitHub issue for bug report")
            return jsonify({"error": "Failed to create GitHub issue"}), 502

        return jsonify(
            {
                "issueNumber": issue["number"],
                "issueUrl": issue["html_url"],
            }
        )


def _create_github_issue(token: str, title: str, body: str) -> dict:
    """Create an issue on GitHub via the REST API and return the response dict."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "labels": ["user-report", "bug"],
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
        return result


def _format_issue_body(description: str, screenshot_url: str, state: dict) -> str:
    """Build a Markdown issue body with description, screenshot, and state table."""
    lines: list[str] = []

    lines.append("## Description")
    lines.append("")
    lines.append(description)
    lines.append("")

    if screenshot_url:
        lines.append("## Screenshot")
        lines.append("")
        lines.append(f"![Bug screenshot]({screenshot_url})")
        lines.append("")

    if state:
        lines.append("## App state")
        lines.append("")
        lines.append("| Key | Value |")
        lines.append("| --- | ----- |")
        for k, v in state.items():
            lines.append(f"| `{k}` | `{v}` |")
        lines.append("")

    lines.append("---")
    lines.append("*Reported via the in-app bug reporter.*")

    return "\n".join(lines)
