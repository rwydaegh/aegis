% PREV: % =====================================================================
% PREV: % Paper A+B (merged)
% PREV: % Closed-form absorbed-power dosimetry on the human body, 1 to 100 GHz:
% PREV: %   from a local Fresnel identity to a whole-body Cauchy formula.
% PREV: % Author: Robin Wydaeghe
% PREV: % Target: IEEE Transactions on Antennas and Propagation
% PREV: % =====================================================================
% PREV:
% PREV: \documentclass[journal,twocolumn,10pt]{IEEEtran}
% PREV:
% PREV: \usepackage[utf8]{inputenc}
% PREV: \usepackage[T1]{fontenc}
% PREV: \usepackage{lmodern}
% PREV: \usepackage{microtype}
% PREV:
% PREV: \usepackage{amsmath,amssymb,mathtools}
% PREV: \usepackage{bm}
% PREV:
% PREV: \usepackage{graphicx}
% PREV: \graphicspath{{figures/}{authors/}}
% PREV: \usepackage{booktabs}
% PREV: \usepackage{array}
% PREV: \usepackage{caption}
% PREV: \usepackage{subcaption}
% PREV:
% PREV: \usepackage{cite}
% PREV: \usepackage{xcolor}
% PREV: \usepackage{tikz}
% PREV: \usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds}
% PREV: \usepackage{xr-hyper}
% PREV: \usepackage[colorlinks=true,allcolors=black]{hyperref}
% PREV: \usepackage{orcidlink}
% PREV: \usepackage[capitalize]{cleveref}
% PREV: \usepackage[acronym,nonumberlist,nopostdot,nomain]{glossaries}
% PREV: % Suppress hyperlinks on \gls expansions so they render as plain black text
% PREV: % rather than picking up the blue linkcolor from hyperref.
% PREV: \glsdisablehyper
% PREV:
% PREV: \newcommand*{\doi}[1]{\href{https://doi.org/#1}{#1}}
% PREV:
% PREV: \newacronym{APD}{APD}{Absorbed Power Density}
% PREV: \newacronym{IPD}{IPD}{Incident Power Density}
% PREV: \newacronym{ACS}{ACS}{Absorption Cross-Section}
% PREV: \newacronym{SAR}{SAR}{Specific Absorption Rate}
% PREV: \newacronym{psSAR10g}{psSAR$_{10\mathrm{g}}$}{peak-spatial SAR averaged over a 10\,g cube}
% PREV: \newacronym{FDTD}{FDTD}{Finite-Difference Time-Domain}
% PREV: \newacronym{ICNIRP}{ICNIRP}{International Commission on Non-Ionizing Radiation Protection}
% PREV: \newacronym{TM}{TM}{Transverse Magnetic}
% PREV: \newacronym{TE}{TE}{Transverse Electric}
% PREV: \newacronym{GPU}{GPU}{Graphics Processing Unit}
% PREV: \newacronym{GELU}{GELU}{Gaussian Error Linear Unit}
% PREV: \newacronym{ReLU}{ReLU}{Rectified Linear Unit}
% PREV: \newacronym{BSA}{BSA}{body surface area}
% PREV:
% PREV: % --- math macros ---
% PREV: \newcommand{\khat}{\hat{\bm{k}}}
% PREV: \newcommand{\nhat}{\hat{\bm{n}}}
% PREV: \newcommand{\rr}{\mathbf{r}}
% PREV: \newcommand{\EE}{\mathbf{E}}
% PREV: \newcommand{\IPD}{\mathrm{IPD}}
% PREV: \newcommand{\APD}{\mathrm{APD}}
% PREV: \newcommand{\Aab}{A_{\mathrm{ab}}}
% PREV: \newcommand{\Aperp}{A_\perp}
% PREV: \newcommand{\Teff}{T_{\mathrm{eff}}}
% PREV: \newcommand{\Tavg}{T_{\mathrm{avg}}}
% PREV: \newcommand{\Tbar}{\bar{T}}
% PREV: \newcommand{\Tlay}{T_{\mathrm{lay}}}
% PREV: \newcommand{\ntilde}{\tilde{n}}
% PREV: \newcommand{\diff}{\mathrm{d}}
% PREV: \newcommand{\pospart}[1]{\left[#1\right]_{+}}
% PREV: \newcommand{\Vis}{V}
% PREV: \newcommand{\APDAvg}{\langle\mathrm{APD}\rangle_{1\,/\,4\,\mathrm{cm}^2}}
% PREV: \DeclareMathOperator{\RE}{Re}
% PREV: \DeclareMathOperator{\IM}{Im}
% PREV:
% PREV: % Load cross-document labels only after commands used in the external
% PREV: % auxiliary file have been defined.
% PREV: \externaldocument{paper_SI}
% PREV:
% PREV: % Flowchart output-box colors
% PREV: \definecolor{outA}{RGB}{216,234,251}
% PREV: \definecolor{outB}{RGB}{251,234,216}
% PREV: \definecolor{outC}{RGB}{226,247,217}
% PREV:
% PREV: % Black censor rectangles over eyes and genitals on Thelonious phantom views.
% PREV: % Rectangle positions are in normalized image coordinates (0,0)=SW, (1,1)=NE.
% PREV: % Args: [width]{file}{eyes_LL}{eyes_UR}{gen_LL}{gen_UR}, each corner as "x,y".
% PREV: \newcommand{\censorphantom}[6][\linewidth]{%
% PREV:   \begin{tikzpicture}
% PREV:     \node[anchor=south west, inner sep=0] (img) at (0,0)
% PREV:       {\includegraphics[width=#1]{#2}};
% PREV:     \begin{scope}[x={(img.south east)}, y={(img.north west)}]
% PREV:       \fill[black] (#3) rectangle (#4);
% PREV:       \fill[black] (#5) rectangle (#6);
% PREV:     \end{scope}
% PREV:   \end{tikzpicture}%
% PREV: }
% NEXT: \begin{abstract}
% NEXT: Regulatory dosimetry on the human body relies on Finite-Difference
% NEXT: Time-Domain (FDTD) simulations, which grow to trillions of cells at
% NEXT: high mmWave frequencies. From 1 to 100~GHz, we replace these
% NEXT: simulations with closed-form Fresnel surface laws for opaque
% NEXT: biological tissue. Locally, Absorbed Power Density (APD) is Incident
% NEXT: Power Density (IPD) multiplied by normal-incidence transmission, the positive
% NEXT: incidence cosine, and an ambient-occlusion factor. For
% NEXT: unpolarized skin at 28~GHz, pseudo-Brewster compensation keeps
% NEXT: angular transmission within 5.6\% of normal incidence up to
% NEXT: $75^\circ$. Integrating the local law over the visible nonconvex body
% NEXT: surface yields a generalized Cauchy whole-body identity governed by a
% NEXT: single geometry-dependent scalar. A layered transmission term captures the sub-6~GHz
% NEXT: whole-body dip. On a $10^4$-triangle mesh under $10^2$ incident
% NEXT: paths, this turns the absorbed-power map into one differentiable
% NEXT: matrix-vector multiply, evaluated in under $10$~ms on a GPU. The
% NEXT: closed form is validated in four ways: Mie theory on lossy spheres,
% NEXT: full polarization-aware Fresnel calculations on the Thelonious
% NEXT: phantom, Sim4Life FDTD, and dosimetry literature across 108
% NEXT: volunteers and 5 FDTD phantoms. In the high-frequency regime, the
% NEXT: error is below 5\%, within the reported uncertainty in human-skin
% NEXT: dielectric parameters. Whole-body compliance reduces to three
% NEXT: precomputed scalars. Antenna and beam optimization under exposure
% NEXT: constraints become differentiable end-to-end.
% NEXT: \end{abstract}
\begin{document}

\title{Closed-Form Absorbed-Power Dosimetry from~1~to~100\,GHz}

\author{Robin~Wydaeghe$^{*}$~\orcidlink{0000-0002-1374-0118},
  Luc~Martens~\orcidlink{0000-0001-9948-9157},~\IEEEmembership{Member,~IEEE},
  G\"unter~Vermeeren~\orcidlink{0000-0002-5309-3808},~\IEEEmembership{Member,~IEEE},
  Emmeric~Tanghe~\orcidlink{0000-0003-0020-6466},~\IEEEmembership{Member,~IEEE},
  and~Wout~Joseph~\orcidlink{0000-0002-8807-0673},~\IEEEmembership{Senior~Member,~IEEE}%
  \thanks{All authors are with the WAVES research group, Department of
  Information Technology, Ghent University--imec, Technologiepark-Zwijnaarde
  126, 9052 Ghent, Belgium.}%
  \thanks{$^{*}$Corresponding author. E-mail: robin.wydaeghe@ugent.be.}}

\markboth{IEEE Transactions on Antennas and Propagation,
Vol.~XX, No.~X, Month~Year}%
{Wydaeghe \MakeLowercase{\textit{et~al.}}: Closed-Form
Absorbed-Power Dosimetry}

\maketitle

## reviews (titleblock)

_(empty — run /review to populate)_
