"""Geocoding helpers for base-station loading."""

from __future__ import annotations

import re

from aegis.viewer.config import DEFAULTS as _VIEWER_DEFAULTS

_NETWORK_TIMEOUT_S = _VIEWER_DEFAULTS["server"]["network_timeout_s"]

_ISO3166_TO_REGION = {
    "BE-VLG": "flanders",
    "BE-BRU": "brussels",
    "BE-WAL": "wallonia",
}

BELGIUM_NAMES: frozenset[str] = frozenset({"belgium", "belgië", "belgie", "belgique", "be"})

COUNTRY_TO_REGION: dict[str, str] = {
    "netherlands": "netherlands",
    "nederland": "netherlands",
    "nl": "netherlands",
    "germany": "germany",
    "deutschland": "germany",
    "de": "germany",
    "austria": "austria",
    "österreich": "austria",
    "at": "austria",
    "australia": "australia",
    "au": "australia",
    "france": "france",
    "fr": "france",
    "denmark": "denmark",
    "danmark": "denmark",
    "dk": "denmark",
    "poland": "poland",
    "polska": "poland",
    "pl": "poland",
    "spain": "spain",
    "españa": "spain",
    "es": "spain",
    "switzerland": "switzerland",
    "schweiz": "switzerland",
    "suisse": "switzerland",
    "ch": "switzerland",
    "canada": "canada",
    "ca": "canada",
    "united kingdom": "uk",
    "uk": "uk",
    "gb": "uk",
    "brazil": "brazil",
    "brasil": "brazil",
    "br": "brazil",
    "luxembourg": "luxembourg",
    "luxemburg": "luxembourg",
    "lu": "luxembourg",
}


def geocode_location(location: str) -> tuple[float, float, dict]:
    """Geocode a location string to (latitude, longitude, address_details).

    Tries parsing as "lat, lon" first (returns empty address dict),
    falls back to geopy Nominatim with address details.
    Raises ValueError on failure.
    """
    match = re.match(
        r"^\s*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)\s*$",
        location,
    )
    if match:
        return float(match.group(1)), float(match.group(2)), {}

    from geopy.exc import GeopyError
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent="aegis-viewer", timeout=_NETWORK_TIMEOUT_S)
    try:
        result = geolocator.geocode(location, addressdetails=True, language="en")  # pyright: ignore[reportArgumentType]  # geopy stub bug: language typed as bool
    except GeopyError as e:
        raise ValueError(f"Geocoding service unavailable: {e}") from e

    if result is None:
        raise ValueError(f"Could not geocode location: {location!r}")
    address = result.raw.get("address", {})  # pyright: ignore[reportAttributeAccessIssue]  # geopy stub bug: geocode returns Location, not Coroutine
    return result.latitude, result.longitude, address  # pyright: ignore[reportAttributeAccessIssue]  # same


def _resolve_belgian_region(address: dict, lat: float, lon: float) -> str:
    """Determine the Belgian region from Nominatim address or coordinates.

    Uses ISO 3166-2 level 4 code from Nominatim (authoritative), with a
    coordinate-based fallback for raw lat/lon input without address data.
    """
    iso_code = address.get("ISO3166-2-lvl4", "")
    region = _ISO3166_TO_REGION.get(iso_code)
    if region:
        return region

    if 50.79 <= lat <= 50.92 and 4.24 <= lon <= 4.49:
        return "brussels"
    if lat >= 50.75:
        return "flanders"
    return "wallonia"


def reverse_geocode_country(lat: float, lon: float) -> dict:
    """Reverse-geocode (lat, lon) to an address dict. Raises on failure."""
    from geopy.exc import GeopyError
    from geopy.geocoders import Nominatim

    geolocator = Nominatim(user_agent="aegis-viewer", timeout=_NETWORK_TIMEOUT_S)
    try:
        result = geolocator.reverse(
            (lat, lon),
            addressdetails=True,
            language="en",  # pyright: ignore[reportArgumentType]  # geopy stub bug: language typed as bool
        )
    except GeopyError as e:
        raise ValueError(f"Reverse geocoding service unavailable: {e}") from e
    if result is None:
        return {}
    return result.raw.get("address", {})  # pyright: ignore[reportAttributeAccessIssue]  # geopy stub bug
