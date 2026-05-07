# Report: DISCUSSION_CONCLUSION — Wave 2

## Edits applied

### En-dash conversions (numeric ranges: " to " → "--")
All instances of `X to Y` for numeric ranges in this section have been converted
to en-dash form per style rule 18. Specific changes:

- Table caption: `$1$ to $100\,$GHz` → `$1$--$100\,$GHz`; `$6$ to $100\,$GHz` → `$6$--$100\,$GHz`
- Table cells: `$0.3$ to $1\,$GHz`, `$10\%$ to $30\%$`, `$1$ to $6\,$GHz`, `$5\%$ to $10\%$`, `$6$ to $100\,$GHz` all converted to en-dash form
- Low-frequency boundary para 1: `$700\,$MHz to $1\,$GHz` → `$700\,$MHz--$1\,$GHz`
- Low-frequency boundary para 2: `$3$ to $5\,$GHz` → `$3$--$5\,$GHz`; `$5\%$ to $14\%$` → `$5\%$--$14\%$`
- High-frequency boundary para 1: `$200$ to $250\,$GHz` → `$200$--$250\,$GHz`; `$1.8$ to $2$` → `$1.8$--$2$`
- High-frequency boundary para 2: `$10$ to $100\,\mu$m` → `$10$--$100\,\mu$m`; `$0.4$ to $0.5\,$mm` → `$0.4$--$0.5\,$mm`
- Other regime boundaries: `$10^4$ to $10^5$` → `$10^4$--$10^5$`
- Conclusion para 1: `$0.3$ to $100\,$GHz` → `$0.3$--$100\,$GHz`

Preserved as "to": "growing from X to Y to Z" progressions (not ranges) and
prepositional "to" throughout.

### "hotspot/Hotspot" → "hot-spot/Hot-spot"
Three instances converted to hyphenated form per STYLE_ANALYSIS.md §2.3:
- `with hotspots at ankles` → `with hot-spots at ankles`
- `Hotspot positions` → `Hot-spot positions`
- `resonance and hotspots` (table cell) → `resonance and hot-spots`

### Result-then-reason restructuring — Low-frequency boundary
All three paragraphs previously buried the numeric boundary at the end. Restructured
to state the boundary up front, then give the supporting evidence.

Paragraph 1 (opacity): now opens "The opacity criterion places the lower validity
limit near $700\,$MHz--$1\,$GHz for limbs and near $250\,$MHz for a torso, below
which the wave passes through the body rather than being fully absorbed at the
surface." The penetration-depth table and formal criterion expression follow.

Paragraph 2 (Mie): now opens "The Mie regime sets a second lower limit: the
surface law underestimates absorption below $3$--$5\,$GHz on a torso and below
$1\,$GHz on a child phantom, where diffraction into the geometric shadow contributes
$5\%$--$14\%$." The ka derivation follows. The ambiguous "at body-part sizes in
mmWave" was replaced with "at body-part sizes at mmWave frequencies."

Paragraph 3 (resonance): now opens "Whole-body resonance dominates below
approx.\ $300\,$MHz, where the surface law is the wrong starting point." The
dipole resonance details and hot-spot discussion follow.

### Result-then-reason restructuring — High-frequency boundary
Paragraph 1 (Azzam): now leads "The pseudo-Brewster compensation softens above
$200$--$250\,$GHz, where the Azzam high-index criterion $|\ntilde| > 2.5$ weakens
and worst-case angular variation grows from $5.6\%$..." The refractive-index table
follows.

Paragraph 2 (roughness): now leads "Skin roughness sets an upper limit near
$1\,$THz, where the Rayleigh criterion $h\cos\theta/\lambda < 1/8$ is violated on
papillary-ridge-scale features and diffuse scattering becomes the dominant
correction." Feature-size and wavelength tables follow.

## Tougher questions for the author

Conclusion closing three-step shape: the closing sentence provides the headline
($\pm 7\%$) and condition (the band, $\pm 20\%$ dielectric input), but the
implication step (for regulators, network planners) lives in an earlier sentence of
the same paragraph ("Whole-body ICNIRP compliance no longer requires a per-scenario
full-wave solve"). The three-step shape is present across the paragraph, not in the
final line alone. A minimal fix: append "...uncertainty, placing routine compliance
assessment within closed-form reach." to the closing sentence — but this risks
padding what is already a clean close. Leave as-is unless the author wants an
explicit implication in the final line.

New compound adjective "papillary-ridge-scale" introduced in the roughness
paragraph rewrite: confirm this is the right level of specificity, or shorten to
"ridge-scale" for consistency with surrounding text.

## DOIs / references that look suspicious
None. Only \cite{Durney1986}, \cite{AlekseevZiskin2007}, and \cite{Azzam2015} are
cited in this range. Consistent with wave-1 finding.

## Anti-patterns found and fixed
- Numeric ranges with " to " instead of "--": 15 instances fixed.
- "hotspot" without hyphen: 3 instances fixed.
- Result-then-reason inversion: all five boundary paragraphs restructured.

## Patterns introduced
- Result-then-reason opening structure applied to all boundary-subsection paragraphs.
- En-dash form consistent throughout Discussion and Conclusion.

## Out-of-scope items spotted
- Wave-1 future-work sentence is correctly positioned before the closing assertion;
  three-step closing shape is intact and not padded.
- \section*{Acknowledgment} (singular, IEEE TAP) confirmed unchanged.

## Assessment: exposure-fraction paragraph in Other regime boundaries (wave-1 flag)

The paragraph ("The exposure fraction eta coincides with the ambient-occlusion factor
of computer graphics. On a $10^4$--$10^5$ triangle mesh it evaluates in tens of
milliseconds on commodity hardware.") is a computational-complexity note, not a
regime-boundary discussion. The other paragraphs in the subsection address physics
limits (near-field evanescent coupling, dielectric uncertainty). The connection to
regime boundaries is weak.

Recommendation: relocate to the section where ambient occlusion and the exposure
fraction are first introduced (methods or geometry section), or to a closing
computational remark in the compliance section. Do not expand it in place. Moving
it cross-section is outside this wave-2 agent's range.
