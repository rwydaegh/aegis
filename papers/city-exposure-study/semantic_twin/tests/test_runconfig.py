"""Tests for the run config and the provenance record it writes.

The serialisation tests here are not "a setter returns what was set". They check
the two things a config has to survive: a round trip through JSON, which is how it
gets into a manifest and back out again, and a rejection when the JSON says
something this code cannot honour. The second one is the important half. A
manifest written by a later version carries a parameter this code ignores, and
silently ignoring it is how a manifest ends up describing a run that never
happened.

Two more kinds are here and they are the ones with teeth.

The digests of four shipped configurations are pinned to literal hex strings.
That is the golden lock for the run identity. Every output file in the study is
named after a digest, so a new numerical choice usually renames every one of
them. The explicit name for a sole historical default can retain its canonical
form, but the pin makes either policy visible.

The defaults are read out of the drivers with :mod:`ast` rather than compared to
themselves. The test these replaced read the dataclass back to the dataclass and
never opened a driver, so it would have passed with every default wrong.
``run_next_event.py`` checks the facade-tip law, next-event estimator and route
walk. ``run_exposure.py`` checks the shared crop, sampling and material defaults.
"""

from __future__ import annotations

import ast
import json
from typing import Any

import pytest

from semantic_twin import paths
from semantic_twin.runconfig import (
    ESTIMATORS,
    LAWS,
    MATERIALS,
    TRANSPORT_KERNELS,
    WALK_PATHS,
    WALKS,
    NextEventConfig,
    Provenance,
    RunConfig,
)


def escape() -> RunConfig:
    """The escape run that wrote the eleven city headline."""
    return RunConfig(
        site="korenmarkt",
        crop_m=250,
        law="band",
        models=("isotropic", "rooftop", "street_small_cell"),
        estimator="escape",
        walk="grid",
        walk_spacing_m=3.0,
        locations=80,
        rays=200_000,
        materials="geometric",
        tag="city250_L3_korenmarkt",
    )


def next_event() -> RunConfig:
    return RunConfig(
        site="brussels_grandplace",
        crop_m=250,
        law="roofline",
        models=("rooftop",),
        estimator="next_event",
        next_event=NextEventConfig(builders=128, held_out=16, drop_clutter=True),
        walk="route",
        walk_path="closest",
    )


def package_constant(name: str) -> Any:
    """A module level constant, found wherever in the package it is defined.

    Searched rather than pointed at. The subpackages are moving underneath this
    test and a hardcoded module path would fail for the wrong reason. Two
    definitions of one constant is itself a finding, since that is how a study
    ends up with two versions of a number, so it raises rather than picking one.
    """
    found: dict[str, Any] = {}
    for path in sorted((paths.root() / "semantic_twin").rglob("*.py")):
        for node in ast.parse(path.read_text()).body:
            targets = node.targets if isinstance(node, ast.Assign) else []
            if not any(isinstance(target, ast.Name) and target.id == name for target in targets):
                continue
            try:
                found[str(path)] = ast.literal_eval(node.value)
            except ValueError:
                continue
    if len(found) != 1:
        raise AssertionError(f"{name} is defined in {len(found)} places: {', '.join(sorted(found))}")
    return next(iter(found.values()))


