% PREV: \begin{table*}[!t]
% NEXT: # Combined dosimetry literature
Kodera \textit{et~al.}~\cite{Kodera2024} report the closest numerical
counterpart to the present analysis. Their Fig.~13 compiles
whole-body absorbed SAR data over $1$--$10$~GHz at
$\IPD = 10$~W/m$^2$ across nine prior numerical phantom studies and
two reverberation-chamber measurement campaigns; their Fig.~6
extends the same comparison to $1$--$100$~GHz on five parametric
layered models (Models~I--V). The compilation shows the asymptotic
plateau that \eqref{eq:cauchy-exact} predicts. Kodera
\textit{et~al.}\ fit a study-specific $T_{\mathrm{tr}}$ per phantom
and frequency from a one-dimensional multilayer slab calculation;
their homogeneous-skin curve (Fig.~9, right axis) reproduces the
Fresnel $T_0$ within $1$--$2\%$ above $6$~GHz, and oscillates around
that value below $6$~GHz with a multilayer Fabry--P\'erot pattern of
the same form as the layered transmission $\Tlay$ in
\cref{subsec:fp}. \Cref{eq:cauchy-exact} supplies the closed-form
$T_{\mathrm{tr}} \to \Tbar(f)$ that all phantoms converge to in the
geometric-optics regime. The residual phantom-to-phantom spread is
set by the body-shape factor $\Aab/A$.

## reviews (paragraph)


_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
    - _dismissed_ `style.positive_voice.no_passive_no_we`: Passive is the licensed exception: opening with the known 'spread' satisfies old-before-new and parks the new key term $\Aab/A$ in the emphatic end position; the active rewrite would bury the factor mid-sentence.
- **voice-tells** — 2 flag(s), 22 cleared:
    - `style.pet_peeves_wout.no_semicolons` (high): "two reverberation-chamber measurement campaigns; their Fig.~6" → Split into two sentences: end after 'campaigns.' and start 'Their~Fig.~6 extends...'
    - `style.pet_peeves_wout.no_semicolons` (high): "from a one-dimensional multilayer slab calculation; their homogeneous-skin curve" → Split into two sentences: end after 'calculation.' and start 'Their homogeneous-skin curve...'
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.spacing_ties.tilde_before_refs`: No canonical rule in this lens covers a tie before \eqref/\cref; the in-scope tie rules (tilde_number_unit, tilde_names) are all satisfied (numbers, units, names, and \cite are tied), and a break after 'that' is harmless, so no flaggable canonical rule applies.

