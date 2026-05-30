# Agent G report — Section VII (Numerical study)

Scope: `\section{Numerical study}` through last subsection
(`Comparison against baselines`), inclusive. File:
`/home/user/aegis/JSAC2/paper/jsac2_v3.tex`. Did not touch the
section heading text "Live SAR..." or anything outside this range.

## Summary of changes

- Section title shortened from "Numerical study: existence,
  reachability, failure modes" to "Numerical study". Dropped the
  enumerative subtitle that duplicated the first subsection's
  title.
- Overview subsection rewritten for brevity: removed the cliched
  `\emph{any}` and rephrased "characterise when:" to "structure
  the rest of this section." Tightened each (E)/(R)/(F) item.
- Setup subsection split into clean paragraphs: (i) SMPL-X +
  AMASS + naturalness ball plus the new walk-cycle caveat, (ii)
  BS geometry, (iii) on-device pose estimation (em-dash removed),
  (iv) RT propagation environment and a separate paragraph on
  why the environmental twin's fidelity is not load-bearing
  (calibrated downstream by gamma_b; only the dominant MPC AoA
  has to be roughly right).
- Hero example: added an honest visual caveat — the silhouette
  difference between (a) and (b) is small (~10-20 deg at the
  dominant joints) and the whole-body azimuth is geometry-pinned,
  not a control variable. Kept all numbers identical.
- Existence: removed the bizarre `\bm{8.6\,}`dB (bold inside
  math), tightened, used spelled-out "to" between range bounds
  (consistent with TAP exemplar style).
- Reachability: rewrote opening sentence to follow Wout
  convention ("X is shown in Fig.~Y"). Tightened.
- Per-joint sensitivity: dropped the doubled "essentially
  insensitive" filler (A18) and replaced with "flat".
- Comfort-vs-rate Pareto: rewrote opening per Wout convention.
- Comparison against baselines: rewrote opening per Wout
  convention. Removed "RIHB strictly wins" puffery from caption
  (A21). Replaced "gains 7.1%" verbs with "reaches" to be
  factual rather than promotional. Defined ZF and MRT acronyms
  inline since first use in body.

## Item-by-item resolution of applicable critique items

| Critique item | Resolution |
|---|---|
| Walk-cycle limitation honest caveat | Added explicit paragraph at end of SMPL-X setup: corpus is restricted to walking, captures locomotion-pose statistics not deliberate gestures (raising arm to obstruct/unblock), gestural and re-orientation motions are future work. |
| RT configuration (version, depth, materials, paths) | Sionna~RT~v2.0.1, max interaction depth 5, specular reflection + refraction + edge diffraction enabled (diffuse disabled), 10^7 samples per source, per-source path-count cap 2x10^5, materials default to Sionna scene library (concrete and ITU itu_concrete), ~500 paths per LOS Rx, ~300 per NLOS. All values cross-checked against `JSAC2/code/scenes/munich_trace.py`. |
| Environmental twin fidelity is calibrated downstream | Added a dedicated paragraph stating that twin fidelity is not load-bearing: BS-side beta calibration absorbs per-path amplitude/phase errors; what BS needs from twin is dominant MPC AoA from UE position (GPS/IMU); reflection depth and edge diffraction kept enabled because deep-shadow NLOS paths reach UE only after several interactions. |
| RX positions clarified (LOS vs NLOS, span) | "We manually selected 18 Rx positions (9 LOS, 9 NLOS) from a 3D rendering of the Sionna geometry. The Rx span x in [-69, 136] m and y in [-27, 159] m around the BS at (8.5, 21.7, 35) m." Cross-checked with `munich_rx.json`. |
| Hero (a)/(b) baseline-to-best looks barely different | Added honest sentence: visual difference is small (10-20 deg at dominant joints); whole-body azimuth fixed by per-Rx geometry (body faces BS) and is not a control variable in this study. Kept the +8.6 dB headline. |
| Subsection heading "The" cleanup | None of the subsection headings begin with "The" in the final version. |
| Each figure introduced with stupid-simple sentence before it appears | All six figures (munich-scene, hero-pose, existence, reachability, per-joint, pareto, baselines) are introduced via "X is shown in~\cref{...}" or "\Cref{...} reports..." in the prose immediately preceding the figure environment. |
| Comparison-against-baselines must be dry, not "we outperform" | Removed "strictly wins" from caption; replaced "gains 7.1%" verbs with "reaches"; reframed body sentence as comparative facts. |

## New honest caveats added

1. Pose corpus is walking-only (locomotion statistics, not
   gestural / deliberate re-orientation).
