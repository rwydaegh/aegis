% PREV: \IEEEPARstart{W}{ireless} exposure of the human body is regulated
% PREV: through two basic restrictions in the \gls{ICNIRP} 2020
% PREV: guidelines~\cite{ICNIRP2020}, IEC/IEEE~63195, and IEEE~C95.1: the
% PREV: mass-averaged \gls{SAR} below 6~GHz, with peak values evaluated as
% PREV: \gls{psSAR10g}, and the surface-averaged \gls{APD} above 6~GHz. Direct evaluation uses
% PREV: \gls{FDTD} simulations on an anatomical
% PREV: phantom~\cite{Kodera2024,Diao2024,Hirata2021,Wydaeghe2026}. Resolving the submillimeter
% PREV: absorption layer at ten cells per wavelength
% PREV: sets a cell count of $10^{8}$ at 6~GHz, growing to $10^{12}$ near
% PREV: 100~GHz. A simulation campaign that covers frequencies, postures, and
% PREV: incidence directions takes weeks on \gls{GPU} clusters. Whole-body
% PREV: simulations above 30~GHz become computationally difficult~\cite{Wydaeghe2026}.
% PREV: This work shows that the surface absorbed-power map on a
% PREV: $10^4$-triangle body mesh reduces to one matrix-vector multiply,
% PREV: evaluated in under $10$~ms on a commercial modern GPU at any
% PREV: frequency from 1 to 100~GHz. The whole-body absorbed power
% PREV: reduces to only three precomputed scalars: the body mass, the
% PREV: body surface area, and the flux-weighted Fresnel transmission.
% NEXT: This work derives the closed form behind these coefficients. On
% NEXT: high-index tissue, the unpolarized Fresnel transmission becomes a
% NEXT: near-constant scalar~\cite{Azzam2015}. The local law then integrates
% NEXT: over a nonconvex body through a generalized Cauchy identity
% NEXT: from 1841~\cite{Cauchy1841}, with self-shadowing from ambient
% NEXT: occlusion~\cite{Zhukov1998,Landis2002,AkenineMoller2018}. A layered
% NEXT: correction in the fat layer covers the $3$~GHz dip~\cite{Flintoft2014}.
% NEXT: The five fitted coefficients are special cases of this expression. In
% NEXT: the mmWave band it reproduces \gls{FDTD} to within the tissue
% NEXT: dielectric uncertainty of $7\%$, at a small fraction of the cost. Because it is
% NEXT: also differentiable, antenna and beam design under exposure limits
% NEXT: becomes a continuous optimization.
Several groups already capture this absorption with a single fitted
coefficient~\cite{Bamba2014,Flintoft2014,Zhang2017thesis,ZhangRobinson2020,Kodera2024,Diao2024}.
The coefficient is defined in different ways, as an efficiency, a
normalized cross-section, or a transmission, but in every study it
falls between about $0.4$ and $0.7$ above $6$~GHz. This shared range
points to a single underlying closed-form quantity. Each coefficient
is fitted separately for each phantom and frequency from an \gls{FDTD}
sweep or a chamber measurement, so the values are slow to obtain, they
differ between studies, and they provide no gradients for design. No
study writes them as one expression, and none treats a nonconvex body
in closed form.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.vague_attribution`: "Several groups" is immediately backed by six named citations, so the attribution is concrete, not vague.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.misused_words.obtains_gets`: "slow to obtain" is a standard collocation for being costly to compute; the rule's swap to "slow to get" reads colloquial and would worsen, not improve, the line.
    - _dismissed_ `style.prose_structure.parallel_form`: Three coordinated clauses with co-referring subjects (values = they) read cleanly; forcing identical structure would be merely different, not clearer.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.spacing_ties.thin_space_math_units`: Math-wrapped integer plus text-mode tilde unit; matches the paper's deliberate "5~GHz"-style tie convention and the tie is present, so the form is internally consistent and changing it would be merely different.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).
