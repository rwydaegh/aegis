#!/usr/bin/env python3
"""Reconstruct the underlying slide deck from a webinar screen-capture video.

The video is a full-frame slide capture (no webcam overlay). We detect slide
changes from per-second frame differences, collapse PowerPoint "build" steps and
live-demo runs by comparing the title band (top of the frame), drop near-black
fade frames, then export one crisp PNG per distinct slide plus a combined PDF.

Deps: ffmpeg/ffprobe on PATH, pillow, numpy. Usage: python extract_slides.py
"""
import glob
import json
import os
import subprocess
import tempfile

import img2pdf
import numpy as np
from PIL import Image

VIDEO = "/home/user/aegis/spinoff/Enabling 6G Technologies.mp4"
BASE = "/home/user/aegis/spinoff/6g_webinar"
SLIDES_DIR = os.path.join(BASE, "slides")

# tuned on this recording (640x360, 25fps, ~60min)
T_BIG = 10.0      # per-second mean-abs-diff (0..255) that marks a slide change
MIN_DWELL = 4     # segments shorter than this (s) are transient -> merged back
T_STRIP = 6.0     # title-band MAD below this => same slide (a build or demo run)
STRIP = slice(0, 16)   # top 16 of 90 analysis rows ~ the title band
MIN_LUMA = 25     # drop near-black fade/transition frames


def hms(t):
    t = int(round(t))
    return f"{t//3600:02d}:{(t%3600)//60:02d}:{t%60:02d}"


def main():
    os.makedirs(SLIDES_DIR, exist_ok=True)
    for f in glob.glob(f"{SLIDES_DIR}/*.png"):
        os.remove(f)

    with tempfile.TemporaryDirectory() as ana:
        # 1 fps grayscale thumbnails for change analysis
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", VIDEO,
             "-vf", "fps=1,scale=160:90:flags=area,format=gray",
             f"{ana}/%05d.png", "-y"], check=True)
        files = sorted(glob.glob(f"{ana}/*.png"))
        N = len(files)
        arr = np.stack([np.asarray(Image.open(f), dtype=np.float32) for f in files])
        d = np.mean(np.abs(np.diff(arr, axis=0)), axis=(1, 2))

        # segment into runs separated by large changes, drop transient runs
        raw = [i + 1 for i in range(len(d)) if d[i] > T_BIG]
        bounds = []
        for b in raw:
            if bounds and b - bounds[-1] <= 2:
                bounds[-1] = b
            else:
                bounds.append(b)
        cuts = [0] + bounds + [N]
        segs = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]
        merged = []
        for s, e in segs:
            if merged and (e - s) < MIN_DWELL:
                merged[-1] = (merged[-1][0], e)
            else:
                merged.append((s, e))

        # representative = calmest (settled) second in the 2nd half of each run
        def settled(s, e):
            lo = max(s + (e - s) // 2, s)
            hi = max(e - 1, lo)
            best, score = hi, 1e9
            for t in range(lo, hi + 1):
                v = (d[t - 1] if t > 0 else 0) + (d[t] if t < len(d) else 0)
                if v < score:
                    score, best = v, t
            return best

        reps = [settled(s, e) for s, e in merged]

        # collapse builds / demo runs that share the same title band; keep last
        groups = [[0]]
        for i in range(1, len(reps)):
            strip_mad = np.mean(np.abs(arr[reps[i], STRIP] - arr[reps[i - 1], STRIP]))
            if strip_mad < T_STRIP:
                groups[-1].append(i)
            else:
                groups.append([i])
        # one entry per group: on-screen start (first build) + settled frame (last build)
        curated = []
        for g in groups:
            settled_sec = reps[g[-1]]
            if arr[settled_sec].mean() < MIN_LUMA:   # skip near-black fade frames
                continue
            curated.append((merged[g[0]][0], settled_sec))

        # export the settled (most complete) full-res frame for each slide
        pages, manifest = [], []
        for n, (start_sec, t) in enumerate(curated, 1):
            name = f"slide_{n:02d}_{hms(t).replace(':', '-')}.png"
            dst = os.path.join(SLIDES_DIR, name)
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(t),
                 "-i", VIDEO, "-frames:v", "1", "-q:v", "2", dst, "-y"], check=True)
            pages.append(dst)
            manifest.append({"n": n, "file": name, "start": start_sec,
                             "start_hms": hms(start_sec), "shown": t,
                             "shown_hms": hms(t)})

    # combined PDF (one slide per page), lossless PNG embedding
    with open(os.path.join(BASE, "slides.pdf"), "wb") as pf:
        pf.write(img2pdf.convert(pages))

    with open(os.path.join(BASE, "slides.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"wrote {len(pages)} slides + slides.json + slides.pdf under {BASE}")


if __name__ == "__main__":
    main()
