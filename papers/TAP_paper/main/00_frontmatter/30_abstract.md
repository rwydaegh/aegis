% PREV: \begin{document}
% PREV:
% PREV: \title{Closed-Form Absorbed-Power Dosimetry from~1~to~100\,GHz}
% PREV:
% PREV: \author{Robin~Wydaeghe$^{*}$~\orcidlink{0000-0002-1374-0118},
% PREV:   Luc~Martens~\orcidlink{0000-0001-9948-9157},~\IEEEmembership{Member,~IEEE},
% PREV:   G\"unter~Vermeeren~\orcidlink{0000-0002-5309-3808},~\IEEEmembership{Member,~IEEE},
% PREV:   Emmeric~Tanghe~\orcidlink{0000-0003-0020-6466},~\IEEEmembership{Member,~IEEE},
% PREV:   and~Wout~Joseph~\orcidlink{0000-0002-8807-0673},~\IEEEmembership{Senior~Member,~IEEE}%
% PREV:   \thanks{All authors are with the WAVES research group, Department of
% PREV:   Information Technology, Ghent University--imec, Technologiepark-Zwijnaarde
% PREV:   126, 9052 Ghent, Belgium.}%
% PREV:   \thanks{$^{*}$Corresponding author. E-mail: robin.wydaeghe@ugent.be.}}
% PREV:
% PREV: \markboth{IEEE Transactions on Antennas and Propagation,
% PREV: Vol.~XX, No.~X, Month~Year}%
% PREV: {Wydaeghe \MakeLowercase{\textit{et~al.}}: Closed-Form
% PREV: Absorbed-Power Dosimetry}
% PREV:
% PREV: \maketitle
% NEXT: \begin{IEEEkeywords}
% NEXT: APD, dosimetry, FDTD, Fresnel transmission, ICNIRP, mmWave, SAR.
% NEXT: \end{IEEEkeywords}
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

## reviews (abstract)



_PaperMaker9000 sweep — 2 flag(s) across 1 lens(es)._

- **abstract** — 2 flag(s), 16 cleared:
    - `structural.abstract.word_count_and_content` (high): `evaluated in under $10$~ms on a GPU` -> Spell out GPU on first use in the abstract: "on a graphics processing unit (GPU)".
    - `style.abstract_keywords.abstract_word_count_and_acronyms` (high): `evaluated in under $10$~ms on a GPU` -> Expand GPU on its first abstract appearance, e.g. "graphics processing unit (GPU)".
- **incremental (2026-05-22)** — pass (1 new/edited rules cleared).
