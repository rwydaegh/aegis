% PREV: \IEEEPARstart{W}{ireless} exposure on the human body is regulated
% NEXT: This work derives the closed form behind these coefficients.
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

