"""The base station antenna axis of the illumination model.

Everything the estimator knows about the network lives in one function, the
angular power density `Q_S(u)` of section 4 of PAPER_METHODS.md. Until now that
function described a population of **isotropic** radiators: a site contributed
to `Q` in proportion to how many sites the direction `u` holds, and not at all
in proportion to where its antenna was pointing. This module puts the pattern
back.

The reason a pattern is a re-weighting of `Q` and nothing else is derived in
BEAMFORMING.md section 2 and is worth one paragraph here, because it is what
makes the whole module twenty lines of physics rather than a second tracer.
Write the exact adjoint identity for the estimator,

    chi = [ (1/N) sum_j w_j Lambda(x_K_j, u_ext_j) ]
          / [ (1/4pi) integral over 4pi of Lambda(x, u) dOmega ]

    Lambda(y, u) = integral over t of nu(y + t u) P(y + t u) G(-u ; y + t u) dt

where `nu` is the volumetric site density, `P` the per site transmit power and
`G(d ; S)` the gain of the site at `S` in direction `d`. The numerator's line
integral starts at the last scattering vertex `x_K_j` and the denominator's at
the observer `x`. The shipped estimator replaces the first by the second, which
is the far source approximation it has always made, and under that replacement
the gain enters only as a function of the exit direction. So

    Q_G(u) proportional to Q(u) * G(-u ; a site lying along u from x)

and the deposit rule, the ray paths, the throughputs and the random numbers are
all untouched. Adding an antenna is adding an illumination model.

Three consequences follow immediately and they are the module's reason to exist.

**A matched beam is invisible.** If every site steers its peak at the
pedestrian then `G(-u ; S)` is the same constant for every `u`, it factors out
of both line integrals, and the normalisation of `Q` removes it. `chi` is
exactly unchanged. BEAMFORMING.md section 3 shows this is a real result for
full digital maximum ratio transmission and an artefact of the far source
approximation for geometric beam steering, and measures the size of the
artefact.

**A broadcast beam is not.** The elevation at which a site sits on the
pedestrian's sky is exactly the depression angle at which it has to radiate to
reach them, so a vertical pattern with electrical downtilt multiplies `Q` in the
one variable the whole study turns on.

**A beam serving somebody else is somewhere in between**, and where in between
is set by how the served user population's angular spread compares with the
array's beamwidth.

Patterns follow 3GPP TR 38.901 clause 7.3. Angle conventions are the standard's:
`theta` from the zenith so that 90 degrees is the horizon, `phi` in azimuth from
the antenna boresight.
"""

from __future__ import annotations

import json
import math
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from ..illumination import (
    ISOTROPIC,
    ROOFTOP,
    ROOFTOP_PATHLOSS,
    STREET_SMALL_CELL,
    STREET_SMALL_CELL_PATHLOSS,
    IlluminationModel,
    Isotropic,
)
from ..sites import STUDY_ORDER
from ..transport.tracer import TERMINATIONS

SPEED_OF_LIGHT_M_S = 299_792_458.0

# --------------------------------------------------------------------------
# The single element, 3GPP TR 38.901 clause 7.3, Table 7.3-1
# --------------------------------------------------------------------------

#: Vertical and horizontal 3 dB beamwidths of the single element, in degrees.
#: Table 7.3-1 of TR 38.901 gives 65 degrees for both, inherited from
#: TR 37.840 clause 5.4.4.2.
ELEMENT_THETA_3DB_DEG = 65.0
ELEMENT_PHI_3DB_DEG = 65.0
#: Side lobe level limit in the vertical cut and the front to back ratio in the
#: horizontal cut, both 30 dB in Table 7.3-1.
ELEMENT_SLA_V_DB = 30.0
ELEMENT_A_MAX_DB = 30.0
#: Maximum directional gain of the element, 8 dBi in Table 7.3-1. It is a
#: constant and every quantity in this module is a normalised density, so it
#: cancels. It is carried because a reader checking against the table will look
#: for it.
ELEMENT_GAIN_DBI = 8.0


def element_pattern_db(
    theta_deg: np.ndarray,
    phi_deg: np.ndarray,
    *,
    theta_3db_deg: float = ELEMENT_THETA_3DB_DEG,
    phi_3db_deg: float = ELEMENT_PHI_3DB_DEG,
    sla_v_db: float = ELEMENT_SLA_V_DB,
    a_max_db: float = ELEMENT_A_MAX_DB,
) -> np.ndarray:
    """Table 7.3-1 of TR 38.901, in dB relative to the element's peak.

    ``theta_deg`` is measured from the zenith, so 90 is the horizon and a site
    radiating down at a depression of ``alpha`` uses ``theta = 90 + alpha``.
    ``phi_deg`` is measured from the boresight and is wrapped to
    ``[-180, 180]`` here rather than being required to arrive that way.

    The three lines of the table, in order:

        A_V   = -min[ 12 ((theta - 90)/theta_3dB)^2 , SLA_V ]
        A_H   = -min[ 12 (phi/phi_3dB)^2 , A_max ]
        A_3D  = -min[ -(A_V + A_H) , A_max ]

    The third line is the one that is easy to drop. Without it the pattern
    reaches -60 dB in the back upper quadrant, where the standard holds it at
    -30.
    """
    vertical = -np.minimum(12.0 * ((np.asarray(theta_deg, dtype=np.float64) - 90.0) / theta_3db_deg) ** 2, sla_v_db)
    wrapped = (np.asarray(phi_deg, dtype=np.float64) + 180.0) % 360.0 - 180.0
    horizontal = -np.minimum(12.0 * (wrapped / phi_3db_deg) ** 2, a_max_db)
    return -np.minimum(-(vertical + horizontal), a_max_db)


def element_gain(theta_deg: np.ndarray, phi_deg: np.ndarray, **kwargs: float) -> np.ndarray:
    """:func:`element_pattern_db` as a linear power gain with a peak of one."""
    return 10.0 ** (element_pattern_db(theta_deg, phi_deg, **kwargs) / 10.0)


# --------------------------------------------------------------------------
# The array, 3GPP TR 38.901 clause 7.3
# --------------------------------------------------------------------------


def _dirichlet_power(count: int, phase: np.ndarray) -> np.ndarray:
    """``|sum_{m=0}^{count-1} exp(i m phase)|^2``, safe at the grating lobes.

    Equals ``sin^2(count*phase/2) / sin^2(phase/2)`` away from
    ``phase = 0 mod 2 pi`` and ``count^2`` on it. The naive form is 0/0 there
    and that is exactly the main lobe, so the branch is not an edge case.
    """
    half = 0.5 * np.asarray(phase, dtype=np.float64)
    denominator = np.sin(half)
    near_axis = np.abs(denominator) < 1.0e-9
    safe = np.where(near_axis, 1.0, denominator)
    value = (np.sin(count * half) / safe) ** 2
    return np.where(near_axis, float(count) ** 2, value)


