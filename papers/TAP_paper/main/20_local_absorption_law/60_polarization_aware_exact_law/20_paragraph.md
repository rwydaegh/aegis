% PREV: A plane wave is fully polarized.
% NEXT: # Polarization-aware exact law
To proceed, write
\begin{equation}\label{eq:Teff-decomp}
  \Teff(\rr) = \Tavg(\theta) + \tfrac{1}{2}\,q(\rr)\,\Delta T(\theta)\, ,
\end{equation}
with $\Tavg = \tfrac{1}{2}(T_s + T_p)$ the unpolarized baseline,
$\Delta T = T_p - T_s$ the polarization splitting, and $q = |e_p|^2 -
|e_s|^2 \in [-1, 1]$ the local TM excess. The polarization correction
vanishes pointwise for circular illumination, in expectation for
random-orientation linear illumination, and to within $2.5\%$ for
multipath averaging above 20 paths. First, for circular polarization
the TE and TM intensities are equal at every point on every body, so
$q \equiv 0$ pointwise. Second, for linear polarization with random
ensemble orientation either in space or time, the ensemble average
$\langle q\rangle$ vanishes by the same argument. Third, for a body
in a multipath environment with $N$ independent path orientations,
the variance of the polarization correction scales as $D_B/\sqrt{2N}$,
where $D_B \le 16\%$ is the body's polarization directivity on the
Thelonious phantom, and for $N \ge 20$ paths the correction drops
below $2.5\%$. Section~\ref{si:fresnel} of the SI derives all three
conditions and the $D_B/\sqrt{2N}$ variance bound. Under any of these conditions the exact law reduces to
\begin{equation}\label{eq:Sab-Tavg}
  \APD(\rr) = \IPD \, \Tavg(\theta(\rr)) \, \pospart{\mu(\rr)}\, .
\end{equation}
The angular dependence is now confined to the scalar function
$\Tavg(\theta)$. The next section shows that this function is nearly
constant for biological tissue.

## reviews (paragraph)


_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): "multipath averaging above 20 paths" → Use a non-breaking tie before the number: "above~20 paths".
- **lexical-spotcheck** — 1 flag(s), 53 cleared:
    - `style.anti_ai_language.first_second_third_overuse` (low): "First, for circular polarization the TE and TM intensities are equal at every point on every body, so $q \equiv 0$ pointwise. Second, for linear polarization with random ensemble o…" → Drop the First/Second/Third cadence (the prior sentence already enumerates the three conditions) and join with prose connectives such as "For circular illumination... For random-orientation linear illumination... For a multipath body...".
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.structure_style.acronym_first_use`: TE/TM and the SI are standard EM/document acronyms whose first definition lives in an earlier leaf of this polarization section; cannot establish first use at leaf scope, and the prev neighbour does not define them.
    - _dismissed_ `latex.math.subscript_labels_upright`: The s/p polarization subscripts on $T_s$, $T_p$, $e_p$, $e_s$ are universally italic in Fresnel notation and the B on $D_B$ is a conventional identifier; forcing \mathrm here would diverge from the paper-wide convention, a notation-block decision not fixable at leaf scope.
    - _dismissed_ `latex.substitutions.cref_capitalized`: Manual "Section~\ref" is standard IEEE cross-referencing; the paper need not adopt cleveref, so \Cref is not required.

