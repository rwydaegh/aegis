"""Contact sheet of every acquired city, with the numbers that decide its value.

The point of the sheet is comparison, so each tile carries the two quantities that
actually differ between these sites and drive exposure: how much of the sphere is
sky from a standing observer, and how tall the built form is. Sites that were
acquired and then rejected stay on the sheet, labelled, because the reason a site
failed is worth as much as the sites that passed.
"""

from __future__ import annotations

import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
GALLERY = ROOT / "outputs/city_gallery"
TITLES = {
    "mexico_zocalo": "Plaza de la Constitucion, Mexico City",
    "milan_duomo": "Piazza del Duomo, Milan",
    "prague_staromestske": "Staromestske namesti, Prague",
    "krakow_rynek": "Rynek Glowny, Krakow",
    "london_trafalgar": "Trafalgar Square, London",
    "madrid_plazamayor": "Plaza Mayor, Madrid",
    "brussels_grandplace": "Grand-Place, Brussels",
    "tokyo_hachiko": "Hachiko square, Shibuya, Tokyo",
    "newyork_timessquare": "Times Square, New York",
    "korenmarkt": "Korenmarkt, Ghent",
    "toulouse_capitole": "Place du Capitole, Toulouse",
    "istanbul_sultanahmet": "Sultanahmet Meydani, Istanbul",
}
#: Toulouse used to be labelled here as a reserve site whose anchor sat on a
#: roofline. That was the ground datum defect of GROUND_DATUM.md and not the
#: square, and Toulouse is one of the eleven in the published run.
NOTES = {
    "istanbul_sultanahmet": "rejected, coarse base mesh, no photogrammetry",
}
FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
COLUMNS = 3
TILE_WIDTH = 620
#: The sheet is placed at \textwidth in a two column IEEE float, so 1928 px of
#: canvas prints at about 269 ppi and a point size is a pixel size divided by
#: 3.74. Everything drawn on the sheet is set from that.
PX_PER_PT = 3.74
#: The headline and the four line standfirst that used to sit here said what the
#: LaTeX caption says, at 4.5 pt, which no printed page carries. Only the key to
#: the two numbers under each tile is kept, and it is set to be read.
SUB = [
    "Assembled at a 130 m radius everywhere except Milan, which predates the set at 200 m.",
    "Sky fraction is the median over that square's 80 standpoints. Skyline height is measured above the pavement.",
]
#: Light sheet, because every other figure in the paper is on white and a page
#: of solid black is a poor neighbour to them in print.
PAPER = (255, 255, 255)
INK = (26, 27, 30)
GREY = (96, 99, 105)
FLAG = (168, 62, 40)


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONTS[0 if bold else 1], size)
    except OSError:
        return ImageFont.load_default()


def fitted(draw, text: str, size: int, limit: int, bold: bool = False) -> ImageFont.ImageFont:
    """The largest font at or under ``size`` whose ``text`` fits inside ``limit``.

    A tile label that runs into its neighbour is not a small blemish on a contact
    sheet, it reads as though the neighbour is mislabelled. Mexico City's name
    and the Istanbul rejection note are both wider than a tile at full size.
    """
    for candidate in range(size, 8, -1):
        chosen = font(candidate, bold)
        if draw.textlength(text, font=chosen) <= limit:
            return chosen
    return font(9, bold)


def metrics() -> dict[str, dict[str, float]]:
    """Sky fraction and skyline height per site, from `measure_city_metrics.py`.

    Sky fraction is the median over that square's own walk in the published
    eleven city run rather than a reading at one anchor, because the anchor
    reading was taken at a ground level that put the observer on the Sukiennice
    at Krakow and inside the Capitole at Toulouse.
    """
    path = ROOT / "outputs/city_gallery/metrics.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def main() -> None:
    stats = metrics()
    sites = [s for s in TITLES if (GALLERY / f"{s}.png").is_file()]
    tiles = []
    for site in sites:
        image = Image.open(GALLERY / f"{site}.png").convert("RGB")
        scale = TILE_WIDTH / image.width
        tiles.append(image.resize((TILE_WIDTH, int(image.height * scale)), Image.LANCZOS))

    tile_height = tiles[0].height
    # Point sizes first, pixels second, so the sheet is set the way the rest of
    # the figures are.
    name_px = round(8.5 * PX_PER_PT)
    detail_px = round(7.2 * PX_PER_PT)
    sub_px = round(7.2 * PX_PER_PT)
    line = round(1.45 * sub_px)

    caption, gap, pad = name_px + detail_px + 26, 12, 22
    head = line * len(SUB) + 16
    rows = (len(tiles) + COLUMNS - 1) // COLUMNS
    width = pad * 2 + COLUMNS * TILE_WIDTH + (COLUMNS - 1) * gap
    height = head + rows * (tile_height + caption) + (rows - 1) * gap + pad
    canvas = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(canvas)
    for index, sentence in enumerate(SUB):
        draw.text((pad, 2 + line * index), sentence, font=font(sub_px), fill=GREY)

    for index, (site, tile) in enumerate(zip(sites, tiles)):
        column, row = index % COLUMNS, index // COLUMNS
        x = pad + column * (TILE_WIDTH + gap)
        y = head + row * (tile_height + caption + gap)
        canvas.paste(tile, (x, y))
        name = TITLES[site]
        draw.text((x, y + tile_height + 8), name, font=fitted(draw, name, name_px, TILE_WIDTH, True), fill=INK)
        detail = NOTES.get(site, "")
        if site in stats:
            numbers = f"{stats[site]['sky_median']:.0%} sky   {stats[site]['skyline_m']:.0f} m skyline"
            detail = f"{numbers}   {detail}" if detail else numbers
        colour = FLAG if site in NOTES else GREY
        draw.text(
            (x, y + tile_height + 14 + name_px),
            detail,
            font=fitted(draw, detail, detail_px, TILE_WIDTH),
            fill=colour,
        )

    out = ROOT / "FIGURES/11_eleven_cities.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"wrote {out}  {canvas.size}  {len(sites)} sites")


if __name__ == "__main__":
    main()
