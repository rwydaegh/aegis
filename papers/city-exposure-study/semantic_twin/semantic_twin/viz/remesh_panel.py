"""Three support meshes, same camera, with what each one costs written on it."""

from PIL import Image, ImageDraw, ImageFont
from semantic_twin import paths
from semantic_twin.viz import figures

ROOT = paths.root()
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


def compose_remesh_panel() -> None:
    images = [Image.open(ROOT / name).convert("RGB") for name, *_ in PANELS]
    width, height = images[0].size
    scale = 1100 / width
    width, height = int(width * scale), int(height * scale)
    images = [image.resize((width, height), Image.LANCZOS) for image in images]

    head, caption, gap, pad = 116, 104, 18, 26
    canvas = Image.new(
        "RGB",
        (width + 2 * pad, head + 3 * (height + caption) + 2 * gap + pad),
        (22, 23, 26),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 18), TITLE, font=font(30, True), fill=(242, 242, 244))
    for line_number, line in enumerate(SUB):
        draw.text((pad, 58 + 24 * line_number), line, font=font(17), fill=(150, 152, 158))

    y = head
    for image, (_, label, triangles, numbers) in zip(images, PANELS, strict=True):
        canvas.paste(image, (pad, y))
        y += height
        draw.text((pad, y + 8), label, font=font(25, True), fill=(242, 242, 244))
        draw.text((pad + 320, y + 12), triangles, font=font(20), fill=(196, 198, 204))
        draw.text((pad, y + 44), numbers, font=font(18), fill=(150, 152, 158))
        y += caption + gap

    out = figures.get("remesh_visual").path()
    canvas.save(out)
    print(f"wrote {out}  {canvas.size}")
