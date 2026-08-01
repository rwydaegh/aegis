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
NOTES = {
    "toulouse_capitole": "reserve, anchor on a roofline",
    "istanbul_sultanahmet": "rejected, coarse base mesh, no photogrammetry",
}
FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
COLUMNS = 3
TILE_WIDTH = 620
TITLE = "Eleven squares, one pipeline, nothing hand placed"
SUB = [
    "Photorealistic 3D Tiles assembled in double precision, at a 130 m radius everywhere except Milan, which",
    "predates the set at 200 m. Framing is derived from each city's own geometry, so a 26 m square in Toulouse",
    "and a 255 m canyon in New York are framed alike. Sky fraction is measured from 1.5 m above the anchor.",
]


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONTS[0 if bold else 1], size)
    except OSError:
        return ImageFont.load_default()


def metrics() -> dict[str, dict[str, float]]:
    """Sky fraction and skyline height per site, if the quality pass recorded them."""
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
    caption, gap, pad, head = 62, 12, 22, 142
    rows = (len(tiles) + COLUMNS - 1) // COLUMNS
    width = pad * 2 + COLUMNS * TILE_WIDTH + (COLUMNS - 1) * gap
    height = head + rows * (tile_height + caption) + (rows - 1) * gap + pad
    canvas = Image.new("RGB", (width, height), (20, 21, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 20), TITLE, font=font(34, True), fill=(243, 243, 245))
    for index, line in enumerate(SUB):
        draw.text((pad, 64 + 24 * index), line, font=font(17), fill=(150, 152, 158))

    for index, (site, tile) in enumerate(zip(sites, tiles)):
        column, row = index % COLUMNS, index // COLUMNS
        x = pad + column * (TILE_WIDTH + gap)
        y = head + row * (tile_height + caption + gap)
        canvas.paste(tile, (x, y))
        draw.text((x, y + tile_height + 6), TITLES[site], font=font(19, True), fill=(238, 238, 242))
        detail = NOTES.get(site, "")
        if site in stats:
            numbers = f"{stats[site]['sky']:.0%} sky   {stats[site]['skyline_m']:.0f} m skyline"
            detail = f"{numbers}   {detail}" if detail else numbers
        colour = (206, 138, 120) if site in NOTES else (150, 152, 158)
        draw.text((x, y + tile_height + 32), detail, font=font(16), fill=colour)

    out = ROOT / "FIGURES/11_eleven_cities.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"wrote {out}  {canvas.size}  {len(sites)} sites")


if __name__ == "__main__":
    main()
