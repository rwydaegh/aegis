"""
Phantom dosimetry animation -- Thelonious STL to single-triangle close-up.

Build:   cd presentations/group && manim-slides render -qh phantom_scene.py PhantomScene
Present: manim-slides present PhantomScene
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from manim import *
from manim_slides import ThreeDSlide

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BODY_GREY = ManimColor("#AAAAAA")
BODY_DARK = ManimColor("#777777")
WIRE_COLOR = ManimColor("#CCCCCC")
BG_COLOR = ManimColor("#1a1a2e")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
STL_PATH = DATA_DIR / "thelonious.stl"

SCALE = 7.0
TARGET_FACES = 600


# ---------------------------------------------------------------------------
# Mesh helpers
# ---------------------------------------------------------------------------

def load_and_decimate(path: Path, target_faces: int):
    import trimesh
    m = trimesh.load(str(path))
    s = m.simplify_quadric_decimation(face_count=target_faces)
    return s.vertices, s.faces, s.face_normals, s.triangles_center


def stl_to_manim(pts: np.ndarray, center: np.ndarray) -> np.ndarray:
    """STL (X right, Y front, Z up) -> manim 3D (X right, Y front, Z up).

    Manim ThreeDScene uses Z as vertical axis, matching STL convention.
    Just center and scale.
    """
    return (pts - center) * SCALE


def normal_to_manim(n: np.ndarray) -> np.ndarray:
    return n / np.linalg.norm(n)


def build_solid_mesh(verts_m, faces, arm_idx=None) -> VGroup:
    """VGroup of filled Polygon objects. Arm triangle is bright yellow."""
    polys = []
    for i, face in enumerate(faces):
        if i == arm_idx:
            p = Polygon(
                verts_m[face[0]], verts_m[face[1]], verts_m[face[2]],
                fill_color=YELLOW, fill_opacity=1.0,
                stroke_color=YELLOW, stroke_width=2.5,
            )
        else:
            p = Polygon(
                verts_m[face[0]], verts_m[face[1]], verts_m[face[2]],
                fill_color=BODY_GREY, fill_opacity=1.0,
                stroke_color=BODY_DARK, stroke_width=0.3,
            )
        polys.append(p)
    return VGroup(*polys)


def build_wireframe(verts_m, faces) -> VMobject:
    """Single VMobject with stroke only (fast wireframe)."""
    vm = VMobject(
        stroke_color=WIRE_COLOR, stroke_width=0.5,
        fill_opacity=0.0,
    )
    pts = []
    for face in faces:
        a, b, c = verts_m[face[0]], verts_m[face[1]], verts_m[face[2]]
        pts.extend([a, a, b, b, b, b, c, c, c, c, a, a])
    vm.points = np.array(pts, dtype=float)
    return vm


def find_arm_triangle(vertices, faces, centroids, normals) -> int:
    """Find an outward-facing triangle on the right arm, preferring equilateral."""
    mask = (
        (centroids[:, 0] > 0.12)
        & (centroids[:, 2] > -0.45)
        & (centroids[:, 2] < -0.15)
        & (normals[:, 0] > 0.3)
    )
    indices = np.where(mask)[0]
    best_idx, best_score = indices[0], 1e9
    for idx in indices:
        verts = vertices[faces[idx]]
        edges = [
            np.linalg.norm(verts[1] - verts[0]),
            np.linalg.norm(verts[2] - verts[1]),
            np.linalg.norm(verts[0] - verts[2]),
        ]
        aspect = max(edges) / min(edges)
        area = 0.5 * np.linalg.norm(np.cross(verts[1] - verts[0], verts[2] - verts[0]))
        score = aspect - area * 500
        if score < best_score:
            best_score = score
            best_idx = idx
    return int(best_idx)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

class PhantomScene(ThreeDSlide):
    def construct(self):
        self.camera.background_color = BG_COLOR

        # -- Load mesh -----------------------------------------------------
        vertices, faces, face_normals, centroids = load_and_decimate(
            STL_PATH, TARGET_FACES,
        )
        mesh_center = vertices.mean(axis=0)
        verts_m = stl_to_manim(vertices, mesh_center)

        # Arm triangle
        arm_idx = find_arm_triangle(vertices, faces, centroids, face_normals)
        arm_center_m = stl_to_manim(
            centroids[arm_idx].reshape(1, 3), mesh_center,
        ).flatten()
        arm_normal_m = normal_to_manim(face_normals[arm_idx])
        arm_verts_m = verts_m[faces[arm_idx]]

        # -- Build meshes --------------------------------------------------
        solid = build_solid_mesh(verts_m, faces, arm_idx=arm_idx)

        # Wireframe without the arm triangle
        other_mask = np.ones(len(faces), dtype=bool)
        other_mask[arm_idx] = False
        wire = build_wireframe(verts_m, faces[other_mask])

        # Arm triangle as separate Polygon (starts yellow to match solid)
        arm_poly = Polygon(
            *arm_verts_m,
            fill_color=YELLOW, fill_opacity=0.3,
            stroke_color=YELLOW, stroke_width=2.5,
        )

        # =================================================================
        # SLIDE 1: Solid grey phantom with yellow arm triangle, face on
        # =================================================================
        self.set_camera_orientation(
            phi=90 * DEGREES,
            theta=270 * DEGREES,
            zoom=0.85,
            frame_center=[0.0, 0.0, 0.2 * SCALE],
        )

        self.play(FadeIn(solid), run_time=2)
        self.next_slide()

        # =================================================================
        # SLIDE 2: Crossfade solid -> wireframe + camera orbit to arm
        # =================================================================
        v0, v1, v2 = arm_verts_m
        edge_vecs = [v1 - v0, v2 - v1, v0 - v2]
        longest = max(edge_vecs, key=lambda e: float(np.linalg.norm(e)))
        x_dir = longest / np.linalg.norm(longest)
        d_dir = -arm_normal_m  # depth into body

        # Camera: edge-on strip view
        view_dir = np.cross(arm_normal_m, x_dir)
        view_dir = view_dir / np.linalg.norm(view_dir)

        vx, vy, vz = view_dir
        target_phi = float(np.arccos(np.clip(vz, -1, 1)))
        target_theta = float(np.arctan2(vy, vx))

        # Pre-add wireframe and arm poly (invisible)
        wire.set_stroke(opacity=0)
        arm_poly.set_stroke(opacity=0)
        arm_poly.set_fill(opacity=0)
        self.add(wire, arm_poly)

        # Gamma so x_dir appears horizontal on screen
        cam_right = np.array([-np.sin(target_theta), np.cos(target_theta), 0.0])
        cam_up = np.cross(view_dir, cam_right)
        cam_up = cam_up / np.linalg.norm(cam_up)
        x_screen_h = float(np.dot(x_dir, cam_right))
        x_screen_v = float(np.dot(x_dir, cam_up))
        target_gamma = float(-np.arctan2(x_screen_v, x_screen_h))

        self.move_camera(
            phi=target_phi,
            theta=target_theta,
            gamma=target_gamma,
            frame_center=arm_center_m,
            zoom=0.85,
            added_anims=[
                FadeOut(solid, run_time=5),
                wire.animate.set_stroke(opacity=1),
                arm_poly.animate.set_stroke(color=YELLOW, width=2.5, opacity=1)
                    .set_fill(color=YELLOW, opacity=0.3),
            ],
            run_time=5,
            rate_func=smooth,
        )
        self.remove(solid)
        self.next_slide()

        # =================================================================
        # SLIDE 3: Isolate arm triangle, zoom in
        # =================================================================
        self.play(FadeOut(wire), run_time=2)

        self.move_camera(
            frame_center=arm_center_m,
            zoom=8.0,
            run_time=2,
        )

        # Restyle to clean grey + white edges
        self.play(
            arm_poly.animate
                .set_fill(color=BODY_GREY, opacity=0.4)
                .set_stroke(color=WHITE, width=2),
            run_time=1,
        )
        self.next_slide()

        # =================================================================
        # SLIDE 4: Draw x-axis (simple Arrow)
        # =================================================================
        tc = arm_center_m
        ax_len = 0.18
        delta = 0.15  # skin depth in manim units
        d_ax_len = delta * 1.6  # d-axis long enough for voxels + some margin

        x_arrow = Arrow(
            start=tc - x_dir * ax_len * 0.15,
            end=tc + x_dir * ax_len,
            color=RED,
            stroke_width=2.5,
            tip_length=0.015,
            max_stroke_width_to_length_ratio=999,
            max_tip_length_to_length_ratio=0.15,
        )

        x_label = Tex("$x$", color=RED, font_size=24).move_to(
            tc + x_dir * (ax_len + 0.03),
        )
        self.add_fixed_orientation_mobjects(x_label)

        self.play(Create(x_arrow), FadeIn(x_label), run_time=1.5)
        self.next_slide()

        # =================================================================
        # SLIDE 5: Draw d-axis (depth into body)
        # =================================================================
        d_arrow = Arrow(
            start=tc,
            end=tc + d_dir * d_ax_len,
            color=BLUE,
            stroke_width=2.5,
            tip_length=0.015,
            max_stroke_width_to_length_ratio=999,
            max_tip_length_to_length_ratio=0.15,
        )

        d_label = Tex("$d$", color=BLUE, font_size=24).move_to(
            tc + d_dir * (d_ax_len + 0.025),
        )
        self.add_fixed_orientation_mobjects(d_label)

        self.play(Create(d_arrow), FadeIn(d_label), run_time=1.5)
        self.next_slide()

        # =================================================================
        # SLIDE 6: Damped exponential + skin depth delta
        # =================================================================
        # E-field decays as exp(-d/delta) along d-axis.
        # Amplitude shown perpendicular to d (in x-direction).
        n_pts = 80
        d_vals = np.linspace(0, d_ax_len * 0.9, n_pts)
        amp_scale = 0.10  # max amplitude perpendicular to d-axis

        curve_pts = []
        for d in d_vals:
            pos = tc + d_dir * d + x_dir * amp_scale * np.exp(-d / delta)
            curve_pts.append(pos)

        exp_curve = VMobject(stroke_color=GREEN, stroke_width=2.5)
        exp_curve.set_points_smoothly([np.array(p) for p in curve_pts])

        # Dashed horizontal line at d = delta from curve to d-axis
        delta_amp = amp_scale * np.exp(-1)  # amplitude at d=delta
        delta_pt_on_curve = tc + d_dir * delta + x_dir * delta_amp
        delta_pt_on_axis = tc + d_dir * delta

        dashed_line = DashedLine(
            delta_pt_on_curve, delta_pt_on_axis,
            color=WHITE, stroke_width=1.2, dash_length=0.006,
        )

        # Delta label: between d=0 and d=delta on left side of d-axis
        delta_label_pos = tc + d_dir * (delta * 0.5) - x_dir * 0.035
        delta_label = Tex(r"$\delta$", color=YELLOW, font_size=26).move_to(
            delta_label_pos,
        )
        self.add_fixed_orientation_mobjects(delta_label)

        # Small tick at d=delta on d-axis
        tick_delta = Line(
            delta_pt_on_axis - x_dir * 0.008,
            delta_pt_on_axis + x_dir * 0.008,
            color=WHITE, stroke_width=1.5,
        )

        self.play(Create(exp_curve), run_time=2)
        self.play(
            Create(dashed_line),
            FadeIn(tick_delta),
            FadeIn(delta_label),
            run_time=1.5,
        )
        self.next_slide()

        # =================================================================
        # SLIDE 7: FDTD voxels between d=0 and d=delta
        # =================================================================
        n_voxels = 10
        delta_x = delta / n_voxels  # voxel size along d
        voxel_width = 0.04  # wider in x for visibility

        voxels = VGroup()
        for i in range(n_voxels):
            d_start = i * delta_x
            d_end = (i + 1) * delta_x
            c0 = tc + d_dir * d_start - x_dir * voxel_width * 0.5
            c1 = tc + d_dir * d_end - x_dir * voxel_width * 0.5
            c2 = tc + d_dir * d_end + x_dir * voxel_width * 0.5
            c3 = tc + d_dir * d_start + x_dir * voxel_width * 0.5

            voxel = Polygon(
                c0, c1, c2, c3,
                fill_color=ORANGE,
                fill_opacity=0.25,
                stroke_color=ORANGE,
                stroke_width=1.2,
            )
            voxels.add(voxel)

        # Delta_x label: to the right of the voxels, midway up
        dx_label_pos = tc + d_dir * (delta_x * 2.5) + x_dir * (voxel_width * 0.5 + 0.02)
        dx_label = Tex(r"$\Delta x$", color=ORANGE, font_size=18).move_to(
            dx_label_pos,
        )
        self.add_fixed_orientation_mobjects(dx_label)

        # Equation: placed to the right, clear of the diagram
        eq_pos = tc + x_dir * (amp_scale + 0.05) + d_dir * (delta * 0.4)
        equation = Tex(
            r"$\Delta x = \delta / 10$",
            color=WHITE, font_size=18,
        ).move_to(eq_pos)
        self.add_fixed_orientation_mobjects(equation)

        self.play(
            LaggedStart(
                *[FadeIn(v, scale=0.8) for v in voxels],
                lag_ratio=0.08,
            ),
            run_time=2,
        )
        self.play(FadeIn(dx_label), FadeIn(equation), run_time=1)
        self.next_slide()

        self.wait(1)
