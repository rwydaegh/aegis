% NEXT: \documentclass[journal,twocolumn,10pt]{IEEEtran}
# Frontmatter

<!-- AUTO_BEGIN: assembled -->
% =====================================================================
% Paper A+B (merged)
% Closed-form absorbed-power dosimetry on the human body, 1 to 100 GHz:
%   from a local Fresnel identity to a whole-body Cauchy formula.
% Author: Robin Wydaeghe
% Target: IEEE Transactions on Antennas and Propagation
% =====================================================================

\documentclass[journal,twocolumn,10pt]{IEEEtran}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{microtype}

\usepackage{amsmath,amssymb,mathtools}
\usepackage{bm}

\usepackage{graphicx}
\graphicspath{{figures/}{authors/}}
\usepackage{booktabs}
\usepackage{array}
\usepackage{caption}
\usepackage{subcaption}

\usepackage{cite}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds}
\usepackage{xr-hyper}
\usepackage[colorlinks=true,allcolors=black]{hyperref}
\usepackage{orcidlink}
\usepackage[capitalize]{cleveref}
\usepackage[acronym,nonumberlist,nopostdot,nomain]{glossaries}
% Suppress hyperlinks on \gls expansions so they render as plain black text
% rather than picking up the blue linkcolor from hyperref.
\glsdisablehyper

\newcommand*{\doi}[1]{\href{https://doi.org/#1}{#1}}

\newacronym{APD}{APD}{Absorbed Power Density}
\newacronym{IPD}{IPD}{Incident Power Density}
\newacronym{ACS}{ACS}{Absorption Cross-Section}
\newacronym{SAR}{SAR}{Specific Absorption Rate}
\newacronym{psSAR10g}{psSAR$_{10\mathrm{g}}$}{peak-spatial SAR averaged over a 10\,g cube}
\newacronym{FDTD}{FDTD}{Finite-Difference Time-Domain}
\newacronym{ICNIRP}{ICNIRP}{International Commission on Non-Ionizing Radiation Protection}
\newacronym{TM}{TM}{Transverse Magnetic}
\newacronym{TE}{TE}{Transverse Electric}
\newacronym{GPU}{GPU}{Graphics Processing Unit}
\newacronym{GELU}{GELU}{Gaussian Error Linear Unit}
\newacronym{ReLU}{ReLU}{Rectified Linear Unit}
\newacronym{BSA}{BSA}{body surface area}

% --- math macros ---
\newcommand{\khat}{\hat{\bm{k}}}
\newcommand{\nhat}{\hat{\bm{n}}}
\newcommand{\rr}{\mathbf{r}}
\newcommand{\EE}{\mathbf{E}}
\newcommand{\IPD}{\mathrm{IPD}}
\newcommand{\APD}{\mathrm{APD}}
\newcommand{\Aab}{A_{\mathrm{ab}}}
\newcommand{\Aperp}{A_\perp}
\newcommand{\Teff}{T_{\mathrm{eff}}}
\newcommand{\Tavg}{T_{\mathrm{avg}}}
\newcommand{\Tbar}{\bar{T}}
\newcommand{\Tlay}{T_{\mathrm{lay}}}
\newcommand{\ntilde}{\tilde{n}}
\newcommand{\diff}{\mathrm{d}}
\newcommand{\pospart}[1]{\left[#1\right]_{+}}
\newcommand{\Vis}{V}
\newcommand{\APDAvg}{\langle\mathrm{APD}\rangle_{1\,/\,4\,\mathrm{cm}^2}}
\DeclareMathOperator{\RE}{Re}
\DeclareMathOperator{\IM}{Im}

% Load cross-document labels only after commands used in the external
% auxiliary file have been defined.
\externaldocument{paper_SI}

% Flowchart output-box colors
\definecolor{outA}{RGB}{216,234,251}
\definecolor{outB}{RGB}{251,234,216}
\definecolor{outC}{RGB}{226,247,217}

% Black censor rectangles over eyes and genitals on Thelonious phantom views.
% Rectangle positions are in normalized image coordinates (0,0)=SW, (1,1)=NE.
% Args: [width]{file}{eyes_LL}{eyes_UR}{gen_LL}{gen_UR}, each corner as "x,y".
\newcommand{\censorphantom}[6][\linewidth]{%
  \begin{tikzpicture}
    \node[anchor=south west, inner sep=0] (img) at (0,0)
      {\includegraphics[width=#1]{#2}};
    \begin{scope}[x={(img.south east)}, y={(img.north west)}]
      \fill[black] (#3) rectangle (#4);
      \fill[black] (#5) rectangle (#6);
    \end{scope}
  \end{tikzpicture}%
}

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

\begin{abstract}
Regulatory dosimetry on the human body relies on Finite-Difference
Time-Domain (FDTD) simulations, which grow to trillions of cells at
high mmWave frequencies. From 1 to 100~GHz, we replace these
simulations with closed-form Fresnel surface laws for opaque
biological tissue. Locally, Absorbed Power Density (APD) is Incident
Power Density (IPD) multiplied by normal-incidence transmission, the positive
incidence cosine, and an ambient-occlusion factor. For
unpolarized skin at 28~GHz, pseudo-Brewster compensation keeps
angular transmission within 5.6\% of normal incidence up to
$75^\circ$. Integrating the local law over the visible nonconvex body
surface yields a generalized Cauchy whole-body identity governed by a
single geometry-dependent scalar. A layered transmission term captures the sub-6~GHz
whole-body dip. On a $10^4$-triangle mesh under $10^2$ incident
paths, this turns the absorbed-power map into one differentiable
matrix-vector multiply, evaluated in under $10$~ms on a GPU. The
closed form is validated in four ways: Mie theory on lossy spheres,
full polarization-aware Fresnel calculations on the Thelonious
phantom, Sim4Life FDTD, and dosimetry literature across 108
volunteers and 5 FDTD phantoms. In the high-frequency regime, the
error is below 5\%, within the reported uncertainty in human-skin
dielectric parameters. Whole-body compliance reduces to three
precomputed scalars. Antenna and beam optimization under exposure
constraints become differentiable end-to-end.
\end{abstract}

\begin{IEEEkeywords}
APD, dosimetry, FDTD, Fresnel transmission, ICNIRP, mmWave, SAR.
\end{IEEEkeywords}

\IEEEpeerreviewmaketitle
<!-- AUTO_END: assembled -->










## section notes

_(AI-owned notes about this section as a whole)_
