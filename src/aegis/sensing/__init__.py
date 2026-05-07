"""Bystander sensing primitives for the BS-side digital twin.

Tier-C of the body-telemetry tier table (paper §VI) requires the BS to
localise non-cooperating bystanders well enough to budget their exposure
in the precoder. The only on-aperture lever for this is monostatic
integrated-sensing-and-communication (ISAC) at the carrier itself.

This module provides the closed-form back-of-envelope link budget,
detection-probability model, and angular/range resolution calculators
that justify (or refute) the tier-C claim. It is intentionally small:
no tracker, no multi-target deconfliction, no clutter rejection, no
micro-Doppler. The question is the antecedent of the tier-C row, "can
the BS see that a body is out there at range R," and only that.

When the BS cannot see (sensing blind spot or bistatic geometry),
tier-D is the policy fallback: the precoder budgets exposure against an
ordinance-defined occupancy envelope across the unsensed region.
"""

from __future__ import annotations

from aegis.sensing.rcs import (
    DetectionResult,
    SensingGeometry,
    angular_resolution_deg,
    crossrange_resolution_m,
    detection_probability,
    monostatic_snr_db,
    occupancy_envelope_density,
    range_resolution_m,
    tier_c_cell_area_m2,
)

__all__ = [
    "DetectionResult",
    "SensingGeometry",
    "angular_resolution_deg",
    "crossrange_resolution_m",
    "detection_probability",
    "monostatic_snr_db",
    "occupancy_envelope_density",
    "range_resolution_m",
    "tier_c_cell_area_m2",
]
