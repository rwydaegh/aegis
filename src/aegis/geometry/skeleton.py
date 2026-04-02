"""Forward kinematics for glTF skeletons. Produces BodyMesh from pose parameters."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from aegis.geometry.mesh import BodyMesh


def _read_accessor(gltf, accessor_index: int, blob: bytes) -> np.ndarray:
    """Read a glTF accessor into a numpy array."""
    accessor = gltf.accessors[accessor_index]
    buffer_view = gltf.bufferViews[accessor.bufferView]

    byte_offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
    count = accessor.count

    # Component type -> numpy dtype
    component_dtypes = {
        5120: np.int8,
        5121: np.uint8,
        5122: np.int16,
        5123: np.uint16,
        5125: np.uint32,
        5126: np.float32,
    }
    dtype = component_dtypes[accessor.componentType]

    # Type -> number of components
    type_sizes = {
        "SCALAR": 1,
        "VEC2": 2,
        "VEC3": 3,
        "VEC4": 4,
        "MAT2": 4,
        "MAT3": 9,
        "MAT4": 16,
    }
    n_components = type_sizes[accessor.type]

    item_size = np.dtype(dtype).itemsize * n_components
    stride = buffer_view.byteStride or item_size

    if stride == item_size:
        data = np.frombuffer(blob, dtype=dtype, count=count * n_components, offset=byte_offset)
    else:
        # Strided access
        data = np.empty(count * n_components, dtype=dtype)
        for i in range(count):
            start = byte_offset + i * stride
            chunk = np.frombuffer(blob, dtype=dtype, count=n_components, offset=start)
            data[i * n_components : (i + 1) * n_components] = chunk

    if n_components == 1:
        return data.copy()
    data = data.reshape(count, n_components)

    # MAT4 is stored column-major in glTF, transpose to row-major
    if accessor.type == "MAT4":
        data = data.reshape(count, 4, 4).transpose(0, 2, 1)
    elif accessor.type == "MAT3":
        data = data.reshape(count, 3, 3).transpose(0, 2, 1)

    return data.copy()


def _node_local_matrix(node) -> np.ndarray:
    """Build a 4x4 local transform from a glTF node's TRS properties."""
    mat = np.eye(4, dtype=np.float64)

    if node.matrix is not None:
        # glTF matrix is column-major flat list
        mat = np.array(node.matrix, dtype=np.float64).reshape(4, 4).T
        return mat

    if node.scale is not None:
        s = node.scale
        mat[:3, :3] *= np.array(s, dtype=np.float64)

    if node.rotation is not None:
        # glTF quaternion is [x, y, z, w]
        qx, qy, qz, qw = node.rotation
        rot = Rotation.from_quat([qx, qy, qz, qw]).as_matrix()
        mat[:3, :3] = rot @ mat[:3, :3]

    if node.translation is not None:
        mat[:3, 3] = np.array(node.translation, dtype=np.float64)

    return mat