def argparse_defaults(relative: str) -> dict[str, Any]:
    """Every ``--flag`` default a driver ships, read without importing it.

    Importing a driver pulls in Mitsuba, and a config test should not need a ray
    tracer to run. A default written as a name rather than a literal comes back as
    that name, so the two that are shared constants get resolved against the
    module that defines them instead of being retyped here and going stale.
    """
    found: dict[str, Any] = {}
    for node in ast.walk(ast.parse((paths.root() / relative).read_text())):
        if not (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument"):
            continue
        flags = [arg.value for arg in node.args if isinstance(arg, ast.Constant)]
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        if not flags or not str(flags[0]).startswith("--"):
            continue
        name = str(flags[0]).removeprefix("--").replace("-", "_")
        if "default" in keywords:
            value = keywords["default"]
            found[name] = value.id if isinstance(value, ast.Name) else ast.literal_eval(value)
        elif isinstance(keywords.get("action"), ast.Constant) and keywords["action"].value == "store_true":
            found[name] = False
    return found


# ------------------------------------------------------------- serialisation


@pytest.mark.parametrize("config", [escape(), next_event()], ids=["escape", "next_event"])
def test_a_config_survives_a_round_trip_through_json(config):
    assert RunConfig.from_json(config.to_json()) == config


@pytest.mark.parametrize("config", [escape(), next_event()], ids=["escape", "next_event"])
def test_the_serialised_form_is_plain_json_with_no_python_left_in_it(config):
    """It has to sit inside a manifest that anything can read."""
    document = json.loads(config.to_json())
    assert document["models"] == list(config.models)
    assert isinstance(document["next_event"], (dict, type(None)))
    assert json.dumps(document)


def test_the_nested_source_set_comes_back_as_an_object_and_not_a_dict():
    restored = RunConfig.from_json(next_event().to_json())
    assert isinstance(restored.next_event, NextEventConfig)
    assert restored.next_event.drop_clutter is True


def test_a_field_this_code_does_not_have_is_refused_rather_than_dropped():
    document = json.loads(escape().to_json())
    document["diffraction_order"] = 2
    with pytest.raises(ValueError, match="diffraction_order"):
        RunConfig.from_dict(document)


def test_two_configs_that_differ_anywhere_get_different_digests():
    base = escape()
    assert base.digest() == RunConfig.from_json(base.to_json()).digest()
    assert base.digest() != base.replace(seed=8).digest()
    assert base.digest() != base.replace(law="roofline").digest()
    assert base.digest() != base.replace(models=("isotropic", "rooftop")).digest()
    assert base.digest() != base.replace(transport_kernel="drjit").digest()


def test_the_established_numpy_kernel_keeps_the_published_digest():
    """Adding the explicit default does not rename the runs already on disk."""
    document = escape().identity()
    assert escape().transport_kernel == "numpy"
    assert "transport_kernel" not in document
    assert "transport_kernel" in escape().as_dict()


@pytest.mark.parametrize("field", ["ray_epsilon_m", "roulette_floor", "batch"])
def test_the_three_parameters_that_look_like_execution_details_are_in_the_identity(field):
    """Each one changes a number, so each one changes the digest.

    ``ray_epsilon_m`` moves ``chi_bounce`` from 1.4541e-4 to 1.4590e-4 across
    0.1 mm to 1 cm, measured in ``docs/BUGS.md``. ``roulette_floor`` chooses which
    rays are killed the moment roulette fires, and older manifests record the
    ``roulette_start`` of 3 that fires it. ``batch`` decides where the tracer's one
    random stream is cut, and a batch draws several times over its own rays, so
    the same rays in two batches are not the same rays.
    """
    base = escape()
    changed = {"ray_epsilon_m": 1.0e-2, "roulette_floor": 0.10, "batch": 100_000}[field]
    assert getattr(base, field) != changed
    assert base.digest() != base.replace(**{field: changed}).digest()


def test_a_run_written_under_two_tags_is_one_run_with_two_names():
    """What ``--tag-suffix`` is for, and what the digest used to make impossible.

    ``run_exposure.py:1503`` ships the flag so a rerun lands beside a published
    run rather than on top of it. The tag was inside the hash, so that rerun came
    back with a fresh identity and nothing could tell it was the same run. The
    files still separate, because the tag leads the stem.
    """
    base = escape()
    beside = base.replace(tag=f"{base.tag}_rerun")
    assert beside.digest() == base.digest()
    assert beside.stem() != base.stem()
    assert "tag" not in base.identity()


def test_the_roulette_start_a_manifest_spells_out_and_the_one_left_open_are_one_run():
    """Old manifests write the 4 that this code writes as None, at a budget of 3.

    The tracer fires roulette on ``depth + 1 >= roulette_start`` and its loop
    breaks at ``depth == max_bounces`` first, so at a three bounce budget every
    value above 3 leaves that branch unentered and draws no random number. Those
    runs are bit identical, so they get one digest.
    """
    default = RunConfig(site="korenmarkt", max_bounces=3)
    assert default.roulette_start is None
    assert default.digest() == default.replace(roulette_start=4).digest()
    assert default.digest() == default.replace(roulette_start=9).digest()
    assert default.digest() != default.replace(roulette_start=3).digest()

    #: A budget of six makes 4 a value that fires, so there it is a different run.
    deeper = default.replace(max_bounces=6)
    assert deeper.digest() != deeper.replace(roulette_start=4).digest()


def test_the_stem_carries_the_tag_the_frequency_and_the_identity():
    stem = escape().stem()
    assert stem.startswith("city250_L3_korenmarkt_15ghz_")
    assert stem.endswith(escape().digest())
    assert stem.count(escape().tag) == 1


def test_a_run_with_no_tag_still_names_itself():
    stem = escape().replace(tag="").stem()
    assert stem.startswith("escape_korenmarkt_250m_15ghz_")


# --------------------------------------------------------------- the golden lock

#: Digests of four shipped configurations, pinned to the literal strings this code
#: produces today.
#:
#: This is the golden lock for the run identity, and it is here because nothing
#: else in the study holds it. Every output file is named after a digest, so a new
#: numerical choice usually renames every file the study writes. An explicit name
#: for the sole historical default may keep the old canonical form. The pins make
#: either policy visible before the next sweep tries to find its published runs.
#:
#: When one of these moves, the question to answer is not "what is the new hash".
#: It is whether the field that moved it belongs in the identity at all. If it
#: does, repin and say in the commit which outputs have to be renamed or retraced.
PINNED_DIGESTS = {
    "escape headline": ("escape", "625d70fbc60a"),
    "next event": ("next_event", "935fd2b2d422"),
    "bare defaults": ("defaults", "ae070a9de9f1"),
    "escape at 130 m": ("escape_130", "36b390dfb402"),
}


def pinned(kind: str) -> RunConfig:
    return {
        "escape": escape(),
        "next_event": next_event(),
        "defaults": RunConfig(site="korenmarkt"),
        "escape_130": escape().replace(crop_m=130, tag="korenmarkt"),
    }[kind]


@pytest.mark.parametrize(("label", "case"), list(PINNED_DIGESTS.items()), ids=list(PINNED_DIGESTS))
def test_a_shipped_configuration_still_hashes_to_the_string_it_always_did(label, case):
    kind, expected = case
    assert pinned(kind).digest() == expected


def test_the_pinned_digests_are_four_different_runs_and_not_four_copies():
    """A pin that is the same string four times would pass while measuring nothing."""
    digests = {pinned(kind).digest() for kind, _ in PINNED_DIGESTS.values()}
    assert len(digests) == len(PINNED_DIGESTS)


def test_atlas_materials_are_opt_in_and_identify_their_atlas():
    legacy = escape()
    first = legacy.replace(materials="atlas", atlas_npz="outputs/site_semantics/site/joint_atlas_250m_r8.npz")
    second = first.replace(atlas_npz="outputs/site_semantics/site/joint_atlas_250m_r16.npz")

    assert legacy.digest() == PINNED_DIGESTS["escape headline"][1]
    assert first.digest() != legacy.digest()
    assert second.digest() != first.digest()


# ---------------------------------------------------------------- validation


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("law", "height_band"),
        ("estimator", "monostatic"),
        ("walk", "street"),
        ("walk_path", "grid"),
        ("materials", "sam3"),
        ("transport_kernel", "cupy"),
    ],
)
def test_a_name_outside_the_allowed_set_is_refused_at_construction(field, value):
    """A typo in a law name must not reach a manifest and look authoritative."""
    with pytest.raises(ValueError, match=field):
        RunConfig(site="korenmarkt", **{field: value})


