"""SMPL-X rig extraction for browser linear blend skinning."""

import numpy as np


def build_rig(gender: str, betas: np.ndarray) -> dict:
    """Shaped template, faces, skinning weights, rest joints, parents.

    Everything the browser needs to forward-kinematic + skin the body live. The
    pose-dependent corrective blendshapes (posedirs) are intentionally NOT sent;
    the live preview skips them and the server adds them in the authoritative
    re-pose. Pulled from the raw smplx model buffers.
    """
    from aegis.geometry.parametric import ParametricBody

    pb = ParametricBody.load("smplx", gender)
    m = pb._model

    def npy(x):
        return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)

    v_template = npy(m.v_template).astype(np.float64)  # (V, 3)
    shapedirs = npy(m.shapedirs).astype(np.float64)  # (V, 3, n_betas)
    nb = min(int(betas.shape[0]), shapedirs.shape[2])
    shaped = v_template + shapedirs[:, :, :nb] @ betas[:nb]  # (V, 3)
    j_regressor = npy(m.J_regressor).astype(np.float64)  # (J, V)
    rest_joints = j_regressor @ shaped  # (J, 3)
    lbs_weights = npy(m.lbs_weights).astype(np.float32)  # (V, J)
    parents = npy(m.parents).astype(np.int64)  # (J,)
    faces = pb._faces.astype(np.int64).reshape(-1)  # (3F,)
    return {
        "n_vertices": int(shaped.shape[0]),
        "n_joints": int(rest_joints.shape[0]),
        "template": shaped.reshape(-1).astype(np.float32).tolist(),
        "faces": faces.tolist(),
        "lbs_weights": lbs_weights.astype(np.float16).reshape(-1).tolist(),
        "rest_joints": rest_joints.reshape(-1).astype(np.float32).tolist(),
        "parents": parents.tolist(),
    }
