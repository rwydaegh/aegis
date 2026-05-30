"""
Minimal example: write a Huygens Box ASCII (.txt) input file for Sim4Life.

The format follows the Sim4Life Reference Guide v7.2, Section 5.3,
pages 172 to 173. The file can be loaded by setting the Huygens
Source 'Input Type' to 'File'.

The grid must be uniform rectilinear. Each axis line carries
    (lower-corner-coordinate, number-of-points, step)
so that x_i = x0 + i * dx for i = 0, 1, ..., nx-1.

The fields are written in the order (slowest to fastest axis):
    for i_x in range(nx):
        for i_y in range(ny):
            for i_z in range(nz):
                write one line with E (or H) at point (x_i, y_j, z_k)
Each line in the e-field block contains six numbers:
    Re(E_x)  Im(E_x)  Re(E_y)  Im(E_y)  Re(E_z)  Im(E_z)
The h-field block has the same layout for H.

All six field components live on the same grid node, so no Yee
staggering is needed on your side. Sim4Life handles the projection
to its internal Yee grid.
"""

from __future__ import annotations

import numpy as np


def write_huygens_txt(
    path: str,
    x0: float, dx: float, nx: int,
    y0: float, dy: float, ny: int,
    z0: float, dz: float, nz: int,
    frequency_hz: float,
    incident_power_w: float,
    E: np.ndarray,  # shape (3, nx, ny, nz), complex
    H: np.ndarray,  # shape (3, nx, ny, nz), complex
) -> None:
    """Write a Huygens Box .txt file in the Sim4Life-expected format."""

    assert E.shape == (3, nx, ny, nz), f"E shape mismatch: {E.shape}"
    assert H.shape == (3, nx, ny, nz), f"H shape mismatch: {H.shape}"
    assert np.iscomplexobj(E) and np.iscomplexobj(H), "E and H must be complex"

    with open(path, "w", encoding="ascii") as f:
        f.write("<huygens>\n")
        f.write("<axes>\n")
        f.write(f"{x0:.10g} {nx} {dx:.10g}\n")
        f.write(f"{y0:.10g} {ny} {dy:.10g}\n")
        f.write(f"{z0:.10g} {nz} {dz:.10g}\n")
        f.write("</axes>\n")

        f.write("<frequency>\n")
        f.write(f"{frequency_hz:.10g}\n")
        f.write("</frequency>\n")

        f.write("<incident-power>\n")
        f.write(f"{incident_power_w:.10g}\n")
        f.write("</incident-power>\n")

        f.write("<e-field>\n")
        for ix in range(nx):
            for iy in range(ny):
                for iz in range(nz):
                    ex, ey, ez = E[0, ix, iy, iz], E[1, ix, iy, iz], E[2, ix, iy, iz]
                    f.write(
                        f"{ex.real:.6e} {ex.imag:.6e} "
                        f"{ey.real:.6e} {ey.imag:.6e} "
                        f"{ez.real:.6e} {ez.imag:.6e}\n"
                    )
        f.write("</e-field>\n")

        f.write("<h-field>\n")
        for ix in range(nx):
            for iy in range(ny):
                for iz in range(nz):
                    hx, hy, hz = H[0, ix, iy, iz], H[1, ix, iy, iz], H[2, ix, iy, iz]
                    f.write(
                        f"{hx.real:.6e} {hx.imag:.6e} "
                        f"{hy.real:.6e} {hy.imag:.6e} "
                        f"{hz.real:.6e} {hz.imag:.6e}\n"
                    )
        f.write("</h-field>\n")
        f.write("</huygens>\n")


if __name__ == "__main__":
    # Toy demo: a 0.5 m cube around the origin with a 25 mm step.
    # E and H here are placeholders. Replace with values from your
    # own simulator, sampled at the same x, y, z grid points.
    x0, dx, nx = -0.25, 0.025, 21
    y0, dy, ny = -0.25, 0.025, 21
    z0, dz, nz = -0.25, 0.025, 21

    E = np.zeros((3, nx, ny, nz), dtype=complex)
    H = np.zeros((3, nx, ny, nz), dtype=complex)

    # Example: a simple plane wave travelling along +x, polarised along y.
    # Replace this block with your own simulator output on the same grid.
    k0 = 2 * np.pi * 1e9 / 2.998e8  # 1 GHz wavenumber in vacuum
    eta0 = 376.73
    xs = x0 + dx * np.arange(nx)
    for ix, x in enumerate(xs):
        phase = np.exp(-1j * k0 * x)
        E[1, ix, :, :] = phase
        H[2, ix, :, :] = phase / eta0

    write_huygens_txt(
        "demo_huygens_input.txt",
        x0, dx, nx, y0, dy, ny, z0, dz, nz,
        frequency_hz=1.0e9,
        incident_power_w=1.0,
        E=E,
        H=H,
    )
    print("Wrote demo_huygens_input.txt")
