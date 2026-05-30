# TODO: verify and fix hallucinated references in the IDF

*Created 2026-05-24. Scope: the "Prior art: publications by others most closely related to the invention" list in `IDF_geometric_dosimetry.md` (the 9 numbered references). Each entry was checked twice: once manually by Robin, once independently by Claude via web search. The two passes agree. This file records the verdicts, the correct citations, and the fixes needed.*

**Headline: 5 of the 9 references are wrong or fabricated.** The error pattern (real authors, real topic, plausible-looking but jumbled or invented titles / journals / volumes) is the signature of LLM-generated citations. Do not let any of these reach UGent TechTransfer, a patent examiner, or the JSAC paper before fixing. A fabricated citation in a patent disclosure is a credibility landmine.

---

## Summary verdict

| # | IDF citation (as written) | Verdict | Fix |
|---|---|---|---|
| 1 | Y. Kodera, T. Hikage, T. Nagaoka, "Whole-body average SAR estimation using surface area and a transmission coefficient at frequencies above 6 GHz," Phys. Med. Biol., vol. 69, 2024 | **Not verifiable as written** | Find the exact Kodera paper; concept is real |
| 2 | K. Li, K. Sasaki, S. Watanabe, "Relationship between power density and temperature elevation in human tissue," IEEE Access, vol. 7, 2019 | **Wrong** (journal + title + missing author) | Replace |
| 3 | A. Bamba et al., "Experimental assessment of specific absorption rate using room electromagnetics," IEEE Trans. EMC, vol. 54, no. 4, 2012 | **Correct** | Keep |
| 4 | A. Bamba et al., "Assessing whole-body absorption cross section for diffuse exposure from reverberation chamber measurements," IEEE Trans. EMC, vol. 57, no. 1, 2015 | **Correct** (confirm issue/pages) | Keep, verify pages |
| 5 | R. M. A. Azzam, "High-index dielectric substrates with nearly constant reflectance," J. Mod. Opt., vol. 62, no. 18, 2015 | **Real but truncated; relevance questionable** | Fix title, reconsider inclusion |
| 6 | Z. Ying, D. J. Love, B. M. Hochwald, "Closed-form capacity-SAR tradeoff for MIMO beamforming," IEEE Trans. Wireless Commun., vol. 14, no. 1, 2015 | **Wrong** (title + issue) | Replace |
| 7 | M. R. Castellanos et al., "Closed-form Fresnel-based approach for 5G mmWave human body exposure assessment," IEEE Access, vol. 8, 2020 | **Fabricated** (no such paper) | Replace with real Castellanos paper(s) |
| 8 | I. D. Flintoft et al., "Average absorption cross-section of the human body measured at 1-12 GHz in a reverberant environment," IEEE Trans. AP, vol. 62, no. 5, 2014 | **Wrong** (journal + vol/issue + title) | Replace |
| 9 | S. Shikhantsov et al., "Hybrid ray-tracing/FDTD method ... industrial indoor environment," IEEE Access, vol. 7, pp. 21020-21031, 2019 | **Correct** | Keep |

---

## Per-reference detail

### #1 Kodera (not verifiable as written) - needs care, do not just delete

The cited title/authors/journal ("Y. Kodera, T. Hikage, T. Nagaoka ... Phys. Med. Biol. vol. 69, 2024") could not be found. The closest real 2024 paper is:

> S. Kodera, K. Taguchi, Y. Diao, T. Kashiwa, A. Hirata, "Computation of whole-body average SAR in realistic human models from 1 to 100 GHz," IEEE Trans. Microwave Theory Tech., vol. 72, no. 1, pp. 91-100, Jan. 2024.

Note the first-author initial: it is **S. Kodera (Sachiko Kodera)**, not "Y. Kodera." But the IDF body text (Section 1, the empirical-transmission-coefficient paragraph) attributes a specific result to Kodera: `SAR_wb = T_tr x A_perp x S_inc / W`, reproducing 3D FDTD within 5% from 10-100 GHz, with `T_tr` from a 1D slab model. That is a real, specific Kodera contribution, so the citation is pointing at something real, it is just mis-titled or pointing at the wrong Kodera paper. **Action: locate the exact paper that states the surface-area x transmission-coefficient whole-body SAR result and cite that.** It may be the TMTT paper above or a different one. Do not drop the reference, fix it, because the IDF's whole novelty argument leans on distinguishing AEGIS from Kodera.

### #2 Li (wrong journal and title) - replace with

> K. Li, K. Sasaki, S. Watanabe, H. Shirai, "Relationship between power density and surface temperature elevation for human skin exposure to electromagnetic waves with oblique incidence angle from 6 GHz to 1 THz," Phys. Med. Biol., vol. 64, no. 6, 065016, 2019. DOI: 10.1088/1361-6560/ab057a.

The IDF has the wrong journal (Phys. Med. Biol., not IEEE Access), a truncated/altered title, and drops co-author Shirai.

### #3 Bamba 2012 (correct) - keep

> A. Bamba et al., "Experimental Assessment of Specific Absorption Rate Using Room Electromagnetics," IEEE Trans. Electromagn. Compat., vol. 54, no. 4, pp. 747-757, 2012. (IEEE Xplore doc 6174464.)

Verified exact.

### #4 Bamba 2015 (correct, confirm pages) - keep

