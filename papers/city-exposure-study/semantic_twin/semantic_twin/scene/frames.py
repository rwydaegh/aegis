"""The camera axes that a panorama sampler and the mesh cutter have to share.

Two things read a rectilinear crop of a panorama. :mod:`semantic_twin.pano_geometry`
samples image pixels out of the sphere, and :mod:`semantic_twin.scene.pinhole`
projects mesh triangles into the same crop. They agree only if they build the
crop's axes the same way, and until now each had its own copy of this function.

The two copies were checked before they were merged. They differed in one
expression, ``math.radians(x)`` against ``np.radians([yaw, pitch])``, and they
returned the same three vectors bit for bit over 140,000 angle pairs including
every multiple of 45 degrees and both poles. The surviving body is the one
:mod:`semantic_twin.pano_geometry` used, so the module with thirty importers is
unchanged and the one with four moved.
"""

from __future__ import annotations

import math

import numpy as np


def view_basis(yaw_deg: float, pitch_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Panorama-local right, forward and up axes of one rectilinear view.

    ``right`` stays in the horizontal plane at every pitch, so a crop is never
    rolled about its own axis. That is what lets an image column stand for a
    single azimuth and a row for a single elevation, which the boundary chains
    of the fishnet rely on.
    """
    yaw, pitch = np.radians([yaw_deg, pitch_deg])
    forward = np.array([math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)])
    right = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    up = np.cross(right, forward)
    return right, forward, up
