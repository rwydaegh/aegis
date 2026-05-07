# Report: VALIDATION

Lines 944–1223 of `paper.tex` (`\section{Validation}` and all four subsections).

## Edits applied

- **Subject-verb agreement**: "literature … tests" → "literature … test" (section intro).
- **Unit spacing — all `$X\,$UNIT` → `$X$~UNIT`** for plain numeric literals throughout: 2 mm, 5 GHz, 60 GHz, 0.45–5.8 GHz, 1 mm, 4 mm, 39 GHz, 28 GHz (body text, subfig captions, main captions, table rows, discussion paragraphs), 7 GHz, 5.8 GHz, 100 GHz, 12 GHz, 11 GHz, 18 GHz, 10–100 GHz, 3 GHz, 9 GHz, table cell values (48.12 mW, 47.95 mW, 0.185/0.186/0.539 W/m², 105.9 mW, 10 W/m², 4 cm²).
- **Standard number spacing**: `IEC/IEEE\,$63195` → `IEC/IEEE~63195`.
- **Subsection headings — sentence case applied**:
  - `Mie Theory on Lossy Spheres` → `Mie theory on lossy spheres`
  - `Full Fresnel on the Thelonious Phantom` → `Full Fresnel on the Thelonious phantom`
  - `Sim4Life FDTD on the Thelonious Phantom` → `Sim4Life FDTD on the Thelonious phantom`
  - `Combined Dosimetry Literature` → `Combined dosimetry literature`
- **Result-then-reason restructuring (Mie paragraph)**: "Fingers at sub-mmWave frequencies are the worst case, with errors above 30%" → "For fingers at sub-mmWave frequencies, errors exceed 30%." Number pulled forward; semicolon replaces comma before mechanism clause.
- **Topic-first paragraph (Combined dosimetry literature)**: Paragraph now leads with `\Cref{fig:waterfall} compares…` instead of the equation cross-reference.
- **Post-table paragraph (Full Fresnel subsection)**: Added `\Cref{tab:phantom} reports total absorbed power, mean, and peak $\Sab$.` as topic sentence. Moved "total power error is 0.35%" up as the second sentence; removed the redundant "total power error is below 1%" at end.
- **Awkward line break fixed**: "…closed form. The second\nis the direction-averaged…" → "…closed form. The second metric\nis the direction-averaged…".

## Tougher questions for the author

None. All changes were unambiguous style fixes.

## DOIs / references that look suspicious

- **`\bibitem{Bamba2014}`**: The cite key implies 2014, but the entry lists **Feb. 2013** (Bioelectromagnetics, vol. 34, no. 2, pp. 122–132). Verify whether the key should be `Bamba2013` or whether 2014 is the correct year (online-first vs print). All `\cite{Bamba2014}` calls will need updating if the key changes.
- No DOIs appear in any of the six heavily-cited entries. None look fabricated — they simply omit DOIs, which is acceptable.

## Anti-patterns found and fixed

- Title-case subsection headings (four headings converted to sentence case).
- Buried lead in post-table paragraph.
- Paragraph opening with equation cross-reference instead of figure or numeric claim.
- `$X\,$UNIT` thin-space pattern (replaced with `$X$~UNIT` throughout).

## Patterns introduced

- Topic-first opening for Combined dosimetry literature subsection.
- Result-then-reason restructure in Mie error paragraph.
- `\Cref{tab:phantom} reports…` topic sentence introducing the Fresnel statistics paragraph.

## Out-of-scope items spotted

- Many `$X\,$UNIT` patterns remain in lines 1224+ (Higher-Order Corrections and beyond). Out of scope.
- The Bamba2014 key/year mismatch affects all cite locations throughout the paper.
