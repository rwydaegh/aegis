import re
import numpy as np
import matplotlib.pyplot as plt
from xml.etree import ElementTree as ET  # kept for compatibility, even if unused


class AntennaPattern:
    def __init__(
        self,
        horizontal_pattern: list[str],
        vertical_pattern: list[str] = None,
        max_gain_dbi: float = 0,
    ):
        # Store as float arrays (same as original behaviour)
        self.horizontal_pattern = np.array(horizontal_pattern, dtype=float)
        self.vertical_pattern = (
            np.array(vertical_pattern, dtype=float) if vertical_pattern is not None else None
        )
        self.max_gain_dbi = max_gain_dbi

    def plot_2dpattern(self, orientation=None, title: str = "Antenna Pattern") -> plt.Figure:
        """The patterns are list of values of the gain (360 values for horizontal, 360 for vertical)"""
        if orientation == "Horizontal":
            pattern = self.horizontal_pattern
        elif orientation == "Vertical":
            pattern = self.vertical_pattern
        else:
            raise ValueError("Orientation must be 'Horizontal' or 'Vertical'")

        if pattern is None:
            raise ValueError(f"No {orientation} pattern data available.")

        angles = np.arange(0, 360)
        # convert gains from linear to dBi if necessary (preserve original logic)
        gains = 10 * np.log10(pattern)

        fig, ax = plt.subplots(subplot_kw={"projection": "polar"})
        ax.plot(np.deg2rad(angles), gains)
        ax.set_title(title)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_rlabel_position(90)
        ax.grid(True)
        return fig

    def get_3dpattern(self, return_angles: bool = False):
        """
        Generate a 3D gain matrix (dBi) for elevation -90..+90 and azimuth -180..179.

        Behaviour matches the original implementation but uses vectorized numpy
        operations for speed.
        """
        if self.vertical_pattern is None:
            raise ValueError("No vertical pattern data available for 3D pattern.")
        if self.horizontal_pattern is None:
            raise ValueError("No horizontal pattern data available for 3D pattern.")

        # Angles
        elevation_angles = np.arange(-90, 91, dtype = np.int16)   # -90 to +90  (181 values)
        azimuth_angles = np.arange(-180, 180, dtype = np.int16)   # -180 to 179 (360 values)

        # Normalise patterns (same as original)
        vert = np.array(self.vertical_pattern, dtype=np.float16)
        horiz = np.array(self.horizontal_pattern, dtype=np.float16)

        max_v = np.max(vert)
        max_h = np.max(horiz)
        # Avoid division by zero; if max is 0, keep as zeros (will become NaN later)
        normalized_vert = vert / max_v if max_v != 0 else vert
        normalized_horiz = horiz / max_h if max_h != 0 else horiz

        # Map elevation -90..+90 to indices 0..360 via index_vert = abs(elev - 90)
        # For elev = -90..+90, this yields [180, 179, ..., 0]
        vert_indices = np.abs(elevation_angles - 90)
        vert_vec = normalized_vert[vert_indices]  # shape (181,)

        # Map azimuth -180..179 to indices 0..359 via index_horiz = (azim + 360) % 360
        az_indices = (azimuth_angles + 360) % 360
        horiz_vec = normalized_horiz[az_indices]  # shape (360,)

        # Outer product to get linear gain matrix
        glin = np.outer(vert_vec, horiz_vec)  # shape (181, 360)

        # Convert to dB; where glin == 0, we set NaN as in original (which skipped zeros)
        gain_matrix = np.full_like(glin, np.nan, dtype=np.float16)
        nonzero_mask = glin > 0
        gain_matrix[nonzero_mask] = 10 * np.log10(glin[nonzero_mask]) + self.max_gain_dbi

        if return_angles:
            return gain_matrix, elevation_angles, azimuth_angles
        else:
            return gain_matrix

    def plot_3dpattern(self, title: str = "3D Antenna Pattern (Gain Radius)") -> plt.Figure:
        """
        Plot a 3D antenna gain pattern as a spherical surface where
        the radius equals the gain (in dB) in that direction.
        """
        # gain_matrix in dBi
        gain_matrix = np.nan_to_num(self.get_3dpattern())

        # angle grids
        az = np.deg2rad(np.arange(0, 360))      # azimuth angles
        el = np.deg2rad(np.arange(-90, 91))     # elevation angles
        Az, El = np.meshgrid(az, el)

        # convert gain (dB) to a radial distance (relative scale)
        r = 10 ** ((gain_matrix - gain_matrix.max()) / 20)

        # spherical → Cartesian
        X = r * np.cos(El) * np.cos(Az)
        Y = r * np.cos(El) * np.sin(Az)
        Z = r * np.sin(El)

        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")

        # normalize color values between min and max gain
        norm = plt.Normalize(vmin=gain_matrix.min(), vmax=gain_matrix.max())
        colors = plt.cm.viridis(norm(gain_matrix))

        surf = ax.plot_surface(
            X,
            Y,
            Z,
            facecolors=colors,
            rstride=2,
            cstride=2,
            linewidth=0,
            antialiased=True,
        )

        ax.set_title(title)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_box_aspect([1, 1, 1])
        ax.view_init(elev=25, azim=45)
        ax.grid(False)

        # colorbar
        mappable = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
        mappable.set_array([])
        fig.colorbar(mappable, ax=ax, shrink=0.6, pad=0.1, label="Gain (dBi)")

        return fig

    def _3d_pattern_heatmap(self):
        gain_matrix = np.nan_to_num(self.get_3dpattern())  # in dBi

        fig, ax = plt.subplots(figsize=(10, 5))
        cax = ax.imshow(
            gain_matrix,
            extent=[-180, 180, -90, 90],
            aspect="auto",
            cmap="viridis",
        )
        ax.set_title("Antenna 3D Pattern Heatmap")
        ax.set_xlabel("Azimuth (degrees)")
        ax.set_ylabel("Elevation (degrees)")
        fig.colorbar(cax, label="Gain (dBi)")
        return fig
