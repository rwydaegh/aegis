# Agent I — Discussion + Conclusion style pass

Scope: `\section{Discussion}` through end of `\section{Conclusion}` in
`/home/user/aegis/JSAC2/paper/jsac2_v3.tex` (currently lines 1291–1399).

## Summary of changes

Five paragraphs rewritten end-to-end. No spine changes; no figures, tables, equations, or numerical claims altered.

### §IX-A Bandwidth and per-slot compute
- Anthropomorphism cleanup: components now "take" wall-clock time rather than "run at" milliseconds (a render does not "run at 100 ms").
- Hyphenation fix: "ridge-least-squares fit" → "ridge least-squares fit" (compound is "least-squares", "ridge" is the modifier).
- "top-six sensitivity-ranked joints" → "top six sensitivity-ranked joints" (compound was wrong).
- Last sentence reorganized to make the $\sim\!24$ bits explicit in prose, not just in the table.
- Added thin-space tilde inside `T_{\mathrm{vis}} \sim\!10^{4}` for consistency with the rest of the paper.

### §IX-B Privacy delta vs. a model-only baseline
- Killed the awkward "The reading's per-tick" possessive (per-A22 internal-codebase-naming hygiene; "the reading" was being treated as a load-bearing noun).
- "for cohort use, opt-in" rewritten as "and only on opt-in for cohort use" (avoids comma-tag construction).
- Tightened math spacing: `$\gammab \in \Complex^{K}$ for $K \leq M$` → `$\gammab\in\Complex^{K}$ for $K\leq M$`.

### §IX-C Limitations
- Killed opener "Three limitations of the present work are explicit." (meta-talk, A12 territory; reader can count).
- "is a parallel research thread not treated here" → "is not treated here" (puffery removed).
- Removed semicolon in "FR2; fingertip features" → split into two sentences.
- Removed semicolon and parenthetical in "regime; the supplementary information" → "regime does not exhibit. The supplementary information…" (parenthetical inverted to relative clause).
- Reads plainly per Robin's rule that limitations should be factual not dramatic.

### §IX-D Future work
- Was a single 6-line sentence with three nested parentheticals and an em-dash-style aside.
- Rewritten as three short subject-verb-rest sentences, each item rooted in the corresponding limitation (per `structural_things_quality.md` item 48).
- Killed "flagged as a future paper" (unnecessary self-referential aside).
- Killed "where… where… where…" parenthetical pattern.

### §X Conclusion
The previous version was ~24 lines of one-paragraph dump with three semicolons and was a near-paraphrase of the abstract.

Restructured into three beats per `structural_things_quality.md` item 32:
1. **What was shown** (past tense, "We presented…"): on-device twin, Kirchhoff–PO machinery, K-mode SVD calibration, UE-anchored render in $\mathcal{O}(M\,T_{\mathrm{vis}})$, on-device loop at 1–10 Hz.
2. **What it means** (implications): cascaded-SINR gain large enough to convert NLOS outage to service; peak-local APD two orders below ICNIRP; body twin returns the per-individual exposure series the regulatory framework specifies but does not currently measure.
3. **What's next** (real open problems, rooted in §IX-C limitations): multi-user, vehicular twins, AR/XR rate targets.

- Killed "the wireless-native intelligent agent the special-issue scope calls for" (twice — appeared in both opener and closer; sales pitch + brittle reference to the journal CFP).
- Killed "regulatory framing was originally designed to inform" (vague, anthropomorphism-adjacent).
- Killed "central new computational primitive" → "A UE-anchored Kirchhoff render evaluates…" (no "new" per the agent brief; no "this paper" framing).
- Past tense for the contribution recap, present tense for the implications.
- Removed all semicolons in scope.
- Numerical claims that previously appeared in the conclusion ("0.2 to 10.5 dB", "25%", "29%", "7%", "six torso joints out of 22", "0.58%") are dropped from the conclusion as recommended by item 33 (no new numbers in the conclusion). The two qualitative bullets that remain ("large enough to convert outage to service", "two orders of magnitude below the ICNIRP reference") are anchored in §VI–VIII results which carry the precise figures.

