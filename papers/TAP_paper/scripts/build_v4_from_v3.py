"""Build the v4 manuscript source from the archived v3 source and ET decisions."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one source match, found {count}")
    return text.replace(old, new, 1)


def build_revision(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")

    edits = [
        (
            r"\usepackage{amsmath,amssymb,amsthm,mathtools}",
            r"\usepackage{amsmath,amssymb,mathtools}",
            "remove amsthm",
        ),
        (
            "\\theoremstyle{plain}\n\\newtheorem{theorem}{Theorem}\n\n",
            "",
            "remove theorem definition",
        ),
        (
            "surface yields a generalized Cauchy whole-body identity with one\ngeometry scalar.",
            "surface yields a generalized Cauchy whole-body identity governed by a\nsingle geometry-dependent scalar.",
            "geometry-dependent abstract scalar",
        ),
        (
            r"\IEEEPARstart{W}{ireless} exposure on the human body is regulated",
            r"\IEEEPARstart{W}{ireless} exposure of the human body is regulated",
            "exposure of the human body",
        ),
        (
            "\\gls{APD} law for the human body, validated four independent ways.",
            "\\gls{APD} law for the human body, validated in four independent ways.",
            "validated in four ways",
        ),
        (
            "absorbed power reduces to a flux-weighted transmission scalar and an\n"
            "  ambient-occlusion geometry scalar.",
            "absorbed power reduces to a flux-weighted transmission scalar and a\n  single ambient-occlusion scalar.",
            "ambient-occlusion scalar",
        ),
        (
            "under many incident paths, the absorbed-power map is one $10$~ms\n  matrix-vector multiply.",
            "under many incident paths, the absorbed-power map is a single\n"
            "  matrix-vector multiplication, evaluated in under $10$~ms.",
            "matrix-vector wording",
        ),
        (
            "giving the polarization-degenerate value",
            "giving the polarization-independent normal-incidence value",
            "normal-incidence polarization wording",
        ),
        (
            "The polarization correction\n"
            "vanishes pointwise for circular illumination, in expectation for\n"
            "random-orientation linear illumination, and to within $2.5\\%$ for\n"
            "multipath averaging above~20 paths.",
            "The polarization correction\n"
            "vanishes pointwise for circularly polarized illumination, in expectation\n"
            "for randomly oriented linearly polarized illumination, and to within\n"
            "$2.5\\%$ under multipath averaging with at least 20 paths.",
            "polarization illumination wording",
        ),
        (
            "The unpolarized curve closely\n"
            "tracks the simplified prediction, and the small gap is the Fresnel\n"
            "approximation error. \\Cref{tab:fresnel-skin} quantifies the deviation\n"
            "of $\\Tavg$ from $T_0$ across $[0^\\circ, 75^\\circ]$ on skin at 28~GHz.\n"
            "The maximum deviation is $5.6\\%$ at $70$--$75^\\circ$. Below $30^\\circ$\n"
            "the deviation stays below $0.2\\%$.",
            "The unpolarized curve closely\n"
            "tracks the simplified prediction, and the small gap is the Fresnel\n"
            "approximation error. $\\Tavg/T_0$ is at most $1.056$ across\n"
            "$[0^\\circ,90^\\circ]$ on skin at 28~GHz. Below $20^\\circ$, the\n"
            "deviation stays below $0.2\\%$.",
            "replace Table I discussion",
        ),
        (
            "$\\Tavg$ stays within $5.6\\%$ of $T_0$ up to $75^\\circ$.",
            "$\\Tavg/T_0$ is at most $1.056$ over $[0^\\circ,90^\\circ]$.",
            "Figure 3 caption range",
        ),
        (
            "\\begin{table}[!t]\n"
            "\\centering\n"
            "\\caption{Fresnel transmission for skin at 28~GHz. Here $T_0 =\n"
            "\\Tavg(0)$ is the normal-incidence value, and $\\Tavg/T_0$ stays\n"
            "within $5.6\\%$ of unity over $[0^\\circ, 75^\\circ]$.}\n"
            "\\label{tab:fresnel-skin}\n"
            "\\begin{tabular}{ccccc}\n"
            "\\toprule\n"
            "$\\theta$ & $T_s$ (TE) & $T_p$ (TM) & $\\Tavg$ & $\\Tavg/T_0$ \\\\\n"
            "\\midrule\n"
            "$0^\\circ$  & 0.539 & 0.539 & 0.539 & 1.000 \\\\\n"
            "$30^\\circ$ & 0.489 & 0.591 & 0.540 & 1.002 \\\\\n"
            "$45^\\circ$ & 0.422 & 0.666 & 0.544 & 1.010 \\\\\n"
            "$60^\\circ$ & 0.321 & 0.791 & 0.556 & 1.032 \\\\\n"
            "$70^\\circ$ & 0.233 & 0.902 & 0.568 & 1.054 \\\\\n"
            "$75^\\circ$ & 0.182 & 0.952 & 0.567 & 1.053 \\\\\n"
            "\\bottomrule\n"
            "\\end{tabular}\n"
            "\\end{table}\n\n",
            "",
            "remove Table I",
        ),
        (
            "The generalized Cauchy formula is the central whole-body identity.\n"
            "\\begin{theorem}\\label{thm:cauchy}\n"
            "Let a body $\\Sigma$ have surface area $A$, exposure fraction\n"
            "$\\eta(\\rr)$, and absorption area\n"
            "$\\Aab \\equiv \\int_\\Sigma \\eta(\\rr)\\,\\diff A$. Under isotropic,\n"
            "unpolarized plane-wave illumination of intensity $\\IPD$ on tissue\n"
            "with normal-incidence transmission $T_0$, the direction-averaged\n"
            "whole-body absorbed power is\n"
            "\\begin{equation}\\label{eq:cauchy}\n"
            "  \\langle P_{\\mathrm{abs}} \\rangle = \\IPD\\,T_0\\,\\Aab/4\\, .\n"
            "\\end{equation}\n"
            "\\end{theorem}\n\n"
            "\\begin{proof}\n"
            "Apply Fubini's theorem to exchange the surface and direction\n",
            "The generalized Cauchy formula is the central whole-body identity.\n"
            "Let a body $\\Sigma$ have surface area $A$, exposure fraction\n"
            "$\\eta(\\rr)$, and absorption area\n"
            "$\\Aab \\equiv \\int_\\Sigma \\eta(\\rr)\\,\\diff A$. Under isotropic,\n"
            "unpolarized plane-wave illumination of intensity $\\IPD$ on tissue\n"
            "with normal-incidence transmission $T_0$, the direction-averaged\n"
            "whole-body absorbed power is\n"
            "\\begin{equation}\\label{eq:cauchy}\n"
            "  \\langle P_{\\mathrm{abs}} \\rangle = \\IPD\\,T_0\\,\\Aab/4\\, .\n"
            "\\end{equation}\n"
            "To see why, apply Fubini's theorem to exchange the surface and direction\n",
            "remove first theorem and proof opening",
        ),
        (
            "Integration over $\\Sigma$ gives~\\eqref{eq:cauchy}.\n\\end{proof}\n",
            "Integration over $\\Sigma$ gives~\\eqref{eq:cauchy}.\n",
            "remove first proof ending",
        ),
        (
            "The following bound links the cube quantity to APD.\n"
            "\\begin{theorem}\\label{thm:apd-bound}\n"
            "For an axis-aligned $10$~g cube placed per IEC/IEEE~62704-1 on a planar\n",
            "The following bound links the cube quantity to APD. For an axis-aligned\n"
            "$10$~g cube placed per IEC/IEEE~62704-1 on a planar\n",
            "remove second theorem opening",
        ),
        (
            "below the limb restriction of $4$~W/kg.\n\\end{theorem}\n",
            "below the limb restriction of $4$~W/kg.\n",
            "remove second theorem ending",
        ),
        (
            "\\emph{Phys. Med. Biol.}, 2026, under review.",
            "\\emph{Phys. Med. Biol.}, accepted for publication, 2026.",
            "accepted bibliography status",
        ),
    ]

    for old, new, label in edits:
        text = replace_once(text, old, new, label)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("v3_to_coauthors/paper.tex"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("v4_to_coauthors/paper.tex"),
    )
    args = parser.parse_args()
    build_revision(args.source, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
