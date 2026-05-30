"""Slice each page PNG of a rendered deck into a 4x4 grid for close inspection."""
import sys
from pathlib import Path
from PIL import Image

src_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("_render")
out_dir = src_dir / "tiles"
out_dir.mkdir(exist_ok=True)
for f in sorted(out_dir.glob("*.png")):
    f.unlink()

pages = sorted(src_dir.glob("page-*.png"))
n = 2
for p in pages:
    img = Image.open(p)
    W, H = img.size
    stem = p.stem  # page-1
    tw, th = W // n, H // n
    for r in range(n):
        for c in range(n):
            box = (c * tw, r * th, (c + 1) * tw if c < n - 1 else W,
                   (r + 1) * th if r < n - 1 else H)
            tile = img.crop(box)
            tile.save(out_dir / f"{stem}_r{r}c{c}.png")
    print(f"{p.name}: {W}x{H} -> 16 tiles of ~{tw}x{th}")
print(f"tiles in {out_dir}")