@dataclass(frozen=True)
class PlanarArray:
    """A uniform rectangular panel, TR 38.901 clause 7.3 ``(M, N, P, Mg, Ng)``.

    ``rows`` is `M`, the number of elements in the vertical direction, and
    ``columns`` is `N`, the number in the horizontal direction. Only one panel
    and one polarisation are modelled, so ``P = Mg = Ng = 1``. Spacings are in
    wavelengths, ``dV`` and ``dH`` in the standard's notation.

    The composite pattern is the element pattern times the array factor,

        AF(theta, phi) = | sum_{m,n} w_{m,n} v_{m,n}(theta, phi) |^2

        v_{m,n} = exp( i 2 pi [ (m-1) dV cos(theta)
                                + (n-1) dH sin(theta) sin(phi) ] )
        w_{m,n} = (1/sqrt(MN)) exp( -i 2 pi [ (m-1) dV cos(theta_tilt)
                                + (n-1) dH sin(theta_tilt) sin(phi_scan) ] )

    which peaks at ``MN`` in the steered direction. The weight is the conjugate
    of the response, that is, the array is matched to its own steering
    direction, which is what makes ``AF`` a maximum ratio combiner over the
    aperture. The rectangular grid and the separable weight make ``AF``
    factorise into two Dirichlet kernels, so this is closed form and costs no
    memory in the element count.
    """

    rows: int = 8
    columns: int = 8
    row_spacing_wavelengths: float = 0.5
    column_spacing_wavelengths: float = 0.5

    @property
    def elements(self) -> int:
        return int(self.rows * self.columns)

    @property
    def peak_gain_db(self) -> float:
        """The array factor's peak, ``10 log10(MN)``, over the element."""
        return 10.0 * math.log10(self.elements)

    def aperture_m(self, frequency_hz: float) -> tuple[float, float]:
        """Physical (vertical, horizontal) extent of the panel, in metres."""
        wavelength = SPEED_OF_LIGHT_M_S / float(frequency_hz)
        return (
            (self.rows - 1) * self.row_spacing_wavelengths * wavelength,
            (self.columns - 1) * self.column_spacing_wavelengths * wavelength,
        )

    def array_factor(
        self,
        theta_deg: np.ndarray,
        phi_deg: np.ndarray,
        *,
        tilt_deg: np.ndarray | float = 90.0,
        scan_deg: np.ndarray | float = 0.0,
    ) -> np.ndarray:
        """``|AF|^2`` as a linear power gain, peaking at ``MN``.

        ``tilt_deg`` is `theta_etilt` and ``scan_deg`` is `phi_escan`, both in
        the standard's convention, so ``tilt_deg = 90`` points at the horizon
        and ``tilt_deg = 102`` is a 12 degree electrical downtilt. All four
        arguments broadcast against each other, which is what makes averaging
        over a served user population one call rather than a loop.
        """
        theta = np.radians(np.asarray(theta_deg, dtype=np.float64))
        phi = np.radians(np.asarray(phi_deg, dtype=np.float64))
        tilt = np.radians(np.asarray(tilt_deg, dtype=np.float64))
        scan = np.radians(np.asarray(scan_deg, dtype=np.float64))
        vertical = _dirichlet_power(
            self.rows,
            2.0 * np.pi * self.row_spacing_wavelengths * (np.cos(theta) - np.cos(tilt)),
        )
        horizontal = _dirichlet_power(
            self.columns,
            2.0 * np.pi * self.column_spacing_wavelengths * (np.sin(theta) * np.sin(phi) - np.sin(tilt) * np.sin(scan)),
        )
        return vertical * horizontal / self.elements


#: The canonical panel this study uses. Eight by eight at half wavelength
#: spacing is the TR 38.901 dense urban macro configuration, and at 15 GHz its
#: aperture is 70 mm by 70 mm.
CANONICAL_ARRAY = PlanarArray()


# --------------------------------------------------------------------------
# From a direction on the pedestrian's sky to an angle in the site's frame
# --------------------------------------------------------------------------


