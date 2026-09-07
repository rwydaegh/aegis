% PREV: \begin{document}
% PREV:
% PREV: \receiveddate{XX Month, XXXX}
% PREV: \reviseddate{XX Month, XXXX}
% PREV: \accepteddate{XX Month, XXXX}
% PREV: \publisheddate{XX Month, XXXX}
% PREV: \currentdate{XX Month, XXXX}
% PREV:
% PREV: \title{Human-Centric 6G RF-EMF Exposure with AI-Assisted Digital Twins in Ten Cities}
% PREV:
% PREV: \author{ROBIN WYDAEGHE~\orcidlink{0000-0002-1374-0118}\IEEEauthorrefmark{1},
% PREV: G\"UNTER VERMEEREN~\orcidlink{0000-0002-5309-3808}\IEEEauthorrefmark{1},
% PREV: \IEEEmembership{Member, IEEE},
% PREV: EMMERIC TANGHE~\orcidlink{0000-0003-0020-6466}\IEEEauthorrefmark{1},
% PREV: \IEEEmembership{Member, IEEE},
% PREV: and WOUT JOSEPH~\orcidlink{0000-0002-8807-0673}\IEEEauthorrefmark{1},
% PREV: \IEEEmembership{Senior Member, IEEE}}
% PREV:
% PREV: \affil{Department of Information Technology, Ghent University/IMEC,
% PREV: 9052 Ghent, Belgium}
% PREV:
% PREV: \corresp{CORRESPONDING AUTHOR: Robin Wydaeghe
% PREV: (e-mail: robin.wydaeghe@ugent.be).}
% PREV:
% PREV: \markboth{Human-Centric 6G RF-EMF Exposure with AI-Assisted Digital Twins in Ten Cities}
% PREV: {Wydaeghe \textit{et al.}}
% NEXT: \begin{IEEEkeywords}
% NEXT: AI-assisted digital twins, human-centric wireless systems, ray tracing,
% NEXT: RF-EMF exposure, whole-body specific absorption rate.
% NEXT: \end{IEEEkeywords}
% NEXT:
% NEXT: \maketitle
\begin{abstract}
Realistic urban radiofrequency electromagnetic-field (RF-EMF) assessment must
connect the field in a city to the power absorbed by the human body. This
supports monitoring and epidemiological studies. The goal of
this study is to compute direction-aware whole-body specific absorption rate
(SAR) along pedestrian routes in ten cities. We combine 360-degree street
images, photogrammetric geometry, and AI-derived object and material labels in
a human-centric digital twin. Its agentic AI stage uses SAM~3 Agent for
material and vegetation labeling. The calculation places possible transmitters
along visible rooflines at 15~GHz, traces direct and single-reflection paths,
and applies each arrival direction to an anatomical body model. Results are
normalized per unit product of source density and effective isotropic radiated
power. The ten routes contain 163 observation points, each evaluated with 64
independent runs. The normalized route-median whole-body SAR ranges from
0.00902 to 0.129~m$^2$~kg$^{-1}$, a factor of 14.31. Direct paths give the
largest component at 156 of 157 points with line of sight. The single-reflection
specular component is largest at one point, while the single-reflection diffuse component is
the only nonzero component at six shadowed points. Increasing the number of
runs from 48 to 64 changes the total at any point by at most 0.32\%. Validation
in a controlled scene gives maximum differences of 1.43\% against deterministic
quadrature and 0.80\% against an independent Sionna RT forward calculation.
The reported values apply to the selected routes under the stated source model.
\end{abstract}

## reviews (abstract)

_(empty: run the manuscript review pass to populate)_