@pytest.mark.parametrize(("field", "value"), [("crop_m", 0), ("rays", 0), ("max_bounces", -1), ("frequency_hz", 0.0)])
def test_a_quantity_that_cannot_be_traced_is_refused(field, value):
    with pytest.raises(ValueError, match=field):
        RunConfig(site="korenmarkt", **{field: value})


def test_a_run_has_to_score_at_least_one_illumination_model():
    with pytest.raises(ValueError, match="illumination model"):
        RunConfig(site="korenmarkt", models=())


def test_an_escape_run_cannot_carry_a_source_set():
    """The source set is what next event estimation has and escape does not.

    Letting one sit on an escape config would put nine numbers in the manifest
    that describe nothing the run did.
    """
    with pytest.raises(ValueError, match="source set"):
        RunConfig(site="korenmarkt", estimator="escape", next_event=NextEventConfig())


def test_a_next_event_run_gets_a_source_set_whether_it_asked_or_not():
    config = RunConfig(site="korenmarkt", estimator="next_event")
    assert isinstance(config.next_event, NextEventConfig)


def test_the_source_set_refuses_a_thinning_that_is_neither_plan_nor_space():
    with pytest.raises(ValueError, match="dims"):
        NextEventConfig(dims=4)


# ------------------------------------------------------------------ defaults


