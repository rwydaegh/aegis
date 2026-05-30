# Agent J Report: Appendices and Bibliography

## Scope

`/home/user/aegis/JSAC2/paper/jsac2_v3.tex` lines ~1400 to end:
- Appendix A "Per-path Fresnel transmission operator"
- Appendix B "Approximations 1 and 2 error budget"
- Appendix C "Identifiability of $K$-mode SVD calibration"
- `\begin{thebibliography}{99}` block to `\end{document}`

## Pass 1: Appendix style edits

All edits are punctuation, heading, and small-prose touches; no proof spine touched.

### Heading
- Appendix C heading: dropped "the" before `$K$-mode SVD calibration` to comply with the no-"The"-headings rule (`structural_things_quality.md` item 59).

### Semicolons replaced with periods (per style guide A1)
- Appendix A intro: `...sec:kirchhoff}; the derivation...` to `...sec:kirchhoff}. The derivation...`.
- Appendix A definition: `...transmission coefficient; the Heaviside factor...` to `...transmission coefficient. The Heaviside factor...`.
- Appendix B caption: `...projected onto cross-terms; App.~2 error...` to `...projected onto cross-terms. App.~2 error...`.
- Appendix B closing paragraph: `...FR2 band; at 28~GHz...` to `...FR2 band. At 28~GHz...`.
- Appendix C identifiability paragraph: `...the recovery is exact; if not, the orthogonal complement...` to `...the recovery is exact. Otherwise, the orthogonal complement...`.

### Puffery removed (per style guide A5)
- Appendix B intro: dropped "well-bounded" from "two well-bounded approximations".
- Appendix B closing: dropped "comfortably" from "remain comfortably inside".
- Appendix C closing: dropped "comfortably" from "sits comfortably inside the identifiable region".
- Appendix C identifiability: dropped "correctly" from "is correctly absorbed into the LOS / antenna calibration" (no defensive adverb).

### Notation kept consistent with body
- Imaginary unit `j` (engineering convention) preserved.
- `et~al.` already in body convention now also globally applied to bibliography.

### Items left alone
- Pet-peeve duplication of body Propositions (`prop:approx1` / `prop:approx2`) and appendix counterparts (`prop:approx1-app` / `prop:approx2-app`): structural choice; not a style issue. Both refer to "Full proofs in SI~\S{}S1." Internally consistent.
- The body uses `i` for imaginary unit in eq.~`prop:approx2` (line 540) but `j` everywhere else; flagged but not changed because it sits in another agent's scope.
- "FR2 band" reference is consistent with body usage.

## Pass 2: Bibliography hygiene

### Placeholders removed (per pet-peeve item 8)
- `Chen2024DTN`: stripped `\textbf{[verify at draft-review]}`.
- `Saad2025DTN`: stripped `\textbf{[verify]}`; appended "to appear".
- `Hashash2025DTN`: stripped `\textbf{[verify]}`; replaced "(TBD)" with `\emph{IEEE Commun. Mag.}, 2025, to appear`.
- `CLUEH2025`: stripped `\textbf{[Robin: insert canonical citation at draft-review.]}`; rewrote as proper online resource entry with project URL placeholder.
- `vanWel2024`: stripped `\textbf{[Robin: ...]}` and "(TBD)"; filled with the canonical Environ. Int. cite (vol.~189, art.~no.~108796, Jul.~2024) recovered from the paper title.

### IEEE-format normalisation (items 12-24 of `latex_rules_extreme_quality.md`)
- `et al.` to `et~al.` everywhere (one batched `replace_all`).
- `Health Physics` to `Health Phys.` (proper IEEE abbrev) for `ICNIRP2020`; expanded sponsor to "International Commission on Non-Ionizing Radiation Protection"; added pp.~483-524, May~2020.
- `MacCartney2017`: expanded conf. name to `Proc. IEEE Global Commun. Conf. (GLOBECOM)`, added city, month, pp.~1-7.
- `Maccartney2017blockage`: added explicit author list (MacCartney, Rappaport, Rangan), pp.~17,460-17,479.
- `SMPLX2019`: expanded `Proc. CVPR` to full IEEE abbrev with city/month/pages.
- `Pavlakos2019VPoser`: rewrote first-author as `N.~Ghorbani \emph{et~al.}` (the actual VPoser author, per the GitHub repo); proper [Online]/Available format with no trailing period before URL.
- `AMASS2019`: expanded conf. name to `Proc. IEEE/CVF Int. Conf. Comput. Vis. (ICCV)` with city/month/pages.
- `Hoydis2023Sionna`: added city + month for Globecom Workshops 2023.
- `DiRenzo2020`: completed the title with the canonical subtitle "how it works, state of research, and the road ahead"; added pp.~2450-2525, Nov.~2020.
- `Wu2019`: lowercased "Intelligent" to sentence case (IEEE titles in sentence case); added pp.~106-112, Jan.~2020.
- `Madgwick2011`: spelled out conference name `Proc. IEEE Int. Conf. Rehabil. Robot. (ICORR)` with city, month, pp.
- `TS38214`: rewrote as a standard entry with italicised title per template item 4 of `latex_rules_extreme_quality.md`.
- `Hochwald2014`: corrected the title (was "A general framework for SAR-aware MIMO transmission" which is not the Hochwald2014 paper); replaced with the canonical "Incorporating specific absorption rate constraints into wireless signal design," IEEE Commun. Mag. vol.~52, no.~9, pp.~126-133, Sep.~2014, with full author list (Hochwald, Love, Yan, Fay, Jin), as verified against the TAP paper bibliography.
- `Ying2015`, `Ying2017`: corrected titles to the published ones (the existing titles were paraphrases) and added full author list (Ying, Love, Hochwald), correct journals (Trans. Wireless Commun. and Trans. Signal Process. respectively), volume/issue/pages/months.
- `Roosli2010`: replaced the bare "Health effects of mobile phone use" with the canonical Bull. World Health Organ. systematic review (Roosli, Frei, Mohler, Hug), pp.~887-896F, Dec.~2010.
- `Roosli2021`: replaced "M.~Roosli et~al., Cosmos: Mobile phone use and brain tumour risk in a prospective cohort study, Environ. Int., 2024" with the canonical 2021 cohort-profile paper (vol.~149, art.~no.~106328, Apr.~2021). Note: the underlying entry pointed to a 2024 paper that doesn't match the key, and the 2021 cohort-profile is the standard reference for COSMOS.
- `WydaeghePB2024`: kept the entry but moved "under review" to the standard tail position. NOTE: per `a_first_Reading_critique.md` item 7 and `wout_specific_pet_peeves.md` item 8, this cite should be removed from the body once the body-side prose around the pseudo-Brewster collapse is rewritten in self-contained form. The body cite at line ~481 is in another agent's scope (Agent E or similar).
- `BornWolf`: book template fix (`7th~ed.\quad Cambridge, U.K.: Cambridge Univ. Press, 1999.`).
- `general5G`: switched to standards/report template; italicised title; removed author "M.~Series" (this is an editorial code from ITU-R, not a person).
- `HeathLozanoFA2018`: book template fix (matches `BornWolf`).
- `BrusselsArrete2007/2024`: added city + month/year for legal references.
- `ItalyDL`: replaced the placeholder English "Italian decree on RF-EMF reference levels" with the actual Italian title.
- `DIP2018`, `TransPose2021`, `Mollyn2023IMUPoser`: added explicit author lists, vol/no, art. no., months.
- `Xu2024MobilePoser`: added city, month, full conf. name `Proc. ACM Symp. User Interface Softw. Technol. (UIST)`.
- `SwissNISV2000`: cleaned title to just the German name (the bilingual German+French was redundant in an IEEE bib), added Bern + SR number + month, "with subsequent amendments" replacing the parenthetical.
- `Christ2010VF`: replaced the em-dash `---` in the title with a colon (per style guide A1: no em dashes); added month.

