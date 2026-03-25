"""
Geometric Dosimetry — 15-minute group presentation.

Build:  manim-slides render -qh slides.py GroupTalk
Present: manim-slides present GroupTalk
Export:  manim-slides convert GroupTalk talk.html --one-file --offline
PDF:    manim-slides convert --to=pdf GroupTalk talk.pdf
"""

from manim import *
from manim_slides import Slide
import numpy as np

# ================================================================
# Color palette (matching promotor presentation)
# ================================================================
NAVY = ManimColor("#193764")
MEDBLUE = ManimColor("#3264AA")
LIGHTBLUE = ManimColor("#DCebFA")
ALERTRED = ManimColor("#B41E1E")
RESULTGREEN = ManimColor("#006E37")
DIMGRAY = ManimColor("#3C3C3C")
SKIN_BLUE = ManimColor("#4488CC")
SKIN_RED = ManimColor("#CC4444")
SKIN_GREEN = ManimColor("#44AA44")

# ================================================================
# Utilities
# ================================================================

def result_box(content: Mobject, title: str = None, width: float = 11) -> VGroup:
    """Create a result box similar to Beamer tcolorbox."""
    box = SurroundingRectangle(
        content, color=NAVY, buff=0.25,
        corner_radius=0.08, stroke_width=2,
    )
    # Light blue fill
    bg = box.copy().set_fill(LIGHTBLUE, opacity=0.3).set_stroke(width=0)
    group = VGroup(bg, box, content)
    if title:
        label = Tex(r"\textbf{" + title + "}", font_size=20, color=WHITE)
        label_bg = SurroundingRectangle(
            label, color=NAVY, buff=0.1,
            corner_radius=0.05, stroke_width=0,
        ).set_fill(NAVY, opacity=1)
        label_group = VGroup(label_bg, label)
        label_group.next_to(box, UP, buff=0).align_to(box, LEFT).shift(RIGHT * 0.2)
        group.add(label_group)
    return group


def slide_title(text: str) -> Tex:
    """Standard slide title."""
    return Tex(r"\textbf{" + text + "}", font_size=36, color=NAVY).to_edge(UP, buff=0.4)


def footer_text(text: str) -> Tex:
    """Small footer."""
    return Tex(text, font_size=14, color=DIMGRAY).to_edge(DOWN, buff=0.15)


# ================================================================
# Main presentation
# ================================================================

