"""Animation 3: Coherent phasor alignment.

Random phasors -> aligned. Sum vector grows. Flash.
TransformMatchingTex morphs |E|^2 ~ N -> N^2.

Render: manim render -qh coherent.py CoherentPhasors
"""

import numpy as np
from manim import *

# ---------- semantic palette (matches Beamer) ----------
SINC_BLUE = "#3264AA"
T0_RED = "#B41E1E"
GEOM_GREEN = "#006E37"
WAVE_GOLD = "#DDAA22"
DIM = "#555555"
LABEL_GRAY = "#999999"

# Phasor colors
PHASOR_COLORS = [BLUE_C, TEAL_C, GREEN_C, GOLD]


class CoherentPhasors(Scene):
    def construct(self):
        # ============================================================
        # PART 1: Title + random phasors (0-5s)
        # ============================================================
        title = Tex(
            r"Coherent hotspot formation",
            font_size=40, color=WHITE,
        ).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=1.5)

        # Phasor origin
        origin = LEFT * 2.5 + DOWN * 0.5

        # Random phases (fixed seed for reproducibility)
        rng = np.random.default_rng(42)
        n_phasors = 4
        amplitude = 1.2
        initial_phases = rng.uniform(0, TAU, n_phasors)

        # Phase ValueTrackers
        phase_trackers = [ValueTracker(p) for p in initial_phases]

        def make_phasor_arrow(tracker, color):
            def updater():
                phi = tracker.get_value()
                end = origin + amplitude * np.array([np.cos(phi), np.sin(phi), 0])
                return Arrow(
                    origin, end, color=color, stroke_width=3, buff=0,
                    max_tip_length_to_length_ratio=0.15,
                )
            return always_redraw(updater)

        def make_sum_arrow():
            def updater():
                total = np.array([0.0, 0.0, 0.0])
                for tracker in phase_trackers:
                    phi = tracker.get_value()
                    total += amplitude * np.array([np.cos(phi), np.sin(phi), 0])
                if np.linalg.norm(total) < 0.05:
                    return Dot(origin, radius=0.01, color=BLACK)  # invisible
                return Arrow(
                    origin, origin + total, color=RED_C, stroke_width=5, buff=0,
                    max_tip_length_to_length_ratio=0.1,
                )
            return always_redraw(updater)

        # Create phasor arrows
        phasor_arrows = [
            make_phasor_arrow(phase_trackers[i], PHASOR_COLORS[i])
            for i in range(n_phasors)
        ]
        sum_arrow_mob = make_sum_arrow()

        # Labels
        incoherent_label = MathTex(
            r"\text{Incoherent:}\;|E|^2 \sim N",
            font_size=30, color=LABEL_GRAY,
        ).shift(RIGHT * 3 + UP * 1.5)

        # Draw phasors one by one
        for i, arrow in enumerate(phasor_arrows):
            self.play(Create(arrow), run_time=0.5)

        self.wait(0.3)

        # ============================================================
        # PART 2: Sum vector (5-10s)
        # ============================================================
        self.add(sum_arrow_mob)
        self.play(FadeIn(incoherent_label), run_time=0.5)

        # Show the sum is small
        sum_brace_text = Tex(
            r"Partial cancellation", font_size=22, color=DIM,
        ).shift(RIGHT * 3 + UP * 0.5)
        self.play(FadeIn(sum_brace_text), run_time=0.5)
        self.wait(1.5)

        # ============================================================
        # PART 3: Smooth alignment (10-20s)
        # ============================================================
        self.play(FadeOut(sum_brace_text), run_time=0.3)

        # Target: all phases aligned at 0 (pointing right)
        target_phase = 0.0

        # Alignment text
        aligning_text = Tex(
            r"Beamforming aligns the phasors\ldots",
            font_size=26, color=LABEL_GRAY,
        ).shift(RIGHT * 3 + DOWN * 0.5)
        self.play(FadeIn(aligning_text), run_time=0.5)

        # Smoothly rotate all phasors toward target_phase
        # Stagger the animations slightly for visual interest
        self.play(
            phase_trackers[0].animate.set_value(target_phase),
            phase_trackers[1].animate.set_value(target_phase),
            phase_trackers[2].animate.set_value(target_phase),
            phase_trackers[3].animate.set_value(target_phase),
            run_time=6.0,
            rate_func=smooth,
        )
        self.wait(0.5)

        # ============================================================
        # PART 4: Flash + N^2 (20-25s)
        # ============================================================
        self.play(FadeOut(aligning_text), run_time=0.3)

        # The sum vector is now 4 * amplitude long
        sum_tip = origin + n_phasors * amplitude * np.array([1, 0, 0])
        self.play(
            Flash(sum_tip, color=YELLOW, num_lines=16, flash_radius=1.0),
            run_time=0.8,
        )

        # Morph the label
        coherent_label = MathTex(
            r"\text{Coherent:}\;|E|^2 \sim", r"N^2",
            font_size=30, color=WHITE,
        ).move_to(incoherent_label)
        coherent_label[1].set_color(T0_RED)

        self.play(
            FadeTransform(incoherent_label, coherent_label),
            run_time=1.5,
        )

        # N^2 emphasis
        self.play(
            Indicate(coherent_label[1], color=YELLOW, scale_factor=1.5),
            run_time=1.0,
        )
        self.wait(1.0)

        # ============================================================
        # PART 5: Coherent absorption law (25-35s)
        # ============================================================
        # Fade phasors and diagram
        to_fade = VGroup(*phasor_arrows, sum_arrow_mob, coherent_label)
        self.play(FadeOut(to_fade), FadeOut(title), run_time=0.8)

        # Write coherent law
        law1 = MathTex(
            r"S_{\mathrm{ab}}(\mathbf{r}) = "
            r"\bigl\|\tilde{\mathbf{G}}(\mathbf{r})\,\mathbf{x}\bigr\|^2",
            font_size=42, color=WHITE,
        ).shift(UP * 1.0)

        law2 = MathTex(
            r"P_{\mathrm{abs}} = \mathbf{x}^H\,\mathbf{Q}\,\mathbf{x}",
            font_size=42, color=WHITE,
        ).next_to(law1, DOWN, buff=0.6)

        q_def = MathTex(
            r"\mathbf{Q} = \int_\Sigma "
            r"\tilde{\mathbf{G}}^H \tilde{\mathbf{G}}\,\mathrm{d}A"
            r"\;\in\;\mathbb{C}^{M \times M}",
            font_size=32, color=LABEL_GRAY,
        ).next_to(law2, DOWN, buff=0.4)

        self.play(Write(law1), run_time=2.0)
        self.wait(0.5)
        self.play(Write(law2), run_time=1.5)
        self.play(FadeIn(q_def), run_time=0.8)
        self.wait(0.5)

        # Highlight Q
        self.play(
            Circumscribe(law2, color=YELLOW, buff=0.1, run_time=1.5),
        )

        # ============================================================
        # PART 6: Brief annotation (35-40s)
        # ============================================================
        annotation = Tex(
            r"$\mathbf{Q}$: Hermitian PSD, $M \times M$. "
            r"Dominant eigenvector maximises body absorption.",
            font_size=24, color=LABEL_GRAY,
        ).to_edge(DOWN, buff=0.8)
        self.play(FadeIn(annotation), run_time=0.6)
        self.wait(2.5)

        # Fade out
        self.play(FadeOut(*self.mobjects), run_time=1.0)
        self.wait(0.3)
