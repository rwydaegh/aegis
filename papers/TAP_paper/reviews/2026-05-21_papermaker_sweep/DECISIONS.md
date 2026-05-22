# Sweep decisions — Robin, 2026-05-22

Verbatim record of Robin's verdicts on `RANKED_REPORT.md`, in report order, plus
resulting actions. Legend: ✅ apply · ❌ skip · 🔁 reword (see note) · 🔍 investigated
(findings below) · ❓ needs Robin. Unlisted items = "no comment → agree → apply".

General standing instruction (applies to every prose fix below):
> do check the surrounding context well. since it risks ruining the flow a bit by
> having the perfect sentence but at the cost of a tougher-to-read paragraph...
> especially when meaning gets lost.

---

## style.positive_voice.no_passive_no_we (20)

1. ✅ ok
2. ✅ ok
3. ✅ ok
4. ✅ ok
5. ✅ ok
6. ✅ ok
7. 🔁 Robin's wording: **"The theory is validated in four independent ways"** (keep this passive form; overrides my "Four checks validate the theory").
8. ✅ ok
9. ✅ ok
10. ✅ ok
11. ✅ ok
12. 🔁 "ok but wdym 'in turn' here? idk if necessary? or simpler way" — drop "in turn"; see Q1.
13. ✅ "ok on option 1" → **"First, consider the influence of curvature."**
14. ❌ "youve lost meaning there. We is not a crime" — keep original (the rewrite asserted a different claim).
15. 🔁 "ok but gives the largest" → "...**gives the largest** skin deviation of ±7% at 28 GHz."
16. ✅ ok
17. ❌ no — keep "the basic restriction is met".
18. ✅ "you altered meaning slightly, but the spirit is good" — apply, preserve original meaning.
19. ✅ ok
20. ❌ "no, changes meaning here. it's a conclusion" — keep "A closed-form method is proposed".

## style.positive_voice.subject_verb_early (18)

1. ❌ no — "somehow this changes the meaning but throwing away the connective tissue".
2. ✅ ok
3. ❌ no, confusing.
4. ✅ ok
5. ❌ no — "you threw away connective tissue that made it easier to read".
6. 🔁 "this is a good opportunity to use ..., e.g., .... (with those commas)" → "Concavities, e.g., the armpits, the gap between the legs, and the neck region, cause one part of the body to shadow another."
7. ✅ ok
8. ❓🔁 "the idea is goodish but you threw away Flintoft's and that's not acceptable. perhaps... idk if u can come up with something" — keep "Flintoft's"; see Q2.
9. ✅ ok
10. ✅ ok
11. ✅ ok
12. ✅ ok
13. ❌ "this is an example of you throwing away an article illegally. prolly not worth it idk" — keep "The ratio of law to FDTD...".
14. ✅ ok
15. ✅ ok
16. ✅ ok
17. ✅ ok
18. ✅ ok

## style.pet_peeves_wout.tilde_spacing (9)
✅ not commented → agree → apply all 9 non-breaking ties.

## figures.conventions.axis_units (4)
✅ "figures: all ok, i like [\,]" — apply the dimensionless bracket using `[\,]` for consistency.

## structural.spine.section_opening_frames_content (4)
Standing note: "in general, this is the moment to refer to the famous flowchart as guiding light."
1. ❓ "why not sentence 1 or one before?" — see Q3.
2. 🔁 "hmh. idk if that will flow well. you are in a 'Methods: XXX' section after all. but maybe refer to flowchart idk." — lean to a flowchart reference; see Q3.
3. ✅ fair.
4. ❌ "and no we wont do this. it's fine." PLUS global instruction: **stop using the word "band stratification"** everywhere (find/replace across paper).

## style.pet_peeves_wout.no_semicolons (3)
✅ "semicolons all good, go fix" — apply all 3.

## structural.results.no_interpretation_in_results (2)
❌ "this rule only contains if we do a proper IMRAD structure, here we dont." — skip both. (Rule note: presupposes a Results section distinct from Discussion.)

## structural.introduction.contribution_matches_paper (2)
1. ✅ "its fine".
2. 🔍❓ investigated — see "Investigation A" + Q4 (168 / phantom count).

## style.prose_structure.subject_verb_rest (2)
1. ✅ "youre already rewriting it anyways" (handled by the mie rewrite).
2. ✅ ok.

## style.prose_structure.action_in_verb (2)
1. ✅ ok.
2. ✅ "ok but into → in, no?" — apply with "into" → "in" (in the convergence sentence).

## BOOK_WILLIAMS comma_after_long_intro (4)
✅ 1 ok, 2 ok, 3 ok, 4 ok — apply all.

## figures.conventions.scripting_log_ticks (2)
✅ 1 ok, 2 ok — apply both (explicit linear-readable ticks).