class GroupTalk(Slide):
    def construct(self):
        self.camera.background_color = WHITE

        self.slide_00_title()
        self.slide_01_problem()
        self.slide_02_key_equation()
        self.slide_03_pseudo_brewster()
        self.slide_04_geometric_law()
        self.slide_05_geometry_animation()
        self.slide_06_relu_network()
        self.slide_07_validation()
        self.slide_08_demo_card()
        self.slide_09_coherent_bridge()
        self.slide_10_coherent_hotspot()
        self.slide_11_ecbf()
        self.slide_12_summary()
        self.slide_13_thankyou()

    # ============================================================
    # SLIDE 0: Title
    # ============================================================
    def slide_00_title(self):
        title = Tex(
            r"\textbf{Geometric Dosimetry}",
            font_size=52, color=NAVY,
        )
        subtitle = Tex(
            r"Closed-form absorption laws\\from 100 MHz to 100 GHz",
            font_size=28, color=DIMGRAY,
        )
        author = Tex(r"Robin Wydaeghe", font_size=22, color=DIMGRAY)
        affil = Tex(r"Ghent University \& imec", font_size=18, color=DIMGRAY)

        group = VGroup(title, subtitle, author, affil).arrange(DOWN, buff=0.4)

        self.play(FadeIn(title, shift=DOWN * 0.3), run_time=0.8)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.5)
        self.play(FadeIn(VGroup(author, affil), shift=UP * 0.1), run_time=0.4)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.4)

    # ============================================================
    # SLIDE 1: The problem
    # ============================================================
    def slide_01_problem(self):
        title = slide_title("FDTD at millimetre-wave is intractable")

        # Scale mismatch visual
        body_line = Line(DOWN * 2, UP * 2, color=NAVY, stroke_width=4)
        body_label = Tex(r"$\sim$1 m", font_size=18, color=NAVY).next_to(body_line, RIGHT, buff=0.15)

        skin_rect = Rectangle(
            width=0.08, height=0.06, color=ALERTRED,
            fill_color=ALERTRED, fill_opacity=0.4,
        ).move_to(body_line.get_top() + RIGHT * 0.04)
        skin_label = Tex(r"$\delta \approx 0.3$ mm", font_size=14, color=ALERTRED).next_to(skin_rect, RIGHT, buff=0.15)
        ratio_text = Tex(r"5 orders of magnitude", font_size=16, color=DIMGRAY).next_to(body_line, LEFT, buff=0.3)

        figure = VGroup(body_line, body_label, skin_rect, skin_label, ratio_text)
        figure.move_to(RIGHT * 3.5 + DOWN * 0.2)

        # Bullets
        bullets = VGroup(
            Tex(r"Body: $\sim$1 m.  Skin depth at 28 GHz: 0.3 mm.", font_size=22, color=BLACK),
            Tex(r"FDTD mesh: $\sim 10^{12}$ cells per simulation.", font_size=22, color=BLACK),
            Tex(r"One plane wave, one phantom: weeks of GPU.", font_size=22, color=BLACK),
            Tex(r"Parametric study (550 runs): months.", font_size=22, color=BLACK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        bullets.move_to(LEFT * 2.5 + DOWN * 0.2)

        # Result box
        punch = Tex(
            r"We replace the volumetric simulation\\with surface-level geometric operations.",
            font_size=20, color=BLACK,
        )
        box = result_box(punch)
        box.to_edge(DOWN, buff=0.6)

        self.play(FadeIn(title), run_time=0.3)
        self.play(
            LaggedStart(
                *[FadeIn(b, shift=RIGHT * 0.2) for b in bullets],
                lag_ratio=0.2,
            ),
            FadeIn(figure),
            run_time=1.5,
        )
        self.play(FadeIn(box, shift=UP * 0.2), run_time=0.5)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 2: Key equation (first pass)
    # ============================================================
    def slide_02_key_equation(self):
        title = slide_title("Exact absorption law")

        eq = MathTex(
            r"S_{\mathrm{ab}}(\mathbf{r})",
            r"=",
            r"S_{\mathrm{inc}}",
            r"\cdot",
            r"T_{\mathrm{eff}}(\mathbf{r})",
            r"\cdot",
            r"\mathrm{ReLU}\!\bigl[\hat{\mathbf{n}}(\mathbf{r})\cdot(-\hat{\mathbf{k}})\bigr]",
            font_size=40, color=BLACK,
        )

        # Labels for each factor
        label_sinc = Tex(r"Environment", font_size=18, color=MEDBLUE)
        label_teff = Tex(r"Material", font_size=18, color=ALERTRED)
        label_relu = Tex(r"Geometry", font_size=18, color=RESULTGREEN)

        brace_sinc = Brace(eq[2], DOWN, color=MEDBLUE, buff=0.1)
        brace_teff = Brace(eq[4], DOWN, color=ALERTRED, buff=0.1)
        brace_relu = Brace(eq[6], DOWN, color=RESULTGREEN, buff=0.1)

        label_sinc.next_to(brace_sinc, DOWN, buff=0.08)
        label_teff.next_to(brace_teff, DOWN, buff=0.08)
        label_relu.next_to(brace_relu, DOWN, buff=0.08)

        eq_group = VGroup(eq, brace_sinc, label_sinc, brace_teff, label_teff, brace_relu, label_relu)
        eq_group.move_to(ORIGIN + UP * 0.3)

        note = Tex(
            r"Exact under locally flat surface assumption. Any polarisation, any frequency.",
            font_size=16, color=DIMGRAY,
        ).to_edge(DOWN, buff=0.8)

        self.play(FadeIn(title), run_time=0.3)
        self.play(Write(eq), run_time=1.5)
        self.next_slide()

        self.play(
            GrowFromCenter(brace_sinc), FadeIn(label_sinc),
            GrowFromCenter(brace_teff), FadeIn(label_teff),
            GrowFromCenter(brace_relu), FadeIn(label_relu),
            run_time=0.8,
        )
        self.play(FadeIn(note), run_time=0.3)
        self.next_slide()

        # Highlight the material factor
        highlight = SurroundingRectangle(
            VGroup(eq[4], brace_teff, label_teff),
            color=ALERTRED, buff=0.15, stroke_width=3,
        )
        question = Tex(
            r"\textbf{What happens to this term?}",
            font_size=20, color=ALERTRED,
        ).next_to(highlight, RIGHT, buff=0.3)

        self.play(Create(highlight), FadeIn(question), run_time=0.6)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 3: Pseudo-Brewster compensation (HERO ANIMATION 1)
    # ============================================================
    def slide_03_pseudo_brewster(self):
        title = slide_title("Pseudo-Brewster compensation")

        # Create axes
        ax = Axes(
            x_range=[0, 90, 15],
            y_range=[0, 1.05, 0.2],
            x_length=8,
            y_length=4.5,
            axis_config={"color": DIMGRAY, "stroke_width": 1.5, "include_numbers": True,
                         "font_size": 18},
            tips=False,
        ).move_to(DOWN * 0.3)

        x_label = ax.get_x_axis_label(
            MathTex(r"\theta\;(^\circ)", font_size=22, color=DIMGRAY),
            edge=DOWN, direction=DOWN,
        )
        y_label = ax.get_y_axis_label(
            MathTex(r"T(\theta)", font_size=22, color=DIMGRAY),
            edge=LEFT, direction=LEFT,
        )

        # Fresnel curves for skin at 28 GHz
        # Tissue: eps_r=17, sigma=25 S/m => n_tilde = 4.49 - 1.79j, |n_tilde| = 4.84
        # Formulas from monograph Eqs. (rs), (rp), (Ts-Tp): T_q = 1 - |r_q|^2
        n_tilde = 4.4933 - 1.7859j  # sqrt(eps_r - j*sigma/(omega*eps_0))
        n2 = n_tilde**2

        def _fresnel_xi(mu):
            """Normal wave-vector component in tissue: xi = sqrt(n^2 - 1 + mu^2)."""
            xi = np.sqrt(n2 - 1 + mu**2)
            return -xi if xi.real < 0 else xi

        def fresnel_Ts(theta_deg):
            mu = np.cos(np.radians(theta_deg))
            xi = _fresnel_xi(mu)
            r_s = (mu - xi) / (mu + xi)
            return float(np.clip(1 - abs(r_s) ** 2, 0, 1))

        def fresnel_Tp(theta_deg):
            mu = np.cos(np.radians(theta_deg))
            xi = _fresnel_xi(mu)
            r_p = (n2 * mu - xi) / (n2 * mu + xi)
            return float(np.clip(1 - abs(r_p) ** 2, 0, 1))

        def fresnel_Tavg(theta_deg):
            return (fresnel_Ts(theta_deg) + fresnel_Tp(theta_deg)) / 2

        T0 = fresnel_Tavg(0)

        # Create curves
        ts_curve = ax.plot(
            fresnel_Ts, x_range=[0.1, 85, 0.5],
            color=SKIN_BLUE, stroke_width=3,
        )
        tp_curve = ax.plot(
            fresnel_Tp, x_range=[0.1, 85, 0.5],
            color=SKIN_RED, stroke_width=3,
        )
        tavg_curve = ax.plot(
            fresnel_Tavg, x_range=[0.1, 85, 0.5],
            color=SKIN_GREEN, stroke_width=3,
        )

        # T_0 horizontal line
        t0_line = ax.plot(
            lambda x: T0, x_range=[0, 85, 1],
            color=SKIN_GREEN, stroke_width=2,
        ).set_stroke(opacity=0.5)
        t0_dashed = DashedVMobject(t0_line, num_dashes=40)

        # Labels
        ts_label = MathTex(r"T_s(\theta)", font_size=22, color=SKIN_BLUE)
        tp_label = MathTex(r"T_p(\theta)", font_size=22, color=SKIN_RED)
        tavg_label = MathTex(r"T_{\mathrm{avg}}(\theta)", font_size=22, color=SKIN_GREEN)

        ts_label.next_to(ax.c2p(70, fresnel_Ts(70)), UP, buff=0.15)
        tp_label.next_to(ax.c2p(55, fresnel_Tp(55)), UP, buff=0.15)
        tavg_label.next_to(ax.c2p(40, fresnel_Tavg(40)), UP, buff=0.2)

        # T_0 label
        t0_label = MathTex(r"T_0", font_size=22, color=SKIN_GREEN)
        t0_label.next_to(ax.c2p(0, T0), LEFT, buff=0.2)

        self.play(FadeIn(title), run_time=0.3)
        self.play(Create(ax), FadeIn(x_label), FadeIn(y_label), run_time=0.8)
        self.next_slide()

        # Draw T_s
        self.play(Create(ts_curve), FadeIn(ts_label), run_time=1.2)
        self.next_slide()

        # Draw T_p
        self.play(Create(tp_curve), FadeIn(tp_label), run_time=1.2)
        self.next_slide()

        # Draw T_avg
        self.play(Create(tavg_curve), FadeIn(tavg_label), run_time=1.2)
        self.play(Create(t0_dashed), FadeIn(t0_label), run_time=0.6)
        self.next_slide()

        # Annotation: variation < 6%
        var_text = Tex(
            r"Variation $<$ 6\% up to $75^\circ$",
            font_size=18, color=DIMGRAY,
        ).next_to(ax, DOWN, buff=0.3)

        azzam_text = Tex(
            r"Holds for $|\tilde{n}| > 2.5$ (Azzam, 2015).  Biological tissue: $|\tilde{n}| \approx 3$--$6$.",
            font_size=16, color=DIMGRAY,
        ).next_to(var_text, DOWN, buff=0.1)

        self.play(FadeIn(var_text), FadeIn(azzam_text), run_time=0.5)
        self.next_slide()

        # Collapse: fade T_s and T_p, morph T_avg to flat line
        collapse_text = Tex(
            r"\textbf{Material collapses to one number: $T_0$}",
            font_size=26, color=NAVY,
        ).move_to(UP * 2.7 + RIGHT * 1)

        self.play(
            FadeOut(ts_curve, ts_label, tp_curve, tp_label),
            tavg_curve.animate.set_stroke(opacity=0.3),
            FadeIn(collapse_text, shift=DOWN * 0.2),
            run_time=1.0,
        )
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 4: Geometric absorption law
    # ============================================================
    def slide_04_geometric_law(self):
        title = slide_title("The geometric absorption law")

        eq = MathTex(
            r"S_{\mathrm{ab}}(\mathbf{r})",
            r"\approx",
            r"S_{\mathrm{inc}}",
            r"\cdot\;",
            r"T_0",
            r"\;\cdot\;",
            r"\mathrm{ReLU}\!\bigl[\hat{\mathbf{n}}(\mathbf{r})\cdot(-\hat{\mathbf{k}})\bigr]",
            font_size=42, color=BLACK,
        )

        # Highlight T_0
        box_t0 = SurroundingRectangle(eq[4], color=RESULTGREEN, buff=0.1, stroke_width=2)

        label_before = MathTex(
            r"\text{Before: } T_{\mathrm{eff}}(\theta,\,\text{pol},\,\text{tissue},\,f)",
            font_size=24, color=DIMGRAY,
        )
        label_after = MathTex(
            r"\text{After: } T_0 \;\text{(one number)}",
            font_size=24, color=RESULTGREEN,
        )

        comparison = VGroup(label_before, label_after).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        comparison.next_to(eq, DOWN, buff=0.6)

        keypoint = Tex(
            r"\textbf{All spatial variation is determined by the body's shape.}",
            font_size=22, color=NAVY,
        ).next_to(comparison, DOWN, buff=0.5)

        rbox = result_box(eq)
        rbox.move_to(UP * 0.5)

        self.play(FadeIn(title), run_time=0.3)
        self.play(FadeIn(rbox), run_time=0.8)
        self.play(Create(box_t0), run_time=0.4)
        self.next_slide()

        self.play(FadeIn(comparison, shift=UP * 0.2), run_time=0.6)
        self.play(FadeIn(keypoint, shift=UP * 0.2), run_time=0.5)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 5: Dosimetry is geometry (HERO ANIMATION 2)
    # ============================================================
    def slide_05_geometry_animation(self):
        title = slide_title("Dosimetry is geometry")

        # Create a 2D cross-section of a body (ellipse) for clarity
        body = Ellipse(
            width=2.0, height=4.0, color=NAVY,
            fill_color=LIGHTBLUE, fill_opacity=0.3, stroke_width=2,
        ).move_to(LEFT * 1)

        # Wave direction arrow
        k_arrow = Arrow(
            start=LEFT * 5, end=LEFT * 3,
            color=MEDBLUE, stroke_width=3, buff=0,
        )
        k_label = MathTex(r"\hat{\mathbf{k}}", font_size=24, color=MEDBLUE).next_to(k_arrow, UP, buff=0.1)

        # Create normal vectors and illumination indicators
        n_angles = 16
        normals = []
        dots = []
        for i in range(n_angles):
            angle = i * TAU / n_angles
            point = body.point_at_angle(angle)
            normal_dir = np.array([np.cos(angle), np.sin(angle), 0])

            # cos(theta) with k_hat = LEFT means dot product with -k_hat = RIGHT
            cos_theta = np.dot(normal_dir, RIGHT)
            relu_val = max(0, cos_theta)

            color = interpolate_color(BLACK, ALERTRED, relu_val)
            if relu_val > 0.01:
                arrow = Arrow(
                    start=point, end=point + normal_dir * 0.5 * relu_val,
                    color=color, stroke_width=2, buff=0,
                    max_tip_length_to_length_ratio=0.3,
                )
                normals.append(arrow)

            dot = Dot(point, radius=0.05, color=color)
            dots.append(dot)

        normals_group = VGroup(*normals)
        dots_group = VGroup(*dots)

        # Shadow (projected area)
        shadow = Rectangle(
            width=0.1, height=4.0,
            color=DIMGRAY, fill_color=DIMGRAY, fill_opacity=0.2,
        ).move_to(RIGHT * 3)
        shadow_label = MathTex(
            r"A_\perp(\hat{\mathbf{k}})", font_size=22, color=DIMGRAY,
        ).next_to(shadow, RIGHT, buff=0.15)
        shadow_text = Tex(r"shadow area", font_size=16, color=DIMGRAY).next_to(shadow_label, DOWN, buff=0.05)

        # Equation
        eq_shadow = MathTex(
            r"P_{\mathrm{abs}} = S_{\mathrm{inc}} \cdot T_0 \cdot A_\perp(\hat{\mathbf{k}})",
            font_size=28, color=BLACK,
        ).move_to(DOWN * 2.8)

        self.play(FadeIn(title), run_time=0.3)
        self.play(FadeIn(body), Create(k_arrow), FadeIn(k_label), run_time=0.8)
        self.next_slide()

        # Show illumination pattern
        self.play(
            LaggedStart(*[FadeIn(d) for d in dots], lag_ratio=0.05),
            LaggedStart(*[GrowArrow(n) for n in normals], lag_ratio=0.05),
            run_time=1.2,
        )

        relu_note = Tex(
            r"Front-facing: $\cos \theta$.  Back-facing: 0 (ReLU gate).",
            font_size=18, color=DIMGRAY,
        ).move_to(DOWN * 2.2)
        self.play(FadeIn(relu_note), run_time=0.4)
        self.next_slide()

        # Shadow
        self.play(
            FadeIn(shadow, shift=RIGHT * 0.2),
            FadeIn(shadow_label),
            FadeIn(shadow_text),
            run_time=0.6,
        )
        self.play(
            FadeOut(relu_note),
            FadeIn(eq_shadow, shift=UP * 0.2),
            run_time=0.5,
        )
        self.next_slide()

        # Cauchy's formula
        self.play(FadeOut(shadow, shadow_label, shadow_text, eq_shadow, k_arrow, k_label,
                          normals_group, dots_group), run_time=0.3)

        cauchy_eq = MathTex(
            r"\langle P_{\mathrm{abs}} \rangle = S_{\mathrm{inc}} \cdot T_0 \cdot \frac{A_{\mathrm{ab}}}{4}",
            font_size=36, color=BLACK,
        )
        cauchy_box = result_box(cauchy_eq, title="Direction-averaged (Cauchy, 1841)")
        cauchy_box.move_to(RIGHT * 2.5 + DOWN * 0.3)

        ao_text = VGroup(
            Tex(r"Self-shadowing correction $\eta(\mathbf{r})$", font_size=20, color=NAVY),
            Tex(r"$\equiv$ ambient occlusion (GPU graphics)", font_size=20, color=DIMGRAY),
            Tex(r"Thelonious: $A_{\mathrm{ab}} / A \approx 0.87$", font_size=18, color=DIMGRAY),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        ao_text.next_to(cauchy_box, DOWN, buff=0.4)

        self.play(FadeIn(cauchy_box, shift=LEFT * 0.3), run_time=0.8)
        self.play(FadeIn(ao_text, shift=UP * 0.2), run_time=0.5)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 6: ReLU network
    # ============================================================
    def slide_06_relu_network(self):
        title = slide_title("Computational framework")

        eq = MathTex(
            r"\mathbf{S}_{\mathrm{ab}} = T_0 \;\mathrm{ReLU}(\mathbf{N}\,\mathbf{K}^\top)\;\mathbf{s}",
            font_size=40, color=BLACK,
        )
        eq_box = result_box(eq, title="Dosimetry as a ReLU neural network")
        eq_box.move_to(UP * 1.2)

        # Explanation columns
        left_items = VGroup(
            MathTex(r"\mathbf{N}", r"\in \mathbb{R}^{P \times 3}", r"\text{: surface normals (body mesh)}",
                    font_size=20, color=BLACK),
            MathTex(r"\mathbf{K}", r"\in \mathbb{R}^{N \times 3}", r"\text{: path directions (ray tracer)}",
                    font_size=20, color=BLACK),
            MathTex(r"\mathbf{s}", r"\in \mathbb{R}^{N}", r"\text{: path power densities}",
                    font_size=20, color=BLACK),
            Tex(r"ReLU: exact visibility gate", font_size=20, color=BLACK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        left_items.move_to(LEFT * 3 + DOWN * 1.2)

        right_items = VGroup(
            Tex(r"\textbf{Differentiable end-to-end.}", font_size=20, color=NAVY),
            Tex(r"Gradients of SAR w.r.t.\ antenna positions", font_size=18, color=BLACK),
            Tex(r"propagate by backpropagation.", font_size=18, color=BLACK),
            Tex(r"\phantom{x}", font_size=8),
            Tex(r"\textbf{$10^6\times$ speedup over FDTD.}", font_size=22, color=RESULTGREEN),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        right_items.move_to(RIGHT * 3 + DOWN * 1.2)

        self.play(FadeIn(title), run_time=0.3)
        self.play(FadeIn(eq_box), run_time=0.8)
        self.next_slide()

        self.play(
            FadeIn(left_items, shift=RIGHT * 0.2),
            FadeIn(right_items, shift=LEFT * 0.2),
            run_time=0.8,
        )
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 7: Validation
    # ============================================================
    def slide_07_validation(self):
        title = slide_title("Validation")

        # Two columns
        col_left_title = Tex(r"\textbf{Mie theory (exact for lossy spheres)}", font_size=20, color=NAVY)
        col_left_items = VGroup(
            Tex(r"Tests Fresnel + geometric optics jointly", font_size=18, color=BLACK),
            Tex(r"Body-scale at 28 GHz: $\sim$5--10\% error", font_size=18, color=BLACK),
            Tex(r"Dominated by diffraction into shadow", font_size=18, color=BLACK),
            Tex(r"Error is conservative (underestimates)", font_size=18, color=BLACK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        col_left = VGroup(col_left_title, col_left_items).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        col_left.move_to(LEFT * 3.2 + DOWN * 0.2)

        col_right_title = Tex(r"\textbf{Anatomical phantom (Thelonious)}", font_size=20, color=NAVY)
        col_right_items = VGroup(
            Tex(r"Total absorbed power error: 0.35\%", font_size=18, color=BLACK),
            Tex(r"Local RMS error: 3.2\%", font_size=18, color=BLACK),
            Tex(r"Isolates Fresnel from diffraction", font_size=18, color=BLACK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        col_right = VGroup(col_right_title, col_right_items).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        col_right.move_to(RIGHT * 3.2 + DOWN * 0.2)

        # Punchline
        punch = Tex(
            r"Framework error (5--15\%) $<$ tissue dielectric uncertainty ($\sim$20\%).\\The data is less accurate than the model.",
            font_size=20, color=BLACK,
        )
        punch_box = result_box(punch)
        punch_box.to_edge(DOWN, buff=0.5)

        self.play(FadeIn(title), run_time=0.3)
        self.play(FadeIn(col_left, shift=RIGHT * 0.2), FadeIn(col_right, shift=LEFT * 0.2), run_time=0.8)
        self.next_slide()

        self.play(FadeIn(punch_box, shift=UP * 0.2), run_time=0.5)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 8: Demo title card
    # ============================================================
    def slide_08_demo_card(self):
        aegis = Tex(r"\textbf{AEGIS}", font_size=72, color=NAVY)
        subtitle = Tex(
            r"Real-time geometric dosimetry",
            font_size=28, color=DIMGRAY,
        )
        features = Tex(
            r"3D viewer  $\cdot$  9 fidelity levels  $\cdot$  ray tracing  $\cdot$  ICNIRP compliance",
            font_size=18, color=DIMGRAY,
        )
        group = VGroup(aegis, subtitle, features).arrange(DOWN, buff=0.4)

        self.play(FadeIn(aegis, scale=1.2), run_time=0.8)
        self.play(FadeIn(subtitle, shift=UP * 0.2), FadeIn(features, shift=UP * 0.1), run_time=0.5)
        self.next_slide(
            notes="Switch to AEGIS viewer for live demo. ~2 minutes. "
                  "Show: heatmap, rotate source, multipath, compliance overlay, spatial averaging."
        )

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 9: Incoherent to coherent bridge
    # ============================================================
    def slide_09_coherent_bridge(self):
        title = slide_title("From incoherent to coherent")

        # Two columns
        left_title = Tex(r"\textbf{Parts I--II: powers add}", font_size=22, color=NAVY)
        left_eq = MathTex(
            r"S_{\mathrm{ab}} = T_0 \sum_i S_i \,\mathrm{ReLU}(\mu_i)",
            font_size=24, color=BLACK,
        )
        left_col = VGroup(left_title, left_eq).arrange(DOWN, buff=0.2)

        right_title = Tex(r"\textbf{Part III: fields add}", font_size=22, color=ALERTRED)
        right_eq = MathTex(
            r"\mathbf{E}_{\mathrm{total}} = \sum_m x_m \,\mathbf{E}_m",
            font_size=24, color=BLACK,
        )
        right_note = Tex(r"Coherent peak: $N\times$ incoherent", font_size=18, color=ALERTRED)
        right_col = VGroup(right_title, right_eq, right_note).arrange(DOWN, buff=0.15)

        cols = VGroup(left_col, right_col).arrange(RIGHT, buff=1.5)
        cols.move_to(UP * 1)

        # Branch diagram
        branch_title = Tex(r"\textbf{Two branches diverge:}", font_size=20, color=NAVY)
        signal = MathTex(
            r"\text{Signal at UE: } y = \mathbf{h}^\top \mathbf{x} \in \mathbb{C}",
            font_size=22, color=MEDBLUE,
        )
        exposure = MathTex(
            r"\text{Exposure on body: } \tilde{\mathbf{G}}(\mathbf{r})\,\mathbf{x} \in \mathbb{C}^3",
            font_size=22, color=ALERTRED,
        )
        signal_note = Tex(r"scalars sum", font_size=16, color=MEDBLUE)
        exposure_note = Tex(r"vectors sum", font_size=16, color=ALERTRED)

        signal_row = VGroup(signal, signal_note).arrange(RIGHT, buff=0.3)
        exposure_row = VGroup(exposure, exposure_note).arrange(RIGHT, buff=0.3)

        branch = VGroup(branch_title, signal_row, exposure_row).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        branch.move_to(DOWN * 1.2)

        punchline = Tex(
            r"Signal branch collapses to a scalar. Exposure branch retains the full vector structure.\\This is why signal quality and body absorption can decouple.",
            font_size=18, color=DIMGRAY,
        ).to_edge(DOWN, buff=0.4)

        self.play(FadeIn(title), run_time=0.3)
        self.play(FadeIn(left_col, shift=RIGHT * 0.2), FadeIn(right_col, shift=LEFT * 0.2), run_time=0.8)
        self.next_slide()

        self.play(FadeIn(branch, shift=UP * 0.2), run_time=0.8)
        self.play(FadeIn(punchline), run_time=0.4)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 10: Coherent hotspot (HERO ANIMATION 3)
    # ============================================================
    def slide_10_coherent_hotspot(self):
        title = slide_title("Coherent hotspot formation")

        # Show phasors at a body point
        # Incoherent: random phases, moderate sum
        # Coherent: aligned phases, large sum

        origin = LEFT * 2 + DOWN * 0.5

        def make_phasor(angle, length=1.0, color=MEDBLUE):
            return Arrow(
                start=origin,
                end=origin + length * np.array([np.cos(angle), np.sin(angle), 0]),
                color=color, stroke_width=2.5, buff=0,
                max_tip_length_to_length_ratio=0.2,
            )

        # Random phases
        np.random.seed(42)
        random_phases = np.random.uniform(0, TAU, 4)
        random_phasors = VGroup(*[make_phasor(a, 0.8) for a in random_phases])

        # Sum phasor (random)
        sum_random = sum(0.8 * np.exp(1j * a) for a in random_phases)
        sum_random_arrow = Arrow(
            start=origin,
            end=origin + np.array([sum_random.real, sum_random.imag, 0]),
            color=ALERTRED, stroke_width=4, buff=0,
            max_tip_length_to_length_ratio=0.15,
        )

        # Aligned phases
        aligned_phasors = VGroup(*[make_phasor(0.3, 0.8) for _ in range(4)])

        # Sum phasor (aligned)
        sum_aligned_arrow = Arrow(
            start=origin,
            end=origin + RIGHT * 3.2,
            color=ALERTRED, stroke_width=4, buff=0,
            max_tip_length_to_length_ratio=0.1,
        )

        # Labels
        incoh_label = Tex(r"Random phases", font_size=20, color=DIMGRAY).move_to(origin + UP * 2)
        coh_label = Tex(r"Aligned phases (beamforming)", font_size=20, color=ALERTRED).move_to(origin + UP * 2)

        scaling_incoh = MathTex(r"|E|^2 \sim N", font_size=28, color=DIMGRAY).move_to(RIGHT * 3.5 + UP * 1)
        scaling_coh = MathTex(r"|E|^2 \sim N^2", font_size=28, color=ALERTRED).move_to(RIGHT * 3.5 + UP * 1)

        circle = Circle(radius=1.5, color=DIMGRAY, stroke_width=0.5, stroke_opacity=0.3).move_to(origin)

        self.play(FadeIn(title), run_time=0.3)

        # Incoherent
        self.play(FadeIn(incoh_label), FadeIn(circle), run_time=0.3)
        self.play(
            LaggedStart(*[GrowArrow(p) for p in random_phasors], lag_ratio=0.15),
            run_time=0.8,
        )
        self.play(GrowArrow(sum_random_arrow), FadeIn(scaling_incoh), run_time=0.6)
        self.next_slide()

        # Transition to coherent
        self.play(
            FadeOut(random_phasors, sum_random_arrow, scaling_incoh, incoh_label),
            run_time=0.3,
        )
        self.play(FadeIn(coh_label), run_time=0.2)
        self.play(
            LaggedStart(*[GrowArrow(p) for p in aligned_phasors], lag_ratio=0.1),
            run_time=0.6,
        )
        self.play(GrowArrow(sum_aligned_arrow), FadeIn(scaling_coh), run_time=0.6)
        self.next_slide()

        # Landing: exposure operator
        self.play(FadeOut(aligned_phasors, sum_aligned_arrow, coh_label, scaling_coh, circle), run_time=0.3)

        eq_sab = MathTex(
            r"S_{\mathrm{ab}}(\mathbf{r}) = \bigl\|\tilde{\mathbf{G}}(\mathbf{r})\,\mathbf{x}\bigr\|^2",
            font_size=36, color=BLACK,
        ).move_to(UP * 0.5)

        eq_Q = MathTex(
            r"P_{\mathrm{abs}} = \mathbf{x}^H \mathbf{Q}\, \mathbf{x}",
            r",\qquad",
            r"\mathbf{Q} = \int_\Sigma \tilde{\mathbf{G}}^H \tilde{\mathbf{G}}\,\mathrm{d}A",
            font_size=30, color=BLACK,
        ).next_to(eq_sab, DOWN, buff=0.5)

        q_box = result_box(VGroup(eq_sab, eq_Q), title="Coherent absorption law and exposure operator")
        q_box.move_to(DOWN * 0.8)

        q_props = VGroup(
            Tex(r"$\mathbf{Q}$ is Hermitian PSD, $M \times M$.", font_size=18, color=BLACK),
            Tex(r"Eigendecomposition: worst-case precoder = dominant eigenvector.", font_size=18, color=BLACK),
            Tex(r"$\mathrm{tr}(\mathbf{Q})$: isotropic-TX expected absorption.", font_size=18, color=BLACK),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        q_props.next_to(q_box, DOWN, buff=0.3)

        self.play(FadeIn(q_box, shift=UP * 0.3), run_time=0.8)
        self.play(FadeIn(q_props, shift=UP * 0.2), run_time=0.5)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 11: Exposure-constrained beamforming
    # ============================================================
    def slide_11_ecbf(self):
        title = slide_title("Exposure-constrained beamforming")

        problem = MathTex(
            r"\max_{\mathbf{x}}\;|\mathbf{h}^\top\mathbf{x}|^2"
            r"\quad\text{s.t.}\quad"
            r"\mathbf{x}^H\mathbf{Q}\,\mathbf{x} \le P_{\mathrm{abs}}^{\max},"
            r"\quad \|\mathbf{x}\|^2 \le P",
            font_size=28, color=BLACK,
        ).move_to(UP * 1.8)

        solution = MathTex(
            r"\mathbf{x}^\star = \sqrt{P}\;"
            r"\frac{(\lambda\mathbf{Q} + \nu\mathbf{I})^{-1}\,\mathbf{h}^*}"
            r"{\|(\lambda\mathbf{Q} + \nu\mathbf{I})^{-1}\,\mathbf{h}^*\|}",
            font_size=32, color=BLACK,
        )
        sol_box = result_box(solution, title="Optimal precoder (S-procedure, global)")
        sol_box.move_to(UP * 0.0)

        # Three regimes
        regimes = VGroup(
            VGroup(
                MathTex(r"\lambda = 0", font_size=20, color=MEDBLUE),
                Tex(r"MRT (unconstrained)", font_size=16, color=BLACK),
            ).arrange(DOWN, buff=0.08),
            VGroup(
                MathTex(r"\lambda \gg \nu", font_size=20, color=ALERTRED),
                Tex(r"Body-avoiding precoder", font_size=16, color=BLACK),
            ).arrange(DOWN, buff=0.08),
            VGroup(
                MathTex(r"\rho \ll 1", font_size=20, color=RESULTGREEN),
                Tex(r"Natural protection", font_size=16, color=BLACK),
            ).arrange(DOWN, buff=0.08),
        ).arrange(RIGHT, buff=1.0)
        regimes.move_to(DOWN * 1.8)

        note = Tex(
            r"Same structure as Ying (2015), but $\mathbf{Q}$ derived analytically from Fresnel physics.",
            font_size=16, color=DIMGRAY,
        ).to_edge(DOWN, buff=0.4)

        self.play(FadeIn(title), run_time=0.3)
        self.play(Write(problem), run_time=1.0)
        self.next_slide()

        self.play(FadeIn(sol_box, shift=UP * 0.2), run_time=0.8)
        self.next_slide()

        self.play(
            LaggedStart(*[FadeIn(r, shift=UP * 0.2) for r in regimes], lag_ratio=0.15),
            run_time=0.6,
        )
        self.play(FadeIn(note), run_time=0.3)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 12: Summary
    # ============================================================
    def slide_12_summary(self):
        title = slide_title("Summary")

        # Three columns
        col1_title = Tex(r"\textbf{Incoherent}", font_size=22, color=NAVY)
        col1_eq = MathTex(
            r"S_{\mathrm{ab}} = S_{\mathrm{inc}} \cdot T_0 \cdot \mathrm{ReLU}(\mu)",
            font_size=20, color=BLACK,
        )
        col1_text = Tex(r"Material collapses.\\Dosimetry is geometry.", font_size=16, color=DIMGRAY)
        col1 = VGroup(col1_title, col1_eq, col1_text).arrange(DOWN, buff=0.2)

        col2_title = Tex(r"\textbf{Coherent}", font_size=22, color=NAVY)
        col2_eq = MathTex(
            r"S_{\mathrm{ab}} = \|\tilde{\mathbf{G}}\,\mathbf{x}\|^2",
            font_size=20, color=BLACK,
        )
        col2_eq2 = MathTex(r"P_{\mathrm{abs}} = \mathbf{x}^H \mathbf{Q}\,\mathbf{x}", font_size=20, color=BLACK)
        col2_text = Tex(r"Closed-form precoder.\\$\mathbf{Q}$ from Fresnel physics.", font_size=16, color=DIMGRAY)
        col2 = VGroup(col2_title, col2_eq, col2_eq2, col2_text).arrange(DOWN, buff=0.15)

        col3_title = Tex(r"\textbf{Speed}", font_size=22, color=NAVY)
        col3_big = Tex(r"\textbf{$10^6\times$}", font_size=40, color=RESULTGREEN)
        col3_text = Tex(r"over FDTD.\\Real time on a laptop.", font_size=16, color=DIMGRAY)
        col3 = VGroup(col3_title, col3_big, col3_text).arrange(DOWN, buff=0.2)

        columns = VGroup(col1, col2, col3).arrange(RIGHT, buff=1.2, aligned_edge=UP)
        columns.move_to(UP * 0.2)

        # Dividers
        div1 = Line(
            columns[0].get_right() + RIGHT * 0.4 + UP * 1.5,
            columns[0].get_right() + RIGHT * 0.4 + DOWN * 1.5,
            color=DIMGRAY, stroke_width=0.5,
        )
        div2 = Line(
            columns[1].get_right() + RIGHT * 0.4 + UP * 1.5,
            columns[1].get_right() + RIGHT * 0.4 + DOWN * 1.5,
            color=DIMGRAY, stroke_width=0.5,
        )

        punchline = Tex(
            r"\textbf{Tissue physics makes dosimetry geometric. The geometry is fast.\\The fast computation enables exposure-aware network design.}",
            font_size=20, color=NAVY,
        ).to_edge(DOWN, buff=0.6)

        self.play(FadeIn(title), run_time=0.3)
        self.play(
            FadeIn(col1, shift=UP * 0.2),
            FadeIn(col2, shift=UP * 0.2),
            FadeIn(col3, shift=UP * 0.2),
            FadeIn(div1), FadeIn(div2),
            run_time=1.0,
        )
        self.next_slide()

        self.play(FadeIn(punchline, shift=UP * 0.2), run_time=0.6)
        self.next_slide()

        self.play(FadeOut(*self.mobjects), run_time=0.3)

    # ============================================================
    # SLIDE 13: Thank you
    # ============================================================
    def slide_13_thankyou(self):
        thanks = Tex(r"\textbf{Thank you}", font_size=52, color=NAVY)
        qa = Tex(r"Questions and discussion", font_size=24, color=DIMGRAY)
        contact = Tex(
            r"Robin Wydaeghe  $|$  robin.wydaeghe@ugent.be",
            font_size=18, color=DIMGRAY,
        )
        group = VGroup(thanks, qa, contact).arrange(DOWN, buff=0.5)

        self.play(FadeIn(thanks, scale=1.1), run_time=0.8)
        self.play(FadeIn(qa, shift=UP * 0.2), FadeIn(contact, shift=UP * 0.1), run_time=0.5)
        self.next_slide()
