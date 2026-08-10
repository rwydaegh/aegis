% NEXT: \IEEEPARstart{W}{ireless} exposure of the human body is regulated
% NEXT: through two basic restrictions in the \gls{ICNIRP} 2020
% NEXT: guidelines~\cite{ICNIRP2020}, IEC/IEEE~63195, and IEEE~C95.1: the
% NEXT: mass-averaged \gls{SAR} below 6~GHz, with peak values evaluated as
% NEXT: \gls{psSAR10g}, and the surface-averaged \gls{APD} above 6~GHz. Direct evaluation uses
% NEXT: \gls{FDTD} simulations on an anatomical
% NEXT: phantom~\cite{Kodera2024,Diao2024,Hirata2021,Wydaeghe2026}. Resolving the submillimeter
% NEXT: absorption layer at ten cells per wavelength
% NEXT: sets a cell count of $10^{8}$ at 6~GHz, growing to $10^{12}$ near
% NEXT: 100~GHz. A simulation campaign that covers frequencies, postures, and
% NEXT: incidence directions takes weeks on \gls{GPU} clusters. Whole-body
% NEXT: simulations above 30~GHz become computationally difficult~\cite{Wydaeghe2026}.
% NEXT: This work shows that the surface absorbed-power map on a
% NEXT: $10^4$-triangle body mesh reduces to one matrix-vector multiply,
% NEXT: evaluated in under $10$~ms on a commercial modern GPU at any
% NEXT: frequency from 1 to 100~GHz. The whole-body absorbed power
% NEXT: reduces to only three precomputed scalars: the body mass, the
% NEXT: body surface area, and the flux-weighted Fresnel transmission.
\section{Introduction}\label{sec:introduction}

## reviews (section_header)

_(empty — run /review to populate)_
