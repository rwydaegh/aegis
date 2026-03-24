"""CLI for ICNIRP 2020 compliance evaluation.

Usage:
    python3 -m aegis.compliance --freq 28e9 --sab 15.0
    python3 -m aegis.compliance --freq 28e9 --sab 15.0 --sar 0.05 --sinc 8.0
    python3 -m aegis.compliance --freq 60e9 --sab 15.0 --sab-1cm2 35.0 --occupational
    python3 -m aegis.compliance --freq 28e9 --limits
"""

from __future__ import annotations

import argparse
import sys

from aegis.compliance import (
    ExposureScenario,
    evaluate_compliance,
    icnirp_limits,
    max_compliant_power,
    summary_text,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m aegis.compliance",
        description="ICNIRP 2020 compliance evaluation (> 6 GHz to 300 GHz)",
    )
    p.add_argument(
        "--freq",
        type=float,
        required=True,
        help="Frequency in Hz (e.g. 28e9, 60e9)",
    )
    p.add_argument(
        "--sab",
        type=float,
        default=None,
        help="Peak spatially averaged S_ab over 4 cm^2 [W/m^2]",
    )
    p.add_argument(
        "--sab-1cm2",
        type=float,
        default=None,
        help="Peak spatially averaged S_ab over 1 cm^2 [W/m^2] (only > 30 GHz)",
    )
    p.add_argument(
        "--sar",
        type=float,
        default=None,
        help="Whole-body SAR [W/kg]",
    )
    p.add_argument(
        "--sinc",
        type=float,
        default=None,
        help="Peak local incident power density [W/m^2]",
    )
    p.add_argument(
        "--sinc-wb",
        type=float,
        default=None,
        help="Whole-body incident power density [W/m^2]",
    )
    p.add_argument(
        "--power",
        type=float,
        default=None,
        help="Reference transmit power [W] (used for max compliant power calculation)",
    )
    p.add_argument(
        "--occupational",
        action="store_true",
        help="Use occupational limits (default: general public)",
    )
    p.add_argument(
        "--limits",
        action="store_true",
        help="Just print the ICNIRP limits at this frequency and exit",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of plain text",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    scenario = ExposureScenario.OCCUPATIONAL if args.occupational else ExposureScenario.GENERAL_PUBLIC

    try:
        limits = icnirp_limits(scenario, args.freq)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.limits:
        _print_limits(limits, args.json)
        return

    if all(v is None for v in [args.sab, args.sab_1cm2, args.sar, args.sinc, args.sinc_wb]):
        print("No measured values provided. Use --sab, --sar, --sinc, etc.", file=sys.stderr)
        print("Use --limits to see the ICNIRP limits at this frequency.", file=sys.stderr)
        sys.exit(1)

    result = evaluate_compliance(
        freq_hz=args.freq,
        scenario=scenario,
        sab_4cm2=args.sab,
        sab_1cm2=args.sab_1cm2,
        sar_wb=args.sar,
        sinc_local=args.sinc,
        sinc_whole_body=args.sinc_wb,
    )

    if args.json:
        _print_json(result, args.power)
    else:
        print(summary_text(result))
        if args.power is not None:
            p_max = max_compliant_power(result, args.power)
            if p_max < float("inf"):
                import math

                p_max_dbm = 10 * math.log10(p_max * 1e3)
                print(f"\nMax compliant power: {p_max:.4g} W ({p_max_dbm:.1f} dBm)")
            else:
                print("\nMax compliant power: unlimited (all values zero)")


def _print_limits(limits, as_json: bool) -> None:
    if as_json:
        import json

        d = {
            "scenario": limits.scenario.value,
            "freq_hz": limits.freq_hz,
            "sab_4cm2_limit": limits.sab_4cm2,
            "sab_1cm2_limit": limits.sab_1cm2,
            "sar_wb_limit": limits.sar_wb,
            "sinc_local_limit": limits.sinc_local,
            "sinc_whole_body_limit": limits.sinc_whole_body,
        }
        print(json.dumps(d, indent=2))
    else:
        print(f"ICNIRP 2020 limits ({limits.scenario.value})")
        print(f"Frequency: {limits.freq_hz / 1e9:.3f} GHz")
        print()
        print(f"  S_ab (4 cm^2):      {limits.sab_4cm2:g} W/m^2")
        if limits.sab_1cm2 is not None:
            print(f"  S_ab (1 cm^2):      {limits.sab_1cm2:g} W/m^2")
        print(f"  SAR_wb:             {limits.sar_wb:g} W/kg")
        print(f"  S_inc (local):      {limits.sinc_local:.4f} W/m^2")
        print(f"  S_inc (whole-body): {limits.sinc_whole_body:g} W/m^2")


def _print_json(result, ref_power: float | None) -> None:
    import json

    d = {
        "scenario": result.scenario.value,
        "freq_hz": result.freq_hz,
        "overall_pass": result.overall_pass,
        "margin_db": result.margin_db if result.margin_db != float("inf") else None,
        "checks": [
            {
                "label": c.label,
                "value": c.value,
                "limit": c.limit,
                "unit": c.unit,
                "compliant": c.compliant,
                "margin_db": c.margin_db if c.margin_db != float("inf") else None,
            }
            for c in result.all_checks
        ],
    }
    if ref_power is not None:
        p_max = max_compliant_power(result, ref_power)
        d["max_compliant_power_w"] = p_max if p_max < float("inf") else None
    print(json.dumps(d, indent=2))


if __name__ == "__main__":
    main()
