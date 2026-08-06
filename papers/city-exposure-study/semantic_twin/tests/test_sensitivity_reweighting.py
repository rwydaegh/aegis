from __future__ import annotations

import pathlib

import numpy as np

from semantic_twin.illumination.sensitivity import Reweighter, elevation_centres


class ConstantLaw:
    height_band_m = (10.0, 20.0)
    range_band_m = (5.0, 100.0)

    def normalisation(self, samples: int = 0) -> float:
        return 1.0

    def density(self, directions: np.ndarray, normalisation: float) -> np.ndarray:
        return np.full(directions.shape[0], 2.0)


def write_harvest(path: pathlib.Path) -> None:
    np.savez_compressed(
        path,
        fine=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
        direct=np.array([[0.25, 0.5], [0.75, 1.0]], dtype=np.float32),
        crop=np.ones((2, 2, 2), dtype=np.float32),
        crop_range_edges_m=np.array([0.0, 50.0, np.inf]),
        traced_chi=np.zeros((2, 1)),
        traced_models=np.array(["constant"]),
        points=np.zeros((2, 3)),
        index=np.array([1, 3]),
        crop_radius_m=250.0,
        elevation_bins=2,
        crop_elevation_bins=2,
    )


def test_elevation_centres_cover_the_sphere_without_touching_the_poles():
    assert np.array_equal(elevation_centres(4), np.array([-67.5, -22.5, 22.5, 67.5]))


def test_reweighter_applies_one_law_to_full_and_direct_harvests(tmp_path: pathlib.Path):
    harvest = tmp_path / "harvest.npz"
    write_harvest(harvest)
    reweighter = Reweighter(harvest)

    assert np.array_equal(reweighter.chi(ConstantLaw()), np.array([6.0, 14.0]))
    assert np.array_equal(reweighter.chi_direct(ConstantLaw()), np.array([1.5, 3.5]))
    assert reweighter.locations == 2


def test_built_extent_reweighting_never_adds_unbuilt_power(tmp_path: pathlib.Path):
    harvest = tmp_path / "harvest.npz"
    write_harvest(harvest)
    published, built = Reweighter(harvest).chi_built(ConstantLaw())

    assert published.shape == built.shape == (2,)
    assert np.all(built <= published)
