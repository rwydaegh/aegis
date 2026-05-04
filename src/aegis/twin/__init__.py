"""Body-twin abstractions: pose, Q caching, scene path dictionary calibration.

This subpackage is being grown incrementally as the JSAC paper experiments
need it. See JSAC/code/ROADMAP.md §7 for the planned shape (body_twin,
path_dictionary, scheduler).
"""

from aegis.twin.path_dictionary import calibrate_amplitudes

__all__ = ["calibrate_amplitudes"]
