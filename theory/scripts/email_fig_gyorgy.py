import sys, os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Circle
import scienceplots
# Insert scripts dir to load geometry and data
import sys
sys.path.insert(0, 'scripts')

from _geom import load_stl_binary, triangle_areas
from _plot_style import apply_monograph_style
apply_monograph_style(mode='png')

# Parameters
STL_NAME = 'duke'
D_REF = 0.30  # 30 cm
EIRP_W = 0.1995  # 23 dBm
T0 = 0.5302  # at 26 GHz

# Load mesh
v, n, c = load_stl_binary('data/duke.stl')
a = triangle_areas(v)

# Head region logic mimicking the previous correct code
ext = c.max(axis=0) - c.min(axis=0)
up_axis = np.argmax(ext)
z_thr = c.max(axis=0)[up_axis] - 0.15 * ext[up_axis]  # top 15%
head_mask = c[:, up_axis] > z_thr
head_c = c[head_mask]
head_n = n[head_mask]

# Find fb axis
horizontal_axes = [i for i in range(3) if i != up_axis]
head_ext = head_c.max(axis=0) - head_c.min(axis=0)
fb_axis = min(horizontal_axes, key=lambda i: head_ext[i])

# Check all 4 horizontal directions to find face
forward_candidates = []
for axis in horizontal_axes:
    for sign in [1, -1]:
        direction = np.zeros(3)
        direction[axis] = sign
        dots = head_n @ direction
        forward_candidates.append((np.sum(dots > 0.3), direction))
forward_candidates.sort(key=lambda x: -x[0])
face_direction = forward_candidates[0][1]

# Face center
face_mask_local = (head_n @ face_direction) > 0.3
face_center = head_c[face_mask_local].mean(axis=0)

# Find the furthest point (nose tip)
head_c = c[head_mask]
head_n = n[head_mask]
projections = head_c @ face_direction
nose_tip_proj = np.max(projections)
nose_tip_point = face_center + (nose_tip_proj - (face_center @ face_direction)) * face_direction

# Source position (30cm from nose)
source_pos = nose_tip_point + D_REF * face_direction

# Calculate S_ab
diff = source_pos[None, :] - head_c
d_sq = np.sum(diff**2, axis=1)
d = np.sqrt(d_sq)
k_hat = diff / d[:, None]
mu = np.sum(head_n * k_hat, axis=1)
mu_pos = np.maximum(mu, 0.0)

sinc = EIRP_W / (4 * np.pi * d_sq)
sab = sinc * T0 * mu_pos

# Setup figure (1x2 subplots, 3.5x2 inches)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.5, 2.0), gridspec_kw={'width_ratios': [1, 1]})

# We want a 2D front view.
# Duke is +X forward, +Y right?, +Z up.
# For a front view, looking down the face direction.
up_axis = 2
if face_direction[0] != 0:
    horiz_axis = 1
    depth_axis = 0
elif face_direction[1] != 0:
    horiz_axis = 0
    depth_axis = 1
else:
    horiz_axis = 0 # Backup
    depth_axis = 1

# --- Panel 1: Front View ---
# We only plot triangles facing front
front_facing = (head_n @ face_direction) > 0.0

# Extract the front-facing triangles
v_head = v[head_mask]
v_front = v_head[front_facing]

# Project out the depth axis so we get 2D polygons (N, 3, 2)
# The order of coordinates for our 2D view is [horiz_axis, up_axis]
verts_2d_front = np.stack((v_front[:, :, horiz_axis] * 100, v_front[:, :, up_axis] * 100), axis=-1)

poly_front = PolyCollection(verts_2d_front, array=sab[front_facing], cmap='inferno', edgecolors='none', rasterized=True)
poly_front.set_clim(vmin=0, vmax=0.10)

ax1.add_collection(poly_front)
ax1.autoscale_view()
ax1.set_aspect('equal')
ax1.axis('off')
ax1.set_title(r'Front View', fontsize=7)

