"""3D visualizations of AEGIS differentiable optimization.

Non-trivial scenarios where the answer isn't obvious:
1. Constrained placement: antenna on a wall, maximize signal at UE while
   staying below ICNIRP on the body. Can't just move it away.
2. MIMO hotspot reshaping: precoder redistributes the exposure pattern,
   turning a sharp peak into a diffuse wash. Visually dramatic.
3. DiffeRT scene: real multipath exposure from a street canyon.
4. Animated GIF: watching the MIMO exposure pattern morph in real time.

Run:  python3 examples/viz_3d_optimization.py
"""

from __future__ import annotations

import io
import time

import jax
import jax.numpy as jnp
import numpy as np
import plotly.graph_objects as go
from PIL import Image
from plotly.subplots import make_subplots

from aegis.coherent import compute_body_channel
from aegis.constants import Z_0
from aegis.geometry.mesh import BodyMesh
from aegis.kernels.level3_fresnel import level3_fresnel
from aegis.optim import coherent_sab, soft_peak_exposure
from aegis.tissue.dielectric import TissueModel
from aegis.viz.heatmap import _inferno_colorscale

FREQ_HZ = 28e9
TISSUE = TissueModel.from_database("Skin", FREQ_HZ)
N_TILDE = TISSUE.n_complex
K0 = 2 * np.pi * FREQ_HZ / 3e8
SAB_LIMIT = 20.0  # ICNIRP W/m^2


def mesh3d_trace(body, sab, sab_max=None, name=""):
    import matplotlib

    n_tri = body.vertices.shape[0]
    all_v = body.vertices.reshape(-1, 3)
    vmax = sab_max if sab_max is not None else float(np.max(sab))
    vmax = max(vmax, 1e-12)
    sab_norm = np.clip(np.asarray(sab) / vmax, 0, 1)

    cm = matplotlib.colormaps["inferno"]
    colors_rgba = cm(sab_norm)
    face_colors = [f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})" for c in colors_rgba]

    return go.Mesh3d(
        x=all_v[:, 0], y=all_v[:, 1], z=all_v[:, 2],
        i=np.arange(0, 3*n_tri, 3), j=np.arange(1, 3*n_tri, 3), k=np.arange(2, 3*n_tri, 3),
        facecolor=face_colors, flatshading=True,
        hovertext=[f"{name}<br>S_ab={s:.4f}" for s in np.asarray(sab)],
        hoverinfo="text",
        lighting=dict(ambient=0.5, diffuse=0.6, specular=0.15),
        lightposition=dict(x=1000, y=1000, z=2000),
        name=name,
    )


def marker3d(pos, color="red", name="", symbol="diamond", size=8):
    return go.Scatter3d(
        x=[pos[0]], y=[pos[1]], z=[pos[2]],
        mode="markers+text", marker=dict(size=size, color=color, symbol=symbol),
        text=[name], textposition="top center",
        textfont=dict(color="white", size=10), showlegend=False,
    )


def colorbar_trace(vmax):
    return go.Scatter3d(
        x=[None], y=[None], z=[None], mode="markers",
        marker=dict(
            size=0.001, color=[0, vmax], colorscale=_inferno_colorscale(),
            cmin=0, cmax=vmax,
            colorbar=dict(title="S_ab (W/m^2)", thickness=15, len=0.6),
            showscale=True,
        ),
        hoverinfo="skip", showlegend=False,
    )


def scene_layout(camera=None):
    if camera is None:
        camera = dict(eye=dict(x=0, y=-1.8, z=0.3), up=dict(x=0, y=0, z=1))
    return dict(
        xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
        aspectmode="data", camera=camera, bgcolor="rgb(25,25,30)",
    )


# ---------------------------------------------------------------------------
# 1. Constrained placement: antenna on a wall, maximize UE signal,
#    stay below ICNIRP on body. Two competing objectives.
# ---------------------------------------------------------------------------


