"""Named SMPL-X pose presets for the Exposure Lab.

The flat pose vector is length 66: ``pose[0:3]`` is global_orient (pelvis) and
``pose[3:66]`` is the body_pose for 21 body joints. Body joint ``j`` occupies
``pose[3 + 3*j : 6 + 3*j]`` as an axis-angle rotation. SMPL-X frame: Y up, body
faces +Z, X is the body's left.
"""

from __future__ import annotations

# Body-joint indices used below (0-indexed into the 21 body joints).
_LEFT_SHOULDER = 15
_RIGHT_SHOULDER = 16
_RIGHT_ELBOW = 18


def _set(pose: list[float], joint: int, axis_angle: tuple[float, float, float]) -> None:
    """Write an axis-angle rotation for a body joint into a flat pose vector."""
    base = 3 + 3 * joint
    pose[base], pose[base + 1], pose[base + 2] = axis_angle


def _arms_down() -> list[float]:
    pose = [0.0] * 66
    _set(pose, _LEFT_SHOULDER, (0.0, 0.0, -1.2))
    _set(pose, _RIGHT_SHOULDER, (0.0, 0.0, 1.2))
    return pose


def _arm_raised_front() -> list[float]:
    pose = _arms_down()
    # Right arm swung forward (+Z) and inward, with a strong elbow bend so the
    # forearm crosses in front of the chest (the self-shadow demo pose). The
    # hand ends near the chest midline at roughly shoulder height.
    _set(pose, _RIGHT_SHOULDER, (0.0, 1.3, 0.6))
    _set(pose, _RIGHT_ELBOW, (0.0, 1.6, 0.0))
    return pose


def _hand_to_cheek() -> list[float]:
    pose = _arms_down()
    # Right hand up near the head: shoulder slightly forward, strong elbow bend
    # bringing the hand to the side of the face (a plausible phone-to-ear pose).
    _set(pose, _RIGHT_SHOULDER, (-0.3, 0.3, -0.5))
    _set(pose, _RIGHT_ELBOW, (0.0, 2.8, 0.0))
    return pose


POSE_PRESETS: dict[str, list[float]] = {
    "t_pose": [0.0] * 66,
    "arms_down": _arms_down(),
    "arm_raised_front": _arm_raised_front(),
    "hand_to_cheek": _hand_to_cheek(),
}
