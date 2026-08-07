"""The scene director: what the model is asked, and what shape the answer must take.

Two layers, deliberately.

`BRIEF` is the standing rubric. It is not a task. It sets the bar, names the failure
modes, and fixes the rules that every decision inherits. It exists for the same
reason MineBench's system prompt exists: to convert "make it impressive" into
properties that can be checked afterwards.

Under it sit narrow typed tasks, each with a JSON schema. This is a deliberate
rejection of the single master prompt. The evidence is in this directory: the
material A/B (`data/materials_ab.json`) found the cheap model collapsing to
"plasterboard" for 29 of 32 buildings while reporting *higher* mean confidence than
the frontier model, 0.76 against 0.60. Confidence cannot be the routing signal, so
decisions have to be small enough to hold golden sets against, and typed enough that
a wrong answer is localisable to one building rather than one city.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

# --------------------------------------------------------------------------
# The standing brief
# --------------------------------------------------------------------------

BRIEF = """\
You are the scene director for a radio digital twin. The scenes you direct are ray
traced at 28 GHz, where the wavelength is 1.07 cm, and they are also rendered for
people to look at. Both audiences matter and they want different things from you.

## The one rule that governs everything

Macro geometry is faithful to reality. Small detail is plausible for reality.

Footprints, heights, terrain, road layout and water are measured. You never move
them, never override them, and never invent them. Below that scale, where no dataset
exists and none is coming, you generate detail that is statistically right for this
particular place. That is the entire job. You are not recovering the truth about a
building, you are producing a defensible instance of what a building like this, on
this street, in this city, is.

Say which you are doing. Every field you emit is marked `seen` if the evidence
shows it, or `inferred` if you are supplying it from knowledge of the place. A
confident `inferred` is fine and expected. A `seen` that you did not actually see is
the one unforgivable error, because it silently promotes a guess into the measured
layer.

## You set parameters. You do not model.

You never emit vertices, coordinates, or positions. Placement comes from data:
footprints from the cadastre, clutter positions from the road graph. You choose
classes and turn numeric knobs, and a deterministic generator does the geometry.

This is not a limitation imposed on you, it is where you are actually strong. The
thing you know that no dataset knows is that this is a Flemish guild house from the
1600s and therefore has a stepped gable, tall narrow sash windows on a vertical
rhythm, and a stone plinth. Spend yourself on that.

## What good looks like, and the four ways to fail

Judges will rotate the camera. A scene is scored from angles you did not compose
for. The four failure modes, all of which have shown up in this project already:

1. Flat decoration. A texture painted on a box face, standing in for structure that
   should be geometry. If the only thing distinguishing two buildings is their
   albedo, you have failed here.
2. Visible primitives. If a viewer can point at your building and name the box, the
   grammar was too coarse. Extruded footprints with flat tops are the canonical
   case.
3. Static isolation. Correct buildings on an empty street. Real streets have
   vehicles where vehicles are allowed, terraces outside cafes, bins, bikes, wear.
4. Uniform detail. Equal resolution everywhere. Detail belongs on silhouette edges,
   on openings, at the ground floor where the eye goes, and on whatever the beam
   actually illuminates. A building 200 m from the study corridor does not deserve
   the same budget as one 3 m from it.

## The physics, because it constrains what detail is worth asking for

Three regimes at 28 GHz, and putting detail in the wrong one is worse than omitting
it:

- Above roughly 10 cm: explicit geometry. Window reveals, sills, balconies,
  pilasters, parapets, vehicle bodies. These are facets and wedges, a ray tracer
  handles them correctly, and they produce the off-specular scattering that decides
  street-level field. Ask for these.
- 1 cm to 10 cm: not geometry. Brick relief, mortar joints, ornament. Meshing these
  is wrong physics, not merely expensive, because geometrical optics assumes surfaces
  locally smooth over many wavelengths. A centimetre-bumpy mesh produces specular
  garbage. These become a roughness number and a scattering coefficient.
- Below 1 cm: pure material. Permittivity and conductivity.

So when you describe a facade, describe the openings and the ledges, and describe
the brick as a material with a roughness, never as geometry.

## Calibrate to the place, not to Europe in general

The most damaging errors in this project have been generic-plausible rather than
wrong-per-se. A rule that parked cars along every street filled a medieval
pedestrian square with a thousand vehicles, all of them individually reasonable. The
data said `vehicle=private` on 128 of 129 streets and the rule did not look.

Before you set a number, ask what this specific city, street and building type
actually does. If the evidence contradicts your prior, the evidence wins. If the
evidence is absent, say `inferred` and use the prior.

## Think before you answer

