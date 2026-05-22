% PREV: Whole-body ICNIRP compliance reduces to one inequality on three
% PREV: precomputed scalars (\cref{eq:Sinc-max-worst}). The same algebra
% PREV: evaluates the existing reference levels for under- or over-protection
% PREV: across the population without an FDTD campaign.
% NEXT: The closed form gives a closed-form certificate that the existing
% NEXT: reference level fails the basic restriction for the three smaller
% NEXT: body sizes under worst-case directional exposure. Under realistic
% NEXT: plane-wave or multipath exposure the directivity is below this
% NEXT: worst case, and the basic restriction is met~\cite{ICNIRP2020}. The
% NEXT: closed form makes both the worst-case and the directional-average
% NEXT: evaluation explicit.
The ICNIRP general-public reference level above $6$~GHz is
$10$~W/m$^2$~\cite{ICNIRP2020}. Reference levels are the
operationally measured incident-power-density limits intended to
imply compliance with the underlying basic restriction, here
$0.08$~W/kg whole-body SAR. Setting $\IPD_{\mathrm{max}} =
10$~W/m$^2$ in~\eqref{eq:Sinc-max-worst} returns the threshold
$m/A \geq 33.9$~kg/m$^2$ at $\Tbar = 0.543$ ($28$~GHz on skin).
\Cref{tab:anthro} lists $\IPD_{\mathrm{max}}$ values of $6.2$,
$7.6$, and $9.9$~W/m$^2$ for the infant, the six-year-old child, and
the adolescent under the worst-case directional bound
$D \le 2A_{\mathrm{CH}}/\Aab$. The reference level exceeds these
thresholds by $61\%$, $32\%$, and $1\%$ respectively.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `BOOK_ELOS_style.misused_words.respectively`: Three thresholds map to three percentages; the pairing is not unambiguous from order alone, so respectively earns its place (and respectively_welcome explicitly endorses it).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: The number-in-math, unit-in-text `$N$~unit` form is the deliberate paper-wide convention (535 such uses across main/, zero siunitx); it is applied consistently, so reformatting one leaf would break uniformity rather than improve it. Same disposition for thin_space_math_units / thin_space_units / siunitx_consistency.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

