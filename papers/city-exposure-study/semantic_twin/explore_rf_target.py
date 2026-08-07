"""Let Gemini explore one propagation-selected crop with the AEGIS RF tools."""

from __future__ import annotations

import argparse
import json
import pathlib

from semantic_twin.vision.rf_agent import GEMINI_MODEL, RfTargetContext
from semantic_twin.vision.rf_explorer import run_gemini_explorer


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=pathlib.Path)
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--path-rank", type=int, default=1)
    parser.add_argument("--bounce-order", type=int, default=1)
    parser.add_argument("--incidence-deg", type=float)
    parser.add_argument("--multipath-power-share", type=float)
    parser.add_argument("--note", default="")
    parser.add_argument("--model", default=GEMINI_MODEL)
    parser.add_argument("--timeout-s", type=float, default=600.0)
    parser.add_argument("--transcript", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = arguments(argv)
    context = RfTargetContext(
        frequency_ghz=args.frequency_ghz,
        path_rank=args.path_rank,
        bounce_order=args.bounce_order,
        incidence_deg=args.incidence_deg,
        multipath_power_share=args.multipath_power_share,
        note=args.note,
    )
    run = run_gemini_explorer(
        args.image,
        context,
        model=args.model,
        timeout_s=args.timeout_s,
    )
    if args.transcript is not None:
        args.transcript.parent.mkdir(parents=True, exist_ok=True)
        args.transcript.write_text(run.transcript_jsonl)
    print(run.final_response)
    print("\n--- agent trace summary ---")
    print(json.dumps({"tool_calls": list(run.tool_calls), "stderr": run.stderr}, indent=2))


if __name__ == "__main__":
    main()
