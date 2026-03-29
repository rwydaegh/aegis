"""Straight skeleton algorithm for polygon decomposition.

Pure numpy port of blosm's bpypolyskel + bpyeuclid + poly2FacesGraph.
No Blender/mathutils dependency.

Reference: Felkel & Obdrzalek (1998) "Straight skeleton implementation".
"""

from aegis.environment.skeleton.api import polygonize, skeletonize
from aegis.environment.skeleton.events import Subtree

__all__ = ["polygonize", "skeletonize", "Subtree"]