Title, journal, vol. 57, year 2015 are consistent. Confirm the issue number and page range against IEEE Xplore before final submission (not independently re-pulled here).

### #5 Azzam (real but truncated; relevance questionable) - decide

The paper exists. Full title:

> R. M. A. Azzam, "High-index dielectric substrates with nearly constant reflectance for incident unpolarized or circularly polarized light over a wide range of incidence angles," J. Mod. Opt., vol. 62, 2015.

The IDF truncates the title. Confirm the issue number (cited "no. 18"). More importantly: this is an **optics paper about reflectance vs. incidence angle**, not a dosimetry paper. It belongs (if anywhere) as a physics underpinning for the pseudo-Brewster / near-constant-transmission argument, not in a list of "prior art on body exposure by others." Either move it to the physics-background discussion or drop it from the prior-art list.

### #6 Ying/Love/Hochwald (wrong title and issue) - replace with

> Z. Ying, D. J. Love, B. M. Hochwald, "Closed-Loop Precoding and Capacity Analysis for Multiple-Antenna Wireless Systems With User Radiation Exposure Constraints," IEEE Trans. Wireless Commun., vol. 14, no. 10, pp. 5859-5870, Oct. 2015. (IEEE Xplore doc 7121029.)

The IDF title ("Closed-form capacity-SAR tradeoff for MIMO beamforming") does not match, and the issue is 10, not 1.

### #7 Castellanos (FABRICATED) - replace with the real paper(s)

No paper titled "Closed-form Fresnel-based approach for 5G mmWave human body exposure assessment" exists in IEEE Access vol. 8, 2020. Castellanos has two real, relevant exposure papers, both with Love and Hochwald:

> M. R. Castellanos, Y. Liu, D. J. Love, B. Peleato, J.-M. Jin, B. M. Hochwald, "Signal-Level Models of Pointwise Electromagnetic Exposure for Millimeter Wave Communication," IEEE Trans. Antennas Propag., vol. 68, no. 5, 2020. (IEEE Xplore doc 8871335.)

> M. R. Castellanos, D. J. Love, et al., "Hybrid precoding for millimeter wave systems with a constraint on user electromagnetic radiation exposure," 2016 50th Asilomar Conference on Signals, Systems and Computers, pp. 296-300, 2016.

Both are **precoder-design-under-exposure-constraint** work, so they are prior art for the exposure-operator / ECBF claim (Claim 2/2a), not for the surface dosimetry. The 2016 Asilomar paper is the one the US11940477 (Hochwald) patent examiner cited. Pick the one you actually meant and place it under the precoder prior art.

### #8 Flintoft (wrong journal and vol/issue) - replace with

> I. D. Flintoft, S. L. Robinson, G. C. R. Melia, A. C. Marvin, J. F. Dawson, "Average absorption cross-section of the human body measured at 1-12 GHz in a reverberant chamber: results of a human volunteer study," Phys. Med. Biol., vol. 59, no. 13, pp. 3297-3317, 2014. (PubMed 24874464; ADS 2014PMB....59.3297F.)

The IDF has the wrong journal (Phys. Med. Biol., not IEEE Trans. AP), wrong vol/issue, and a truncated title.

### #9 Shikhantsov (correct) - keep

> S. Shikhantsov, A. Thielens, G. Vermeeren, E. Tanghe, P. Demeester, L. Martens, G. Torfs, W. Joseph, "Hybrid Ray-Tracing/FDTD Method for Human Exposure Evaluation of a Massive MIMO Technology in an Industrial Indoor Environment," IEEE Access, vol. 7, pp. 21020-21031, 2019. (IEEE Xplore doc 8636510.)

Verified exact.

---

## This is bigger than these 9 references

The same generator produced the rest of the IDF and very likely the monograph and the JSAC paper. The contamination is almost certainly not confined to this one list. Before any of these documents go out:

1. **IDF in-text citations.** Section 1 names Kodera 2024, Li 2019, Diao 2024, Bamba 2012/2015 in prose. Diao 2024 ("T ~ 0.52 at 28 GHz from anatomical FDTD") has not been verified at all yet. Check it.
2. **The inventor's own 3 papers** (the "publications by the inventors" list). Robin should know these cold, but verify the details anyway, especially "npj Wireless Technology, vol. 2, no. 13, 2026" (very new journal, easy to mis-cite) and the two IEEE Access papers (2022, 2025).
3. **The monograph bibliography** (`../monograph/monograph_v2.tex`). If it reuses any of these references, the same errors propagate into the paper that underpins the patent. Cross-check.
4. **The JSAC paper bibliography.** Same risk, and this is the document with a hard public-disclosure deadline, so an examiner could pull it.

## Action checklist

- [ ] Fix references #2, #6, #7, #8 in the IDF with the correct citations above.
- [ ] Locate and fix reference #1 (find the exact Kodera surface-area x transmission-coefficient paper).
- [ ] Fix reference #5 title; decide whether to keep it in the prior-art list or move it to physics background.
- [ ] Confirm #4 issue/pages against IEEE Xplore.
- [ ] Verify Diao 2024 (cited in Section 1 prose, never checked).
- [ ] Verify the inventor's own 3 publications.
- [ ] Cross-check the monograph and JSAC paper bibliographies for the same hallucinated entries.
- [ ] Add a note to the IDF FTO/prior-art section that all references were independently verified on 2026-05-24 (once the above is done).
