% NEXT: \begin{document}
% NEXT:
% NEXT: \title{Closed-Form Absorbed-Power Dosimetry from~1~to~100\,GHz}
% NEXT:
% NEXT: \author{Robin~Wydaeghe$^{*}$~\orcidlink{0000-0002-1374-0118},
% NEXT:   Luc~Martens~\orcidlink{0000-0001-9948-9157},~\IEEEmembership{Member,~IEEE},
% NEXT:   G\"unter~Vermeeren~\orcidlink{0000-0002-5309-3808},~\IEEEmembership{Member,~IEEE},
% NEXT:   Emmeric~Tanghe~\orcidlink{0000-0003-0020-6466},~\IEEEmembership{Member,~IEEE},
% NEXT:   and~Wout~Joseph~\orcidlink{0000-0002-8807-0673},~\IEEEmembership{Senior~Member,~IEEE}%
% NEXT:   \thanks{All authors are with the WAVES research group, Department of
% NEXT:   Information Technology, Ghent University--imec, Technologiepark-Zwijnaarde
% NEXT:   126, 9052 Ghent, Belgium.}%
% NEXT:   \thanks{$^{*}$Corresponding author. E-mail: robin.wydaeghe@ugent.be.}}
% NEXT:
% NEXT: \markboth{IEEE Transactions on Antennas and Propagation,
% NEXT: Vol.~XX, No.~X, Month~Year}%
% NEXT: {Wydaeghe \MakeLowercase{\textit{et~al.}}: Closed-Form
% NEXT: Absorbed-Power Dosimetry}
% NEXT:
% NEXT: \maketitle
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

## reviews (preamble)

_(empty — run /review to populate)_

## grinder notes
- **role**: documentclass + packages + macros
