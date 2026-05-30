% PREV: \section{Introduction}\label{sec:introduction}
% NEXT: Several groups already capture this absorption with a single fitted
% NEXT: coefficient~\cite{Bamba2014,Flintoft2014,Zhang2017thesis,ZhangRobinson2020,Kodera2024,Diao2024}.
% NEXT: The coefficient is defined in different ways, as an efficiency, a
% NEXT: normalized cross-section, or a transmission, but in every study it
% NEXT: falls between about $0.4$ and $0.7$ above $6$~GHz. This shared range
% NEXT: points to a single underlying closed-form quantity. Each coefficient
% NEXT: is fitted separately for each phantom and frequency from an \gls{FDTD}
% NEXT: sweep or a chamber measurement, so the values are slow to obtain, they
% NEXT: differ between studies, and they provide no gradients for design. No
% NEXT: study writes them as one expression, and none treats a nonconvex body
% NEXT: in closed form.
\IEEEPARstart{W}{ireless} exposure on the human body is regulated
through two basic restrictions in the \gls{ICNIRP} 2020
guidelines~\cite{ICNIRP2020}, IEC/IEEE~63195, and IEEE~C95.1: the
mass-averaged \gls{SAR} below 6~GHz, with peak values evaluated as
\gls{psSAR10g}, and the surface-averaged \gls{APD} above 6~GHz. Direct evaluation uses
\gls{FDTD} simulations on an anatomical
phantom~\cite{Kodera2024,Diao2024,Hirata2021,Wydaeghe2026}. Resolving the submillimeter
absorption layer at ten cells per wavelength
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



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `Resolving the submillimeter absorption layer at ten cells per in-tissue wavelength sets a cell count of $10^{8}$ at 6~GHz` -> Front the subject so the verb arrives early: "Ten cells per in-tissue wavelength resolve the submillimeter absorption layer and set the cell count at $10^{8}$ at 6~GHz".
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

