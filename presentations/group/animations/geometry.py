"""Animation 2: Geometry of absorption.

Equation built term by term. Body cross-section with normals.
Surface heatmap (arc segments). Shadow projection. Wave direction
rotation. Cauchy formula.

Render: manim-slides render animations/geometry.py GeometryOfAbsorption
"""

import numpy as np
from manim import *
from manim_slides import Slide

# ---------- semantic palette (matches Beamer) ----------
SINC_BLUE = "#3264AA"
T0_RED = "#B41E1E"
GEOM_GREEN = "#006E37"
WAVE_GOLD = "#DDAA22"
DIM = "#555555"
LABEL_GRAY = "#999999"


class GeometryOfAbsorption(Slide):
    def construct(self):
        # ============================================================
        # PART 1: Build the equation term by term
        # ============================================================
        eq_parts = [
            MathTex(r"S_{\mathrm{ab}}(\mathbf{r})", font_size=36, color=WHITE),
            MathTex(r"=", font_size=36, color=WHITE),
            MathTex(r"S_{\mathrm{inc}}", font_size=36, color=SINC_BLUE),
            MathTex(r"\cdot", font_size=36, color=WHITE),
            MathTex(r"T_0", font_size=36, color=T0_RED),
            MathTex(r"\cdot", font_size=36, color=WHITE),
            MathTex(
                r"\mathrm{ReLU}\!\bigl[\hat{\mathbf{n}}\!\cdot\!(-\hat{\mathbf{k}})\bigr]",
                font_size=36, color=GEOM_GREEN,
            ),
        ]

        eq_group = VGroup(*eq_parts).arrange(RIGHT, buff=0.12)
        eq_group.to_edge(UP, buff=0.5)

        # Write each piece sequentially with pauses
        self.play(Write(eq_parts[0]), run_time=1.0)
        self.play(Write(eq_parts[1]), run_time=0.4)
        self.wait(0.5)
        self.play(Write(eq_parts[2]), run_time=1.0)
        self.wait(1.0)
        self.play(Write(eq_parts[3]), run_time=0.3)
        self.play(Write(eq_parts[4]), run_time=1.0)
        self.wait(1.0)
        self.play(Write(eq_parts[5]), run_time=0.3)
        self.play(Write(eq_parts[6]), run_time=1.2)
        self.wait(3.0)
        self.next_slide()  # --- SLIDE: equation built ---

        # Shrink equation and move to top-left corner
        self.play(
            eq_group.animate.scale(0.65).to_corner(UL, buff=0.3),
            run_time=1.0,
        )
        self.wait(1.0)

        # ============================================================
        # PART 2: Body cross-section + wave
        # ============================================================
        # Elliptical body cross-section
        body = Ellipse(
            width=3.0, height=4.0,
            color=WHITE, stroke_width=3,
        ).shift(DOWN * 0.3)

        # Incoming wave arrow -- further left and shorter to avoid overlap
        wave_start = LEFT * 6.5 + DOWN * 0.3
        wave_end = LEFT * 4.0 + DOWN * 0.3
        wave_arrow = Arrow(
            wave_start, wave_end,
            color=WAVE_GOLD, stroke_width=4, buff=0,
            max_tip_length_to_length_ratio=0.2,
        )
        k_label = MathTex(
            r"\hat{\mathbf{k}}", font_size=28, color=WAVE_GOLD,
        ).next_to(wave_arrow, UP, buff=0.1)

        self.play(Create(body), run_time=1.5)
        self.wait(1.0)
        self.play(GrowArrow(wave_arrow), Write(k_label), run_time=1.0)
        self.wait(2.0)
        self.next_slide()  # --- SLIDE: body + wave appear ---

        # ============================================================
        # PART 3: Normal arrows grow from lit side
        # ============================================================
        # Wave direction (unit vector pointing right, i.e. k_hat = (1, 0))
        k_hat = np.array([1.0, 0.0, 0.0])

        # Sample points on ellipse and compute normals
        n_normals = 24
        normal_arrows = VGroup()
        relu_dots = VGroup()

        for i in range(n_normals):
            t = i / n_normals * TAU
            # Point on ellipse
            px = 1.5 * np.cos(t)
            py = 2.0 * np.sin(t)
            point = np.array([px, py - 0.3, 0])

            # Outward normal on ellipse (not unit, but proportional)
            nx = 2.0 * np.cos(t)  # partial: x / a^2
            ny = 1.5 * np.sin(t)  # partial: y / b^2
            n_len = np.sqrt(nx**2 + ny**2)
            n_unit = np.array([nx / n_len, ny / n_len, 0])

            # ReLU[n . (-k)]
            cos_val = float(np.dot(n_unit, -k_hat))
            relu_val = max(0, cos_val)

            if relu_val > 0.02:
                arrow_len = relu_val * 1.2
                arr = Arrow(
                    point, point + n_unit * arrow_len,
                    color=GEOM_GREEN, stroke_width=2.5,
                    buff=0, max_tip_length_to_length_ratio=0.2,
                )
                normal_arrows.add(arr)
            elif abs(cos_val) < 0.15:
                # ReLU boundary point
                dot = Dot(point, color=T0_RED, radius=0.06)
                relu_dots.add(dot)

        # Grow normals with LaggedStart
        self.play(
            LaggedStart(
                *[GrowArrow(a) for a in normal_arrows],
                lag_ratio=0.08,
                run_time=4.0,
            ),
        )
        self.wait(1.5)

        # Mark ReLU boundary
        if len(relu_dots) > 0:
            self.play(
                FadeIn(relu_dots),
                run_time=0.5,
            )

        relu_boundary_label = Tex(
            r"ReLU boundary", font_size=20, color=T0_RED,
        )
        if len(relu_dots) > 0:
            relu_boundary_label.next_to(relu_dots[0], RIGHT, buff=0.2)
        else:
            relu_boundary_label.next_to(body, RIGHT, buff=0.5)
        self.play(FadeIn(relu_boundary_label), run_time=0.5)
        self.wait(2.5)
        self.next_slide()  # --- SLIDE: normals grown ---

        # ============================================================
        # PART 4: Surface heatmap -- colored arc segments along surface
        # ============================================================
        # Color the lit hemisphere with arc segments on the ellipse surface.
        # Color interpolates from bright green (facing the wave) to black
        # (at the ReLU boundary), proportional to cos(theta).
        n_segments = 40
        surface_arcs = VGroup()

        for i in range(n_segments):
            t1 = (i / n_segments) * TAU
            t2 = ((i + 1) / n_segments) * TAU
            t_mid = (t1 + t2) / 2

            # Normal at midpoint
            nx = 2.0 * np.cos(t_mid)
            ny = 1.5 * np.sin(t_mid)
            n_len = np.sqrt(nx**2 + ny**2)
            n_unit = np.array([nx / n_len, ny / n_len, 0])

            cos_val = max(0, float(np.dot(n_unit, -k_hat)))

            # Points on the ellipse for this segment
            p1 = np.array([1.5 * np.cos(t1), 2.0 * np.sin(t1) - 0.3, 0])
            p2 = np.array([1.5 * np.cos(t2), 2.0 * np.sin(t2) - 0.3, 0])

            if cos_val > 0.01:
                # Interpolate color from black to GEOM_GREEN based on cos_val
                seg_color = interpolate_color(BLACK, ManimColor(GEOM_GREEN), cos_val)
                segment = Line(
                    p1, p2,
                    color=seg_color,
                    stroke_width=8,
                    stroke_opacity=0.8 + 0.2 * cos_val,
                )
                surface_arcs.add(segment)

        self.play(
            LaggedStart(
                *[Create(seg) for seg in surface_arcs],
                lag_ratio=0.03,
                run_time=2.5,
            ),
        )
        self.wait(2.5)
        self.next_slide()  # --- SLIDE: surface heatmap shown ---

        # ============================================================
        # PART 5: Shadow projection
        # ============================================================
        self.play(
            FadeOut(normal_arrows), FadeOut(relu_dots),
            FadeOut(relu_boundary_label), FadeOut(surface_arcs),
            run_time=0.8,
        )
        self.wait(1.0)

        # Parallel rays from left
        ray_ys = np.linspace(-2.5, 2.0, 12)
        rays_hit = VGroup()
        rays_miss = VGroup()

        for ry in ray_ys:
            start = np.array([-5.5, ry, 0])
            # Check if ray at height ry hits the ellipse
            # Ellipse: (x/1.5)^2 + ((y+0.3)/2.0)^2 = 1
            y_ell = ry + 0.3  # shift
            if abs(y_ell / 2.0) < 1.0:
                # Hits the ellipse
                x_hit = -1.5 * np.sqrt(1 - (y_ell / 2.0) ** 2)
                end = np.array([x_hit, ry, 0])
                ray = Line(
                    start, end,
                    color=T0_RED, stroke_width=1.5, stroke_opacity=0.6,
                )
                rays_hit.add(ray)
            else:
                # Misses
                end = np.array([5.5, ry, 0])
                ray = Line(
                    start, end,
                    color=DIM, stroke_width=1, stroke_opacity=0.3,
                )
                rays_miss.add(ray)

        self.play(
            LaggedStart(
                *[Create(r) for r in rays_hit],
                *[Create(r) for r in rays_miss],
                lag_ratio=0.05, run_time=2.0,
            ),
        )
        self.wait(1.5)

        # Shadow bar on the right
        shadow_top = body.get_top()[1]
        shadow_bot = body.get_bottom()[1]
        shadow_bar = Line(
            np.array([4.0, shadow_top, 0]),
            np.array([4.0, shadow_bot, 0]),
            color=WAVE_GOLD, stroke_width=6,
        )
        shadow_label = MathTex(
            r"A_\perp(\hat{\mathbf{k}})", font_size=28, color=WAVE_GOLD,
        ).next_to(shadow_bar, RIGHT, buff=0.2)

        self.play(
            Create(shadow_bar),
            Write(shadow_label),
            run_time=1.2,
        )
        self.wait(2.0)

        # Power equation
        power_eq = MathTex(
            r"P_{\mathrm{abs}} = ",
            r"S_{\mathrm{inc}}",
            r"\cdot",
            r"T_0",
            r"\cdot",
            r"A_\perp(\hat{\mathbf{k}})",
            font_size=36, color=WHITE,
        ).to_edge(DOWN, buff=0.6)
        power_eq[1].set_color(SINC_BLUE)
        power_eq[3].set_color(T0_RED)
        power_eq[5].set_color(WAVE_GOLD)

        self.play(Write(power_eq), run_time=1.5)
        self.wait(3.0)
        self.next_slide()  # --- SLIDE: shadow projection ---

        # ============================================================
        # PART 6: Wave direction rotates
        # ============================================================
        # Clean up rays for rotation
        self.play(
            FadeOut(rays_hit), FadeOut(rays_miss),
            FadeOut(shadow_bar), FadeOut(shadow_label),
            FadeOut(wave_arrow), FadeOut(k_label),
            FadeOut(power_eq),
            run_time=0.8,
        )
        self.wait(1.0)

        # Rotating wave direction with updating normals
        angle_tracker = ValueTracker(0)  # radians, 0 = from left

        def get_wave_arrow():
            a = angle_tracker.get_value()
            direction = np.array([np.cos(a), np.sin(a), 0])
            start_pt = -direction * 4.5 + np.array([0, -0.3, 0])
            end_pt = -direction * 2.0 + np.array([0, -0.3, 0])
            return Arrow(
                start_pt, end_pt,
                color=WAVE_GOLD, stroke_width=4, buff=0,
                max_tip_length_to_length_ratio=0.15,
            )

        def get_normals():
            a = angle_tracker.get_value()
            k = np.array([np.cos(a), np.sin(a), 0])
            grp = VGroup()
            for i in range(20):
                t = i / 20 * TAU
                px = 1.5 * np.cos(t)
                py = 2.0 * np.sin(t)
                point = np.array([px, py - 0.3, 0])
                nx_val = 2.0 * np.cos(t)
                ny_val = 1.5 * np.sin(t)
                n_len = np.sqrt(nx_val**2 + ny_val**2)
                n_unit = np.array([nx_val / n_len, ny_val / n_len, 0])
                cos_val = max(0, float(np.dot(n_unit, -k)))
                if cos_val > 0.05:
                    arr = Arrow(
                        point, point + n_unit * cos_val * 1.0,
                        color=GEOM_GREEN, stroke_width=2, buff=0,
                        max_tip_length_to_length_ratio=0.25,
                    )
                    grp.add(arr)
            return grp

        rotating_arrow = always_redraw(get_wave_arrow)
        rotating_normals = always_redraw(get_normals)

        self.add(rotating_arrow, rotating_normals)

        # Rotate from 0 (left) through PI/3 (top-left) to -PI/4 (bottom-left)
        self.play(
            angle_tracker.animate.set_value(PI / 3),
            run_time=3.0, rate_func=smooth,
        )
        self.wait(1.0)
        self.play(
            angle_tracker.animate.set_value(-PI / 4),
            run_time=3.0, rate_func=smooth,
        )
        self.wait(1.0)
        self.play(
            angle_tracker.animate.set_value(0),
            run_time=2.0, rate_func=smooth,
        )
        self.wait(2.0)
        self.next_slide()  # --- SLIDE: wave rotation done ---

        # ============================================================
        # PART 7: Direction averaging and Cauchy
        # ============================================================
        self.remove(rotating_arrow, rotating_normals)

        # Show many wave directions as thin arrows from all sides
        dir_arrows = VGroup()
        for i in range(16):
            a = i / 16 * TAU
            direction = np.array([np.cos(a), np.sin(a), 0])
            start_pt = -direction * 3.5 + np.array([0, -0.3, 0])
            end_pt = -direction * 2.0 + np.array([0, -0.3, 0])
            arr = Arrow(
                start_pt, end_pt,
                color=WAVE_GOLD, stroke_width=2, buff=0,
                max_tip_length_to_length_ratio=0.2,
                stroke_opacity=0.5,
            )
            dir_arrows.add(arr)

        self.play(
            LaggedStart(
                *[GrowArrow(a) for a in dir_arrows],
                lag_ratio=0.05, run_time=1.5,
            ),
        )
        self.wait(2.0)

        # Average annotation
        avg_text = Tex(
            r"Average over all directions:",
            font_size=28, color=LABEL_GRAY,
        ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(avg_text), run_time=0.6)
        self.wait(1.5)
        self.next_slide()  # --- SLIDE: all directions shown ---

        # Slide body + arrows to the right to make room for formula
        body_group = VGroup(body, dir_arrows, eq_group)
        self.play(
            body_group.animate.shift(RIGHT * 2.5),
            FadeOut(avg_text),
            run_time=1.5,
        )
        self.wait(1.0)

        # Cauchy formula on the left side
        cauchy = MathTex(
            r"\langle P_{\mathrm{abs}} \rangle = ",
            r"S_{\mathrm{inc}}",
            r"\cdot",
            r"T_0",
            r"\cdot",
            r"\frac{A_{\mathrm{ab}}}{4}",
            font_size=36, color=WHITE,
        ).shift(LEFT * 3.5 + DOWN * 0.3)
        cauchy[1].set_color(SINC_BLUE)
        cauchy[3].set_color(T0_RED)
        cauchy[5].set_color(GEOM_GREEN)

        self.play(Write(cauchy), run_time=2.0)
        self.wait(3.0)

        # Highlight result
        self.play(
            Circumscribe(cauchy, color=YELLOW, buff=0.1, run_time=1.5),
        )
        self.wait(2.0)

        # Cauchy attribution with portrait
        cauchy_img = ImageMobject(
            "figures/cauchy.jpg",
        ).scale_to_fit_height(1.2).next_to(cauchy, DOWN, buff=0.3).shift(LEFT * 0.5)
        cauchy_attr = Tex(
            r"Cauchy, 1841.", font_size=20, color=DIM,
        ).next_to(cauchy_img, RIGHT, buff=0.2)
        self.play(FadeIn(cauchy_img), FadeIn(cauchy_attr), run_time=0.8)
        self.wait(3.0)
        self.next_slide()  # --- SLIDE: Cauchy formula + body (FINAL) ---

        # This final state stays visible until the presenter clicks.
        # The formula on the left, the body with all-direction arrows on the right.
        self.wait(0.5)
