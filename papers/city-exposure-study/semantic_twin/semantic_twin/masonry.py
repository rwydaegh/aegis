"""Brickwork as a specified periodic structure rather than a random height field.

Everything a scattering calculation needs about a masonry facade is fixed by
construction documents. The unit format is a manufacturing standard, the joint
width and profile are workmanship specifications, the bond is a named pattern,
and the unit-to-unit scatter is a declared tolerance class. This module turns
those into the two objects a solver wants: a lattice, and a permittivity map on
the unit cell.

Sign convention for permittivity follows :mod:`semantic_twin.rcwa`, that is
``exp(-i omega t)`` and therefore ``eps = eps' + i eps''`` with a positive
imaginary part for a lossy material. :mod:`semantic_twin.materials` uses the
opposite engineering convention, so :func:`permittivity_from_evaluation`
performs the conjugation explicitly rather than leaving it to a caller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .floquet import Lattice, centred_rectangular_lattice, rectangular_lattice

VACUUM_PERMITTIVITY = 8.8541878128e-12


@dataclass(frozen=True)
class BrickFormat:
    """Nominal work size of a masonry unit, in metres.

    ``length`` runs along the wall, ``height`` up it, ``width`` into it. These
    are work sizes, meaning the manufacturer's declared dimensions before the
    tolerance class is applied.
    """

    name: str
    length_m: float
    height_m: float
    width_m: float
    source: str = ""

    def __post_init__(self) -> None:
        if min(self.length_m, self.height_m, self.width_m) <= 0.0:
            raise ValueError("brick dimensions must be positive")


@dataclass(frozen=True)
class JointGeometry:
    """Mortar joint width and profile.

    ``recess_m`` is positive when the mortar surface sits behind the brick face,
    which is the normal case, zero for a flush joint, and negative for a joint
    struck proud of the face.
    """

    bed_m: float
    perp_m: float
    recess_m: float
    profile: str = "unspecified"
    source: str = ""

    def __post_init__(self) -> None:
        if self.bed_m <= 0.0 or self.perp_m <= 0.0:
            raise ValueError("joint widths must be positive")


@dataclass(frozen=True)
class BondPattern:
    """A named bond, described by where its perpend joints fall.

    ``courses`` holds one entry per course of the vertical repeat. Each entry is
    the tuple of perpend joint centres in that course, given as fractions of the
    horizontal repeat length. ``period_stretchers`` is that repeat length
    measured in stretcher pitches, which is one for every bond built from whole
    stretchers and one and a half for Flemish bond because its repeat is a
    stretcher plus a header.
    """

    name: str
    period_stretchers: float
    courses: tuple[tuple[float, ...], ...]
    source: str = ""

    @property
    def period_courses(self) -> int:
        return len(self.courses)


STACK_BOND = BondPattern(
    name="stack",
    period_stretchers=1.0,
    courses=((0.0,),),
    source="Every perpend aligned. Rare in load bearing work, common in modern rainscreen brick slips.",
)

RUNNING_BOND = BondPattern(
    name="running",
    period_stretchers=1.0,
    courses=((0.0,), (0.5,)),
    source="Stretcher bond, halfsteensverband. Each course offset by half a unit.",
)

ENGLISH_BOND = BondPattern(
    name="english",
    period_stretchers=1.0,
    courses=((0.0,), (0.25, 0.75)),
    source="Alternating stretcher and header courses. Header pitch is half the stretcher pitch.",
)

FLEMISH_BOND = BondPattern(
    name="flemish",
    period_stretchers=1.5,
    courses=((0.0, 2.0 / 3.0), (0.5, 1.0 / 6.0)),
    source="Header and stretcher alternate within every course, so the repeat is 1.5 stretcher pitches.",
)

BONDS = {bond.name: bond for bond in (STACK_BOND, RUNNING_BOND, ENGLISH_BOND, FLEMISH_BOND)}


RANGE_CONSTANT_N10 = 3.078
"""Expected range of ten standard normal draws, the control-chart constant ``d_2``."""


@dataclass(frozen=True)
class ToleranceClass:
    """A BS EN 771-1 dimensional tolerance class.

    The classes are square-root-of-nominal formulas, not fixed triples: the
    familiar 6, 4, 3 mm of T1 and 9, 6, 5 mm of R1 are those formulas evaluated
    for the 215 by 102.5 by 65 mm unit and do not transfer to another format.
    A 50 mm high Waalformaat unit carries an R1 height range of 4 mm, not 5.

    Two families exist and they mean different things. A ``mean`` class bounds
    the deviation of the sample mean from the declared work size, which is a
    batch offset and scatters nothing. A ``range`` class bounds the spread of a
    dimension within one sample of ten units, which is the unit-to-unit scatter
    a scattering calculation needs.
    """

    name: str
    kind: str
    coefficient: float
    floor_mm: float
    sample_size: int = 10
    source: str = ""

    def limit_mm(self, nominal_mm: float) -> float:
        """The declared limit for one nominal dimension, in millimetres."""
        if nominal_mm <= 0.0:
            raise ValueError("nominal dimension must be positive")
        return max(self.coefficient * math.sqrt(nominal_mm), self.floor_mm)

    def standard_deviation_m(self, nominal_mm: float) -> float:
        """Read a declared range limit as a Gaussian standard deviation.

        For a sample of ``n`` normal draws the expected range is ``d_2 sigma``
        with ``d_2 = 3.078`` at ``n = 10``. Reading a declared *limit* as an
        *expected* range is an inversion performed here and is not a published
        equivalence, so the result estimates the scatter a compliant batch may
        carry rather than measuring the scatter of any batch.
        """
        if self.kind != "range":
            raise ValueError(f"{self.name} bounds a mean deviation, which carries no unit to unit scatter")
        return self.limit_mm(nominal_mm) / RANGE_CONSTANT_N10 / 1000.0


_EN771_SOURCE = (
    "BS EN 771-1 dimensional tolerance and range classes, formulas as restated in "
    "KNB infoblad 14 and tabulated in the PAS 70 guide, both read for this study."
)

TOLERANCE_CLASSES = {
    "T1": ToleranceClass(name="T1", kind="mean", coefficient=0.40, floor_mm=3.0, source=_EN771_SOURCE),
    "T2": ToleranceClass(name="T2", kind="mean", coefficient=0.25, floor_mm=2.0, source=_EN771_SOURCE),
    "R1": ToleranceClass(name="R1", kind="range", coefficient=0.60, floor_mm=0.0, source=_EN771_SOURCE),
    "R2": ToleranceClass(name="R2", kind="range", coefficient=0.30, floor_mm=0.0, source=_EN771_SOURCE),
}

WALL_FLATNESS_TOLERANCE_MM = 8.0
"""Permitted departure from plane under a 2 m straightedge, Buildwise TV 297 annex B.

