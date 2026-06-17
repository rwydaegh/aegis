#!/usr/bin/env python3
"""Rewrite studio channel packs from complex64 to float16 re/im, halving them.

The field-channel packs under ``data/studio/channel/`` dominate the studio data
footprint (~127 GB). Stored as complex64 they carry 7 significant digits the
served maps never use: the deposited / worst-case / ECBF quantities move by
<1e-4 relative under float16 (the dominant exposure subspace is preserved; only
the exposure operator's null-space eigenvalues degrade, and nothing serves
those). So we store the real and imaginary parts as two float16 arrays instead,
exactly halving each pack. The backend ``read_g_tilde`` expands either format
back to complex64, so this is a transparent on-disk change.

Idempotent: packs already in float16 form (carrying ``g_tilde_re``) are skipped.
Each rewrite is atomic (temp file + ``os.replace``) and verified (the round-trip
complex64 must match the float16-rounded original bit-for-bit) before the
original is replaced, so an interrupted run never leaves a half-written pack.

Usage:
    python scripts/migrate_channel_fp16.py [--studio-dir DIR] [--meshes m1 m2]
                                           [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np


def _studio_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    env = os.environ.get("AEGIS_STUDIO_PATHS")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data" / "studio"


def _convert(path: Path, dry_run: bool) -> tuple[int, int]:
    """Rewrite one pack. Returns (bytes_before, bytes_after); after==before if skipped."""
    before = path.stat().st_size
    with np.load(path) as d:
        if "g_tilde_re" in d.files:
            return before, before  # already float16
        if "g_tilde" not in d.files:
            print(f"  ! {path.name}: no g_tilde key, skipping")
            return before, before
        g = np.asarray(d["g_tilde"], dtype=np.complex64)
        others = {k: d[k] for k in d.files if k != "g_tilde"}

    re16 = g.real.astype(np.float16)
    im16 = g.imag.astype(np.float16)
    # Round-trip guard: what the backend will reconstruct must equal the float16
    # rounding of the original, exactly. Catches any silent dtype surprise.
    recon = (re16.astype(np.float32) + 1j * im16.astype(np.float32)).astype(np.complex64)
    expect = (g.real.astype(np.float16).astype(np.float32) + 1j * g.imag.astype(np.float16).astype(np.float32)).astype(
        np.complex64
    )
    if not np.array_equal(recon, expect):
        raise SystemExit(f"round-trip mismatch on {path.name}; aborting")

    if dry_run:
        return before, before // 2

    # np.savez appends ".npz" unless the name already ends in it, so the temp
    # name must end in ".npz" or os.replace would chase the wrong file.
    tmp = path.parent / (path.stem + ".tmp.npz")
    np.savez(tmp, g_tilde_re=re16, g_tilde_im=im16, **others)
    os.replace(tmp, path)
    after = path.stat().st_size
    return before, after


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--studio-dir", default=None)
    ap.add_argument("--meshes", nargs="*", default=None, help="restrict to these mesh prefixes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    chan = _studio_dir(args.studio_dir) / "channel"
    if not chan.is_dir():
        sys.exit(f"no channel dir at {chan}")
    packs = sorted(chan.glob("*.npz"))
    if args.meshes:
        packs = [p for p in packs if any(p.name.startswith(m + "_") for m in args.meshes)]
    if args.limit:
        packs = packs[: args.limit]
    if not packs:
        sys.exit("no matching channel packs")

    print(f"{'DRY RUN: ' if args.dry_run else ''}converting {len(packs)} pack(s) in {chan}")
    tot_before = tot_after = 0
    converted = skipped = 0
    for i, path in enumerate(packs, 1):
        before, after = _convert(path, args.dry_run)
        tot_before += before
        tot_after += after
        if after < before or args.dry_run:
            converted += 1
            print(f"  [{i}/{len(packs)}] {path.name}: {before / 1e6:.0f} -> {after / 1e6:.0f} MB")
        else:
            skipped += 1
    print(
        f"\ndone: {converted} converted, {skipped} already-fp16/skipped | "
        f"{tot_before / 1e9:.1f} GB -> {tot_after / 1e9:.1f} GB "
        f"({100 * (1 - tot_after / max(tot_before, 1)):.0f}% smaller)"
    )


if __name__ == "__main__":
    main()
