% PREV: \documentclass{IEEEoj}
% PREV:
% PREV: \usepackage{cite}
% PREV: \usepackage{amsmath,amssymb,amsfonts}
% PREV: \usepackage{bm}
% PREV: \usepackage{booktabs}
% PREV: \usepackage{graphicx}
% PREV: \usepackage{orcidlink}
% PREV: \hypersetup{hidelinks}
% PREV: \usepackage{textcomp}
% PREV: \usepackage{url}
% PREV:
% PREV: \AtBeginDocument{\definecolor{ojcolor}{cmyk}{0.93,0.59,0.15,0.02}}
% PREV: \def\OJlogo{\vspace{-4pt}\hskip-4pt\includegraphics[height=18pt]{ojcoms.png}}
% PREV:
% PREV: \graphicspath{{../}{./}}
% PREV:
% PREV: \newcommand{\rhoA}{\rho_{\mathrm{A}}}
% PREV: \newcommand{\Peirp}{P_{\mathrm{EIRP}}}
% PREV: \newcommand{\wbsar}{\mathrm{SAR}_{\mathrm{wb}}}
% NEXT: \begin{abstract}
% NEXT: Realistic urban radiofrequency electromagnetic-field (RF-EMF) assessment must
% NEXT: connect the field in a city to the power absorbed by the human body. This
% NEXT: supports monitoring and epidemiological studies. The goal of
% NEXT: this study is to compute direction-aware whole-body specific absorption rate
% NEXT: (SAR) along pedestrian routes in ten cities. We combine 360-degree street
% NEXT: images, photogrammetric geometry, and AI-derived object and material labels in
% NEXT: a human-centric digital twin. Its agentic AI stage uses SAM~3 Agent for
% NEXT: material and vegetation labeling. The calculation places possible transmitters
% NEXT: along visible rooflines at 15~GHz, traces direct and single-reflection paths,
% NEXT: and applies each arrival direction to an anatomical body model. Results are
% NEXT: normalized per unit product of source density and effective isotropic radiated
% NEXT: power. The ten routes contain 163 observation points, each evaluated with 64
% NEXT: independent runs. The normalized route-median whole-body SAR ranges from
% NEXT: 0.00902 to 0.129~m$^2$~kg$^{-1}$, a factor of 14.31. Direct paths give the
% NEXT: largest component at 156 of 157 points with line of sight. The single-reflection
% NEXT: specular component is largest at one point, while the single-reflection diffuse component is
% NEXT: the only nonzero component at six shadowed points. Increasing the number of
% NEXT: runs from 48 to 64 changes the total at any point by at most 0.32\%. Validation
% NEXT: in a controlled scene gives maximum differences of 1.43\% against deterministic
% NEXT: quadrature and 0.80\% against an independent Sionna RT forward calculation.
% NEXT: The reported values apply to the selected routes under the stated source model.
% NEXT: We do not estimate whole-city or deployed-network exposure.
% NEXT: \end{abstract}
\begin{document}

\receiveddate{XX Month, XXXX}
\reviseddate{XX Month, XXXX}
\accepteddate{XX Month, XXXX}
\publisheddate{XX Month, XXXX}
\currentdate{XX Month, XXXX}

\title{Human-Centric 6G RF-EMF Exposure with AI-Assisted Digital Twins in Ten Cities}

\author{ROBIN WYDAEGHE~\orcidlink{0000-0002-1374-0118}\IEEEauthorrefmark{1},
G\"UNTER VERMEEREN~\orcidlink{0000-0002-5309-3808}\IEEEauthorrefmark{1},
\IEEEmembership{Member, IEEE},
EMMERIC TANGHE~\orcidlink{0000-0003-0020-6466}\IEEEauthorrefmark{1},
\IEEEmembership{Member, IEEE},
and WOUT JOSEPH~\orcidlink{0000-0002-8807-0673}\IEEEauthorrefmark{1},
\IEEEmembership{Senior Member, IEEE}}

\affil{Department of Information Technology, Ghent University/IMEC,
9052 Ghent, Belgium}

\corresp{CORRESPONDING AUTHOR: Robin Wydaeghe
(e-mail: robin.wydaeghe@ugent.be).}

\markboth{Human-Centric 6G RF-EMF Exposure with AI-Assisted Digital Twins in Ten Cities}
{Wydaeghe \textit{et al.}}

## reviews (titleblock)

_(empty: run the manuscript review pass to populate)_
