% PREV: \subsection{Mie theory on lossy spheres}\label{subsec:val-mie}
% NEXT: \Cref{fig:mie} shows the Mie validation. \Cref{fig:mie}(a) shows
% NEXT: the error versus size parameter at $28$~GHz. It converges from
% NEXT: below towards the Fresnel limit $R_{\mathrm{sphere}} - 1 \approx
% NEXT: -1.2\%$ as $x \to \infty$. \Cref{fig:mie}(b) shows the error versus
% NEXT: frequency for four representative body-part diameters.
For a lossy sphere of radius $a$ and complex refractive index
$\ntilde$, the Mie series gives an exact solution for the absorption
efficiency $Q_{\mathrm{abs}}$. The geometric law predicts
$P_{\mathrm{abs}} = \IPD\,T_0\,\pi a^2$, so its error is
$(T_0/Q_{\mathrm{abs}} - 1)$. We use skin properties from the
IT'IS database~\cite{ITISv5,Gabriel1996} at each frequency. The total error splits into two
contributions. The Fresnel approximation error is shape- and
frequency-dependent but size-independent. On a sphere it is the
sphere ratio $R = T_0/\langle\Tavg\rangle$, which crosses unity at
approximately $39$~GHz (\cref{fig:R-of-f}). The diffraction error is
size-dependent and scales as $x^{-2/3}$ in the optical regime, where
$x = \pi d/\lambda$ is the size parameter. Diffraction bends waves
into the geometric shadow, adding absorption that the surface law
misses. We refer to the regime where $x$ is small enough that this
diffracted contribution exceeds a few percent of total absorption as
the \emph{body-Mie regime}. For body-scale targets it corresponds to
frequencies below approximately $6$~GHz.

## reviews (paragraph)



_PaperMaker9000 sweep — 3 flag(s) across 4 lens(es)._

- **sentence-craft** — 3 flag(s), 11 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `We use skin properties from the IT'IS database~\cite{ITISv5,Gabriel1996} at each frequency.` -> Skin properties come from the IT'IS database~\cite{ITISv5,Gabriel1996} at each frequency.
    - `style.positive_voice.subject_verb_early` (medium): `For a lossy sphere of radius $a$ and complex refractive index $\ntilde$, the Mie series gives an exact solution for the absorption efficiency $Q_{\mathrm{abs}}$.` -> The Mie series gives an exact solution for the absorption efficiency $Q_{\mathrm{abs}}$ of a lossy sphere of radius $a$ and complex refractive index $\ntilde$.
    - `style.prose_structure.subject_verb_rest` (high): `For a lossy sphere of radius $a$ and complex refractive index $\ntilde$, the Mie series gives an exact solution for the absorption efficiency $Q_{\mathrm{abs}}$.` -> Lead with subject-verb: "The Mie series gives an exact solution for the absorption efficiency $Q_{\mathrm{abs}}$ of a lossy sphere ..."
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.elegant_variation`: "surface law" describes the mechanism (a surface ReLU prediction) versus the named "geometric law"; both are honest descriptors here and collapsing them would lose the surface-vs-volume contrast the diffraction point relies on.
    - _dismissed_ `style.pet_peeves_wout.no_anthropomorphism`: Diffraction literally bending waves into the shadow is standard physical description, not anthropomorphism of a standards body, field, or algorithm.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.misused_words.which_that`: Non-restrictive clause adding a fact about R (already fully defined by the equation), correctly set off with a comma and "which"; "that the surface law misses" and "regime where x is small enough that" are correctly restrictive with "that".
    - _dismissed_ `style.anti_ai_language.false_ranges`: These are coordinated compound adjectives, not a "from X to Y" pseudo-scale construction; no false range is present.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: Lowercase \cref is correct inside a parenthetical mid-sentence aside, which renders "(fig. 2)"; \Cref is reserved for sentence-initial or running-text references that must capitalize.
    - _dismissed_ `latex.math.subscript_labels_upright`: Label subscripts abs are already upright via \mathrm; the $T_0$ subscript is a numeric literal, not a label, so it stays as-is.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

