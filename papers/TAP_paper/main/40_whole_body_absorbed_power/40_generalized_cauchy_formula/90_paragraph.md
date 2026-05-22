% PREV: \begin{table}[!t]
% PREV: \centering
% PREV: \caption{Normal-incidence transmission $T_0$, flux-weighted
% PREV: transmission $\Tbar$, and their ratio $R = T_0/\Tbar$ for skin
% PREV: (IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}).}\label{tab:Tbar}
% PREV: \begin{tabular}{rcccc}
% PREV: \toprule
% PREV: $f$\,[GHz] & $|\ntilde|$ & $T_0$ & $\Tbar$ & $R$ \\
% PREV: \midrule
% PREV: 0.3 & 7.93 & 0.381 & 0.406 & 0.938 \\
% PREV: 0.9 & 6.70 & 0.445 & 0.465 & 0.957 \\
% PREV: 2.4 & 6.29 & 0.470 & 0.488 & 0.964 \\
% PREV: 6.0 & 6.07 & 0.481 & 0.497 & 0.968 \\
% PREV: 10  & 5.87 & 0.489 & 0.504 & 0.971 \\
% PREV: 28  & 4.84 & 0.536 & 0.543 & 0.988 \\
% PREV: 40  & 4.30 & 0.570 & 0.571 & 1.000 \\
% PREV: 60  & 3.68 & 0.622 & 0.613 & 1.015 \\
% PREV: 100 & 3.01 & 0.701 & 0.677 & 1.035 \\
% PREV: \bottomrule
% PREV: \end{tabular}
% PREV: \end{table}
The reverberation-chamber literature has been measuring $\Tbar$
directly. Bamba's empirical efficiency $\eta(f)$
coincides with $\Tbar(f)$ to $3\%$ at $5.8$~GHz on four FDTD ellipsoid
phantoms under diffuse-field exposure~\cite{Bamba2014}. It diverges below
$3$~GHz, where the body-Mie contribution to absorption on a finite
ellipsoid becomes non-negligible (\cref{tab:bands}). The framework
is mainly a mmWave method.
Flintoft's plateau $\langle Q^a\rangle/\gamma_s = 0.47$--$0.49$
at $7$--$11$~GHz matches $\Tbar$ at the same frequencies to $2\%$~\cite{Flintoft2014}.
Zhang's plateau $\xi = 0.45$--$0.65$ above $6$~GHz brackets
$\Tbar\cdot\Aab/A$~\cite{Zhang2017thesis}.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `Bamba's empirical efficiency $\eta(f)$ for diffuse-field exposure on four FDTD ellipsoid phantoms~\cite{Bamba2014} coincides with $\Tbar(f)$ to $3\%$ at $5.8$~GHz.` -> Move the qualifier after the verb: "Bamba's empirical efficiency $\eta(f)$ coincides with $\Tbar(f)$ to $3\%$ at $5.8$~GHz on four FDTD ellipsoid phantoms under diffuse-field exposure~\cite{Bamba2014}."
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.no_anthropomorphism` (high): `The reverberation-chamber literature has been measuring $\Tbar$ directly.` -> Attribute the action to the studies, not the literature: "Reverberation-chamber studies have measured $\Tbar$ directly."
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.math.subscript_labels_upright`: The italic superscript label "a" in $Q^a$ is the quoted notation from the cited reverberation-chamber source (Flintoft) and is used identically in five other places across the paper (main.md L884, L896, L1136, L1192, L1212); switching one leaf to $Q^{\mathrm{a}}$ would desync notation and is a paper-wide convention call, not a single-leaf defect.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