Recorded because it bounds the wall-scale wander that unit-to-unit scatter sits
on top of, and because it is often misquoted as the 3 mm plastering tolerance.
A 2 m wander is 187 wavelengths at 28 GHz and is a geometry error rather than a
roughness, so it belongs to the tracer's surface model and not to this one.
"""


def permittivity_from_evaluation(
    relative_permittivity: float, conductivity_s_per_m: float, frequency_hz: float
) -> complex:
    """Complex permittivity in the ``exp(-i omega t)`` convention used by the solvers."""
    omega = 2.0 * math.pi * frequency_hz
    return complex(relative_permittivity, conductivity_s_per_m / (omega * VACUUM_PERMITTIVITY))


@dataclass(frozen=True)
class MasonryWall:
    """A wall, from which a lattice and a unit cell permittivity map follow."""

    brick: BrickFormat
    joint: JointGeometry
    bond: BondPattern
    brick_permittivity: complex = 3.91 + 0.0j
    mortar_permittivity: complex = 3.91 + 0.0j
    name: str = "masonry"
    notes: dict[str, str] = field(default_factory=dict)

    @property
    def course_pitch_m(self) -> float:
        """Vertical repeat, the unit height plus one bed joint."""
        return self.brick.height_m + self.joint.bed_m

    @property
    def stretcher_pitch_m(self) -> float:
        """Horizontal repeat of a stretcher course, the unit length plus one perpend."""
        return self.brick.length_m + self.joint.perp_m

    @property
    def cell_x_m(self) -> float:
        return self.bond.period_stretchers * self.stretcher_pitch_m

    @property
    def cell_y_m(self) -> float:
        return self.bond.period_courses * self.course_pitch_m

    @property
    def joint_area_fraction(self) -> float:
        """Fraction of the elevation that is mortar rather than brick face."""
        brick_area = 0.0
        cell_area = self.cell_x_m * self.cell_y_m
        for course in self.bond.courses:
            positions = sorted(course)
            for index, start in enumerate(positions):
                end = positions[(index + 1) % len(positions)] + (1.0 if index == len(positions) - 1 else 0.0)
                unit_length = (end - start) * self.cell_x_m - self.joint.perp_m
                brick_area += max(0.0, unit_length) * (self.course_pitch_m - self.joint.bed_m)
        return float(1.0 - brick_area / cell_area)

    def lattice(self, *, primitive: bool = False) -> Lattice:
        """The Bravais lattice of the elevation.

        The default is the rectangular computational cell that the solvers use,
        which for a running bond is twice the primitive cell and therefore
        labels the half-integer orders as whole ones. ``primitive=True`` returns
        the centred rectangular primitive cell instead, which is the right
        object for counting distinct orders.
        """
        if primitive and self.bond.name == "running":
            return centred_rectangular_lattice(self.stretcher_pitch_m, self.course_pitch_m, "running_primitive")
        return rectangular_lattice(self.cell_x_m, self.cell_y_m, f"{self.bond.name}_cell")

    def unit_rectangles(self) -> list[tuple[float, float, float, float]]:
        """Every exposed brick face in the cell as ``(x0, y0, width, height)`` in metres."""
        rectangles: list[tuple[float, float, float, float]] = []
        face_height = self.course_pitch_m - self.joint.bed_m
        half_perp = 0.5 * self.joint.perp_m
        for course_index, course in enumerate(self.bond.courses):
            y0 = course_index * self.course_pitch_m + 0.5 * self.joint.bed_m
            positions = sorted(course)
            for index, fraction in enumerate(positions):
                next_fraction = positions[(index + 1) % len(positions)]
                if index == len(positions) - 1:
                    next_fraction += 1.0
                x0 = fraction * self.cell_x_m + half_perp
                width = (next_fraction - fraction) * self.cell_x_m - self.joint.perp_m
                if width > 0.0:
                    rectangles.append((x0, y0, width, face_height))
        return rectangles

    def mortar_mask(self, samples_x: int, samples_y: int) -> np.ndarray:
        """Boolean cell map, ``True`` where the elevation shows mortar.

        Indexed ``[y, x]`` to match the convention of
        :func:`semantic_twin.rcwa.convolution_matrix`.
        """
        if samples_x < 8 or samples_y < 8:
            raise ValueError("the cell needs at least eight samples in each direction")
        x = (np.arange(samples_x) + 0.5) / samples_x * self.cell_x_m
        y = (np.arange(samples_y) + 0.5) / samples_y * self.cell_y_m
        mask = np.zeros((samples_y, samples_x), dtype=bool)
        half_bed = 0.5 * self.joint.bed_m
        half_perp = 0.5 * self.joint.perp_m
        for course_index in range(self.bond.period_courses):
            base = course_index * self.course_pitch_m
            bed_centre = base
            distance = np.abs((y - bed_centre + 0.5 * self.cell_y_m) % self.cell_y_m - 0.5 * self.cell_y_m)
            in_bed = distance < half_bed
            mask[in_bed, :] = True
            in_course = (y >= base + half_bed) & (y < base + self.course_pitch_m - half_bed)
            for fraction in self.bond.courses[course_index]:
                centre = fraction * self.cell_x_m
                offset = np.abs((x - centre + 0.5 * self.cell_x_m) % self.cell_x_m - 0.5 * self.cell_x_m)
                mask[np.ix_(in_course, offset < half_perp)] = True
        return mask

    def height_map(self, samples_x: int, samples_y: int) -> np.ndarray:
        """Surface relief of the elevation in metres, brick face at zero."""
        mask = self.mortar_mask(samples_x, samples_y)
        return np.where(mask, -self.joint.recess_m, 0.0)

    def reflection_map(self, samples_x: int, samples_y: int, *, brick: complex, mortar: complex) -> np.ndarray:
        """Per-facet reflection coefficient over the cell, for Kirchhoff use."""
        mask = self.mortar_mask(samples_x, samples_y)
        return np.where(mask, mortar, brick)

    def rcwa_layers(self, samples_x: int, samples_y: int) -> list:
        """Layer stack for :func:`semantic_twin.rcwa.solve`.

        A recessed joint gives two strata: a relief layer of the recess depth
        that is brick where the units are and air over the joints, then a
        semi-infinite substrate that is brick where the units are and mortar
        over the joints. A flush joint collapses to the substrate alone, so the
        only remaining mechanism is the dielectric contrast, which is exactly
        the ablation worth having.
        """
        from .rcwa import Layer

        mask = self.mortar_mask(samples_x, samples_y)
        if self.mortar_permittivity == self.brick_permittivity:
            # A uniform layer is solved analytically, so saying so rather than
            # handing over a constant map is the difference between one
            # eigenvalue decomposition and two.
            substrate: complex | np.ndarray = self.brick_permittivity
        else:
            substrate = np.where(mask, self.mortar_permittivity, self.brick_permittivity)
        layers = [Layer(1.0 + 0.0j, name="air")]
        recess = self.joint.recess_m
        if abs(recess) > 1e-9:
            if recess > 0.0:
                relief = np.where(mask, 1.0 + 0.0j, self.brick_permittivity)
            else:
                relief = np.where(mask, self.mortar_permittivity, 1.0 + 0.0j)
            layers.append(Layer(relief, thickness_m=abs(recess), name="relief"))
        layers.append(Layer(substrate, name="substrate"))
        return layers


BRICK_FORMATS = {
    "standard_metric": BrickFormat(
        name="standard_metric",
        length_m=0.215,
        height_m=0.065,
        width_m=0.1025,
        source="UK standard metric brick work size 215 x 102.5 x 65 mm. With 10 mm joints: 225 mm stretcher pitch, 75 mm course pitch.",
    ),
    "waalformaat": BrickFormat(
        name="waalformaat",
        length_m=0.210,
        height_m=0.050,
        width_m=0.100,
        source=(
            "Dutch and Belgian Waalformaat work size 210 x 100 x 50 mm. With 10 mm joints: 220 mm stretcher "
            "pitch, 60 mm course pitch, 15 courses to the metre. Wienerberger NL states the alternative "
            "12.5 mm joint convention giving 62.5 mm and 16 courses to the metre, which is also what a "
            "measured 1920s Dutch facade returns."
        ),
    ),
    "waaldikformaat": BrickFormat(
        name="waaldikformaat",
        length_m=0.210,
        height_m=0.065,
        width_m=0.100,
        source="Waaldikformaat, 210 x 100 x 65 mm. With 10 mm joints: 220 mm stretcher pitch, 75 mm course pitch.",
    ),
    "module_m50": BrickFormat(
        name="module_m50",
        length_m=0.188,
        height_m=0.048,
        width_m=0.088,
        source=(
            "Belgian module M50, Wienerberger Belgium work size 188 x 88 x 48 mm. The name is the height "
            "class, not the pitch: with the Belgian traditional 12 mm joint the coordinating pitches are "
            "exactly 200 and 60 mm."
        ),
    ),
    "module_m65": BrickFormat(
        name="module_m65",
        length_m=0.188,
        height_m=0.063,
        width_m=0.088,
        source=(
            "Belgian module M65, work size 188 x 88 x 63 mm, corroborated by Buildwise referring to "
            "'een metselbaksteen van 63 mm hoog (module 65)'. With 12 mm joints the pitches are 200 and 75 mm, "
            "so M65 shares the British 75 mm vertical grating on a different 200 mm horizontal one."
        ),
    ),
}


STANDARD_JOINT = JointGeometry(
    bed_m=0.010,
    perp_m=0.010,
    recess_m=0.000,
    profile="flush",
    source="Nominal 10 mm bed and perpend, flush struck. Buildwise TV 297 gives 10 to 12 mm for pointed traditional masonry, 8 mm minimum.",
)

BELGIAN_JOINT = JointGeometry(
    bed_m=0.012,
    perp_m=0.012,
    recess_m=0.000,
    profile="flush",
    source="Belgian traditional 12 mm joint, Buildwise TV 297 (April 2025) and the Nelissen format fiche.",
)

RECESSED_JOINT = JointGeometry(
    bed_m=0.010,
    perp_m=0.010,
    recess_m=0.005,
    profile="recessed",
    source=(
        "Nominal 10 mm joints raked back 5 mm. KNB infoblad 28 calls 5 mm the routine recess, tells the "
        "bricklayer to rake to a square cross section so depth equals width, and caps the absolute maximum "
        "at 15 mm on a 100 mm unit. Buildwise TV 297 names the verdiepte voeg but states no depth anywhere "
        "in 32 pages, so Belgium has no number of its own."
    ),
)

DEEP_RECESSED_JOINT = JointGeometry(
    bed_m=0.010,
    perp_m=0.010,
    recess_m=0.010,
    profile="recessed_deep",
    source="A 10 mm rake, the square cross section KNB infoblad 28 describes for a 10 mm joint, short of its 15 mm cap.",
)

BUCKET_HANDLE_JOINT = JointGeometry(
    bed_m=0.010,
    perp_m=0.010,
    recess_m=0.002,
    profile="bucket_handle",
    source="Nominal 10 mm joints, tooled concave. Mean recess taken as 2 mm, which is this study's reading of a tooled profile and not a published figure.",
)

PROUD_JOINT = JointGeometry(
    bed_m=0.010,
    perp_m=0.010,
    recess_m=-0.004,
    profile="tuckpointed",
    source="Tuckpointed or baguette joint, which Buildwise TV 297 classes as uitspringend, standing proud of the brick face. Height taken as 4 mm, unsourced.",
)

JOINT_PROFILES = {
    joint.profile: joint
    for joint in (STANDARD_JOINT, RECESSED_JOINT, DEEP_RECESSED_JOINT, BUCKET_HANDLE_JOINT, PROUD_JOINT)
}
