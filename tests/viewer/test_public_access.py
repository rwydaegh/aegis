"""The public-access switch bypasses the gate without discarding its password."""

import pytest
from flask import Flask

from aegis.viewer.server._auth import setup_auth


@pytest.mark.parametrize("flag", [None, "false", "true", "TRUE", "1", ""])
def test_public_access_switch(monkeypatch, flag):
    monkeypatch.delenv("AEGIS_PUBLIC_ACCESS", raising=False)
    if flag is not None:
        monkeypatch.setenv("AEGIS_PUBLIC_ACCESS", flag)
    app = Flask(__name__)
    app.secret_key = "test-secret"
    setup_auth(app, "stored-password")
    app.add_url_rule("/api/protected", view_func=lambda: {"ok": True})
    client = app.test_client()

    public = flag == "true"
    assert client.get("/api/protected").status_code == (200 if public else 401)
    assert client.get("/api/auth").get_json()["authenticated"] is public
    if not public:
        assert client.post("/api/auth", json={"password": "stored-password"}).status_code == 200
        assert client.get("/api/protected").status_code == 200
