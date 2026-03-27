"""Animation 1: Pseudo-Brewster compensation.

ValueTracker traces T_s, T_p, T_avg curves live.
TransformMatchingTex morphs T_eff(theta) -> T_0.
Flash at the collapse moment.

Render: manim-slides render animations/pseudo_brewster.py PseudoBrewster
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

# ---------- Fresnel physics ----------
# Skin at 28 GHz: eps_r=17, sigma=25 S/m
N_TILDE = 4.4933 - 1.7859j
N2 = N_TILDE**2


def _xi(mu):
    """Normal wave-vector component in tissue."""
    xi = np.sqrt(N2 - 1 + mu**2)
    return -xi if xi.real < 0 else xi


def fresnel_Ts(theta_deg):
    mu = np.cos(np.radians(theta_deg))
    xi = _xi(mu)
    r_s = (mu - xi) / (mu + xi)
    return float(np.clip(1 - abs(r_s) ** 2, 0, 1))


def fresnel_Tp(theta_deg):
    mu = np.cos(np.radians(theta_deg))
    xi = _xi(mu)
    r_p = (N2 * mu - xi) / (N2 * mu + xi)
    return float(np.clip(1 - abs(r_p) ** 2, 0, 1))


def fresnel_Tavg(theta_deg):
    return (fresnel_Ts(theta_deg) + fresnel_Tp(theta_deg)) / 2


T0 = fresnel_Tavg(0)  # ~0.5387

# ---------- Pseudo-Brewster angle ----------
_thetas = np.linspace(0, 90, 10000)
_tp_vals = np.array([fresnel_Tp(t) for t in _thetas])
PSEUDO_BREWSTER_DEG = float(_thetas[np.argmax(_tp_vals)])  # ~78.25
PSEUDO_BREWSTER_TP = float(_tp_vals[np.argmax(_tp_vals)])  # ~0.9662


class PseudoBrewster(Slide):
    def construct(self):
        # ---- title ----
        title = Tex(
            r"Pseudo-Brewster compensation",
            font_size=38, color=WHITE,
        ).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=1.5)
        self.wait(1.0)

        # ---- axes ----
        ax = Axes(
            x_range=[0, 90, 15],
            y_range=[0, 1.0, 0.2],
            x_length=9,
            y_length=4.5,
            axis_config={"color": LABEL_GRAY, "stroke_width": 2},
            tips=False,
        ).shift(DOWN * 0.35)

        # Position x-axis label at right end of axis to avoid tick overlap
        x_label = MathTex(
            r"\theta\;(^\circ)", font_size=24, color=LABEL_GRAY,
        ).next_to(ax.c2p(90, 0), DOWN + RIGHT, buff=0.25)

        y_label = ax.get_y_axis_label(
            MathTex(r"T(\theta)", font_size=24, color=LABEL_GRAY),
            edge=LEFT, direction=LEFT,
        )

        # Tick labels
        x_ticks = VGroup(*[
            MathTex(str(v), font_size=18, color=LABEL_GRAY).next_to(
                ax.c2p(v, 0), DOWN, buff=0.2
            )
            for v in range(0, 91, 15)
        ])
        y_ticks = VGroup(*[
            MathTex(f"{v:.1f}", font_size=18, color=LABEL_GRAY).next_to(
                ax.c2p(0, v), LEFT, buff=0.15
            )
            for v in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        ])

        self.play(
            Create(ax), FadeIn(x_label), FadeIn(y_label),
            FadeIn(x_ticks), FadeIn(y_ticks),
            run_time=1.5,
        )
        self.wait(1.0)
        self.next_slide()  # --- SLIDE: axes visible ---

        # ---- Trace T_s with ValueTracker ----
        t_s = ValueTracker(0.5)

        ts_curve = always_redraw(lambda: ax.plot(
            fresnel_Ts,
            x_range=[0.5, max(t_s.get_value(), 0.6), 0.5],
            color=SINC_BLUE, stroke_width=3,
        ))
        ts_dot = always_redraw(lambda: Dot(
            ax.c2p(t_s.get_value(), fresnel_Ts(t_s.get_value())),
            color=SINC_BLUE, radius=0.06,
        ))

        ts_label = MathTex(r"T_s(\theta)", font_size=28, color=SINC_BLUE)
        ts_label.next_to(ax.c2p(72, fresnel_Ts(72)), UP, buff=0.15)

        self.add(ts_curve, ts_dot)
        self.play(
            t_s.animate.set_value(85),
            run_time=5, rate_func=smooth,
        )
        self.play(FadeIn(ts_label, shift=UP * 0.1), run_time=0.5)
        self.remove(ts_dot)
        # Replace with static curve
        ts_static = ax.plot(
            fresnel_Ts, x_range=[0.5, 85, 0.5],
            color=SINC_BLUE, stroke_width=3,
        )
        self.remove(ts_curve)
        self.add(ts_static)
        self.wait(2.0)
        self.next_slide()  # --- SLIDE: T_s traced ---

        # ---- Trace T_p ----
        t_p = ValueTracker(0.5)

        tp_curve = always_redraw(lambda: ax.plot(
            fresnel_Tp,
            x_range=[0.5, max(t_p.get_value(), 0.6), 0.5],
            color=T0_RED, stroke_width=3,
        ))
        tp_dot = always_redraw(lambda: Dot(
            ax.c2p(t_p.get_value(), fresnel_Tp(t_p.get_value())),
            color=T0_RED, radius=0.06,
        ))

        tp_label = MathTex(r"T_p(\theta)", font_size=28, color=T0_RED)
        tp_label.next_to(ax.c2p(50, fresnel_Tp(50)), UP, buff=0.15)

        self.add(tp_curve, tp_dot)
        self.play(
            t_p.animate.set_value(85),
            run_time=5, rate_func=smooth,
        )
        self.play(FadeIn(tp_label, shift=UP * 0.1), run_time=0.5)
        self.remove(tp_dot)
        tp_static = ax.plot(
            fresnel_Tp, x_range=[0.5, 85, 0.5],
            color=T0_RED, stroke_width=3,
        )
        self.remove(tp_curve)
        self.add(tp_static)
        self.wait(1.5)

        # ---- Pseudo-Brewster marker ----
        brewster_dot = Dot(
            ax.c2p(PSEUDO_BREWSTER_DEG, PSEUDO_BREWSTER_TP),
            color=YELLOW, radius=0.08,
        )
        brewster_star = Star(
            n=5, outer_radius=0.15, inner_radius=0.07,
            color=YELLOW, fill_opacity=1.0,
        ).move_to(ax.c2p(PSEUDO_BREWSTER_DEG, PSEUDO_BREWSTER_TP))

        brewster_annotation = Tex(
            r"Pseudo-Brewster angle",
            font_size=20, color=YELLOW,
        ).next_to(brewster_star, UP + LEFT, buff=0.12)

        # Thin dashed vertical guide line from the star down to the x-axis
        brewster_guide = DashedLine(
            ax.c2p(PSEUDO_BREWSTER_DEG, 0),
            ax.c2p(PSEUDO_BREWSTER_DEG, PSEUDO_BREWSTER_TP),
            color=YELLOW, stroke_width=1.5, dash_length=0.08,
            stroke_opacity=0.4,
        )

        self.play(
            FadeIn(brewster_guide),
            GrowFromCenter(brewster_star),
            run_time=0.8,
        )
        self.play(FadeIn(brewster_annotation, shift=UP * 0.1), run_time=0.5)
        self.wait(2.5)
        self.next_slide()  # --- SLIDE: T_p traced with Brewster marker ---

        # ---- Trace T_avg ----
        t_avg = ValueTracker(0.5)

        tavg_curve = always_redraw(lambda: ax.plot(
            fresnel_Tavg,
            x_range=[0.5, max(t_avg.get_value(), 0.6), 0.5],
            color=GEOM_GREEN, stroke_width=4,
        ))
        tavg_dot = always_redraw(lambda: Dot(
            ax.c2p(t_avg.get_value(), fresnel_Tavg(t_avg.get_value())),
            color=GEOM_GREEN, radius=0.06,
        ))

        tavg_label = MathTex(
            r"T_{\mathrm{avg}}(\theta)", font_size=28, color=GEOM_GREEN,
        )
        tavg_label.next_to(ax.c2p(55, fresnel_Tavg(55)), UP, buff=0.2)

        self.add(tavg_curve, tavg_dot)
        self.play(
            t_avg.animate.set_value(85),
            run_time=5, rate_func=smooth,
        )
        self.play(FadeIn(tavg_label, shift=UP * 0.1), run_time=0.5)
        self.remove(tavg_dot)
        tavg_static = ax.plot(
            fresnel_Tavg, x_range=[0.5, 85, 0.5],
            color=GEOM_GREEN, stroke_width=4,
        )
        self.remove(tavg_curve)
        self.add(tavg_static)
        self.wait(2.0)

        # ---- T_0 dashed line ----
        t0_line = DashedLine(
            ax.c2p(0, T0), ax.c2p(85, T0),
            color=YELLOW, stroke_width=2, dash_length=0.12,
        )
        t0_val = MathTex(
            rf"T_0 = {T0:.2f}", font_size=28, color=YELLOW,
        ).next_to(ax.c2p(87, T0), RIGHT, buff=0.15)

        self.play(Create(t0_line), Write(t0_val), run_time=1.0)
        self.wait(2.0)

        # ---- Circumscribe the flat T_avg ----
        self.play(
            Circumscribe(tavg_static, color=YELLOW, buff=0.05, run_time=1.5),
        )
        self.wait(1.5)
        self.next_slide()  # --- SLIDE: T_avg traced + T_0 line ---

        # ---- Variation annotation ----
        var_text = Tex(
            r"Variation $< 6\%$ up to $75^\circ$",
            font_size=28, color=LABEL_GRAY,
        ).next_to(ax, DOWN, buff=0.35)
        azzam_text = Tex(
            r"Holds for $|\tilde{n}| > 2.5$ (Azzam, 2015). "
            r"Biological tissue: $|\tilde{n}| \approx 3$--$6$.",
            font_size=20, color=LABEL_GRAY,
        ).next_to(var_text, DOWN, buff=0.08)

        self.play(FadeIn(var_text), FadeIn(azzam_text), run_time=1.0)
        self.wait(3.0)
        self.next_slide()  # --- SLIDE: variation annotation ---

        # ---- THE COLLAPSE ----
        # Fade T_s and T_p to dim gray
        self.wait(2.0)
        self.play(
            ts_static.animate.set_stroke(color=DIM, opacity=0.3),
            tp_static.animate.set_stroke(color=DIM, opacity=0.3),
            ts_label.animate.set_opacity(0.2),
            tp_label.animate.set_opacity(0.2),
            brewster_star.animate.set_opacity(0.15),
            brewster_annotation.animate.set_opacity(0.15),
            brewster_guide.animate.set_opacity(0.1),
            run_time=1.5, rate_func=smooth,
        )
        self.wait(2.0)

        # TransformMatchingTex: T_eff(theta) -> T_0
        eq_before = MathTex(
            r"T_{\mathrm{eff}}(\theta)",
            font_size=36, color=WHITE,
        ).to_edge(UP, buff=0.5).shift(RIGHT * 0.5)

        eq_after = MathTex(
            r"T_0",
            font_size=36, color=YELLOW,
        ).move_to(eq_before)

        self.play(
            FadeOut(title),
            FadeOut(tavg_label),
            FadeOut(var_text), FadeOut(azzam_text),
            run_time=0.8,
        )
        self.play(Write(eq_before), run_time=1.0)
        self.wait(1.5)
        self.play(
            FadeTransform(eq_before, eq_after),
            run_time=2.0, rate_func=smooth,
        )
        self.play(
            Flash(eq_after, color=YELLOW, num_lines=12, flash_radius=0.8),
            run_time=0.8,
        )
        self.wait(3.0)
        self.next_slide()  # --- SLIDE: collapse moment ---

        # ---- Punchline ----
        punchline = Tex(
            r"Material physics collapses to one number.",
            font_size=36, color=WHITE,
        ).next_to(eq_after, DOWN, buff=0.6)

        self.play(Write(punchline), run_time=2.0)
        self.wait(3.0)
        self.next_slide()  # --- SLIDE: punchline ---

        # ---- Fade out ----
        self.play(FadeOut(*self.mobjects), run_time=1.0)
        self.wait(0.5)
