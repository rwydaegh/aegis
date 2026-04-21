# IDF review notes

Review of `IDF_geometric_dosimetry.md` against AI-writing style rules, sentence complexity, substantiation, and structural coherence. Line numbers refer to the current markdown file.

## Writing style audit

### What's fine

- No em dashes, no "delve", "leverage", "seamlessly", "harness", "unlock", "empower", "comprehensive", "robust", "landscape", "ecosystem" (except the literal IT'IS/SPEAG ecosystem on L381, which is legitimate).
- No bold-header inline list items. No `**Header:** description` pattern.
- No rhetorical-question headings. Template questions are preserved as written.
- No "Great question!", no "Let me explain", no trailing "In conclusion". Good.
- No "in order to", "utilize", "at this point in time". Good.
- Keywords section (L277) is dense and useful, not bloat.

### Style violations

- **En dashes in `--` sequences.** `fill_all_in_one.py` line 104-107 converts ` -- ` to U+2013 when producing the docx. You hit this in L269-305 ("Address -- work", "INVENTOR 1 -- CONTACT PERSON", "Ghent University -- IMEC"), in Section 8 company lists (L399-407, e.g. "Apple (US) -- mmWave pre-compliance"), and in the contribution line (L306 "100% -- Sole inventor..."). Your own `docs-style.md` says no em or en dashes. Pick commas, parens, or periods. At minimum, turn off the en-dash substitution in the script.
- **Semicolons.** Two hits:
  - L188: "The password is changed periodically; contact the inventor for current credentials."
  - L194: "total-power results remain valid via T_bar; the local map limitation is inherent to the surface-confinement physics."
  - L200: "The stochastic channel mode provides an alternative without ray tracing." (no issue, just noting I checked)
  - L309: "...Prof. Wout Joseph, provided general academic guidance but did not contribute to the inventive concepts." (no issue)

  Both semicolons work as periods.

- **"Real-time" overuse.** Eight occurrences. L33, L43, L81, L87 (implicit), L89, L114, L184, L208, L361. Two or three would carry the meaning. Vary: "interactive", "sub-second", "while the user drags the antenna", "at network planning time".
- **"Production-quality" / "production software".** Four uses: L184, L204, L361, L395. Trim to one.

### AI-tell patterns (low severity but present)

- **Perfectly parallel three-item list.** L39-43 "No closed-form spatial dosimetry. / No exposure-aware beamforming. / No real-time compliance workflow." Three "No X" items, identical structure. The third is less punchy than the first two. Human writers usually vary one.
- **"The first X" claim stacking.** L83 "The first method to produce", L85 "The first exposure operator for". Back-to-back firstness claims. One is fine. Two signals sales copy.
- **Absolute-negative claims.** L87 "No existing dosimetry method is differentiable." L89 "No existing compliance tool offers this workflow." L91 "Nothing else connects laboratory dosimetry to operational network compliance." L147 "No existing dosimetry framework is differentiable in the near field." L156 "no prior closed-form exposure-aware precoder exists" (near-field). These are probably true but are unfalsifiable in an IDF without a full FTO search. Soften to "no prior published method" or "to the inventor's knowledge, no prior work".
- **"Most acute" / "fully preserved" / "explicit target".** L249 "The novelty is fully preserved.", L156 "is most acute", L383 "an explicit target". Mild salesmanship. Not fatal but a UGent TTO reviewer will notice.
- **Double statement for emphasis.** L147 "No existing dosimetry framework is differentiable in the near field. FDTD and FEM are not differentiable at all." Two sentences saying the same thing. Pick one.

## Sentence complexity

Generally academic, appropriate tone. A few spots are dense:

- **L128 (regime coverage paragraph) is ~110 words in a single paragraph.** Five ideas: far-field limit, near-field form, unchanged quantities, 63195-2 scope, reactive exclusion. Breaking this into 3 short paragraphs would read better. Most of it survives a split without rewording.
- **L147 (differentiability) has four claims in one sentence.** Splits cleanly in two.
- **L377 (Section 8 item 1) is one very long paragraph** with device OEM context, solid-angle + Gamma_lm description, gradient-based design, and the 6-300 GHz distance-range math. Split into 2-3 paragraphs (market context / computational primitives / scope).

Nothing is too simple. The tone is adequately academic without overreaching.

## Substantiation

### Well-substantiated claims (keep as is)

- Pseudo-Brewster 5.6% error bound (L120). Specific. Derivable from monograph.
- T_0 = 0.54 for skin at 28 GHz (L120). Specific.
- Mie regression R = 0.988 (L216). Specific.
- 2,469 tests (L184, L211, L395). Specific and verifiable.
- 14 government databases, ~293K antennas (L91). Specific.
- 91 3GPP presets (L95). Specific.
- Framework vs. published data error 3-8% (L219). Specific, cites five independent sources by name.
- 10^4 triangles vs. 10^12 cells (L104). Ratio is the basis of the speed claim, computable.

### Weak / unsubstantiated claims

- **"10^6 to 10^9 times faster" (L81).** Back-of-envelope comparison. Hours-to-milliseconds is 10^6, days-to-milliseconds is 10^8. The 10^9 is aspirational. Either keep the range with "approximately" or pin to one number with source.
- **"50-60K/year" Sim4Life license (L63).** Not public pricing. Probably carried over from an earlier session. Either cite where this came from (Robin's estimate, a quote received, a blog) or soften to "five-figure annual".
- **"10,000 geometric evaluations in an hour" (L381).** Inconsistent with the "milliseconds" claim elsewhere: milliseconds per eval gives 3.6M/hour. 10K/hour implies 360 ms each. Reconcile: either it's the full scene with ray tracing, or drop the number and say "thousands per hour".
- **"weeks per product generation" (L151).** Anecdotal. Likely true for Apple-class design cycles but no citation. Hedge: "a loop that typically costs weeks".
- **"seven-figure recertification costs" (L379).** No source. Drop or hedge. UGent reviewer may push back.
- **"millions of units" (L379).** True at Apple scale, fuzzy otherwise. Could replace with "per-product regulatory gate affecting the entire shipment volume".
- **"~10% error on total absorbed power for torso-sized bodies at mmWave" (L196).** Specific number, no cited source in IDF. Should reference the monograph table/section.
- **"1,200+ real antenna patterns" (L184) vs "1200+" (L212).** Minor inconsistency in punctuation. Both OK.
- **"framework error 2-6%" (L198) vs "within 3-8%" (L219).** Different numbers. One is the framework's intrinsic error, the other is match-to-published. Clarify the distinction or use the same range.

### Claims that don't need substantiation (patent prose)

- "Sole inventor" assertions in Section 3. Normal for patent disclosure.
- "Standards alignment" claims (L383). You're stating a target, not a fact.
- EPO G 1/19 paragraph (L114). Legal framing for technical effect. Appropriate.

## Content completeness

### Missing or under-developed

1. **Near-field validation evidence is absent.** The validation section (L215-219) lists only far-field validation (Mie, Bamba, Kodera, Diao, Flintoft). The IDF elevates near-field to parity in Section 1 but the status section does not state explicitly: "near-field point-source formulae have not yet been numerically validated against full-wave FDTD; validation is on the 2026 roadmap." The development-needed bullet (L223) implies it but the validation bullet (L215) should say it too.

2. **Disclosure-risk flag on JSAC timing.** L239 notes a planned May 1, 2026 submission. If the patent isn't filed before public disclosure, novelty is lost in most jurisdictions. The IDF should add a sentence: "Patent filing must precede journal acceptance / preprint posting." Currently L249 says confidential peer review does not count, which is correct, but does not address the preprint question or set a filing deadline.

3. **Freedom-to-operate.** L281 admits no FTO search yet. A one-line plan ("FTO search will be conducted by UGent-appointed patent counsel before filing") would close this hole.

4. **Ownership vs. CloudRF licensing.** L325 says CloudRF patterns are used under "standard commercial terms". If AEGIS is spun out as a commercial product, CloudRF's license terms control whether the patterns can redistribute with the product. Worth a sentence clarifying the license type (data license vs. software license).

5. **No patent filing timeline.** UGent TechTransfer will ask. Given the standards window (Section 8, L379) and the JSAC deadline, a target filing date would anchor the doc.

6. **No IEC 63195-1 (measurement) mention.** Section 8 item 2 talks about DASY integration but doesn't cite the measurement standard. Brief reference would help.

7. **No sub-inventor disclosure** about Carolina (noted in your memory as co-founder). If she has contributed to any inventive concept (even commercial formulation), she should be listed. If not, the sole-inventor note already covers it.

### Possibly redundant / overlapping

- **Advantages 1, 7, 8** (speed, frequency range, stochastic channel) all touch "the engine is fast across wide coverage". Merge.
- **Section 8 item 4** (base-station compliance) reads like a primary market despite L379's clear statement that base-station is the secondary channel. Trim item 4 or relabel it as "longer-term" to match the asymmetry paragraph.
- **Section 7 "purpose" paragraph** (L365) now combines purpose, deployment status, near-field software roadmap, and a standards alignment note. Split or shorten.
- **Advantage #10 "Conservative for compliance"** (L99) is really a limitation's silver lining. Fits better as a note in Section 1 disadvantages than as an advantage.
- **L184 (AEGIS software summary)** and **L208-213 (development status bullet list)** repeat ~80% of the same facts. Keep the bullet list (which is more readable) and trim L184 to one sentence.

### Possibly worth expanding

- **Gamma_lm as a product asset.** The precomputed body-response tables per body shape (SMPL-X coefficient grid) are non-trivial to regenerate and could be a licensed data product separate from the software. Worth one sentence in Section 8.
- **Standards committee leverage.** L383 mentions Wout Joseph in one sentence. That's a rare, non-transferable asset. A short paragraph on what his committee membership enables (proposing new annex text to 63195-2, nominating a mirror-committee member, etc.) would strengthen commercialization potential.
- **Prior-art patents** (L281). "No closely related patents were identified" is thin. A paragraph that lists what the search looked for (keywords, patent classes, key companies Qualcomm / Apple / Nokia / Ericsson / ZMT) would make it credible.

## Structural / high-level

- **Section 1 "Short description" exceeds the template's "max. one page".** In docx, the filled field now spans multiple pages. UGent TTO reviewers may flag this. Either shrink to one page (possible: merge essential elements / variables / extensions into a denser block) or negotiate the limit. The headline near-field content is worth keeping, so trim elsewhere (merge Insights 1 and 2 into one paragraph, compress the advantages-style language in the method description, drop redundancies with Section 7).
- **Section 9 is not part of the template.** L413 already notes this. Fine, but some UGent TTOs will strip non-template sections before forwarding. Keep a clean copy of Section 9 outside the form for the patent attorney.
- **Password in L188.** Fine for TTO eyes only, but the docx is likely to be emailed around. Consider flagging "Password rotated on 2026-04-01; do not redistribute this document without current credentials."

## Summary of recommended actions

- Drop en-dash substitution in `fill_all_in_one.py`, replace ` -- ` in markdown with commas or parens where possible.
- Remove two semicolons (L188, L194).
- Soften five absolute-negative claims ("no existing", "no prior", "nothing else") to "no published" / "to the inventor's knowledge".
- Reconcile 10,000/hour with milliseconds/eval (L381).
- Add one line to the validation section making the far-field-only scope explicit.
- Add one sentence on patent-filing timing vs. JSAC submission.
- Trim Section 1 to stay nearer the template's one-page cap.
- Merge advantages 1+7+8, demote #10 to a disadvantage silver-lining, tighten Section 8 item 4.
- Consider expanding: Gamma_lm as data asset, Wout's committee leverage, patent-landscape paragraph.

None of these are blockers for filing. They are the difference between a reviewer nodding and a reviewer asking follow-up questions.
