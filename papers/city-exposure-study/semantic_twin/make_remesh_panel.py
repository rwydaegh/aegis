"""Three support meshes, same camera, with what each one costs written on it."""

import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path("/home/user/aegis/papers/city-exposure-study/semantic_twin")
PANELS = [
    (
        "orbit_as_built_157k.png",
        "As built",
        "157,862 triangles",
        "median wall flatness 10.1 deg   16.6 % boundary edges   431 components",
    ),
    (
        "orbit_closed_1m_86k.png",
        "Voxel remesh, 1 m",
        "85,853 triangles",
        "flatness 10.2 deg   0 boundary edges   0.51 m median range error",
    ),
    (
        "orbit_flat_2m_87k.png",
        "Voxel remesh, 2 m",
        "86,656 triangles",
        "flatness 6.1 deg   0 boundary edges   2.68 m median range error",
    ),
]
TITLE = "Voxel remeshing does not clean the wall, it removes the building"
SUB = [
    "Korenmarkt, same camera. Closure and half the triangles cost the building form.",
    "The flatness column improves in exact proportion to how much geometry the grid cannot hold.",
]

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONTS[0 if bold else 1], size)
    except OSError:
        return ImageFont.load_default()


images = [Image.open(ROOT / name).convert("RGB") for name, *_ in PANELS]
w, h = images[0].size
scale = 1100 / w
w, h = int(w * scale), int(h * scale)
images = [im.resize((w, h), Image.LANCZOS) for im in images]

head, caption, gap, pad = 116, 104, 18, 26
canvas = Image.new("RGB", (w + 2 * pad, head + 3 * (h + caption) + 2 * gap + pad), (22, 23, 26))
draw = ImageDraw.Draw(canvas)
draw.text((pad, 18), TITLE, font=font(30, True), fill=(242, 242, 244))
for line_number, line in enumerate(SUB):
    draw.text((pad, 58 + 24 * line_number), line, font=font(17), fill=(150, 152, 158))

y = head
for image, (_, label, tris, numbers) in zip(images, PANELS):
    canvas.paste(image, (pad, y))
    y += h
    draw.text((pad, y + 8), label, font=font(25, True), fill=(242, 242, 244))
    draw.text((pad + 320, y + 12), tris, font=font(20), fill=(196, 198, 204))
    draw.text((pad, y + 44), numbers, font=font(18), fill=(150, 152, 158))
    y += caption + gap

out = ROOT / "FIGURES/10_remesh_visual.png"
canvas.save(out)
print(f"wrote {out}  {canvas.size}")
