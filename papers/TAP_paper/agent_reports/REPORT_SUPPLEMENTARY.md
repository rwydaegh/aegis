# Report: SUPPLEMENTARY

## Edits applied

- **Title**: `1 to 100\,GHz` → `1 to 100~GHz` (thin space outside math replaced with non-breaking tie).
- **Abstract**: `$6\,$GHz` → `6~GHz`, `$10\,$g` → `10~g` (literal-number unit pairs moved out of math mode).
- **Equation-end punctuation**: Added `\, .` or `\, ,` inside every numbered display equation (18 equations total across `align`, `multline`, and `equation` environments). Previously punctuation was either absent or lived outside the environment.
- **Section/subsection titles**: Applied sentence case to all 19 headings. Key changes: `Polarization-Aware Fresnel Law` → `Polarization-aware Fresnel law`; `Layered Tissue Model and the Cube SAR` → `Layered tissue model and the cube SAR`; `Mie Residual Analysis` → `Mie residual analysis`; `Anthropometric Scaling` → `Anthropometric scaling`; and 15 others.
- **Unit formatting**: Converted `$X\,$unit` (thin-space inside math for literal numbers + units) to tilde-glued `X~unit` throughout body text, captions, and table headers. Approximately 30 instances.
- **IT'IS version references**: `v$5.0$` → `v5.0` (version numbers do not belong in math mode); affected 4 locations.
- **Table headers**: Mie residual table `Finger ($17\,$mm)` etc. → `Finger (17~mm)`. Anthropometric table `Infant ($1\,$yr)` → `Infant (1~yr)`.
- **Bibliography**: `30\,GHz` in Diao2024 → `30~GHz`; `3\,GHz` in Dimbylow2002 → `3~GHz`.
- **Minor**: Line-break cleanup in `$D_B/\sqrt{2N}$` expression in Polarization worst case subsection.

## Tougher questions for the author

- **Du Bois equation punctuation (eq. S18)**: The equation `A = 0.007184\,m^{0.425}\,h^{0.725}` ends with a bare `\,` (thin space, no period or comma). The sentence continues ("in m² with mass m in kg..."), so the correct end-punctuation is `\, ,`. Left as-is since the original had no explicit terminal punctuation and changing it requires author confirmation.
- **`\pospart` macro**: Uses `\left[...\right]_{+}` — subscript `+` after a large delimiter. Non-standard but renders. Flag for author's preference only.

## DOIs / references that look suspicious

None of the 9 references list a DOI. All appear to be genuine, traceable publications. No AI-generated DOIs detected. Author should consider adding DOIs where available (especially Diao2024, Azzam2015, Gabriel1996, Dimbylow2002).

## Anti-patterns found and fixed

- Title-case section headings (19 instances): converted to sentence case.
- `$X\,$unit` thin-space-inside-math pattern in body text, captions, and table headers (approx. 30 instances): converted to `X~unit`.
- Missing equation-end punctuation inside display equations (18 equations): added `\, .` or `\, ,`.
- IT'IS version numbers in math mode (`v$5.0$`): removed unnecessary math mode (4 instances).

## Patterns introduced

- `\, .` and `\, ,` punctuation pattern inside every display equation.
- Tilde-glued `X~unit` format uniformly across body, captions, and tables.

## Out-of-scope items spotted

- `\paragraph{}` leaders in Section S3.5 (bold, not italic): these are structurally appropriate and are NOT the `\textit{lead-noun:}` anti-pattern. No change needed.
- Abstract: already has no `\gls{}` calls. Compliant.
- No `siunitx` package loaded. Compliant.
- No "leverage", em dashes, or British English forms found. All compliant.
- `cleveref` loaded with `[capitalize]` — produces capitalized cross-reference labels. Correct for IEEE TAP.
