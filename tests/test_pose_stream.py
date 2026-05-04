"""Tests for AMASS pose-stream ingest and runtime loading.

Two layers:

1. Pure-numpy tests on the resampler and on the PoseStream save/load
   round-trip. These run everywhere — no SMPL-X, no AMASS data needed.
2. A synthetic ingest run that builds AMASS-shaped ``.npz`` files in a
   tmpdir, calls ``scripts/ingest_amass.py:main`` programmatically, and
   verifies the output. Also runs everywhere.

Real-data + posed-mesh tests are skip-gated on SMPL-X model files being
present (same convention as ``test_parametric.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from aegis.geometry.pose_stream import PoseStream, resample_axis_angle  # noqa: E402


def _synthetic_amass_npz(path: Path, n_frames: int, fps: float, n_pose: int = 165, gender: str = "neutral") -> None:
    """Write a fake AMASS-shaped .npz: a flat root translation and a small sinusoidal pose."""
    rng = np.random.default_rng(42)
    t = np.arange(n_frames) / fps
    poses = 0.05 * np.sin(2 * np.pi * 1.0 * t)[:, None] * rng.standard_normal((1, n_pose))
    trans = np.stack([0.5 * t, np.zeros_like(t), np.zeros_like(t)], axis=1)
    np.savez(
        path,
        poses=poses.astype(np.float32),
        trans=trans.astype(np.float32),
        betas=np.zeros(16, dtype=np.float32),
        gender=np.array(gender),
        mocap_framerate=np.array(fps, dtype=np.float64),
    )


def test_resample_downsample_120_to_30():
    src_fps, target_fps = 120.0, 30.0
    n_src = 481
    poses = np.random.RandomState(0).standard_normal((n_src, 165))
    trans = np.random.RandomState(1).standard_normal((n_src, 3))
    out_p, out_t = resample_axis_angle(poses, trans, src_fps, target_fps)
    expected_n = int(round((n_src - 1) / src_fps * target_fps)) + 1
    assert out_p.shape == (expected_n, 165)
    assert out_t.shape == (expected_n, 3)
    assert np.allclose(out_p[0], poses[0])
    assert np.allclose(out_p[-1], poses[-1])


def test_resample_passthrough_when_rates_match():
    poses = np.random.RandomState(0).standard_normal((61, 66))
    trans = np.zeros((61, 3))
    out_p, _ = resample_axis_angle(poses, trans, 30.0, 30.0)
    assert out_p.shape == poses.shape
    assert np.allclose(out_p, poses, atol=1e-9)


def test_resample_rejects_short():
    poses = np.zeros((1, 66))
    trans = np.zeros((1, 3))
    out_p, out_t = resample_axis_angle(poses, trans, 30.0, 30.0)
    assert out_p.shape == poses.shape
    assert out_t.shape == trans.shape


def test_pose_stream_round_trip(tmp_path: Path):
    poses = np.random.RandomState(0).standard_normal((90, 165)).astype(np.float64)
    trans = np.random.RandomState(1).standard_normal((90, 3)).astype(np.float64)
    betas = np.arange(16, dtype=np.float64)
    s = PoseStream(poses=poses, trans=trans, betas=betas, gender="neutral", fps=30, source="synthetic_walk")
    out = tmp_path / "synthetic_walk.npz"
    s.save(out)
    s2 = PoseStream.load(out)
    assert s2.gender == "neutral"
    assert s2.fps == 30
    assert s2.source == "synthetic_walk"
    assert np.allclose(s2.poses, s.poses, atol=1e-5)
    assert np.allclose(s2.trans, s.trans, atol=1e-5)
    assert np.allclose(s2.betas, s.betas, atol=1e-5)


def test_pose_stream_frame_loops():
    poses = np.arange(10 * 66, dtype=np.float64).reshape(10, 66)
    trans = np.zeros((10, 3))
    s = PoseStream(poses=poses, trans=trans, betas=np.zeros(10), gender="neutral", fps=30, source="x")
    p0, _ = s.frame(0)
    p10, _ = s.frame(10)
    assert np.allclose(p0, p10)
    p3, _ = s.frame(3)
    p13, _ = s.frame(13)
    assert np.allclose(p3, p13)
    with pytest.raises(IndexError):
        s.frame(10, loop=False)


def test_pose_stream_validates_shapes():
    with pytest.raises(ValueError, match="poses"):
        PoseStream(
            poses=np.zeros((10, 60)), trans=np.zeros((10, 3)), betas=np.zeros(10), gender="neutral", fps=30, source="x"
        )
    with pytest.raises(ValueError, match="trans"):
        PoseStream(
            poses=np.zeros((10, 66)), trans=np.zeros((9, 3)), betas=np.zeros(10), gender="neutral", fps=30, source="x"
        )


def test_ingest_main_synthetic(tmp_path: Path, capsys):
    """End-to-end: build fake AMASS dump, run the CLI, verify outputs."""
    from ingest_amass import main  # noqa: PLC0415

    amass = tmp_path / "amass"
    walking = amass / "CMU" / "01"
    walking.mkdir(parents=True)
    _synthetic_amass_npz(walking / "01_01_walk.npz", n_frames=240, fps=120.0)
    _synthetic_amass_npz(walking / "01_02_walking.npz", n_frames=180, fps=60.0)
    other = amass / "CMU" / "02"
    other.mkdir(parents=True)
    _synthetic_amass_npz(other / "02_01_run.npz", n_frames=240, fps=120.0)

    out_dir = tmp_path / "poses"
    rc = main(["--input", str(amass), "--output", str(out_dir), "--max-sequences", "10", "--filter", "walk"])
    assert rc == 0

    written = sorted(out_dir.glob("*.npz"))
    assert len(written) == 2

    s = PoseStream.load(written[0])
    assert s.fps == 30
    duration = (240 / 120.0) if "01_01" in s.source else (180 / 60.0)
    expected_n = int(round(duration * 30)) + 1
    assert abs(len(s) - expected_n) <= 1


# --- Optional layer: needs SMPL-X model files ---

smplx_mod = pytest.importorskip("smplx", reason="smplx not installed")
SMPLX_DIR = Path.home() / ".aegis" / "models" / "smplx"
has_models = SMPLX_DIR.exists()


@pytest.mark.skipif(not has_models, reason="SMPL-X model files not found")
def test_pose_stream_posed_body(tmp_path: Path):
    from aegis.geometry.parametric import ParametricBody

    poses = np.zeros((30, 165))
    poses[:, 5] = np.linspace(-0.3, 0.3, 30)
    trans = np.zeros((30, 3))
    trans[:, 0] = np.linspace(0.0, 1.0, 30)
    s = PoseStream(poses=poses, trans=trans, betas=np.zeros(10), gender="neutral", fps=30, source="zero")
    pb = ParametricBody.load("smplx", gender="neutral")
    mesh0 = s.posed_body(0, pb)
    mesh10 = s.posed_body(10, pb)
    assert mesh0.n_triangles == mesh10.n_triangles
    assert not np.allclose(mesh0.vertices, mesh10.vertices)
