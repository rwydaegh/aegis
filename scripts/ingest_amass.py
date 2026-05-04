"""Ingest AMASS .npz sequences into per-body pose streams at 30 Hz.

AMASS (https://amass.is.tue.mpg.de/) ships per-subject `.tar.bz2` archives.
Each archive contains many `.npz` sequences keyed roughly:

    poses             (T, P)   axis-angle, P=156 (SMPL-H) or 165 (SMPL-X)
    trans             (T, 3)   root translation in metres
    betas             (B,)     body-shape coeffs, B in {10, 16}
    gender            ()       'male' / 'female' / 'neutral'
    mocap_framerate   ()       float, e.g. 30, 60, 100, 120

This script walks a directory of extracted AMASS data, picks sequences
whose filename matches a substring filter (default: 'walk'), resamples
each onto a target frame rate (default 30 Hz), and writes one compact
`.npz` per body into ``data/poses/`` for the plaza scenario to consume.

Usage:

    python scripts/ingest_amass.py \\
        --input ~/data/amass \\
        --output data/poses \\
        --max-sequences 50

Run with ``--dry-run`` to preview the picks without writing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aegis.geometry.pose_stream import PoseStream, resample_axis_angle  # noqa: E402


def find_sequences(input_dir: Path, name_filter: str | None) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"AMASS input directory not found: {input_dir}")
    candidates = sorted(input_dir.rglob("*.npz"))
    if name_filter:
        f = name_filter.lower()
        candidates = [p for p in candidates if f in p.name.lower() or f in str(p.parent).lower()]
    return candidates


def load_amass_npz(path: Path) -> dict | None:
    """Load an AMASS-format .npz, returning a dict or None if it doesn't look like AMASS."""
    try:
        data = np.load(path, allow_pickle=True)
    except (OSError, ValueError):
        return None
    keys = set(data.files)
    required = {"poses", "trans", "betas"}
    if not required.issubset(keys):
        return None
    fps = None
    for key in ("mocap_framerate", "mocap_frame_rate", "frame_rate", "fps"):
        if key in keys:
            fps = float(np.asarray(data[key]).item())
            break
    if fps is None:
        return None
    gender_arr = data["gender"] if "gender" in keys else np.array("neutral")
    gender_val = np.asarray(gender_arr).item() if gender_arr.shape == () else gender_arr.tolist()
    if isinstance(gender_val, bytes):
        gender_val = gender_val.decode("utf-8")
    return {
        "poses": np.asarray(data["poses"], dtype=np.float64),
        "trans": np.asarray(data["trans"], dtype=np.float64),
        "betas": np.asarray(data["betas"], dtype=np.float64),
        "gender": str(gender_val).strip().lower() or "neutral",
        "fps": fps,
    }


def source_id(input_dir: Path, path: Path) -> str:
    rel = path.relative_to(input_dir).with_suffix("")
    return str(rel).replace("/", "_").replace("\\", "_")


def output_name(source: str) -> str:
    return f"{source}.npz"


def ingest_one(
    path: Path,
    input_dir: Path,
    target_fps: float,
    min_duration_s: float,
) -> PoseStream | None:
    raw = load_amass_npz(path)
    if raw is None:
        return None
    n_frames = raw["poses"].shape[0]
    duration = n_frames / raw["fps"]
    if duration < min_duration_s:
        return None
    poses, trans = resample_axis_angle(raw["poses"], raw["trans"], raw["fps"], target_fps)
    return PoseStream(
        poses=poses,
        trans=trans,
        betas=raw["betas"],
        gender=raw["gender"],
        fps=int(round(target_fps)),
        source=source_id(input_dir, path),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True, help="Root of extracted AMASS archives.")
    parser.add_argument(
        "--output", type=Path, default=REPO_ROOT / "data" / "poses", help="Output directory for per-body .npz files."
    )
    parser.add_argument("--target-fps", type=float, default=30.0)
    parser.add_argument("--max-sequences", type=int, default=50)
    parser.add_argument("--filter", default="walk", help="Substring filter on sequence path; pass '' to disable.")
    parser.add_argument(
        "--min-duration", type=float, default=2.0, help="Skip sequences shorter than this many seconds."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed for sequence shuffling.")
    args = parser.parse_args(argv)

    candidates = find_sequences(args.input, args.filter or None)
    if not candidates:
        print(f"No AMASS .npz files found under {args.input} matching filter {args.filter!r}", file=sys.stderr)
        return 1

    rng = np.random.default_rng(args.seed)
    order = rng.permutation(len(candidates))
    candidates = [candidates[i] for i in order]

    args.output.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    for path in candidates:
        if written >= args.max_sequences:
            break
        stream = ingest_one(path, args.input, args.target_fps, args.min_duration)
        if stream is None:
            skipped += 1
            continue
        out = args.output / output_name(stream.source)
        if args.dry_run:
            print(f"[dry] {path} -> {out}  ({len(stream)} frames, {stream.gender}, betas[{stream.betas.shape[0]}])")
        else:
            stream.save(out)
            print(f"wrote {out}  ({len(stream)} frames, {stream.gender})")
        written += 1

    print(f"\ningested {written} sequence(s); skipped {skipped} (short or non-AMASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