def test_roulette_defaults_to_one_past_the_budget_so_it_never_fires():
    """Stored as None rather than as a number, so it tracks a changed budget."""
    config = escape()
    assert config.roulette_start is None
    assert config.effective_roulette_start == config.max_bounces + 1
    assert config.replace(max_bounces=6).effective_roulette_start == 7
    assert config.replace(roulette_start=3).effective_roulette_start == 3


def test_a_config_nobody_touched_is_the_next_event_driver_as_it_ships():
    """Read out of ``run_next_event.py``'s argparse, not compared to itself.

    That driver runs the current method: the facade tip law, next event
    estimation and the route walk. So a config left alone has to reproduce it,
    and if someone moves a flag there this fails instead of leaving two versions
    of the truth in two files.
    """
    driver = argparse_defaults("run_next_event.py")
    config = RunConfig(site="korenmarkt")

    for field, flag in (
        ("crop_m", "crop_m"),
        ("rays", "rays"),
        ("frequency_hz", "frequency_hz"),
        ("max_bounces", "max_bounces"),
        ("walk_radius_m", "walk_radius_m"),
        ("head_height_m", "head_height_m"),
        ("walk_stride_m", "walk_stride_m"),
        ("walk", "walk"),
        ("walk_path", "walk_path"),
        ("seed", "seed"),
        ("variant", "variant"),
    ):
        assert getattr(config, field) == driver[flag], field

    for field, flag in (
        ("builders", "builders"),
        ("held_out", "held_out"),
        ("azimuths", "azimuths"),
        ("elevations", "elevations"),
        ("cell_m", "cell_m"),
        ("dims", "dims"),
        ("connections", "connections"),
        ("drop_clutter", "drop_clutter"),
    ):
        assert getattr(config.next_event, field) == driver[flag], field

    #: Written as a shared constant in the driver, so it is resolved rather than retyped.
    assert driver["site_lift_m"] == "SITE_LIFT_M"
    assert config.next_event.site_lift_m == package_constant("SITE_LIFT_M")


def test_the_escape_driver_defaults_match_the_run_config():
    """Both drivers now use the current crop, material control and full walk."""
    driver = argparse_defaults("run_exposure.py")
    driver["frequency_hz"] = driver.pop("frequency_ghz") * 1e9
    config = RunConfig(site="korenmarkt")

    shared = {name for name in driver if hasattr(config, name)} - {"site", "tag", "walk"}
    assert {"rays", "seed", "variant", "walk_radius_m", "walk_spacing_m", "walk_npz"} <= shared

    for name in sorted(shared):
        shipped = driver[name]
        if isinstance(shipped, str) and shipped.isupper():
            shipped = package_constant(shipped)
        assert getattr(config, name) == shipped, name

    #: Escape keeps its published grid default. The generic RunConfig default
    #: serves the next-event driver and therefore names the route.
    assert driver["walk"] == "grid"

    #: The bounce budget agrees above by way of the tracer's own constant, which the
    #: driver reads rather than retypes. Worth stating, since it is the one default
    #: shared by both drivers and the tracer.
    assert driver["max_bounces"] == "DEFAULT_MAX_BOUNCES"