def render_constrained_placement():
    """Antenna slides along a wall (y=1.0, z free). Body at origin, UE at (0, -1, 0).

    Moving antenna closer to body: higher exposure but also higher signal at UE.
    Moving antenna away: lower exposure but weaker signal.
    Objective: maximize signal at UE subject to S_ab < 20 W/m^2 on body.
    """
    print("Rendering constrained wall placement...")
    body = BodyMesh.sphere(radius=0.15, n_subdivisions=4)
    normals = jnp.array(body.normals)
    n_tilde = jnp.array(N_TILDE)

    tx_eirp = 500.0  # high EIRP to make the constraint bind
    ue_pos = jnp.array([0.0, -1.0, 0.0])

    # Parameterize: antenna at (0, 1.0, z) where z is optimized
    # Wall constraint: y=1.0 fixed. Only z moves.
    def compute_sab_and_signal(z):
        ant_pos = jnp.array([0.0, 1.0, z])

        # Exposure on body
        to_body = -ant_pos
        d_body = jnp.linalg.norm(to_body)
        k_hat = (to_body / d_body)[None, :]
        pd = tx_eirp / (4 * jnp.pi * d_body**2)
        sab = level3_fresnel(normals, k_hat, jnp.array([pd]), n_tilde)

        # Signal at UE (inverse square law)
        d_ue = jnp.linalg.norm(ant_pos - ue_pos)
        signal = tx_eirp / (4 * jnp.pi * d_ue**2)

        return sab, signal

    def loss(z):
        sab, signal = compute_sab_and_signal(z)
        peak = soft_peak_exposure(sab)
        violation = jnp.maximum(peak - SAB_LIMIT, 0.0)
        # Maximize signal (minimize -log) subject to ICNIRP
        return -jnp.log(signal) + 200.0 * violation**2

    # Before: z=0.0 (antenna directly across from body)
    z_init = jnp.array(0.0)
    sab_before, sig_before = compute_sab_and_signal(z_init)
    sab_before = np.asarray(sab_before)

    # Optimize
    z = z_init
    grad_fn = jax.jit(jax.grad(loss))
    for _ in range(500):
        z = z - 0.002 * grad_fn(z)
        z = jnp.clip(z, -2.0, 2.0)

    sab_after, sig_after = compute_sab_and_signal(z)
    sab_after = np.asarray(sab_after)

    vmax = max(float(np.max(sab_before)), float(np.max(sab_after)))
    print(f"  Before: z=0.0m, peak={np.max(sab_before):.2f} W/m^2, signal={float(sig_before):.4f}")
    print(f"  After:  z={float(z):.2f}m, peak={np.max(sab_after):.2f} W/m^2, signal={float(sig_after):.4f}")

    # Camera looks from +y toward origin (same side as antenna, sees the hotspot)
    camera = dict(eye=dict(x=0.5, y=1.8, z=0.5), up=dict(x=0, y=0, z=1))

    fig = make_subplots(
        rows=1, cols=2, specs=[[{"type": "scene"}, {"type": "scene"}]],
        subplot_titles=[
            f"Before: z=0.0m, peak={np.max(sab_before):.1f} W/m^2, signal={float(sig_before):.3f}",
            f"After: z={float(z):.2f}m, peak={np.max(sab_after):.1f} W/m^2, signal={float(sig_after):.3f}",
        ],
    )

    fig.add_trace(mesh3d_trace(body, sab_before, vmax, "Before"), row=1, col=1)
    fig.add_trace(marker3d([0, 1, 0], "red", "Antenna"), row=1, col=1)
    fig.add_trace(marker3d(np.array(ue_pos), "cyan", "UE", "circle", 6), row=1, col=1)

    fig.add_trace(mesh3d_trace(body, sab_after, vmax, "After"), row=1, col=2)
    fig.add_trace(marker3d([0, 1, float(z)], "lime", "Optimal"), row=1, col=2)
    fig.add_trace(marker3d(np.array(ue_pos), "cyan", "UE", "circle", 6), row=1, col=2)
    fig.add_trace(colorbar_trace(vmax), row=1, col=2)

    fig.update_layout(
        title=dict(
            text="Wall-constrained antenna: maximize UE signal, respect ICNIRP on body",
            x=0.5, font=dict(size=15, color="white"),
        ),
        scene=scene_layout(camera), scene2=scene_layout(camera),
        paper_bgcolor="rgb(25,25,30)", font_color="white",
        width=1400, height=600, margin=dict(l=0, r=0, t=80, b=0),
    )

    fig.write_image("examples/viz_constrained_3d.png", scale=2)
    print(f"  Saved examples/viz_constrained_3d.png")
    return fig