## Verification

### Conclusion three-beat check
- Beat 1 (what was shown, past tense): YES — paragraph 1.
- Beat 2 (what it means): YES — paragraph 2.
- Beat 3 (what's next): YES — paragraph 3.
- Length: ~30 lines = roughly one half-column. Within the half-column-to-one-column band of item 31.
- No new equations, no new figures, no new headline numerical claims (item 33).
- Not a paraphrase of the abstract: the abstract recaps the system, the precoder/SVD machinery, and the headline scene-level numbers; the conclusion now anchors a separate "implications + open problems" arc.

### Limitations factual not dramatic check
- No "Despite … challenges" template (A13).
- No drumroll opener; the three "First / Second / Third" markers carry the structure.
- Each item is one technical statement plus a pointer to where the full treatment lives.

### Style fix counts (within scope)
- Em dashes removed: 0 found (none present).
- Semicolons removed: 5 (1 in Limitations, 1 in Future work, 3 in Conclusion).
- "this paper" / "we now" / "as we have shown" / "in summary": 0 in scope after edit.
- Anthropomorphism rewrites: 2 (component "runs at" → "takes"; "the reading's" possessive killed).
- "central new" / "novel" / "significant" / "groundbreaking" puffery killed: 1 ("central new computational primitive" → "A UE-anchored Kirchhoff render evaluates…").
- Long parentheticals collapsed to plain sentences: 4 (3 in Future work, 1 in Limitations).
- Sentences rewritten for subject-verb-rest core in first 7–9 words: ~8.
- Subsection headings checked for "The"-prefix: clean (none had it).
- Non-breaking tilde audit: `\Cref{tab:cadence}` already had it; `5G NR` → `5G~NR`; `sub-6~GHz` already had it; `Fabry--P\'erot` is a name, no tilde needed.

### Compile check
`pdflatex jsac2_v3.tex` succeeds — 14 pages, no errors originating in scope. The single overfull hbox in the log is in the bibliography (line 1641, Agent J's territory), not in §IX or §X.

## Cross-section flags

1. **Numerical mismatch between abstract and prior conclusion.** The conclusion-as-was claimed "30 Munich scenes" and "0.2 to 10.5 dB" while the abstract says "18 Sionna RT Munich scenes (9 LOS, 9 NLOS)" and "0.6 to 8.6 dB". I dropped the body-section numbers from the new conclusion entirely (per item 33: no new numbers in the conclusion), so the conflict no longer surfaces in §X. **However the underlying mismatch between the abstract and the results sections (§VI–§VIII) is unresolved and not in my scope.** Whoever owns the abstract (Agent A) and whoever owns the results sections need to reconcile: is it 18 scenes or 30 scenes? Is the SINR range 0.6–8.6 dB or 0.2–10.5 dB? The TS 38.214 / MCS27 commit history and v3-to-v5 evolution suggest the 30-scene / 0.2–10.5 dB number is the current one; if so, the abstract still needs to be updated.
2. **§IX-A "5G NR downlink control-channel budget"** — I left this without a citation. If a TS-38.212/38.213 control-channel-budget reference exists in the bibliography (Agent J), an `~\cite{...}` here would be appropriate. Currently only `general5G` and `TS38214` are referenced for 5G in the intro; neither is a control-channel reference.

## Open issues

- The table caption "Refresh cadences and per-update wall-clock for the on-device twin loop" still uses "for the on-device" — minor, kept because rephrasing the caption felt like overreach for a style pass and the caption is grammatical.
- The compute table cells still use `K \log_2(M)` with spaces; harmonized to `K\log_2(M)` in the prose. Not changing the table because table-cell math conventions differ from inline-math prose conventions and this is borderline-spine.
- "Privacy delta" subsection title: kept verbatim per the agent brief ("'Privacy delta vs. a model-only baseline' — fine"). If a future pass wants something cleaner, "Privacy envelope" or "Telemetry on the body side" would also fit.
