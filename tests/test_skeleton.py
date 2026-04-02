"""Tests for GltfSkeleton forward kinematics and LBS."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pygltflib = pytest.importorskip("pygltflib")

from aegis.geometry.skeleton import GltfSkeleton  # noqa: E402


def _pack_accessor_data(array: np.ndarray, component_type: int) -> bytes:
    """Pack a numpy array into raw bytes matching glTF component type."""
    if component_type == 5126:  # FLOAT
        return array.astype("<f4").tobytes()
    elif component_type == 5123:  # UNSIGNED_SHORT
        return array.astype("<u2").tobytes()
    elif component_type == 5125:  # UNSIGNED_INT
        return array.astype("<u4").tobytes()
    elif component_type == 5121:  # UNSIGNED_BYTE
        return array.astype("<u1").tobytes()
    raise ValueError(f"Unknown component type {component_type}")


def _build_minimal_glb(tmp_path: Path) -> Path:
    """Build a minimal GLB with a 2-joint skeleton and a simple mesh.

    The mesh is a rectangular prism (8 verts, 12 triangles).
    Joint 0 (root) is at origin. Joint 1 (child) is at y=1.
    Bottom 4 verts are skinned to joint 0, top 4 to joint 1.
    """
    from pygltflib import (
        GLTF2,
        Accessor,
        Attributes,
        Buffer,
        BufferView,
        Mesh,
        Node,
        Primitive,
        Scene,
        Skin,
    )

    # Box vertices: bottom face at y=0, top face at y=2
    positions = np.array(
        [
            # Bottom 4 (y=0)
            [-0.5, 0.0, -0.5],
            [0.5, 0.0, -0.5],
            [0.5, 0.0, 0.5],
            [-0.5, 0.0, 0.5],
            # Top 4 (y=2)
            [-0.5, 2.0, -0.5],
            [0.5, 2.0, -0.5],
            [0.5, 2.0, 0.5],
            [-0.5, 2.0, 0.5],
        ],
        dtype=np.float32,
    )

    # 12 triangles (6 faces * 2 tris)
    indices = np.array(
        [
            # bottom
            0,
            2,
            1,
            0,
            3,
            2,
            # top
            4,
            5,
            6,
            4,
            6,
            7,
            # front (z+)
            3,
            7,
            6,
            3,
            6,
            2,
            # back (z-)
            0,
            1,
            5,
            0,
            5,
            4,
            # right (x+)
            1,
            2,
            6,
            1,
            6,
            5,
            # left (x-)
            0,
            4,
            7,
            0,
            7,
            3,
        ],
        dtype=np.uint16,
    )

    # Skin weights: bottom verts -> joint 0, top verts -> joint 1
    joints_attr = np.array(
        [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [1, 0, 0, 0],
            [1, 0, 0, 0],
            [1, 0, 0, 0],
            [1, 0, 0, 0],
        ],
        dtype=np.uint8,
    )

    weights_attr = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )

    # Inverse bind matrices: identity for joint 0, translate y=-1 for joint 1
    ibm = np.zeros((2, 4, 4), dtype=np.float32)
    ibm[0] = np.eye(4, dtype=np.float32)
    ibm[1] = np.eye(4, dtype=np.float32)
    ibm[1][1, 3] = -1.0  # joint 1 rest position is at y=1

    # Pack all binary data into a single buffer
    pos_bytes = _pack_accessor_data(positions, 5126)
    idx_bytes = _pack_accessor_data(indices, 5123)
    joints_bytes = _pack_accessor_data(joints_attr, 5121)
    weights_bytes = _pack_accessor_data(weights_attr, 5126)
    # IBM stored column-major (glTF convention)
    ibm_col_major = np.transpose(ibm, (0, 2, 1)).astype(np.float32)
    ibm_bytes = ibm_col_major.tobytes()

    # Calculate offsets
    pos_offset = 0
    idx_offset = pos_offset + len(pos_bytes)
    joints_offset = idx_offset + len(idx_bytes)
    weights_offset = joints_offset + len(joints_bytes)
    ibm_offset = weights_offset + len(weights_bytes)
    total_length = ibm_offset + len(ibm_bytes)

    blob = pos_bytes + idx_bytes + joints_bytes + weights_bytes + ibm_bytes

    gltf = GLTF2(
        scene=0,
        scenes=[Scene(nodes=[0])],
        nodes=[
            # Node 0: mesh + skin reference
            Node(mesh=0, skin=0, children=[1, 2]),
            # Node 1: joint 0 (root) - at origin
            Node(
                name="joint_0",
                translation=[0.0, 0.0, 0.0],
            ),
            # Node 2: joint 1 (child of joint 0) - at y=1
            Node(
                name="joint_1",
                translation=[0.0, 1.0, 0.0],
            ),
        ],
        meshes=[
            Mesh(
                primitives=[
                    Primitive(
                        attributes=Attributes(
                            POSITION=0,
                            JOINTS_0=2,
                            WEIGHTS_0=3,
                        ),
                        indices=1,
                    )
                ]
            )
        ],
        skins=[
            Skin(
                joints=[1, 2],
                inverseBindMatrices=4,
                skeleton=1,
            )
        ],
        accessors=[
            # 0: positions
            Accessor(
                bufferView=0,
                componentType=5126,
                count=8,
                type="VEC3",
                max=positions.max(axis=0).tolist(),
                min=positions.min(axis=0).tolist(),
            ),
            # 1: indices
            Accessor(
                bufferView=1,
                componentType=5123,
                count=len(indices),
                type="SCALAR",
            ),
            # 2: joints
            Accessor(
                bufferView=2,
                componentType=5121,
                count=8,
                type="VEC4",
            ),
            # 3: weights
            Accessor(
                bufferView=3,
                componentType=5126,
                count=8,
                type="VEC4",
            ),
            # 4: inverse bind matrices
            Accessor(
                bufferView=4,
                componentType=5126,
                count=2,
                type="MAT4",
            ),
        ],
        bufferViews=[
            BufferView(buffer=0, byteOffset=pos_offset, byteLength=len(pos_bytes)),
            BufferView(buffer=0, byteOffset=idx_offset, byteLength=len(idx_bytes)),
            BufferView(buffer=0, byteOffset=joints_offset, byteLength=len(joints_bytes)),
            BufferView(buffer=0, byteOffset=weights_offset, byteLength=len(weights_bytes)),
            BufferView(buffer=0, byteOffset=ibm_offset, byteLength=len(ibm_bytes)),
        ],
        buffers=[Buffer(byteLength=total_length)],
    )

    gltf.set_binary_blob(blob)

    out_path = tmp_path / "test_skeleton.glb"
    gltf.save(str(out_path))
    return out_path


@pytest.fixture
def glb_path(tmp_path: Path) -> Path:
    return _build_minimal_glb(tmp_path)


@pytest.fixture
def skeleton(glb_path: Path) -> GltfSkeleton:
    return GltfSkeleton.load(glb_path)


class TestSkeletonLoads:
    def test_n_joints(self, skeleton: GltfSkeleton) -> None:
        assert skeleton.n_joints == 2

    def test_rest_vertices_shape(self, skeleton: GltfSkeleton) -> None:
        assert skeleton.rest_vertices.ndim == 2
        assert skeleton.rest_vertices.shape[1] == 3
        assert skeleton.rest_vertices.shape[0] == 8

    def test_triangles_shape(self, skeleton: GltfSkeleton) -> None:
        assert skeleton.triangles.shape == (12, 3)

    def test_skin_weights_shape(self, skeleton: GltfSkeleton) -> None:
        assert skeleton.skin_weights.shape == (8, 4)

    def test_skin_joints_shape(self, skeleton: GltfSkeleton) -> None:
        assert skeleton.skin_joints.shape == (8, 4)


class TestRestPose:
    def test_rest_pose_produces_body_mesh(self, skeleton: GltfSkeleton) -> None:
        body = skeleton.pose_to_body(joint_angles=None, name="rest")
        assert body.name == "rest"
        assert body.vertices.shape == (12, 3, 3)
        assert body.normals.shape == (12, 3)

    def test_normals_are_unit_length(self, skeleton: GltfSkeleton) -> None:
        body = skeleton.pose_to_body()
        magnitudes = np.linalg.norm(body.normals, axis=1)
        np.testing.assert_allclose(magnitudes, 1.0, atol=1e-6)


class TestPoseChangesVertices:
    def test_rotating_joint_changes_vertices(self, skeleton: GltfSkeleton) -> None:
        body_rest = skeleton.pose_to_body()
        # Rotate joint 1 by 90 degrees around z-axis
        angles = np.zeros(skeleton.n_joints * 3)
        angles[3 + 2] = np.pi / 2  # joint 1, z-axis
        body_posed = skeleton.pose_to_body(joint_angles=angles)
        # Vertices should differ
        assert not np.allclose(body_rest.vertices, body_posed.vertices, atol=1e-6)

    def test_zero_angles_match_rest_pose(self, skeleton: GltfSkeleton) -> None:
        body_rest = skeleton.pose_to_body()
        angles = np.zeros(skeleton.n_joints * 3)
        body_zero = skeleton.pose_to_body(joint_angles=angles)
        np.testing.assert_allclose(body_rest.vertices, body_zero.vertices, atol=1e-6)


class TestImportGuard:
    def test_helpful_error_on_missing_pygltflib(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pygltflib":
                raise ModuleNotFoundError("No module named 'pygltflib'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="pygltflib"):
            GltfSkeleton.load("/nonexistent.glb")