# ---------------------------------------------------------------------------
# 2. MIMO hotspot reshaping
# ---------------------------------------------------------------------------


def render_mimo():
    """MIMO precoder optimization reshapes the exposure pattern on the body.

    MRT concentrates all energy on a hotspot. The peak-minimizing precoder
    spreads it out, trading signal for a flat exposure profile.
    """
    print("Rendering MIMO hotspot reshaping...")
    body = BodyMesh.sphere(radius=0.15, n_subdivisions=4)
    normals_np, centroids_np = body.normals, body.centroids
    n_elements = 4
    wavelength = 3e8 / FREQ_HZ
    d_ant = wavelength / 2

    element_positions = np.array([
        [(i - (n_elements - 1) / 2) * d_ant, 1.0, 0.0]
        for i in range(n_elements)
    ])

    # 3 multipath directions with different arrival angles
    path_directions = np.array([
        [0.0, -1.0, 0.0], [0.4, -0.9, 0.1], [-0.3, -0.85, 0.4],
    ])
    path_directions /= np.linalg.norm(path_directions, axis=1, keepdims=True)
    path_amplitudes = np.array([1.0, 0.6, 0.4])

    E0 = np.sqrt(2 * Z_0 * 5.0)
    n_total = n_elements * len(path_directions)
    k_hat_np = np.zeros((n_total, 3))
    psi_np = np.zeros((n_total, 3), dtype=complex)
    element_index_np = np.zeros(n_total, dtype=np.intp)

    for j in range(n_elements):
        for p, (kd, amp) in enumerate(zip(path_directions, path_amplitudes)):
            idx = j * len(path_directions) + p
            k_hat_np[idx] = kd
            phase = -K0 * np.dot(kd, element_positions[j])
            e_perp = np.cross(kd, [0, 0, 1])
            n = np.linalg.norm(e_perp)
            if n < 1e-6:
                e_perp = np.cross(kd, [1, 0, 0])
                n = np.linalg.norm(e_perp)
            e_perp /= n
            psi_np[idx] = E0 * amp * e_perp * np.exp(1j * phase)
            element_index_np[idx] = j

    G_tilde_np = compute_body_channel(
        normals_np, centroids_np, k_hat_np, psi_np, element_index_np,
        N_TILDE, TISSUE.sigma, FREQ_HZ, n_elements,
    )
    G_tilde = jnp.array(G_tilde_np)

    ue_angle = np.radians(20)
    h = np.array([
        np.exp(1j * K0 * (i - (n_elements - 1) / 2) * d_ant * np.sin(ue_angle))
        for i in range(n_elements)
    ], dtype=complex)
    h /= np.linalg.norm(h)
    h_j = jnp.array(h)

    x_mrt = jnp.array(h / np.linalg.norm(h))
    sab_mrt = np.asarray(coherent_sab(G_tilde, x_mrt))

    # Optimize: minimize peak S_ab, keep 50% signal
    signal_min = 0.5 * float(jnp.abs(jnp.vdot(h_j, x_mrt))**2)

    def loss(x_flat):
        x = x_flat[:n_elements] + 1j * x_flat[n_elements:]
        x = x / jnp.linalg.norm(x)
        sab = coherent_sab(G_tilde, x)
        peak = soft_peak_exposure(sab, temperature=50.0)
        sig = jnp.abs(jnp.vdot(h_j, x))**2
        return peak + 500.0 * jnp.maximum(signal_min - sig, 0.0)**2

    x_flat = jnp.concatenate([jnp.real(x_mrt), jnp.imag(x_mrt)])
    grad_fn = jax.jit(jax.grad(loss))
    for _ in range(1000):
        x_flat = x_flat - 0.01 * grad_fn(x_flat)

    x_opt = x_flat[:n_elements] + 1j * x_flat[n_elements:]
    x_opt = x_opt / jnp.linalg.norm(x_opt)
    sab_opt = np.asarray(coherent_sab(G_tilde, x_opt))

    vmax = float(np.max(sab_mrt))  # use MRT peak as scale
    peak_reduction = (1 - np.max(sab_opt) / np.max(sab_mrt)) * 100

    print(f"  MRT:     peak={np.max(sab_mrt):.4f}, mean={np.mean(sab_mrt):.4f}")
    print(f"  Optimal: peak={np.max(sab_opt):.4f}, mean={np.mean(sab_opt):.4f}")
    print(f"  Peak reduction: {peak_reduction:.1f}%")

    # Camera from antenna side (+y) to see the illuminated face
    camera = dict(eye=dict(x=0.3, y=1.8, z=0.3), up=dict(x=0, y=0, z=1))

    fig = make_subplots(
        rows=1, cols=2, specs=[[{"type": "scene"}, {"type": "scene"}]],
        subplot_titles=[
            f"MRT precoder: peak = {np.max(sab_mrt):.3f} W/m^2",
            f"Peak-optimized: peak = {np.max(sab_opt):.3f} W/m^2 ({peak_reduction:.0f}% lower)",
        ],
    )

    fig.add_trace(mesh3d_trace(body, sab_mrt, vmax, "MRT"), row=1, col=1)
    fig.add_trace(mesh3d_trace(body, sab_opt, vmax, "Optimized"), row=1, col=2)
    fig.add_trace(colorbar_trace(vmax), row=1, col=2)

    fig.update_layout(
        title=dict(
            text="MIMO hotspot reshaping: MRT vs peak-exposure-optimized precoder",
            x=0.5, font=dict(size=15, color="white"),
        ),
        scene=scene_layout(camera), scene2=scene_layout(camera),
        paper_bgcolor="rgb(25,25,30)", font_color="white",
        width=1400, height=600, margin=dict(l=0, r=0, t=80, b=0),
    )

    fig.write_image("examples/viz_mimo_3d.png", scale=2)
    print(f"  Saved examples/viz_mimo_3d.png")

    # Return data for GIF
    return G_tilde, h_j, x_mrt, body, signal_min, vmax