def argparse_choices(relative: str, flag: str) -> set[str]:
    """What a driver's flag will accept, read without importing it."""
    for node in ast.walk(ast.parse((paths.root() / relative).read_text())):
        if not (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument"):
            continue
        if any(isinstance(arg, ast.Constant) and arg.value == flag for arg in node.args):
            for keyword in node.keywords:
                if keyword.arg == "choices":
                    return set(ast.literal_eval(keyword.value))
    raise AssertionError(f"{relative} has no {flag} carrying choices")


def test_every_name_this_class_allows_is_one_a_driver_actually_accepts():
    """The allowed sets are a claim about the drivers, so they are checked against them.

    A name here that no driver takes is a manifest value no run can produce, and a
    name a driver takes that is missing here is a run this class refuses to
    describe. Both have happened to string fields in this study, which is why the
    sets exist at all.
    """
    assert set(MATERIALS) == argparse_choices("run_exposure.py", "--materials")
    assert set(WALKS) == argparse_choices("run_next_event.py", "--walk")
    assert set(WALK_PATHS) == argparse_choices("run_next_event.py", "--walk-path")
    assert set(TRANSPORT_KERNELS) == argparse_choices("run_exposure.py", "--transport-kernel")


def test_the_two_law_families_are_the_two_the_illumination_package_declares():
    """``LAWS`` names families and the law classes carry the family they belong to.

    Every illumination class exported by the package declares one, and the empty
    string is the isotropic model, which places no sources and so belongs to no
    family. That is the column of ``LAW_CHANGE.md`` that survives every law
    change, so it is not allowed to drift.
    """
    import semantic_twin.illumination as illumination

    declared = {
        value.family for value in vars(illumination).values() if isinstance(getattr(value, "family", None), str)
    }
    assert declared == set(LAWS) | {""}


def test_each_law_family_feeds_exactly_one_estimator_and_together_they_feed_both():
    """``ESTIMATORS`` is what the illumination side can serve, not a pair of strings.

    The band models answer an angular density in a direction, which is what the
    escape estimator weights a leaving ray by. The facade tip source set answers a
    list of points, which is what next event connects to. Nothing serves both, and
    that split is the whole reason the two estimators disagree by three to five
    times on real cities.
    """
    import numpy as np

    import semantic_twin.illumination as illumination
    from semantic_twin.illumination.sources import SourceSet

    band = {name for model in illumination.MODELS.values() for name in illumination.credited_by(model)}
    placed = set(illumination.credited_by(SourceSet(np.zeros((1, 3)), 1.0, 3, 1440, 1)))

    assert band == {"escape"}
    assert placed == {"next_event"}
    assert band | placed == set(ESTIMATORS)


# ---------------------------------------------------------------- provenance


def test_provenance_puts_the_law_and_the_git_sha_where_a_reader_will_find_them():
    """The whole reason this module exists.

    ``LAW_CHANGE.md`` is 270 lines of which-numbers-survive tables because no
    output recorded which law made it. These two keys at the top level turn that
    document into a query over manifests.
    """
    record = Provenance.capture(escape(), "run_exposure.py")
    document = record.as_dict()
    assert document["law"] == "band"
    assert document["estimator"] == "escape"
    assert document["transport_kernel"] == "numpy"
    assert document["git_sha"]
    assert document["run_digest"] == escape().digest()
    assert document["run"]["site"] == "korenmarkt"


def test_provenance_survives_a_round_trip_and_brings_the_config_back_with_it():
    record = Provenance.capture(next_event(), "run_next_event.py", numpy="2.1.0")
    restored = Provenance.from_json(record.to_json())
    assert restored == record
    assert restored.run == next_event()
    assert restored.versions == {"numpy": "2.1.0"}


def test_provenance_records_a_dirty_tree_rather_than_pretending_the_sha_is_the_truth():
    record = Provenance.capture(escape(), "run_exposure.py")
    assert isinstance(record.git_dirty, bool)
    assert record.git_sha == "unknown" or len(record.git_sha) == 40
