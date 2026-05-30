#!/usr/bin/env python3
"""Weave the extracted slide images into the whisper transcript.

Reads a plain transcript (segment lines of the form ``**[HH:MM:SS]** text``) and
the slide manifest written by extract_slides.py, then emits a transcript where
each slide image is inserted at the moment that slide appears on screen. Only the
segment lines are consumed, so re-running on the annotated output reproduces it.

Usage: python annotate_transcript.py [input.md]   (default: the bundle transcript)
"""
import json
import os
import re
import sys

BASE = "/home/user/aegis/spinoff/6g_webinar"
OUT = os.path.join(BASE, "transcript.md")
MANIFEST = os.path.join(BASE, "slides.json")
SEG_RE = re.compile(r"^\*\*\[(\d\d):(\d\d):(\d\d)\]\*\*\s*(.*)$")

HEADER = """# Enabling 6G Technologies - transcript

Ansys webinar presented by **Shawn Carpenter** (Program Director, Ansys), 26 June 2024.

Source: `../Enabling 6G Technologies.mp4` (01:00:06). Speech transcribed with
faster-whisper `large-v3` (float16, GPU). Slide images were auto-extracted from
the video; each `## Slide N` heading marks when that slide first appeared on
screen, so the deck reads alongside the talk. Combined deck: `slides.pdf`. See
`README.md` for how this was produced.

---
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else OUT
    with open(src, encoding="utf-8") as f:
        segments = []
        for line in f:
            m = SEG_RE.match(line.rstrip("\n"))
            if m:
                h, mn, s, text = m.groups()
                segments.append((int(h) * 3600 + int(mn) * 60 + int(s), text))

    with open(MANIFEST, encoding="utf-8") as f:
        slides = sorted(json.load(f), key=lambda x: x["start"])

    out, si = [HEADER], 0

    def flush_slides_until(sec):
        nonlocal si
        while si < len(slides) and slides[si]["start"] <= sec:
            sl = slides[si]
            out.append(f"\n## Slide {sl['n']} - appears [{sl['start_hms']}]\n")
            out.append(f"![Slide {sl['n']} (shown {sl['shown_hms']})]"
                       f"(slides/{sl['file']})\n")
            si += 1

    for sec, text in segments:
        flush_slides_until(sec)
        out.append(f"**[{_hms(sec)}]** {text}\n")
    flush_slides_until(10 ** 9)  # any trailing slides after the last words

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {OUT}: {len(segments)} segments, {len(slides)} slides woven in")


def _hms(t):
    return f"{t//3600:02d}:{(t%3600)//60:02d}:{t%60:02d}"


if __name__ == "__main__":
    main()