# ---------------------------------------------------------------------------
# 3. DiffeRT real scene
# ---------------------------------------------------------------------------


def render_differt():
    try:
        from aegis.integration import paths_from_differt_scene
    except ImportError:
        print("  SKIP: DiffeRT not installed")
        return None

    print("Rendering DiffeRT street canyon exposure...")
    body = BodyMesh.sphere(radius=0.15, n_subdivisions=4)
    from aegis.engine import DosimetryEngine
    engine = DosimetryEngine(TISSUE)

    paths = paths_from_differt_scene(
        scene_path="data/scenes/simple_street_canyon/simple_street_canyon.xml",
        tx_positions=np.array([[5.0, 0.0, 3.0]]),
        rx_position=np.array([0.0, 0.0, 1.0]),
        freq_hz=FREQ_HZ, max_bounces=3, tx_power_dbm=30.0,
    )

    result = engine.compute(body, paths, level=3)
    sab = np.asarray(result.sab)

    fig = go.Figure()
    # Camera from TX side to see the illuminated face
    camera = dict(eye=dict(x=2.0, y=-0.5, z=1.0), up=dict(x=0, y=0, z=1))
    fig.add_trace(mesh3d_trace(body, sab, name="Level 3 Fresnel"))
    fig.add_trace(colorbar_trace(float(np.max(sab))))

    fig.update_layout(
        title=dict(
            text=(
                f"DiffeRT street canyon at 28 GHz: {paths.n_paths} paths "
                f"({paths.los_paths.n_paths} LOS + {paths.nlos_paths.n_paths} NLOS), "
                f"peak S_ab = {result.peak_sab:.4f} W/m^2"
            ),
            x=0.5, font=dict(size=14, color="white"),
        ),
        scene=scene_layout(camera),
        paper_bgcolor="rgb(25,25,30)", font_color="white",
        width=900, height=700, margin=dict(l=0, r=0, t=60, b=0),
    )

    fig.write_image("examples/viz_differt_3d.png", scale=2)
    print(f"  Saved examples/viz_differt_3d.png")
    return fig