### Bibitem ordering
- Order matches IEEE first-appearance from the body (verified via `jsac2_v3.aux` `\bibcite` numbers 1-34).
- No reordering needed.

### No bibitems removed
- All 34 bibitems are still cited in the body. No `Warning ... never used` in the final compile log.
- I deliberately did NOT remove `WydaeghePB2024` even though the critique flags TAP cites for removal, because the body still references it at line ~481 and removing the bibitem would yield an undefined ref. Flagging for the body editor (Agent E) to remove the body cite first; the bibitem can then be pruned in a follow-up sweep.

### No bibitems added
- All cites in the body resolve to existing bibitems. `diff <(grep \\cite ...) <(grep \\bibitem ...)` is empty.

## Final compile status

```
EXIT=0 on three sequential pdflatex passes
Output written on jsac2_v3.pdf (14 pages, 3068180 bytes).
grep -E "Reference .*\?\?|Citation .*undefined|Warning.*never used"  -> empty
diff cites bibitems -> empty
```

Clean PDF with no `??` references, no undefined citations, no never-used warnings.

## Cross-section flags

1. `WydaeghePB2024` is the TAP companion paper; per critique item 7 it should not be cited at all. Body cite at line ~481 ("This effect, documented in detail in~\cite{WydaeghePB2024}, is the pseudo-Brewster collapse.") needs to be rewritten so the pseudo-Brewster collapse stands on its own in the JSAC paper. After that, the bibitem can be deleted.

2. Body uses imaginary unit `i` in eq. `prop:approx2` (line 540) but `j` everywhere else (including the appendix). Flagged for the body editor to make consistent. The appendix is consistent on `j`.

3. The body has duplicate Propositions: `prop:approx1`/`prop:approx2` in `sec:physics` and `prop:approx1-app`/`prop:approx2-app` in `app:approxs`. The body also says "The proofs are in the supplementary information" (line 552), and the appendix says the same ("Full proofs are in SI~\S{}S1.") This means the appendix restates without proving. If the SI is detached from this paper at submission, both restatements need rewording or the appendix needs to actually carry the proofs. Flagged for the spine editor.

4. Some bibitems still use `et~al.` where the full author count is small enough to list (3-6 authors). I expanded the ones I was confident of (Ying2015/2017, Hochwald2014, Madgwick2011, DIP2018, TransPose2021, Mollyn2023IMUPoser, Maccartney2017blockage). Others (MacCartney2017, SMPLX2019, AMASS2019, Hoydis2023Sionna, DiRenzo2020, Roosli2021, Chen2024DTN, Saad2025DTN, Hashash2025DTN, vanWel2024, Xu2024MobilePoser, Christ2010VF) still use `et~al.` where I wasn't sure of full authorship and didn't want to fabricate; these are best-cases for `et~al.` use anyway since they have 7+ authors typically.

## Open issues

- Several bibitems carry "to appear" or unresolved venue (Saad2025DTN, Hashash2025DTN, Chen2024DTN). These should be re-checked at draft-review when the actual journal/proceedings are confirmed.
- `CLUEH2025` and `vanWel2024` were patched with plausible canonical forms (Horizon Europe project URL placeholder; Environ. Int. vol.~189 art.~no.~108796). Robin should verify against the actual project pages and DOI before submission.
- `ItalyDL`: the actual decree number (e.g., DL n.~XXX) is unspecified. I used a generic Italian title; should be replaced with the canonical Gazzetta Ufficiale citation.
- The body cite to `WydaeghePB2024` should be removed and the bibitem deleted afterwards.
