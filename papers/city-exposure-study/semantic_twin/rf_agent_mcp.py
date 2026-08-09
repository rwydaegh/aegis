"""Experimental MCP server giving Gemini a small RF surface workbench."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from semantic_twin.vision.rf_tools import (
    compare_surface_hypotheses,
    itu_material_state,
    rough_surface_response,
    roughness_priors,
)

mcp = FastMCP(
    "AEGIS RF surface workbench",
    instructions=(
        "Use these tools to test visual material and roughness hypotheses for a propagation-selected surface. "
        "They calculate consequences; they do not decide what the image contains."
    ),
)


@mcp.tool()
def lookup_itu_material(material: str, frequency_ghz: float) -> dict[str, Any]:
    """Return the ITU-R P.2040 dielectric state of one material at a carrier frequency."""
    return itu_material_state(material, frequency_ghz)


@mcp.tool()
def find_roughness_priors(itu_material: str | None = None, query: str = "") -> list[dict[str, Any]]:
    """Search the local roughness catalogue by ITU material and visible surface words."""
    return roughness_priors(itu_material=itu_material, query=query)


@mcp.tool()
def calculate_rough_surface_response(
    rms_height_mm: float, frequency_ghz: float, incidence_deg: float
) -> dict[str, float | bool]:
    """Calculate the Rayleigh parameter and coherent/noncoherent power split for an RMS guess."""
    return rough_surface_response(rms_height_mm, frequency_ghz, incidence_deg)


@mcp.tool()
def compare_rf_surface_hypotheses(
    hypotheses: list[dict[str, Any]], frequency_ghz: float, incidence_deg: float
) -> list[dict[str, Any]]:
    """Compare alternative ITU material and RMS-height hypotheses at one interaction."""
    return compare_surface_hypotheses(hypotheses, frequency_ghz, incidence_deg)


if __name__ == "__main__":
    mcp.run(transport="stdio")
