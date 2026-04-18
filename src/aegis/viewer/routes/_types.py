"""Shared type aliases for Flask route handlers.

Flask handlers can return a bare ``Response``, a ``str`` (Jinja2 template
output), or ``(Response | str, status_code)`` tuples for error paths. Annotate
handlers with ``RouteResponse`` so the type checker accepts all shapes without
flagging ``tuple[Response, int]`` as a return-type mismatch.
"""

from __future__ import annotations

from flask import Response

RouteResponse = Response | str | tuple[Response, int] | tuple[str, int]
"""Either a bare Response/str or ``(response, status_code)`` for error paths."""