# --- Panel 2: Profile View ---
# For profile, we plot depth_axis vs up_axis.
# We want the face pointing to the right, so we might need to flip the depth axis if face_direction < 0
sign = np.sign(face_direction[depth_axis])

# To make a nice solid profile, we can plot all head triangles or just half
# Plotting all is fine. For the 2D polygons:
verts_2d_profile = np.stack((v_head[:, :, depth_axis] * sign * 100, v_head[:, :, up_axis] * 100), axis=-1)

# To sort polygons from back to front (painter's algorithm) so they render correctly:
# the "depth" in this side-view is horiz_axis
depth_vals = np.mean(v_head[:, :, horiz_axis], axis=1)
# sort so we draw the furthest first. 
# Depending on view, let's just draw all of them or maybe just face. painter's is better.
sort_idx = np.argsort(depth_vals)
verts_2d_profile_sorted = verts_2d_profile[sort_idx]
sab_sorted = sab[sort_idx]

poly_profile = PolyCollection(verts_2d_profile_sorted, array=sab_sorted, cmap='inferno', edgecolors='none', rasterized=True)
poly_profile.set_clim(vmin=0, vmax=0.10)

ax2.add_collection(poly_profile)

# Phone location
phone_y = source_pos[depth_axis] * sign * 100
phone_z = source_pos[up_axis] * 100

# Draw a marker for the phone
ax2.plot(phone_y, phone_z, marker='s', color='black', markersize=3)
ax2.text(phone_y + 1, phone_z, ' Phone', fontsize=6, va='center', ha='left')

# Draw a faint line connecting phone to nose tip
# Find the furthest point (nose tip)
nose_idx = np.argmax(v_head[:, :, depth_axis].max(axis=1) * sign)
nose_y = v_head[nose_idx, :, depth_axis].max() * sign * 100
nose_z = face_center[up_axis] * 100

ax2.plot([nose_y, phone_y], [nose_z, phone_z], color='gray', linestyle=':', linewidth=0.5)

# Calculate the distance from nose tip to phone
dist_nose_to_phone = (phone_y - nose_y)
ax2.text((nose_y + phone_y)/2, nose_z - 3, '30 cm', fontsize=5, ha='center', va='top', color='gray')

# Add a simple transparent sphere representing EIRP
eirp_sphere = Circle((phone_y, phone_z), radius=dist_nose_to_phone / 3, 
                     edgecolor='gray', facecolor='gray', alpha=0.05, lw=0.5)
ax2.add_patch(eirp_sphere)

ax2.autoscale_view()
ax2.set_aspect('equal')
ax2.axis('off')
ax2.set_xlim(ax2.get_xlim()[0], phone_y + (dist_nose_to_phone / 3) + 5) # Ensure sphere fits
ax2.set_title(r'Profile View', fontsize=7)

# Add a shared colorbar
plt.tight_layout(pad=1.5, w_pad=2, rect=[0, 0.08, 1, 0.90])
# Adjust layout to make room for colorbar
fig.subplots_adjust(bottom=0.25)
cbar_ax = fig.add_axes([0.15, 0.1, 0.7, 0.05])
cb = plt.colorbar(poly_profile, cax=cbar_ax, orientation='horizontal')
cb.set_label(r'Absorbed Power Density (W/m$^2$)', fontsize=7, labelpad=2)
cb.ax.tick_params(labelsize=6)
cb.outline.set_linewidth(0.5)

# Overall title
fig.suptitle(r'Phone at 30 cm, 26 GHz (Duke Phantom)', fontsize=9, y=0.98)

# Output directory
out_dir = Path('artifacts/phone_exposure_26ghz')
out_dir.mkdir(parents=True, exist_ok=True)

fig.savefig(out_dir / 'email_figure_gyorgy.pdf', bbox_inches='tight')
fig.savefig(out_dir / 'email_figure_gyorgy.png', dpi=400, bbox_inches='tight')