Identify what you are looking at first: period, building type, function, condition.
The parameters follow from that identification and are much harder to get right
without it. An answer that starts with numbers is usually an answer that pattern
matched on the first plausible template.
"""

# --------------------------------------------------------------------------
# Shared schema pieces
# --------------------------------------------------------------------------

_EVIDENCE = {
    "type": "string",
    "enum": ["seen", "inferred"],
    "description": "seen: the reference image shows this. inferred: supplied from "
                   "knowledge of the place. Never mark inferred data as seen.",
}

ROOF_FORMS = [
    "flat", "gabled", "hipped", "half_hipped", "mansard", "pyramidal",
    "stepped_gable", "bell_gable", "spout_gable", "shed", "dome", "sawtooth",
]

GROUND_FLOOR = ["shopfront", "cafe_glazing", "residential_door", "arcade",
                "blank", "garage", "institutional_portal"]

# Sionna's ITU-R P.2040 vocabulary, plus the two we bind ourselves. Closed on
# purpose: the director picks, it does not name new materials.
MATERIALS = ["brick", "concrete", "plasterboard", "marble", "wood", "glass",
             "metal", "chipboard", "plywood", "very_dry_ground",
             "medium_dry_ground", "wet_ground", "floorboard", "ceiling_board"]


# --------------------------------------------------------------------------
# Task 1: facade grammar
# --------------------------------------------------------------------------

FACADE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["identification", "storeys", "bays", "window", "ground_floor",
                 "roof", "ledges", "material", "confidence"],
    "properties": {
        "identification": {
            "type": "string",
            "description": "One sentence: period, building type, function. Write "
                           "this before deciding any number below.",
        },
        "storeys": {
            "type": "object",
            "additionalProperties": False,
            "required": ["count", "ground_height_m", "upper_height_m", "evidence"],
            "properties": {
                "count": {"type": "integer", "minimum": 1, "maximum": 40,
                          "description": "Storeys above ground, excluding attic."},
                "ground_height_m": {"type": "number", "minimum": 2.2,
                                    "maximum": 8.0},
                "upper_height_m": {"type": "number", "minimum": 2.2,
                                   "maximum": 6.0},
                "evidence": _EVIDENCE,
            },
        },
        "bays": {
            "type": "object",
            "additionalProperties": False,
            "required": ["count", "evidence"],
            "properties": {
                "count": {"type": "integer", "minimum": 1, "maximum": 30,
                          "description": "Vertical window columns across the "
                                         "street facade."},
                "evidence": _EVIDENCE,
            },
        },
        "window": {
            "type": "object",
            "additionalProperties": False,
            "required": ["width_m", "height_m", "reveal_class", "glazing_bars",
                         "evidence"],
            "properties": {
                "width_m": {"type": "number", "minimum": 0.4, "maximum": 4.0},
                "height_m": {"type": "number", "minimum": 0.5, "maximum": 5.0},
                "reveal_class": {
                    "type": "string",
                    "enum": ["flush", "shallow", "deep"],
                    "description": "A class, not a measurement. flush ~0.03 m, "
                                   "shallow ~0.12 m, deep ~0.25 m. Reference "
                                   "imagery cannot resolve this better than a "
                                   "class, so do not pretend otherwise.",
                },
                "glazing_bars": {"type": "boolean"},
                "evidence": _EVIDENCE,
            },
        },
        "ground_floor": {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "evidence"],
            "properties": {
                "kind": {"type": "string", "enum": GROUND_FLOOR},
                "evidence": _EVIDENCE,
            },
        },
        "roof": {
            "type": "object",
            "additionalProperties": False,
            "required": ["form", "ridge_parallel_to_street", "evidence"],
            "properties": {
                "form": {"type": "string", "enum": ROOF_FORMS},
                "ridge_parallel_to_street": {"type": "boolean"},
                "evidence": _EVIDENCE,
            },
        },
        "ledges": {
            "type": "object",
            "additionalProperties": False,
            "required": ["sills", "cornice", "string_courses", "balconies",
                         "evidence"],
            "description": "Horizontal relief above 10 cm, which is the regime "
                           "that becomes explicit geometry.",
            "properties": {
                "sills": {"type": "boolean"},
                "cornice": {"type": "boolean"},
                "string_courses": {"type": "boolean"},
                "balconies": {"type": "boolean"},
                "evidence": _EVIDENCE,
            },
        },
        "material": {
            "type": "object",
            "additionalProperties": False,
            "required": ["wall", "roughness_mm", "trim", "evidence"],
            "properties": {
                "wall": {"type": "string", "enum": MATERIALS},
                "roughness_mm": {
                    "type": "number", "minimum": 0.0, "maximum": 30.0,
                    "description": "RMS surface height. This carries the 1-10 cm "
                                   "regime. Smooth render ~0.5, brick with "
                                   "recessed joints ~3-8, rough stone ~10.",
                },
                "trim": {"type": "string", "enum": MATERIALS},
                "evidence": _EVIDENCE,
            },
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "notes": {"type": "string"},
    },
}

FACADE_TASK = """\
Read this facade and return its grammar.