## structural.spine.paragraph_point_sentence_position (2)
1. ❌ "nah. it's kinda like a derivation".
2. ❌ "nah". (But see Q5 — Robin asked to explain the mie "total error splits" reorg in more detail.)

## style.prose_structure.consistent_topic_thread (2)
1. ✅ ok.
2. ❌ "no, need that at that point specifically".

## BOOK_ELOS while_as_although (3)
✅ 1 ok, 2 ok, 3 ok — apply (while → whereas).

## abstract GPU (word_count + abstract_keywords)
✅ expand on first use, **"Graphics Processing Unit (GPU)" with capitals**.

## figures.wout_specifics.flowchart_style
❌ "flowchart colors: no, disregard".

## BOOK_WSRA figures.conventions.stand_alone (±4% band)
❌ "4% on figure: no".

## figures.visual_quality.colorblind_friendly
❌ "no, i like jet actually (my pet peeve)" — keep jet.

## figures.conventions.scripting_colour_palette (error-budget grey/navy)
✅ not mentioned → assume apply (Wong palette). Flagged in Q8 in case the jet pet-peeve extends here.

## structural.discussion.limitations_explicit
❌ "limitation: no".

## structural.discussion.six_element_checklist
❓ "i am confused? what would you add then? what is this rule even" — see Q6.

## style.pet_peeves_wout.first_time_framing
✅ "YES. do it a lot but dont go insane... vary it with 'premier' or something... mostly on those places where it feels justified." — apply, varied, on justified load-bearing claims.

## latex.math.vector_matrix_bold_consistent
❌ "skip. that gets a pass this paper".

## style.prose_structure.topic_sentence_first
🔁 "I need ya to mention flowchart first... so dont add a sentence. however lead the sentence with **'Next, as shown in the flowchart \ref, ...'** (no passive, no we, btw)." — apply that exact opener pattern.

## style.pet_peeves_wout.no_anthropomorphism (literature measuring)
❌ "i think here it is actually okay" — keep "The reverberation-chamber literature has been measuring...". (Note: flowchart anthropomorphism IS to be fixed — see adversarial item below.)

## style.prose_structure.emphatic_end
❌ "no".

## latex.structure_style.first_coinage_italics (2)
✅ "ok for both" → literally just `\emph{exposure fraction}` and `\emph{sphere ratio}`. (My note about \emph toggling inside italics was overexplaining; ignore it.)

## structural.results.negative_results_acknowledged (grazing angles)
🔍 "interesting remark, not bad" — investigated (Investigation B); Robin will decide what to take. See Q7.

## structural.spine.section_opening_point_last
❌ "no".

## structural.methods.section_title_antipatterns (Configuration vs Setup)
🔁 "would setup be a better subsection title than configuration?" — yes; see Q9 answer.

## latex.spacing_ties.equation_punctuation_gap (the \,)
✅ "the \, you can add it yes" — apply.

## latex.structure_style.no_sentence_starting_with_acronym (Fig.)
✅ "Fig. is an exception... it is always Fig. you may edit the rule" — **rule edited** (Fig. exempt). No manuscript change.

## latex.math.subscript_labels_upright (γ_s)
❌ "γ_s is actually how Flintoft writes it so leave alone".

## latex units math mode (units_math_mode_consistent + thin_space_math_units)
✅ "math mode units: ok" — apply (0.08 W/kg → $0.08\,\mathrm{W/kg}$).

## structural.introduction.para6_organization
✅ "yes, but do so very well. So, '... as follows', then an enumeration. Using simple connector words like 'Then, '. Subject verb the rest. Simple, KISS, clear, especially verb choose. To the point. Simple." — draft roadmap paragraph accordingly.

## style.anti_ai_language.title_case_headings
❌ "false positive so no" (Cauchy is a proper noun).