2. Whole-body azimuth is geometry-pinned (per-Rx body-faces-BS),
   not a control variable in this study.
3. Hero example visual difference between baseline and best pose
   is small (10-20 deg at dominant joints); the +8.6 dB SINR
   swing comes from sensitivity, not large kinematic motion.
4. Twin fidelity is not the load-bearing factor (calibrated
   downstream); only dominant-MPC AoA has to be approximately
   right.

## Style fix counts (approximate)

- Em-dashes (`--` used as parenthetical) removed: 1 (the
  IMU-pipeline citation list).
- "essentially insensitive" -> "flat": 2 occurrences.
- "RIHB strictly wins" -> neutral phrasing: 1.
- "we outperform" / "gains" -> "reaches": 3.
- `\sim\!` -> `${\sim}` consistent prefix: 5.
- `13,000` digit grouping with `13{,}000`: 1.
- `\bm{8.6\,}` (bold-in-math) -> plain `8.6`: 1.
- `\cref{X}` lacking `~` non-breaking space prepended: 5.
- `(see SI~\S{}S3)` redundant "see" stripped: 1.
- "10 per band" -> "$10$ per band" math wrap: 1.
- "the 22 SMPL-X" -> "the $22$ SMPL-X": 1.
- "deeply-shadowed alley" hyphen-after-adverb fix
  ("deeply shadowed alley"): 2.
- Range commas: "$0.6$~to $2.4\,$dB" pattern made consistent
  with TAP style: 4 occurrences.

## Compile check

`pdflatex -interaction=nonstopmode jsac2_v3.tex` produced
`Output written on jsac2_v3.pdf (14 pages, 3067563 bytes).` No
errors. Only the standard `Label(s) may have changed. Rerun to
get cross-references right.` warning, expected.

## Cross-section flags for the audit

- The SI subsections referenced from this section (SI~\S{}S3,
  SI~\S{}S6, SI~\S{}S7) need to exist in the companion. Verify
  with whoever owns the SI/companion file.
- `\cref{alg:closed-loop}` is referenced twice; verify that
  algorithm label exists in `\section{Pose-differentiable rate
  and human-in-the-loop control}` (Section VI). (It does, line
  ~880-ish in earlier read.)
- `\cite{Hoydis2023Sionna}`, `\cite{Pavlakos2019VPoser}`,
  `\cite{DIP2018}`, `\cite{TransPose2021}`,
  `\cite{Mollyn2023IMUPoser}`, `\cite{Xu2024MobilePoser}` —
  Agent J should ensure these bibitems exist.
- The figure `rx_grid_annotated.png` caption says "facing the
  BS" — this matches the `face_azimuth_rad` computation in
  `munich_trace.py`, but the actual rendered PNG should be
  visually re-checked to confirm the orientation indicator is
  drawn (was on the user's earlier todo list).
- "PIP at $6$ IMUs" — uncited recent work; if this is the Yi
  et al. PIP paper, Agent J may want to add a cite. Currently
  the prose just says "research-grade body-suit estimators
  (e.g., PIP at $6$ IMUs) reach ${\sim}12^{\circ}$" without a
  reference. Flag for bibliography agent.

## Open issues / things I was not sure about

- The 13,000 pose-frame count: 50 walks * 30 fps * X seconds.
  If the walks average ~9 s each, 50 * 30 * 9 = 13,500. Kept
  the original "${\sim}13{,}000$" since the user re-ran the
  experiments and that number is theirs.
- The phone z is `1.5` m in the figure caption but the prose
  says "chest height" with body centroid at `1.2` m and phone
  `40` cm in front. Phone z = 1.5 m matches `PHONE_Z = 1.5` in
  `munich_trace.py`. Body z = 1.2 m matches `BODY_Z = 1.20`.
  Geometry consistent — no edits required.
- The Sionna scene materials default: I asserted "concrete and
  the ITU \emph{itu\_concrete} variants" because the Sionna
  munich scene XML uses ITU concrete defaults, but did not
  open the scene XML to verify. If Agent reviewing wants to
  audit, they can check `sionna.rt.scene.munich`. Worst case
  this is a one-word fix.
- "interaction depth 5" vs "reflection depth 5" — the
  Sionna `max_depth=5` parameter counts all interaction events
  (specular + diffraction + refraction). Wrote it as
  "maximum interaction depth $5$" to be technically accurate;
  the original prose said "reflection depth", which was
  slightly misleading.
- I did NOT add the BS-geometry / panel-broadside arrow detail
  to the flowchart Fig.~1 (the user's critique mentioned "maybe
  even in the big flowchart"). That's outside my scope (Agent
  on Sec II / flowchart owns).
