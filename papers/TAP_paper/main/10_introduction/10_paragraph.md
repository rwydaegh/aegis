% PREV: # Introduction
% NEXT: Several groups already capture this absorption with a single fitted
\IEEEPARstart{W}{ireless} exposure on the human body is regulated
through two basic restrictions in the \gls{ICNIRP} 2020
guidelines~\cite{ICNIRP2020}, IEC/IEEE~63195, and IEEE~C95.1: the
mass-averaged \gls{SAR} below 6~GHz, with peak values evaluated as
\gls{psSAR10g}, and the surface-averaged absorbed power density
(\gls{APD}) above 6~GHz. Direct evaluation uses
\gls{FDTD} simulations on an anatomical
phantom~\cite{Kodera2024,Diao2024,Hirata2021,Wydaeghe2026}. Resolving the submillimeter
absorption layer at ten cells per in-tissue wavelength
sets a cell count of $10^{8}$ at 6~GHz, growing to $10^{12}$ near
100~GHz. A simulation campaign that covers frequencies, postures, and
incidence directions takes weeks on \gls{GPU} clusters. Whole-body
simulations above 30~GHz become computationally difficult~\cite{Wydaeghe2026}.
This work shows that the surface absorbed-power map on a
$10^4$-triangle body mesh reduces to one matrix-vector multiply,
evaluated in under $10$~ms on a commercial modern GPU at any
frequency from 1 to 100~GHz. The whole-body absorbed power
reduces to only three precomputed scalars: the body mass, the
body surface area, and the flux-weighted Fresnel transmission.

## reviews (paragraph)

_(empty — run /review to populate)_
