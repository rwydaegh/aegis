"""Hotspot field reconstruction for the coherent exposure operator.

Reconstructs the coherent Maxwell field around a beamforming focus from the
same ray-traced paths that feed the exposure operator, resolves the hotspot
on oriented slice planes and 3D volumes, and (via the layered-skin TMM)
shows the internal field that the focus drives into tissue.

Public surface:

    grid          FieldVolume, SlicePlane, orthonormal_frame
    synthesis     field_on, channel_at, field_channel_at, collapse_paths,
                  synthesize_field, power_density
    metrics       analyse_slice, analyse_volume, fwhm_1d, HotspotReport,
                  speckle_contrast
    averaging     exposure_average, propagation_average, patch_sweep,
                  radial_profile, incoherent_power, path_power,
                  participation_ratio, decohere_weights
    worstcase     local_max_intensity, worst_case_map, intensity_under,
                  worst_case_body
    internal      internal_panel, InternalPanel, transmitted_field,
                  nearest_surface
    antenna       dipole_response, AntennaPattern, make_rx_response
    layered_skin  solve_layered, single_layer_reference, default_stack, Layer,
                  DepthProfile
"""

from __future__ import annotations

from aegis.hotspot.antenna import (
    AntennaPattern,
    dipole_response,
    make_rx_response,
)
from aegis.hotspot.averaging import (
    decohere_weights,
    exposure_average,
    incoherent_power,
    participation_ratio,
    patch_sweep,
    path_power,
    propagation_average,
    radial_profile,
)
from aegis.hotspot.grid import FieldVolume, SlicePlane, orthonormal_frame
from aegis.hotspot.internal import (
    InternalPanel,
    internal_panel,
    nearest_surface,
    transmitted_field,
)
from aegis.hotspot.layered_skin import (
    DepthProfile,
    Layer,
    default_stack,
    single_layer_reference,
    solve_layered,
)
from aegis.hotspot.metrics import (
    HotspotReport,
    analyse_slice,
    analyse_volume,
    fwhm_1d,
    speckle_contrast,
)
from aegis.hotspot.synthesis import (
    channel_at,
    collapse_paths,
    field_channel_at,
    field_on,
    power_density,
    synthesize_field,
)
from aegis.hotspot.worstcase import (
    intensity_under,
    local_max_intensity,
    worst_case_body,
    worst_case_map,
)

__all__ = [
    "AntennaPattern",
    "dipole_response",
    "make_rx_response",
    "FieldVolume",
    "SlicePlane",
    "orthonormal_frame",
    "field_on",
    "channel_at",
    "field_channel_at",
    "collapse_paths",
    "synthesize_field",
    "power_density",
    "analyse_slice",
    "analyse_volume",
    "fwhm_1d",
    "speckle_contrast",
    "HotspotReport",
    "exposure_average",
    "propagation_average",
    "patch_sweep",
    "radial_profile",
    "incoherent_power",
    "path_power",
    "participation_ratio",
    "decohere_weights",
    "local_max_intensity",
    "worst_case_map",
    "intensity_under",
    "worst_case_body",
    "internal_panel",
    "InternalPanel",
    "transmitted_field",
    "nearest_surface",
    "solve_layered",
    "single_layer_reference",
    "default_stack",
    "Layer",
    "DepthProfile",
]