## style.anti_ai_language.first_second_third_overuse
🔁 "this is actually a PATTERN rather than an ANTI pattern. deeeefinitely remove this from ai language... first second third/finally is a top pattern that I love. you can even scan the paper for places where we can drop-in add these connectors (dont force it)." — **rule deleted; connectors.md now endorses it.** Plus: scan paper for drop-in ordinal opportunities (don't force).

## Incremental pass-1
- KISS verb change: ✅ yes.
- section_economy: ✅ "both ok".

## Cross-section / section-flow
"most of the cross section/paragraph stuff i already addressed, please list only those i have not addressed."
→ All section-flow rows duplicate per-rule findings already decided above; nothing new EXCEPT Q5 (explain the mie "total error splits" reorg in detail).

---

## Adversarial cold read

- **FDTD per-direction spread (1.06 / 1.20 / 0.83):** 🔍 answered — YES, consistent with the paper's own implied uncertainty at 7 GHz (Investigation C). Optionally state the 7.2-vs-10 cells/in-tissue-wavelength point. One caption nit: the error-budget figure says "28 GHz" while the text invokes "7 GHz" (both round to ±7%, but a reviewer could notice).
- **10 ms claim:** ❓ Robin: "i genuinely dont think it's an issue... modern commercial GPU... 10 ms is an upper bound." — my honest take in Q10.
- **Single-phantom generalization:** ✅ add one sentence: results generalize well across phantoms, and a small (child) phantom is the worst case because diffraction is more prominent — which motivates choosing it. (Draft pending.)
- **Flowchart metadiscourse / anthropomorphism:** 🔁 keep the flowchart as guiding light, but de-anthropomorphize ("the flowchart doesnt do the research lol"): use "as shown in the flowchart" phrasing; the sentence is about the structure/physics, not the flowchart acting.

---

## Pass-2 (redone kiss + new rules)

Standing instruction: **"falls", "drops", "stays" can be kept** (mild, carry meaning).
→ kiss rule updated; the following pass-2 kiss flags are **RETRACTED**:
10_introduction_20 (falls between), 20_..._60_20 (drops below), 30_mechanism_10 (has fallen below),
30_geometric_70_10 (drop to zero), 40_layered_20 (slope falling to), 50_mie_40 (stays within),
50_sim4life_10 (falls inside), 50_residuals_50 "stays below" (the "brings this to → gives" half stands),
80_validity_20 (must stay smaller).

kiss flags that STAND: collapses (intro_30, cauchy_60, conclusion_20), decouples (conclusion_20),
shrinks (conclusion_30 → "is on the order of **centi- to millimeters**"), softens (validity_70 → weakens),
brackets...within (cauchy_40), brings...to (residuals_50), delivers/controls (pssar_30),
carries (comp_struct_20), re-enters (polariz_10), moves (brewster_10 → fold into flowchart-reframe).

no_dropped_article (3): ✅ all three stand (Body surface area → The body surface area;
Skin refractive-index modulus → The skin...; Wavelength → The wavelength).

paragraph_substance (17 stubs): broadly ✅ ("broadly im agreeable"). Robin asked me to **re-read the
full paper and re-verify every merge in context** for side-effects/flow before applying. See Q11.

---

## Corpus rule changes made (PaperMaker9000, local, uncommitted at time of writing)
1. `kiss_simple_verbs`: falls/drops/stays now PASS; softens added to offenders; "centi- to millimeters".
2. `no_sentence_starting_with_acronym`: "Fig." exempted (always "Fig.").
3. `first_second_third_overuse`: **deleted**; `connectors.md` now endorses First/Second/Third/Finally as a loved pattern.

## Manuscript-edit queue (approved, to apply next)
Semicolons (3) · commas-after-intro (4) · while→whereas (3) · GPU caps · log-tick figures (2) ·
math-mode units (2) · equation \, · coinage \emph (2) · tilde ties (9) · axis-unit brackets [\,] ·
error-budget Wong palette · no_passive items {1,2,3,4,5,6,8,9,10,11,16,19} + 7(Robin's wording) +
15(gives the largest) + 18(careful) · subject_verb_early {2,4,7,9,10,11,12,14,15,16,17,18} + 6(e.g.) ·
action_in_verb (into→in) · consistent_topic 1 · first-time framing (varied) · topic_sentence flowchart opener ·
para6 roadmap · single-phantom sentence · flowchart de-anthropomorphize · drop "band stratification" ·
scan for drop-in First/Second/Third.

## Open questions for Robin (Q1–Q11): see chat.

---

## Round-2 resolutions (2026-05-22)

- **Q1 (in turn):** Robin's wording — "We examine three types of corrections: ..." (KISS, "we" is fine).
- **Q2 (Flintoft):** ✅ ok — "Flintoft's data show ⟨Qᵃ⟩ correlating negatively with mean subcutaneous fat thickness d_SF, steepest at 3 GHz."
- **Q3 (flowchart opener):** ✅ yes — standardize "As shown in the flowchart (Fig. X), this section …" (active, no we) for method-section frames.
- **Q4 (168 / phantoms):** 🔍 RESOLVED. 168 is an error — forensic traced to a 2026-05-04 session that bundled "168 across Flintoft, Zhang, Bamba", miscounting Bamba (FDTD-only, 0 volunteers, already in the 5 phantoms) as a ~60-subject cohort. **Correct = 108** (Flintoft 60 + Zhang 48). Phantoms = **5** (Thelonious, Billie, Ella, Duke [Bamba T7] + TARO [Diao]); Eartha absent. ACTION: change 168→108 in all 5 leaf locations (abstract, intro ×2, validation ×2); keep "5".
- **Q5 (mie total-error-splits):** ❌ "yeah, nah lets not do this".
- **Q6 (six element / limitations):** prose reminded; Robin reconsidering limitations ("few on the computational side"). Candidate computational limitations + a one-line future-work close offered in chat — pending Robin.
- **Q7 (grazing):** V-conditioned recompute — θ≥75° is **~50%** of *illuminated* area (not 63%; self-shadowing removes the grazing medial/under-surfaces), ~15% of absorbed power, abs error ≤ near-normal band. Updated candidate sentence in chat — pending Robin.
- **Q8 (colours):** 🔁 rule changed — pure saturated hues, order black/red/green/blue/orange; jet kept for scalar maps. (PaperMaker9000 commit 108dd18.)
- **Q9 (Configuration/Setup):** first stays **"Configuration"** (Wout pet peeve), second → **"Setup"**. Rule updated (108dd18).
- **FDTD spread:** include "~±15% at this frequency" (no CPW detail). Method's own diffraction error at 7 GHz = **~5%** (tab:si-diffraction; ran diffraction_integrated.py). So spread ≈ ~5% method ⊕ ~±15% FDTD. ACTION: add a sentence to that effect.
- **10 ms:** ✅ agreed, not an issue (upper bound, modern commercial GPU).

## PaperMaker9000 realignment (committed 108dd18, local)
no_passive_no_we reframed (passive is the enemy, "we" is fine, never lose flow/meaning) ·
scripting_colour_palette → pure hues black/red/green/blue/orange · colorblind_friendly →
jet OK for scalar maps · section_title_antipatterns → "Configuration" is Wout's ·
lens-reviewer.md + review skill → "context over local perfection" principle. Earlier
commit 17a3fa8: kiss falls/drops/stays OK + Fig. exempt + first/second/third loved.

## Round-3: grazing resolved + phantom count
- **Grazing geometry RESOLVED** (figure: grazing_angle_distribution.png). Thelonious mesh: z vertical (1.18 m), y anterior-posterior, x lateral. The paper's tab:phantom pointwise result uses a SINGLE **top-down** wave k=[0,0,−1] ("plane wave from above") — the most grazing-heavy direction for an upright body. Area-weighted θ≥75° fraction: top-down **50%**, frontal (−y) **19%**, convex-sphere reference **26%**. So Robin's intuition holds for frontal/typical illumination (~19%, a minority); the 50% is a top-down artifact. The headline pointwise check is therefore done at the worst-case incidence — a robustness point worth stating.
- **Phantoms: it is 5, not 6.** Bamba's Virtual Family four are Thelonious, **Billie**, Ella, Duke (NOT Eartha). Robin's AEGIS set is Thel/Eartha/Ella/Duke, so Billie↔Eartha is being mentally swapped. Paper uses Bamba's four + TARO (Diao) = 5; Eartha appears nowhere. To make it 6, add an Eartha validation run.

## Round-4: final polished new sentences (rule-checked, RIS dropped)
- **Future-work close (Discussion):** "Three applications follow. First, the millisecond cost makes real-time dosimetry possible, so exposure updates live as bodies and antennas move. Second, the differentiable form makes exposure a design constraint for beamforming and coherent MIMO. Third, the whole-body identity reduces a population study to one Fresnel quadrature, shared across bodies, and one occlusion pass per body."
- **Grazing — main text (brief, defers to SI):** "The validation excludes $\theta > 75^\circ$, where the surfaces carry little absorbed power, and \cref{si:grazing} gives the detail."
- **Grazing — SI paragraph (si:grazing):** top-down worst case (50% vs 19% frontal vs 26% sphere, sin θ weighting); grazing carries ~15% of power; absolute error ≤ near-normal band (max ~2% of peak); large relative errors are a vanishing-APD artifact; integrated total recovered to ~0.35%.

## Round-5: kill abstract-subject agency verbs; numbers not "little"
Robin: the polished sentences still had the quiet AI tell (abstraction + agency verb: "makes possible", "follow", "makes a constraint"). Rewrote to "X is Y". Also: grazing main must state the number (15%), not "little".
- **Future-work (final):** "Three applications are now practical. First, dosimetry is real-time: each evaluation is one matrix-vector multiply under $10$~ms, so exposure updates as bodies and antennas move. Second, exposure is a differentiable constraint in beamforming and coherent-MIMO design. Third, a population study reduces to one Fresnel quadrature shared across bodies and one occlusion pass per body."
- **Grazing main (final):** "Above $75^\circ$ the local error rises, but these surfaces carry only $15\%$ of the absorbed power (\cref{si:grazing})."
- **Grazing SI (final):** unchanged except "recovers" -> "matches the area-integrated total absorbed power to within about 0.35%".
- **Rule:** kiss_simple_verbs gains the abstract-subject + filler-agency-verb class (test step 4: check the SUBJECT). Commit 8a77603.