# ---------------------------------------------------------------------------
# 4. Animated GIF: MIMO exposure pattern morphing during optimization
# ---------------------------------------------------------------------------


def render_mimo_gif(G_tilde, h_j, x_mrt, body, signal_min, vmax):
    """Watch the exposure hotspot dissolve as the precoder optimizes."""
    print("Rendering MIMO optimization GIF (~30s)...")
    n_elements = G_tilde.shape[2]

    def loss(x_flat):
        x = x_flat[:n_elements] + 1j * x_flat[n_elements:]
        x = x / jnp.linalg.norm(x)
        sab = coherent_sab(G_tilde, x)
        peak = soft_peak_exposure(sab, temperature=50.0)
        sig = jnp.abs(jnp.vdot(h_j, x))**2
        return peak + 500.0 * jnp.maximum(signal_min - sig, 0.0)**2

    x_flat = jnp.concatenate([jnp.real(x_mrt), jnp.imag(x_mrt)])
    grad_fn = jax.jit(jax.grad(loss))

    # Collect frames at logarithmically spaced iterations
    frame_iters = sorted(set([0] + list(np.geomspace(1, 999, 30).astype(int))))
    frames = {}

    for i in range(1000):
        if i in frame_iters:
            x = x_flat[:n_elements] + 1j * x_flat[n_elements:]
            x = x / jnp.linalg.norm(x)
            sab = np.asarray(coherent_sab(G_tilde, x))
            sig = float(jnp.abs(jnp.vdot(h_j, x))**2)
            frames[i] = (sab, float(np.max(sab)), sig)
        x_flat = x_flat - 0.01 * grad_fn(x_flat)

    camera = dict(eye=dict(x=0.3, y=1.8, z=0.3), up=dict(x=0, y=0, z=1))
    images = []

    for i in sorted(frames.keys()):
        sab, peak, sig = frames[i]
        fig = go.Figure()
        fig.add_trace(mesh3d_trace(body, sab, vmax, ""))
        fig.add_trace(colorbar_trace(vmax))
        fig.update_layout(
            title=dict(
                text=f"Iter {i}: peak S_ab = {peak:.3f} W/m^2, signal = {sig:.3f}",
                x=0.5, font=dict(size=14, color="white"),
            ),
            scene=scene_layout(camera),
            paper_bgcolor="rgb(25,25,30)", font_color="white",
            width=700, height=550, margin=dict(l=0, r=0, t=55, b=0),
        )
        img_bytes = fig.to_image(format="png", scale=1.5)
        images.append(Image.open(io.BytesIO(img_bytes)))

    out = "examples/viz_mimo_anim.gif"
    images[0].save(out, save_all=True, append_images=images[1:], duration=250, loop=0)
    print(f"  Saved {out} ({len(images)} frames)")
    return out


if __name__ == "__main__":
    print("AEGIS 3D Visualization Demos")
    print()

    t0 = time.perf_counter()
    render_constrained_placement()
    mimo_data = render_mimo()
    render_differt()
    if mimo_data:
        render_mimo_gif(*mimo_data)
    elapsed = time.perf_counter() - t0

    print(f"\nAll done in {elapsed:.1f}s.")