{evidence}

Every image is paired with an annotated copy in which the target building is
outlined in magenta. The outline is drawn on afterwards and is not part of the
scene. Read detail from the clean copy and use the outlined one only to be certain
which building you are being asked about. Where an outline has a dashed top edge,
the building continues above the top of that frame.

What is known from data, do not contradict it:
{facts}

Identify the building first, in one sentence, then set the parameters. Mark a field
`seen` only if an image actually shows it at a resolution that supports the answer.
"""

# How much each evidence source can actually carry, stated to the director rather
# than left implied. The two sources fail in opposite directions and saying so is
# what stops a roof form being read off a photograph that cannot see the roof.
EVIDENCE_NOTE = {
    "tiles_street": "Image set A is a rendered eye-level view of Inhouse "
                    "photorealistic 3D tiles. It carries true colour, massing and "
                    "storey rhythm, and dissolves below roughly 25 cm per texel, "
                    "so it cannot resolve mullions, reveal depth or brick bond.",
    "tiles_oblique": "Image set A is a rendered aerial three-quarter view of "
                     "Inhouse photorealistic 3D tiles, used because this building "
                     "has no street a camera can stand in. It is the only view of "
                     "the roof, and it is weak evidence for anything on the wall.",
    "photo": "Image set B is a real street photograph. It is the strongest "
             "evidence available for wall material, window size and subdivision, "
             "sills and string courses, and what the ground floor is. It is weak "
             "evidence for roof form, which is foreshortened or hidden from the "
             "pavement, and its wide lens curves straight lines near the frame "
             "edge.",
    "photo_pano": "One image in set B is a 360 panorama, so the facade is "
                  "stretched. Trust its material and colour, distrust its "
                  "proportions.",
}


# --------------------------------------------------------------------------
# Task 2: street character
# --------------------------------------------------------------------------

STREET_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["character", "clutter", "confidence"],
    "properties": {
        "character": {
            "type": "string",
            "enum": ["pedestrian_tourist", "pedestrian_civic", "residential_quiet",
                     "shopping", "quayside", "through_traffic", "service_yard"],
        },
        "clutter": {
            "type": "object",
            "additionalProperties": False,
            "required": ["terrace_density", "bike_density", "bollard_run",
                         "tree_pitch_m", "evidence"],
            "properties": {
                "terrace_density": {"type": "number", "minimum": 0.0,
                                    "maximum": 1.0,
                                    "description": "Fraction of hospitality "
                                                   "frontage with an outdoor "
                                                   "terrace."},
                "bike_density": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "bollard_run": {"type": "boolean",
                                "description": "Is the edge lined with bollards."},
                "tree_pitch_m": {"type": "number", "minimum": 0.0, "maximum": 40.0,
                                 "description": "0 means no street trees."},
                "evidence": _EVIDENCE,
            },
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "notes": {"type": "string"},
    },
}

STREET_TASK = """\
Characterise this street so its clutter can be generated at the right density.

Do not place anything. You are setting densities and pitches, and the generator will
place against the real road graph.

What the data says, which you may not contradict:
{facts}

Note that access tags are authoritative. A street closed to general traffic does not
get parked cars no matter what it looks like.
"""


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

@dataclass
class Task:
    """One director call, ready to send."""

    name: str
    system: str
    prompt: str
    schema: dict
    images: list[str]

    def as_dict(self) -> dict:
        return {"name": self.name, "system": self.system, "prompt": self.prompt,
                "schema": self.schema, "images": self.images}


def facade_task(*, osm_id: int, facts: dict, images: list[str],
                evidence: str) -> Task:
    return Task(
        name=f"facade:{osm_id}",
        system=BRIEF,
        prompt=FACADE_TASK.format(evidence=evidence,
                                  facts=json.dumps(facts, indent=2)),
        schema=FACADE_SCHEMA,
        images=images,
    )


def street_task(*, way_id: int, facts: dict, images: list[str]) -> Task:
    return Task(
        name=f"street:{way_id}",
        system=BRIEF,
        prompt=STREET_TASK.format(facts=json.dumps(facts, indent=2)),
        schema=STREET_SCHEMA,
        images=images,
    )


# Reveal classes to metres, applied by the generator not the director. Keeping the
# mapping here rather than in the schema is the point: the director picks a class it
# can actually justify, and the number is a project constant that can be swept.
REVEAL_M = {"flush": 0.03, "shallow": 0.12, "deep": 0.25}