def source_frame_angles(
    elevation_rad: np.ndarray,
    azimuth_rad: np.ndarray,
    *,
    boresight_azimuth_deg: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Where the pedestrian sits in the radiation pattern of a site along `u`.

    This is the only geometry in the module and it is one line of trigonometry
    with one useful consequence. A site seen at elevation ``alpha`` above the
    pedestrian's horizon must radiate at a depression of exactly ``alpha`` to
    reach them, so its pattern is sampled at ``theta = 90 + alpha``. **The
    elevation axis of `Q` and the elevation axis of the antenna pattern are the
    same axis**, which is why a downtilt lands directly on the variable the
    study's whole result is about.

    In azimuth the pedestrian is at ``beta + 180`` from the site, since the site
    is at ``beta`` from the pedestrian, and ``phi`` is measured from the site's
    boresight.
    """
    theta_deg = 90.0 + np.degrees(np.asarray(elevation_rad, dtype=np.float64))
    phi_deg = np.degrees(np.asarray(azimuth_rad, dtype=np.float64)) + 180.0 - boresight_azimuth_deg
    return theta_deg, (phi_deg + 180.0) % 360.0 - 180.0


def direction_angles(directions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Elevation and azimuth, in radians, of unit vectors leaving the observer."""
    array = np.asarray(directions, dtype=np.float64)
    return np.arcsin(np.clip(array[:, 2], -1.0, 1.0)), np.arctan2(array[:, 1], array[:, 0])


# --------------------------------------------------------------------------
# The gain laws
# --------------------------------------------------------------------------

#: A gain law maps (elevation, azimuth) of a site on the pedestrian's sky, both
#: in radians, to the linear power gain that site has **towards the
#: pedestrian**. Only its shape matters, since `Q` is normalised.
GainLaw = Callable[[np.ndarray, np.ndarray], np.ndarray]

#: Azimuths of the three sector boresights, before the site grid is rotated.
THREE_SECTOR_AZIMUTHS_DEG = (0.0, 120.0, 240.0)


def matched_gain(elevation_rad: np.ndarray, azimuth_rad: np.ndarray) -> np.ndarray:
    """Every site puts its peak on the pedestrian.

    Constant, so it divides out of a normalised `Q` and leaves `chi` exactly
    where it was. It is here to be run rather than asserted: the test suite
    traces it and checks the invariance rather than trusting the algebra.
    """
    return np.ones_like(np.asarray(elevation_rad, dtype=np.float64))


def element_only_gain(elevation_rad: np.ndarray, azimuth_rad: np.ndarray) -> np.ndarray:
    """The serving sector's element pattern, with the array pointed at the pedestrian.

    This is what full digital maximum ratio transmission reduces to. The array
    factor contributes its peak `MN` for every site and therefore cancels, and
    the element pattern does not cancel, because it multiplies each path's
    power before the aperture ever sees it. BEAMFORMING.md section 3.

    The two non serving sectors are dropped. They sit at 120 degrees in
    azimuth, where the element pattern is on its 30 dB floor, so with a serving
    sector carrying 18.1 dB of array gain they are 30 dB down and worth
    0.004 dB on the sum.
    """
    theta_deg, _ = source_frame_angles(elevation_rad, azimuth_rad)
    return element_gain(theta_deg, np.zeros_like(theta_deg))


@dataclass(frozen=True)
class BroadcastBeam:
    """A fixed cell defining beam with real downtilt, pointed at nobody.

    The synchronisation signal block beam has to cover the whole sector, so it
    is not the narrow traffic beam. The configuration modelled is the usual one
    for a cell defining beam: the full vertical aperture, which is what sets
    coverage depth, and no azimuth narrowing, so the horizontal shape is the
    element's own 65 degree pattern. ``columns`` of the array is therefore not
    consulted, only ``rows``.

    ``sectors`` sums the sites' three sectors, all of which transmit their own
    broadcast beam at the same time. With 65 degree elements on a 120 degree
    grid that sum ripples by about 7 dB in azimuth, which is the ordinary
    three sector cusp and is why the azimuth of the sector grid relative to the
    square is a nuisance parameter rather than a detail.
    """

    array: PlanarArray = CANONICAL_ARRAY
    tilt_deg: float = 102.0
    grid_rotation_deg: float = 0.0
    sectors: tuple[float, ...] = THREE_SECTOR_AZIMUTHS_DEG

    def __call__(self, elevation_rad: np.ndarray, azimuth_rad: np.ndarray) -> np.ndarray:
        total = np.zeros_like(np.asarray(elevation_rad, dtype=np.float64))
        for sector in self.sectors:
            theta_deg, phi_deg = source_frame_angles(
                elevation_rad, azimuth_rad, boresight_azimuth_deg=sector + self.grid_rotation_deg
            )
            total = total + element_gain(theta_deg, phi_deg) * self.array.array_factor(
                theta_deg, np.zeros_like(phi_deg), tilt_deg=self.tilt_deg, scan_deg=0.0
            )
        return total


@dataclass(frozen=True)
class SteeredOffsetBeam:
    """The beam serves somebody a fixed angular offset away from the pedestrian.

    The one knob that turns the invariance off continuously. At zero offset
    every site is matched to the pedestrian, the gain is constant over the
    directions being integrated, and `chi` is exactly the isotropic site answer.
    Move the offset and the pedestrian slides down the pattern, so this is the
    invariance and its failure on the same axis, which is what makes it worth
    sweeping rather than tabulating two cases.

    The offset is defined in each site's own frame, from the direction of the
    pedestrian, so ``offset_elevation_deg`` is how much steeper or shallower the
    served user is and ``offset_azimuth_deg`` is how far round. That is the
    right variable because the array's response depends on the offset and not on
    where the pair sits on the sky.

    Only the serving sector is modelled, for the reason
    :func:`element_only_gain` gives.
    """

    array: PlanarArray = CANONICAL_ARRAY
    offset_elevation_deg: float = 0.0
    offset_azimuth_deg: float = 0.0

    def __call__(self, elevation_rad: np.ndarray, azimuth_rad: np.ndarray) -> np.ndarray:
        theta_deg, _ = source_frame_angles(elevation_rad, azimuth_rad)
        phi_deg = np.zeros_like(theta_deg)
        return element_gain(theta_deg, phi_deg) * self.array.array_factor(
            theta_deg,
            phi_deg,
            tilt_deg=theta_deg + self.offset_elevation_deg,
            scan_deg=phi_deg + self.offset_azimuth_deg,
        )


@dataclass(frozen=True)
class SweptBeam:
    """The envelope of a synchronisation signal block sweep, in azimuth.

    A site that forms several narrow beams and sweeps them across the sector
    leaves a pedestrian camped on whichever one is best, so what they see over a
    burst is the **envelope** of the beam set and not its average. Modelled as
    the maximum over ``scan_deg`` of the full panel with the vertical steered at
    ``tilt_deg``.

    This is an upper bound on the broadcast case, and the honest statement of
    what it neglects is duty cycle: a swept beam is on the pedestrian for one
    slot in ``len(scan_deg)`` rather than continuously, so a time averaged
    exposure would fall between :class:`BroadcastBeam` and this.
    """

    array: PlanarArray = CANONICAL_ARRAY
    tilt_deg: float = 102.0
    grid_rotation_deg: float = 0.0
    sectors: tuple[float, ...] = THREE_SECTOR_AZIMUTHS_DEG
    scan_deg: tuple[float, ...] = (-45.0, -30.0, -15.0, 0.0, 15.0, 30.0, 45.0)

    def __call__(self, elevation_rad: np.ndarray, azimuth_rad: np.ndarray) -> np.ndarray:
        best = np.zeros_like(np.asarray(elevation_rad, dtype=np.float64))
        for sector in self.sectors:
            theta_deg, phi_deg = source_frame_angles(
                elevation_rad, azimuth_rad, boresight_azimuth_deg=sector + self.grid_rotation_deg
            )
            element = element_gain(theta_deg, phi_deg)
            for scan in self.scan_deg:
                gain = element * self.array.array_factor(theta_deg, phi_deg, tilt_deg=self.tilt_deg, scan_deg=scan)
                best = np.maximum(best, gain)
        return best


class TabulatedGain:
    """A gain law sampled onto an (elevation, azimuth) grid and interpolated.

    Only a performance layer, and it exists because the tracer evaluates the
    gain on every escaping ray of every batch. The loaded beam averages the
    array factor over a few thousand served user directions, which is a second
    of work for one call and an hour of work for a run.

    Interpolation is bilinear, periodic in azimuth and clamped in elevation. The
    error it introduces is measured in the test suite by refining the grid
    rather than argued for, and the laws that need a fine grid are the ones with
    pattern nulls in them, not the ones being averaged.
    """

    def __init__(
        self,
        gain: GainLaw,
        *,
        elevation_nodes: int = 1_201,
        azimuth_nodes: int = 361,
        chunk: int = 65_536,
    ) -> None:
        self.source = gain
        self._elevation = np.radians(np.linspace(-90.0, 90.0, int(elevation_nodes)))
        self._azimuth = np.radians(np.linspace(-180.0, 180.0, int(azimuth_nodes)))
        grid_elevation = np.repeat(self._elevation, self._azimuth.size)
        grid_azimuth = np.tile(self._azimuth, self._elevation.size)
        table = np.empty(grid_elevation.size)
        for start in range(0, grid_elevation.size, chunk):
            stop = min(start + chunk, grid_elevation.size)
            table[start:stop] = gain(grid_elevation[start:stop], grid_azimuth[start:stop])
        self._table = table.reshape(self._elevation.size, self._azimuth.size)

    def __call__(self, elevation_rad: np.ndarray, azimuth_rad: np.ndarray) -> np.ndarray:
        elevation = np.asarray(elevation_rad, dtype=np.float64)
        azimuth = (np.asarray(azimuth_rad, dtype=np.float64) + np.pi) % (2.0 * np.pi) - np.pi
        de = self._elevation[1] - self._elevation[0]
        da = self._azimuth[1] - self._azimuth[0]
        fi = np.clip((elevation - self._elevation[0]) / de, 0.0, self._elevation.size - 1.0)
        fj = np.clip((azimuth - self._azimuth[0]) / da, 0.0, self._azimuth.size - 1.0)
        i0 = np.minimum(fi.astype(np.int64), self._elevation.size - 2)
        j0 = np.minimum(fj.astype(np.int64), self._azimuth.size - 2)
        ti = fi - i0
        tj = fj - j0
        top = self._table[i0, j0] * (1.0 - tj) + self._table[i0, j0 + 1] * tj
        bottom = self._table[i0 + 1, j0] * (1.0 - tj) + self._table[i0 + 1, j0 + 1] * tj
        return top * (1.0 - ti) + bottom * ti


@dataclass
class LoadedBeam:
    """The beam is serving somebody else and the pedestrian gets what is left.

    **The user density assumption, stated because the answer is a functional of
    it.** The site's scheduled user is taken to be *exchangeable with the
    pedestrian*: its depression angle below the site is drawn from the same
    elevation density ``user_population`` that describes where sites sit on the
    pedestrian's sky, and its azimuth is uniform across the serving sector. The
    justification is a symmetry, not a measurement. A homogeneous site process
    and a homogeneous user process in the same slab produce the same angle
    distribution read from either end, so the pedestrian's own view of the
    network is the best available description of the network's view of its
    users.

    Two things that assumption gets wrong, with their signs:

    - **Cell association.** A user attaches to a strong site, not a uniformly
      drawn one, so real served users sit closer and therefore steeper than
      this. The beam then points below a pedestrian who is at the median
      elevation, and the gain towards them falls. This model is optimistic.
    - **Scheduling.** One user per site per slot is assumed. A site multiplexing
      several users spreads its beam over several directions, which pushes the
      average towards the uniform limit below.

    The limit worth knowing is that an array whose steering direction is
    uniform over the whole sphere delivers, on average, **approximately** unit
    array gain. Exactly one for a line array at half wavelength spacing, where
    the steering vectors are orthonormal over the sphere, and 0.68 to 0.72 for
    this 8 by 8 panel, where they are not: a rectangular lattice's diagonal
    element offsets are ``lam/2 sqrt(dm^2 + dn^2)``, which are not whole half
    wavelengths, so the sinc cross terms do not vanish.
    ``tests/test_antenna.py`` measures both, once by quadrature and once from
    the closed form sinc sum, because the exact version of this statement was
    asserted here before it was checked and it was wrong.
    **A loaded array only reshapes `Q` to the extent that the user population is
    more concentrated than that**, and this class measures how much of the array
    gain that concentration is worth.
    """

    array: PlanarArray = CANONICAL_ARRAY
    user_population: IlluminationModel = ROOFTOP
    grid_rotation_deg: float = 0.0
    sectors: tuple[float, ...] = THREE_SECTOR_AZIMUTHS_DEG
    sector_half_width_deg: float = 60.0
    user_elevation_nodes: int = 24
    user_azimuth_nodes: int = 13
    chunk: int = 2048
    _users: tuple[np.ndarray, np.ndarray, np.ndarray] | None = field(default=None, repr=False, compare=False)

    def _user_draw(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Quadrature nodes and weights over the served user's direction."""
        if self._users is not None:
            return self._users
        from ..illumination import elevation_band_measure

        edges = np.linspace(
            self.user_population.elevation_min_deg,
            self.user_population.elevation_max_deg,
            self.user_elevation_nodes + 1,
        )
        measure = elevation_band_measure(self.user_population, edges)
        elevation = np.radians(0.5 * (edges[:-1] + edges[1:]))
        weight = measure / measure.sum()
        # Bin centres, matching the elevation axis above, because ``__call__``
        # gives every azimuth node the same weight ``1 / user_azimuth_nodes``
        # and equal weights are the midpoint rule, not the endpoint inclusive
        # one. Sampling the endpoints instead and still weighting them equally
        # over weights the two sector edges by a factor of two, is first order
        # rather than second, and at the default thirteen nodes it lifted the
        # loaded gain by about 30 percent over a rooftop population and by a
        # factor of 2.7 in the isotropic user limit where the sector is the
        # whole circle and the two endpoints are literally the same azimuth.
        azimuth_edges = np.linspace(
            -self.sector_half_width_deg, self.sector_half_width_deg, self.user_azimuth_nodes + 1
        )
        azimuth = np.radians(0.5 * (azimuth_edges[:-1] + azimuth_edges[1:]))
        self._users = (elevation, weight, azimuth)
        return self._users

    def __call__(self, elevation_rad: np.ndarray, azimuth_rad: np.ndarray) -> np.ndarray:
        user_elevation, user_weight, user_azimuth = self._user_draw()
        # theta_u and phi_escan of the served user, in the site's own frame.
        user_theta = 90.0 + np.degrees(user_elevation)
        elevation_rad = np.asarray(elevation_rad, dtype=np.float64)
        azimuth_rad = np.asarray(azimuth_rad, dtype=np.float64)
        total = np.zeros_like(elevation_rad)
        for sector in self.sectors:
            theta_deg, phi_deg = source_frame_angles(
                elevation_rad, azimuth_rad, boresight_azimuth_deg=sector + self.grid_rotation_deg
            )
            element = element_gain(theta_deg, phi_deg)
            # One broadcast over (evaluation point, user depression, user
            # azimuth). The loop is over blocks of evaluation points only, and
            # exists so the intermediate never exceeds a few tens of megabytes.
            scan_deg = np.degrees(user_azimuth)[None, None, :]
            tilt_deg = user_theta[None, :, None]
            mass = user_weight[None, :, None] / scan_deg.size
            average = np.zeros_like(theta_deg)
            for start in range(0, theta_deg.size, self.chunk):
                stop = min(start + self.chunk, theta_deg.size)
                gain = self.array.array_factor(
                    theta_deg[start:stop, None, None],
                    phi_deg[start:stop, None, None],
                    tilt_deg=tilt_deg,
                    scan_deg=scan_deg,
                )
                average[start:stop] = (gain * mass).sum(axis=(1, 2))
            total = total + element * average
        return total


# --------------------------------------------------------------------------
# An illumination model with a pattern on it
# --------------------------------------------------------------------------


class AntennaIllumination:
    """A site population times a per site gain towards the pedestrian.

    Satisfies :class:`~semantic_twin.illumination.model.AngularIllumination`
    so :class:`~semantic_twin.transport.tracer.SbrTracer` consumes it with no
    change at all. That protocol is ``name``, ``law``, ``family``,
    ``describe()``, the elevation window, ``weight()``, ``knots()``,
    ``normalisation()`` and ``density(directions, normalisation)``, and calls
    ``density`` on the exact exit direction of every escaping ray rather than on
    a grid cell, so a pattern with nulls in it costs variance and never bias.

    The normalisation cannot use the base model's elevation quadrature, because
    a sectorised pattern is not uniform in azimuth. It is done as an outer
    integral in elevation over an azimuth mean, on the base model's own
    abscissae with the base model's knots inserted, so the sharp part of the
    integrand is handled exactly as it is for the laws this wraps.
    """

    def __init__(
        self,
        name: str,
        base: IlluminationModel,
        gain: GainLaw,
        description: str,
        *,
        azimuth_nodes: int = 360,
        gain_nodes: int = 4_097,
    ) -> None:
        self.name = name
        self.base = base
        self.gain = gain
        self.description = description
        self.azimuth_nodes = int(azimuth_nodes)
        self.gain_nodes = int(gain_nodes)
        self._normalisation: float | None = None
        self._mean_gain: tuple[np.ndarray, np.ndarray] | None = None

    # The tracer reads these off the model when it writes a manifest.
    @property
    def law(self) -> str:
        return self.base.law

    @property
    def elevation_min_deg(self) -> float:
        return self.base.elevation_min_deg

    @property
    def elevation_max_deg(self) -> float:
        return self.base.elevation_max_deg

    @property
    def height_band_m(self) -> tuple[float, float] | None:
        return self.base.height_band_m

    @property
    def range_band_m(self) -> tuple[float, float] | None:
        return self.base.range_band_m

    def knots(self) -> tuple[float, ...]:
        return self.base.knots()

    def azimuth_mean_gain(self, elevation_rad: np.ndarray) -> np.ndarray:
        """``(1/2pi) integral of the gain over azimuth``, at each elevation."""
        azimuth = np.linspace(0.0, 2.0 * np.pi, self.azimuth_nodes, endpoint=False)
        elevation = np.asarray(elevation_rad, dtype=np.float64)
        grid_elevation = np.repeat(elevation, azimuth.size)
        grid_azimuth = np.tile(azimuth, elevation.size)
        return self.gain(grid_elevation, grid_azimuth).reshape(elevation.size, azimuth.size).mean(axis=1)

    def _mean_gain_table(self) -> tuple[np.ndarray, np.ndarray]:
        if self._mean_gain is None:
            low = math.radians(self.base.elevation_min_deg)
            high = math.radians(self.base.elevation_max_deg)
            nodes = np.linspace(low, high, self.gain_nodes)
            self._mean_gain = (nodes, self.azimuth_mean_gain(nodes))
        return self._mean_gain

    def weight(self, directions: np.ndarray) -> np.ndarray:
        elevation, azimuth = direction_angles(directions)
        return self.base.weight(directions) * self.gain(elevation, azimuth)

    def normalisation(self, quadrature: int = 200_001) -> float:
        """The same elevation quadrature the base law uses, with the gain in it.

        The azimuth mean of the gain is smooth even where the base law is not,
        so it is tabulated on a coarser grid and interpolated onto the fine one.
        The test suite refines both and checks that the answer stops moving.
        """
        if self._normalisation is not None:
            return self._normalisation
        low = math.radians(self.base.elevation_min_deg)
        high = math.radians(self.base.elevation_max_deg)
        elevation = np.linspace(low, high, quadrature)
        for knot in self.base.knots():
            if low < knot < high:
                elevation = np.insert(elevation, int(np.searchsorted(elevation, knot)), knot)
        nodes, table = self._mean_gain_table()
        mean_gain = np.interp(elevation, nodes, table)
        raw = self.base.profile(np.clip(elevation, low, high))
        self._normalisation = float(2.0 * np.pi * np.trapezoid(raw * mean_gain * np.cos(elevation), elevation))
        return self._normalisation

    def density(self, directions: np.ndarray, normalisation: float | None = None) -> np.ndarray:
        total = self.normalisation() if normalisation is None else normalisation
        if total <= 0.0:
            raise ValueError(f"antenna illumination {self.name!r} has no support")
        return self.weight(directions) / total


# --------------------------------------------------------------------------
# The transfer kernel in elevation, which is the object a pattern re-weights
# --------------------------------------------------------------------------


def elevation_probes(edges_deg: np.ndarray, *, prefix: str = "band") -> dict[str, IlluminationModel]:
    """Illumination models that are indicators on elevation bands.

    Tracing against these returns `K(alpha)`, the transfer kernel of section 1.3
    of PAPER_METHODS.md averaged over each band, because an indicator normalised
    to a density is ``1/Omega_band`` inside the band, and a free space trace
    deposits ``Omega_band/4pi`` of its rays there with unit throughput. So every
    entry is 1 in free space, exactly as `chi` is.

    `K` is the whole point of the module's efficiency claim. Any azimuthally
    symmetric illumination density, with or without an antenna on it, evaluates
    as ``sum_b K_b m_b`` with ``m_b`` the density's measure in band `b`, so a
    downtilt sweep or a pattern comparison costs no tracing once `K` exists.
    """
    edges = np.asarray(edges_deg, dtype=np.float64)
    return {
        f"{prefix}{index:03d}": Isotropic(
            name=f"{prefix}{index:03d}",
            elevation_min_deg=float(edges[index]),
            elevation_max_deg=float(edges[index + 1]),
            description=f"transfer kernel probe, elevation {edges[index]:.3f} to {edges[index + 1]:.3f} deg",
        )
        for index in range(edges.size - 1)
    }


#: Elevation band edges for the kernel. Dense at grazing, because that is where
#: every directional law puts its measure and where the kernel changes fastest,
#: and coarse near the zenith, where it is smooth and carries little weight.
KERNEL_EDGES_DEG = np.unique(
    np.concatenate(
        [
            np.linspace(0.0, 6.0, 25),
            np.linspace(6.0, 20.0, 29)[1:],
            np.linspace(20.0, 45.0, 26)[1:],
            np.linspace(45.0, 90.0, 16)[1:],
        ]
    )
)


def kernel_susceptibility(
    kernel: np.ndarray,
    edges_deg: np.ndarray,
    model: Any,
    *,
    samples: int = 4_096,
) -> float:
    """``chi`` for an azimuthally symmetric ``model``, from a tabulated kernel.

    Integrated band by band rather than sampled at a midpoint, for the reason
    section 4.4 of PAPER_METHODS.md gives: the grazing laws are convex, so a
    midpoint rule reads as a factor of six error in the physics.
    """
    from ..illumination import elevation_band_measure

    edges = np.asarray(edges_deg, dtype=np.float64)
    measure = elevation_band_measure(model, edges, samples=samples)
    return float(np.dot(np.asarray(kernel, dtype=np.float64), measure))


# --------------------------------------------------------------------------
# How big the far source artefact is
# --------------------------------------------------------------------------


def steering_artefact(
    record: Any,
    origin: np.ndarray,
    model: IlluminationModel,
    *,
    array: PlanarArray = CANONICAL_ARRAY,
    range_nodes: int = 24,
    codebook: tuple[int, int] | None = None,
) -> dict[str, float]:
    """How much a beam aimed at the pedestrian's real position suppresses multipath.

    This is the one number section 3.4 of BEAMFORMING.md needs and the one the
    shipped estimator structurally cannot produce, because the far source
    approximation sets it to unity by construction.

    A site that steers geometrically at the pedestrian puts its peak on the
    direction of `x`. A bounced path leaves that site towards the **last
    scattering vertex** `x_K`, which is somewhere else, so it collects a
    sidelobe. The free space reference has no bounce and keeps the peak. The
    ratio of the two gains is therefore a suppression that applies to the
    numerator of `chi` and not to its denominator, so

        chi (geometric steering) = chi (isotropic sites) * <suppression>

    with the average taken over exactly the deposit weights the estimator uses.
    Zero bounce rays have ``x_K = x``, offset zero and suppression one, which is
    the check that the LOS term is untouched.

    ``record`` is a :class:`~semantic_twin.transport.tracer.PathRecord`. The
    source range along each escaping ray is integrated over the same radial
    interval the illumination law itself integrates, so the site population here
    is the population the law describes and not a new assumption.

    What is measured is the array factor alone, with the aperture taken to be
    broadside on the pedestrian so the element pattern is unity in both the
    numerator and the reference. The element factor is not ignored, it is the
    separate ``_element`` column, and the two multiply. Keeping them apart is
    what makes this number readable as the size of the far source artefact
    rather than as a mixture of that and a fixed pattern.

    ``codebook`` names a discrete Fourier beam grid, ``(vertical, horizontal)``
    beams, and makes the site pick the grid beam nearest the pedestrian instead
    of steering exactly. The grid is the standard one, uniform in the direction
    cosine, so a grid as wide as the aperture puts its beams one beamwidth apart
    and its worst case scallop loss is the classical ``4/pi^2``, 3.92 dB per
    axis. That loss lands on the reference as well as on the scene, so it partly
    cancels, and how much of it cancels is exactly what a coarse codebook buys
    the pedestrian. ``None`` steers exactly and is the pure geometric case.
    """
    if model.height_band_m is None or model.range_band_m is None:
        raise ValueError(f"{model.name!r} has no site band, so it names no source population")
    lengths = np.diff(record.offsets)
    last = record.offsets[1:] - 2  # the sky point is last, the surface vertex before it
    keep = (np.asarray(record.termination) == TERMINATIONS.index("sky")) & (lengths >= 2)
    vertex = record.vertices[last[keep]]
    exit_direction = np.asarray(record.exit_direction)[keep]
    weight = record.throughput[record.offsets[1:][keep] - 1]
    bounces = np.asarray(record.bounces)[keep]
    density = model.density(exit_direction)
    deposit = weight * density
    live = deposit > 0.0
    if not np.any(live):
        raise ValueError("no escaping ray carries any illumination measure")
    vertex, exit_direction, deposit = vertex[live], exit_direction[live], deposit[live]
    bounces = bounces[live]

    elevation = np.arcsin(np.clip(exit_direction[:, 2], -1.0, 1.0))
    sine = np.sin(elevation)
    cosine = np.cos(elevation)
    low_h, high_h = model.height_band_m  # type: ignore[misc]
    low_d, high_d = model.range_band_m  # type: ignore[misc]
    near = np.maximum(low_h / sine, low_d / cosine)
    far = np.minimum(high_h / sine, high_d / cosine)

    # Radial quadrature over the slant ranges this direction can hold, with the
    # law's own radial weight: r^2 for the count form, flat for the path loss one.
    node = (np.arange(range_nodes) + 0.5) / range_nodes
    ranges = near[:, None] + node[None, :] * (far - near)[:, None]
    radial = np.ones_like(ranges) if model.law.endswith("pathloss") else ranges**2
    radial = radial / radial.sum(axis=1, keepdims=True)

    site = vertex[:, None, :] + ranges[:, :, None] * exit_direction[:, None, :]
    to_observer = np.asarray(origin, dtype=np.float64)[None, None, :] - site
    to_observer = to_observer / np.linalg.norm(to_observer, axis=2, keepdims=True)
    launch = np.broadcast_to(-exit_direction[:, None, :], to_observer.shape)

    def angles(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        theta = np.degrees(np.arccos(np.clip(direction[..., 2], -1.0, 1.0)))
        phi = np.degrees(np.arctan2(direction[..., 1], direction[..., 0]))
        return theta, phi

    theta_path, phi_path = angles(launch)
    theta_direct, phi_direct = angles(to_observer)

    # The two direction cosines the separable steering vector is a function of.
    # Working in these rather than in angles is what makes the codebook grid
    # uniform and the quantisation error a bounded constant.
    def cosines(theta_deg: np.ndarray, phi_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        theta = np.radians(theta_deg)
        phi = np.radians(phi_deg)
        return np.cos(theta), np.sin(theta) * np.sin(phi)

    path_v, path_h = cosines(theta_path, phi_path)
    direct_v, direct_h = cosines(theta_direct, phi_direct)
    steer_v, steer_h = direct_v, direct_h
    if codebook is not None:
        rows, columns = codebook
        steer_v = np.round(direct_v * rows / 2.0) * 2.0 / rows
        steer_h = np.round(direct_h * columns / 2.0) * 2.0 / columns

    def gain(cosine_v: np.ndarray, cosine_h: np.ndarray) -> np.ndarray:
        return (
            _dirichlet_power(array.rows, 2.0 * np.pi * array.row_spacing_wavelengths * (cosine_v - steer_v))
            * _dirichlet_power(
                array.columns,
                2.0 * np.pi * array.column_spacing_wavelengths * (cosine_h - steer_h),
            )
            / array.elements
        )

    suppression = gain(path_v, path_h) / gain(direct_v, direct_h)
    offset = np.degrees(np.arccos(np.clip(np.sum(launch * to_observer, axis=2), -1.0, 1.0)))

    total = float(deposit.sum())
    per_ray = (suppression * radial).sum(axis=1)
    offset_per_ray = (offset * radial).sum(axis=1)
    mean = float(np.dot(deposit, per_ray) / total)
    direct = bounces == 0

    def quantile(values: np.ndarray, level: float, *, mask: np.ndarray | None = None) -> float:
        """``level`` quantile of ``values`` under the deposit measure.

        ``mask`` restricts to a sub population and renormalises. The offsets are
        read over the bounced rays only, because the direct ones are exactly zero
        by construction and are a majority of the measure, so an unrestricted
        median would report a property of the direct share rather than a scale.

        A scene with no surfaces in it leaves that sub population empty, which
        is not a degenerate case to guard against but the reference case the
        whole measurement is read against, so it returns the zero it means
        rather than raising out of ``np.interp`` on an empty abscissa. Nothing
        is hidden by that: ``direct_measure`` is 1 in exactly that situation and
        says so.
        """
        weight = deposit if mask is None else deposit[mask]
        subset = values if mask is None else values[mask]
        if subset.size == 0 or weight.sum() <= 0.0:
            return 0.0
        order = np.argsort(subset)
        return float(np.interp(level, np.cumsum(weight[order]) / weight.sum(), subset[order]))

    return {
        "rays": int(deposit.size),
        "mean_suppression": mean,
        "mean_suppression_db": 10.0 * math.log10(mean) if mean > 0.0 else float("-inf"),
        "median_offset_deg": quantile(offset_per_ray, 0.5, mask=~direct),
        "p90_offset_deg": quantile(offset_per_ray, 0.9, mask=~direct),
        "measure_within_one_beamwidth": float(np.dot(deposit, offset_per_ray < 0.5 * 101.5 / array.rows) / total),
        # The share of the illumination measure that arrives without touching a
        # surface. It is the floor on the suppression, because those paths have
        # `x_K = x`, keep the beam peak, and cannot be steered away from.
        "direct_measure": float(deposit[direct].sum() / total),
        "bounced_suppression_db": (
            10.0 * math.log10(float(np.dot(deposit[~direct], per_ray[~direct]) / deposit[~direct].sum()))
            if np.any(~direct)
            else float("nan")
        ),
        # The two lengths whose ratio sets the offset, and therefore the whole
        # size of the effect: how far the last vertex is from the observer, and
        # how far away the site that sees it is.
        "median_last_vertex_offset_m": quantile(np.linalg.norm(vertex - np.asarray(origin), axis=1), 0.5, mask=~direct),
        "median_slant_range_m": quantile((ranges * radial).sum(axis=1), 0.5),
    }


# --------------------------------------------------------------------------
# The registry
# --------------------------------------------------------------------------

#: Electrical downtilt of the macro broadcast beam, as `theta_etilt` in the
#: standard's zenith referenced convention. 102 degrees is 12 degrees of
#: downtilt, the 3GPP urban macro evaluation value for a 25 m site on a 500 m
#: inter site distance. The study's own rooftop population puts its median site
#: at 9.5 degrees of elevation, so 12 degrees is a beam pointed slightly below
#: the population's centre of mass, which is what a planner aiming at cell edge
#: coverage would do.
MACRO_TILT_DEG = 102.0
#: Interpolation grid for the loaded beam. It is coarser than the default
#: because the loaded gain is an average of the array factor over about a
#: thousand served user directions, so it is smooth on the scale of the beam
#: width and has none of the pattern nulls that force a fine grid elsewhere.
LOADED_TABLE = {"elevation_nodes": 121, "azimuth_nodes": 61}
#: The street small cell equivalent. 3GPP urban micro street canyon uses a 10 m
#: site, and its population here sits at a 2.5 degree median elevation, so the
#: beam is nearly on the horizon.
MICRO_TILT_DEG = 96.0


#: Angular offsets, in degrees, at which the served user is placed away from the
#: pedestrian for the sweep of :class:`SteeredOffsetBeam`. Zero is the matched
#: case and is included so the invariance and its failure sit in one column set.
OFFSET_SWEEP_DEG = (0.0, 2.0, 5.0, 10.0, 20.0, 45.0)

#: Rotations of the three sector grid relative to the square, in degrees. The
#: pattern has a 120 degree period, so this covers it. The grid orientation is a
#: nuisance parameter of the deployment that no register in this study can pin,
#: so the spread across this sweep is the result rather than any one column.
GRID_ROTATION_SWEEP_DEG = (0.0, 40.0, 80.0)


def build_models(
    *,
    grid_rotation_deg: float = 0.0,
    macro_tilt_deg: float = MACRO_TILT_DEG,
    micro_tilt_deg: float = MICRO_TILT_DEG,
    array: PlanarArray = CANONICAL_ARRAY,
    offsets_deg: tuple[float, ...] = OFFSET_SWEEP_DEG,
    rotations_deg: tuple[float, ...] = GRID_ROTATION_SWEEP_DEG,
) -> dict[str, Any]:
    """Every antenna variant, over the rooftop and street populations.

    Grouped by what they are for. ``matched`` and the zero offset column are the
    invariance. ``element`` is what full digital maximum ratio transmission
    reduces to. ``broadcast``, ``swept`` and the rotation sweep are radiation
    that is not aimed at the pedestrian, which is the only kind that can move
    `chi`. ``loaded`` and the offset sweep are the same statement made
    continuous.
    """
    models: dict[str, Any] = {
        "isotropic": ISOTROPIC,
        "rooftop": ROOFTOP,
        "street_small_cell": STREET_SMALL_CELL,
        "rooftop_pathloss": ROOFTOP_PATHLOSS,
        "street_small_cell_pathloss": STREET_SMALL_CELL_PATHLOSS,
    }
    populations = {"rooftop": (ROOFTOP, macro_tilt_deg), "street_small_cell": (STREET_SMALL_CELL, micro_tilt_deg)}
    for stem, (base, tilt) in populations.items():
        for offset in offsets_deg:
            models[f"{stem}_offset{offset:g}"] = AntennaIllumination(
                f"{stem}_offset{offset:g}",
                base,
                SteeredOffsetBeam(array=array, offset_elevation_deg=offset),
                f"The served user is {offset:g} deg steeper than the pedestrian in the site's own "
                "frame, so the pedestrian is that far down the beam. Zero is the matched case and "
                "has to reproduce the isotropic site column exactly.",
            )
        for rotation in rotations_deg:
            models[f"{stem}_broadcast_rot{rotation:g}"] = AntennaIllumination(
                f"{stem}_broadcast_rot{rotation:g}",
                base,
                BroadcastBeam(array=array, tilt_deg=tilt, grid_rotation_deg=rotation),
                f"Broadcast beam with the three sector grid rotated {rotation:g} deg relative to the "
                "square. The spread across the sweep is what a sector boundary is worth.",
            )
        models[f"{stem}_matched"] = AntennaIllumination(
            f"{stem}_matched",
            base,
            matched_gain,
            "Every site puts its beam peak on the pedestrian. Constant gain, so it cancels in a "
            "normalised Q and chi is unchanged. BEAMFORMING.md section 3.",
        )
        models[f"{stem}_element"] = AntennaIllumination(
            f"{stem}_element",
            base,
            element_only_gain,
            "What full digital maximum ratio transmission reduces to: the array factor's peak is "
            "common to every site and cancels, the TR 38.901 element pattern does not. "
            "BEAMFORMING.md section 3.",
        )
        models[f"{stem}_loaded"] = AntennaIllumination(
            f"{stem}_loaded",
            base,
            TabulatedGain(
                LoadedBeam(array=array, user_population=base, grid_rotation_deg=grid_rotation_deg),
                **LOADED_TABLE,
            ),
            "The beam serves a scheduled user exchangeable with the pedestrian, and the pedestrian "
            "receives whatever the pattern leaves in their direction, averaged over the user "
            "population. BEAMFORMING.md section 5.",
        )
    return models


# --------------------------------------------------------------------------
# The study
# --------------------------------------------------------------------------

SITES = tuple(sorted(STUDY_ORDER))


@dataclass(frozen=True)
class AntennaStudyConfig:
    """Inputs for an antenna model or steering artefact study."""

    sites: list[str]
    all_sites: bool
    kernel: bool
    artefact: bool
    locations: int
    rays: int
    max_bounces: int
    frequency_hz: float
    crop_m: int
    walk_radius_m: float
    seed: int
    grid_rotation_deg: float
    macro_tilt_deg: float
    micro_tilt_deg: float
    tag: str


def _trace_site(site: str, config: AntennaStudyConfig, models: dict[str, Any]) -> dict[str, np.ndarray]:
    """One traced pass over a site, scoring every model on the same rays."""
    from ..exposure.study import GROUND_DATUM_M
    from .geometry import MitsubaGeometry
    from ..materials import classify_faces, load_table
    from ..paths import site_mesh
    from ..transport.tracer import SbrTracer, TraceConfig
    from ..walk import build_walk, ground_datum, stratified_subset

    config_dir = pathlib.Path(__file__).resolve().parents[2] / "config"
    geometry = MitsubaGeometry(site_mesh(site, config.crop_m))
    datum = GROUND_DATUM_M if site == "korenmarkt" else ground_datum(geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(config_dir, config.frequency_hz)
    trace_config = TraceConfig(
        frequency_hz=config.frequency_hz,
        rays=config.rays,
        local_cells=512,
        max_bounces=config.max_bounces,
        seed=config.seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, trace_config)
    walk = build_walk(
        geometry,
        ground_datum_m=datum,
        radius_m=config.walk_radius_m,
        spacing_m=3.0,
        seed=config.seed,
    )
    picks = stratified_subset(walk, config.locations)

    rows: list[dict[str, float]] = []
    for offset, index in enumerate(picks):
        result = tracer.trace(
            walk.points[index],
            models,
            ground_z_m=float(walk.ground_z_m[index]),
            seed=config.seed + 1000 * int(index),
        )
        rows.append(result.scalars())
        if offset % 10 == 0:
            print(f"  [{site}] {offset + 1}/{picks.size} ({result.seconds:.1f} s)", flush=True)
    keys = {key for row in rows for key in row}
    return {key: np.array([row.get(key, np.nan) for row in rows]) for key in sorted(keys)}


#: Apertures swept in the steering measurement, as ``(rows, columns)`` element
#: counts. The canonical 8 by 8 is in the middle of it and the two ends are
#: there because the reduction is a range rather than a number and the range is
#: set by the aperture.
ARTEFACT_APERTURES: tuple[int, ...] = (2, 4, 8, 16, 32)
#: Beams per axis in the codebook sweep, on the canonical panel. All of these
#: are at least as fine as the aperture, for the reason BEAMFORMING.md section
#: 6.4 gives: a grid coarser than the aperture cannot aim at the pedestrian at
#: all, so the free space reference lands in a pattern null and the ratio stops
#: meaning anything.
ARTEFACT_CODEBOOKS: tuple[int, ...] = (8, 16, 32)


def _artefact_site(site: str, config: AntennaStudyConfig) -> dict[str, Any]:
    """The steering measurement at one site. Needs the polylines, so it re-traces.

    This is the generator for BEAMFORMING.md section 6.3 and for the paper's
    geometric steering table. It lives here rather than in a scratch script
    because it produces a number the paper cites, and because the thing it needs
    is precisely the thing no published payload keeps: `rho_rooftop` is a
    histogram of the local arrival direction at the body, and the last
    scattering vertex is marginalised away by the deposit. The recorder is the
    only way to see it, and it is bounded by its own capacity and never reaches
    disk.
    """
    from ..exposure.study import GROUND_DATUM_M
    from .geometry import MitsubaGeometry
    from ..materials import classify_faces, load_table
    from ..paths import site_mesh
    from ..transport.tracer import PathRecorder, SbrTracer, TraceConfig
    from ..walk import build_walk, ground_datum, stratified_subset

    config_dir = pathlib.Path(__file__).resolve().parents[2] / "config"
    geometry = MitsubaGeometry(site_mesh(site, config.crop_m))
    datum = GROUND_DATUM_M if site == "korenmarkt" else ground_datum(geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(config_dir, config.frequency_hz)
    trace_config = TraceConfig(
        frequency_hz=config.frequency_hz,
        rays=config.rays,
        local_cells=512,
        max_bounces=config.max_bounces,
        seed=config.seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, trace_config)
    walk = build_walk(
        geometry,
        ground_datum_m=datum,
        radius_m=config.walk_radius_m,
        spacing_m=3.0,
        seed=config.seed,
    )
    picks = stratified_subset(walk, config.locations)
    populations = {"rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}

    rows: list[dict[str, Any]] = []
    for offset, index in enumerate(picks):
        recorder = PathRecorder(capacity=config.rays)
        result = tracer.trace(
            walk.points[index],
            {"isotropic": ISOTROPIC, **populations},
            ground_z_m=float(walk.ground_z_m[index]),
            seed=config.seed + 1000 * int(index),
            recorder=recorder,
        )
        record = recorder.result()
        row: dict[str, Any] = {"index": int(index), "chi": result.scalars()}
        for name, model in populations.items():
            for count in ARTEFACT_APERTURES:
                row[f"{name}_{count}x{count}"] = steering_artefact(
                    record, walk.points[index], model, array=PlanarArray(count, count)
                )
            for beams in ARTEFACT_CODEBOOKS:
                row[f"{name}_codebook{beams}"] = steering_artefact(
                    record, walk.points[index], model, codebook=(beams, beams)
                )
        rows.append(row)
        if offset % 5 == 0:
            print(f"  [{site}] {offset + 1}/{picks.size} ({result.seconds:.1f} s)", flush=True)

    summary: dict[str, dict[str, float]] = {}
    for column in rows[0]:
        if column in ("index", "chi"):
            continue
        linear = np.array([row[column]["mean_suppression"] for row in rows])
        summary[column] = {
            "median_db": float(10.0 * np.log10(np.median(linear))),
            "p10_db": float(10.0 * np.log10(np.percentile(linear, 10.0))),
            "p90_db": float(10.0 * np.log10(np.percentile(linear, 90.0))),
            "floor_db": float(10.0 * np.log10(np.median([row[column]["direct_measure"] for row in rows]))),
            **{
                key: float(np.median([row[column][key] for row in rows]))
                for key in (
                    "direct_measure",
                    "bounced_suppression_db",
                    "median_offset_deg",
                    "median_last_vertex_offset_m",
                    "median_slant_range_m",
                )
            },
        }
    return {"standpoints": rows, "summary": summary}


def run_antenna_study(config: AntennaStudyConfig) -> None:
    """Run the antenna model or geometric steering study."""
    output = pathlib.Path(__file__).resolve().parents[2] / "outputs" / "antenna"
    output.mkdir(parents=True, exist_ok=True)
    sites = SITES if config.all_sites else tuple(config.sites)

    if config.artefact:
        started = time.perf_counter()
        payload = {"kind": "artefact", "arguments": dict(config.__dict__), "sites": {}}
        path = output / f"{config.tag}_artefact_{config.crop_m}m.json"
        for site in sites:
            print(f"[artefact] {site} at {config.crop_m} m", flush=True)
            payload["sites"][site] = _artefact_site(site, config)
            path.write_text(json.dumps(payload, indent=2, default=float) + "\n")
        payload["seconds"] = time.perf_counter() - started
        path.write_text(json.dumps(payload, indent=2, default=float) + "\n")
        for site, block in payload["sites"].items():
            print(f"\n{site}: median over {len(block['standpoints'])} standpoints of the paired shift in chi")
            for column, value in block["summary"].items():
                print(
                    f"  {column:28s} {value['median_db']:+7.2f} dB"
                    f"  ({value['p10_db']:+.2f}, {value['p90_db']:+.2f})"
                    f"  floor {value['floor_db']:+.2f}  offset {value['median_offset_deg']:5.2f} deg"
                )
        print(f"\n[done] {path} in {payload['seconds']:.0f} s")
        return

    models: dict[str, Any] = build_models(
        grid_rotation_deg=config.grid_rotation_deg,
        macro_tilt_deg=config.macro_tilt_deg,
        micro_tilt_deg=config.micro_tilt_deg,
    )
    payload: dict[str, Any] = {"kind": "models"}
    if config.kernel:
        # The kernel rides along on the same rays. It costs one more deposit per
        # band and it buys every azimuthally symmetric pattern offline, so a
        # downtilt sweep after the fact needs no tracing at all.
        models.update(elevation_probes(KERNEL_EDGES_DEG))
        payload["edges_deg"] = KERNEL_EDGES_DEG.tolist()
    payload["models"] = sorted(models)

    started = time.perf_counter()
    payload["arguments"] = dict(config.__dict__)
    payload["sites"] = {}
    for site in sites:
        print(f"[trace] {site} at {config.crop_m} m, {len(models)} models", flush=True)
        scored = _trace_site(site, config, models)
        payload["sites"][site] = {key: value.tolist() for key, value in scored.items()}
        path = output / f"{config.tag}_{config.crop_m}m.json"
        path.write_text(json.dumps(payload, indent=2, default=float) + "\n")
    payload["seconds"] = time.perf_counter() - started
    path = output / f"{config.tag}_{config.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=2, default=float) + "\n")
    print(f"[done] {path} in {payload['seconds']:.0f} s")
