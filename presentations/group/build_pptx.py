"""Build the final single PPTX by merging Beamer images + Manim animation PPTXs.

Uses ZIP-level manipulation to copy slides with embedded videos from
manim-slides PPTXs into the beamer image PPTX.

Usage: python build_pptx.py
Output: geometric_dosimetry.pptx
"""

import shutil
import subprocess
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

# Register namespaces so we don't mangle the XML
NSMAP = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
for prefix, uri in NSMAP.items():
    ET.register_namespace(prefix, uri)
# Also register common namespaces found in PPTX
ET.register_namespace("", "http://schemas.openxmlformats.org/presentationml/2006/main")
ET.register_namespace("mc", "http://schemas.openxmlformats.org/markup-compatibility/2006")


HERE = Path(__file__).parent

# Animation placeholder pages (1-indexed in the PDF).
# These get REPLACED by the animation PPTX slides.
# Slide 2 has 2 overlays, slide 3 has 4, so:
# page 1=title, 2-3=slide2, 4-7=slide3, 8=anim1 placeholder,
# 9-10=slide5, 11=anim2 placeholder, 12-14=slide7,
# 15=demo intro, 16=live demo, 17-19=slide10,
# 20=anim3 placeholder, 21-22=slide12, 23=summary, 24=thankyou
ANIMATION_PAGES = {
    8: HERE / "animations" / "PseudoBrewster.pptx",
    11: HERE / "animations" / "GeometryOfAbsorption.pptx",
    20: HERE / "animations" / "CoherentPhasors.pptx",
}


def pdf_to_images(pdf_path, output_dir, dpi=300):
    """Convert PDF pages to PNG images using pdftoppm."""
    prefix = output_dir / "slide"
    subprocess.run(
        ["pdftoppm", str(pdf_path), str(prefix), "-png", "-r", str(dpi)],
        check=True,
    )
    return sorted(output_dir.glob("slide-*.png"))


def build_simple():
    """Build by creating a base PPTX from beamer images, then splicing
    animation PPTXs at the right positions using a two-pass approach.

    Pass 1: Create beamer_only.pptx with all beamer image slides
            (skipping animation placeholders).
    Pass 2: For each animation position, insert the animation PPTX slides.

    Since python-pptx cannot copy slides between presentations easily,
    we use a simpler approach: create the FULL presentation as images,
    but for animation pages, extract frames from the animation MP4s
    and embed the MP4 as a video that auto-plays.
    """
    from pptx import Presentation
    from pptx.util import Inches, Emu, Pt

    SLIDE_WIDTH = Inches(13.333)
    SLIDE_HEIGHT = Inches(7.5)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Convert PDF to images
        pdf_path = HERE / "main.pdf"
        if not pdf_path.exists():
            print("ERROR: main.pdf not found.")
            return

        print("Converting Beamer PDF to images...")
        images = pdf_to_images(pdf_path, tmpdir, dpi=300)
        print(f"  {len(images)} pages")

        prs = Presentation()
        prs.slide_width = SLIDE_WIDTH
        prs.slide_height = SLIDE_HEIGHT

        print("Building presentation...")
        for i, img in enumerate(images):
            page_num = i + 1

            if page_num in ANIMATION_PAGES:
                anim_pptx = ANIMATION_PAGES[page_num]
                print(f"  Page {page_num}: inserting animation slides from {anim_pptx.name}")

                # Open the animation PPTX and extract each slide as an image
                # + embed the video on the first slide
                anim_prs = Presentation(str(anim_pptx))
                mp4_path = anim_pptx.with_suffix(".mp4")

                for j, anim_slide in enumerate(anim_prs.slides):
                    blank = prs.slide_layouts[6]
                    new_slide = prs.slides.add_slide(blank)

                    # Extract slide image from animation PPTX
                    # Each manim-slides PPTX slide has an image shape
                    for shape in anim_slide.shapes:
                        if hasattr(shape, "image") and shape.image is not None:
                            blob = shape.image.blob
                            img_tmp = tmpdir / f"anim_{page_num}_{j}.png"
                            img_tmp.write_bytes(blob)
                            new_slide.shapes.add_picture(
                                str(img_tmp),
                                Emu(0), Emu(0),
                                SLIDE_WIDTH, SLIDE_HEIGHT,
                            )
                            break
                    else:
                        # No image found, add a black slide
                        from pptx.util import Emu as E
                        from pptx.dml.color import RGBColor
                        bg = new_slide.background
                        fill = bg.fill
                        fill.solid()
                        fill.fore_color.rgb = RGBColor(0, 0, 0)

                print(f"    ({len(anim_prs.slides)} slides)")
            else:
                # Regular beamer slide
                blank = prs.slide_layouts[6]
                slide = prs.slides.add_slide(blank)
                slide.shapes.add_picture(
                    str(img),
                    Emu(0), Emu(0),
                    SLIDE_WIDTH, SLIDE_HEIGHT,
                )

        output = HERE / "geometric_dosimetry.pptx"
        prs.save(str(output))
        print(f"\nDone! {output}")
        print(f"  {len(prs.slides)} total slides")
        print(f"\nNote: Animation slides are static frames (click-to-advance).")
        print(f"The videos don't auto-play in this version, but each")
        print(f"manim-slides breakpoint is a separate slide with its")
        print(f"frame, so click-through works naturally.")


if __name__ == "__main__":
    build_simple()
