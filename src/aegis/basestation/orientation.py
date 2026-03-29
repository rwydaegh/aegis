"""Antenna orientation: azimuth + tilt -> 3D rotation matrix."""

from __future__ import annotations

import numpy as np


def antenna_rotation_matrix(azimuth_deg: float, tilt_deg: float) -> np.ndarray:
    """Build rotation from world ENU frame to antenna-local frame.

    Convention (world): X=East, Y=North, Z=Up (ENU)
    Convention (antenna-local): y=boresight, x=right, z=up (before tilt)

    The boresight direction in world frame points along azimuth (CW from
    North in horizontal plane), tilted below horizontal by tilt_deg.

    Returns R such that d_local = R @ d_world.
    """
    az = np.deg2rad(azimuth_deg)
    tilt = np.deg2rad(tilt_deg)

    c_a, s_a = np.cos(az), np.sin(az)
    c_t, s_t = np.cos(tilt), np.sin(tilt)

    # Step 1: rotate around Z by +azimuth (align boresight with +Y)
    # In ENU, azimuth=0 means North (+Y), azimuth=90 means East (+X).
    # Boresight in world = [sin(az), cos(az), 0] (horizontal).
    # R_az rotates world vectors so that the azimuth direction maps to +Y.
    R_az = np.array(
        [
            [c_a, -s_a, 0.0],
            [s_a, c_a, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    # Step 2: rotate around local X by +tilt (positive tilt = boresight below horizontal)
    # After R_az, tilted boresight is [0, cos(tilt), -sin(tilt)].
    # R_tilt(+tilt) maps this to [0, 1, 0].
    R_tilt = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, c_t, -s_t],
            [0.0, s_t, c_t],
        ]
    )

    return R_tilt @ R_az


def departure_to_antenna_local(
    departure_dirs: np.ndarray,
    azimuth_deg: float,
    tilt_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert world-frame departure directions to antenna-local (elev, azim).

    Parameters
    ----------
    departure_dirs : (N, 3) unit vectors in ENU (from antenna toward target)
    azimuth_deg : compass bearing of main beam
    tilt_deg : total downtilt (electrical + mechanical)

    Returns
    -------
    elevation_deg : (N,) in [-90, 90], 0=horizontal
    azimuth_local_deg : (N,) in [-180, 180], 0=boresight direction
    """
    R = antenna_rotation_matrix(azimuth_deg, tilt_deg)
    d_local = (R @ departure_dirs.T).T  # (N, 3)

    # In antenna-local frame, z=boresight, x=right, y=up
    # Elevation: angle above/below horizontal = arcsin(y_local)
    # But we define boresight as the +Y direction after R_az,
    # so the boresight in local frame is along Y.
    # Actually, let's use a simpler approach:
    # The boresight direction in local frame = R @ boresight_world
    # should be [0, 1, 0] (the Y-axis after rotation).

    # Spherical angles relative to boresight:
    # boresight = local Y. azimuth_local = atan2(x, y), elevation_local = arcsin(z)
    x, y, z = d_local[:, 0], d_local[:, 1], d_local[:, 2]

    elevation_deg = np.rad2deg(np.arcsin(np.clip(z, -1.0, 1.0)))
    azimuth_local_deg = np.rad2deg(np.arctan2(x, y))

    return elevation_deg, azimuth_local_deg