class GltfSkeleton:
    """Parse a glTF skeleton and apply forward kinematics + LBS."""

    def __init__(
        self,
        rest_vertices: np.ndarray,
        triangles: np.ndarray,
        joint_parents: np.ndarray,
        inverse_bind_matrices: np.ndarray,
        joint_local_transforms: np.ndarray,
        skin_weights: np.ndarray,
        skin_joints: np.ndarray,
    ):
        self.rest_vertices = np.asarray(rest_vertices, dtype=np.float64)
        self.triangles = np.asarray(triangles, dtype=np.int64)
        self.joint_parents = np.asarray(joint_parents, dtype=np.int64)
        self.inverse_bind_matrices = np.asarray(inverse_bind_matrices, dtype=np.float64)
        self.joint_local_transforms = np.asarray(joint_local_transforms, dtype=np.float64)
        self.skin_weights = np.asarray(skin_weights, dtype=np.float64)
        self.skin_joints = np.asarray(skin_joints, dtype=np.int64)

    @property
    def n_joints(self) -> int:
        return len(self.joint_parents)

    @staticmethod
    def load(path: str | Path) -> GltfSkeleton:
        """Load skeleton data from a GLB file."""
        try:
            import pygltflib
        except ImportError:
            raise ImportError("pygltflib is required for GltfSkeleton. Install with: pip install pygltflib") from None

        path = Path(path)
        gltf = pygltflib.GLTF2().load(str(path))
        blob = gltf.binary_blob()

        # Find first mesh with skin
        skin_node_idx = None
        mesh_idx = None
        skin_idx = None
        for i, node in enumerate(gltf.nodes):
            if node.mesh is not None and node.skin is not None:
                skin_node_idx = i
                mesh_idx = node.mesh
                skin_idx = node.skin
                break

        if skin_idx is None:
            raise ValueError("No skinned mesh found in the glTF file")

        skin = gltf.skins[skin_idx]
        mesh = gltf.meshes[mesh_idx]
        prim = mesh.primitives[0]

        # Read position, index, joints, weights accessors
        rest_vertices = _read_accessor(gltf, prim.attributes.POSITION, blob)
        triangles = _read_accessor(gltf, prim.indices, blob).reshape(-1, 3)
        skin_joints_attr = _read_accessor(gltf, prim.attributes.JOINTS_0, blob)
        skin_weights = _read_accessor(gltf, prim.attributes.WEIGHTS_0, blob)

        # Read inverse bind matrices
        ibm = _read_accessor(gltf, skin.inverseBindMatrices, blob).reshape(-1, 4, 4)

        # Build joint hierarchy
        joint_node_indices = skin.joints
        n_joints = len(joint_node_indices)

        # Find parent for each joint by checking which joint node has it as a child
        joint_parents = np.full(n_joints, -1, dtype=np.int64)
        for j, node_idx in enumerate(joint_node_indices):
            # Search all joint nodes for one that lists this node as child
            for candidate_j, candidate_node_idx in enumerate(joint_node_indices):
                candidate_node = gltf.nodes[candidate_node_idx]
                if candidate_node.children and node_idx in candidate_node.children:
                    joint_parents[j] = candidate_j
                    break

        # Also check the skin node itself for root joints
        if skin_node_idx is not None:
            skin_node = gltf.nodes[skin_node_idx]
            if skin_node.children:
                for j, node_idx in enumerate(joint_node_indices):
                    if node_idx in skin_node.children and joint_parents[j] == -1:
                        # This is a root joint parented to the skin node
                        joint_parents[j] = -1

        # Build local transforms for each joint
        joint_local_transforms = np.zeros((n_joints, 4, 4), dtype=np.float64)
        for j, node_idx in enumerate(joint_node_indices):
            node = gltf.nodes[node_idx]
            joint_local_transforms[j] = _node_local_matrix(node)

        return GltfSkeleton(
            rest_vertices=rest_vertices,
            triangles=triangles,
            joint_parents=joint_parents,
            inverse_bind_matrices=ibm,
            joint_local_transforms=joint_local_transforms,
            skin_weights=skin_weights,
            skin_joints=skin_joints_attr,
        )

    def pose_to_body(
        self,
        joint_angles: np.ndarray | None = None,
        name: str = "posed",
    ) -> BodyMesh:
        """Apply FK + LBS and return a BodyMesh."""
        J = self.n_joints
        V = len(self.rest_vertices)

        # Build per-joint rotation matrices from axis-angle
        if joint_angles is None:
            local_rots = np.tile(np.eye(4), (J, 1, 1))
        else:
            angles = joint_angles.reshape(J, 3)
            local_rots = np.tile(np.eye(4), (J, 1, 1))
            for j in range(J):
                angle_mag = np.linalg.norm(angles[j])
                if angle_mag > 1e-8:
                    local_rots[j, :3, :3] = Rotation.from_rotvec(angles[j]).as_matrix()

        # FK: compute global transforms
        global_transforms = np.zeros((J, 4, 4))
        for j in range(J):
            local = self.joint_local_transforms[j] @ local_rots[j]
            parent = self.joint_parents[j]
            if parent < 0:
                global_transforms[j] = local
            else:
                global_transforms[j] = global_transforms[parent] @ local

        # Skin matrices
        skin_matrices = np.einsum("jab,jbc->jac", global_transforms, self.inverse_bind_matrices)

        # LBS
        v_homo = np.ones((V, 4))
        v_homo[:, :3] = self.rest_vertices

        posed = np.zeros((V, 3))
        for k in range(4):
            joint_idx = self.skin_joints[:, k].astype(np.int64)
            weight = self.skin_weights[:, k, None]
            mats = skin_matrices[joint_idx]
            transformed = np.einsum("vab,vb->va", mats, v_homo)
            posed += weight * transformed[:, :3]

        # De-index into triangle soup
        tri_verts = posed[self.triangles]  # (T, 3, 3)

        # Face normals
        e1 = tri_verts[:, 1] - tri_verts[:, 0]
        e2 = tri_verts[:, 2] - tri_verts[:, 0]
        normals = np.cross(e1, e2)
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms = np.where(norms < 1e-10, 1.0, norms)
        normals = normals / norms

        return BodyMesh.from_arrays(tri_verts, normals, name=name)
