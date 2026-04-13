"""Tests for the bug report endpoint."""

import os
from unittest.mock import patch

import pytest

from aegis.viewer.server import create_app


@pytest.fixture
def client(tmp_path):
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    app = create_app(data_dir=data_dir)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_bug_report_missing_description(client):
    resp = client.post(
        "/api/bug-report",
        json={"screenshot": "data:image/jpeg;base64,/9j/4AAQ", "state": {}},
    )
    assert resp.status_code == 400
    assert "description" in resp.get_json()["error"].lower()


def test_bug_report_missing_screenshot(client):
    resp = client.post(
        "/api/bug-report",
        json={"description": "something is broken", "state": {}},
    )
    assert resp.status_code == 400
    assert "screenshot" in resp.get_json()["error"].lower()


@patch("aegis.viewer.routes.bugreport._upload_screenshot_to_github")
@patch("aegis.viewer.routes.bugreport._create_github_issue")
def test_bug_report_success(mock_create_issue, mock_upload, client):
    mock_upload.return_value = "https://raw.githubusercontent.com/rwydaegh/aegis/bug-screenshots/test.jpg"
    mock_create_issue.return_value = {"number": 999, "html_url": "https://github.com/rwydaegh/aegis/issues/999"}

    # Minimal 1x1 JPEG in base64
    pixel = (
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
        "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN"
        "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
        "MjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBg"
        "cICQoL/8QAFRABAAAAAAAAAAAAAAAAAAAAAf/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQ"
        "EAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAB//2Q=="
    )

    resp = client.post(
        "/api/bug-report",
        json={
            "screenshot": f"data:image/jpeg;base64,{pixel}",
            "description": "tooltip clips behind sidebar",
            "state": {"mode": "spatial", "freqGhz": 28.0},
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["issueNumber"] == 999
    assert "github.com" in data["issueUrl"]
    mock_upload.assert_called_once()
    mock_create_issue.assert_called_once()
