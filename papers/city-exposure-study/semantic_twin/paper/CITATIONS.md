# Citation verification

Every entry in the `thebibliography` block of `paper.tex` was checked against the
work itself, not against an index. Where a PDF exists in the gitignored `lit/`
directory the title page and the relevant table were read from the PDF. Where it
does not, metadata came from the Crossref REST API, from the ITU-R recommendation
pages, or from the publisher's own citation block.

24 entries. 6 corrected, 18 verified as written, 0 unverifiable in a way that
should worry a reviewer.

## Read this first

**No entry was found that fails to support the claim the text makes of it.** The
three claims flagged as least trusted were all checked against the source text
and all three hold to the printed digit. What was wrong was bibliographic, and it
was wrong in exactly the way the brief predicted.

Three entries carried an invented or transplanted title on top of otherwise
correct metadata. In each case the volume, issue, pages, year and DOI pointed at
the right paper and the title pointed at nothing, or at a different paper. A
reader following the DOI would have landed correctly. A reader searching the
title would have found either nothing or the wrong work.

| entry | title as written | title of the work the metadata identifies |
|---|---|---|
| `adhikari` | "Over-the-top propagation in urban millimetre wave networks" | "Around-Corner and Over-Top 28 GHz Measurement in Manhattan: Path Loss and AoA for MU-MIMO" |
| `duchizhik` | "Suburban and urban ducting and around-the-corner propagation at 28 GHz" | "Directional Measurements in Urban Street Canyons From Macro Rooftop Sites at 28 GHz for 90% Outdoor Coverage" |
| `vitucci` | "Ray tracing RF field prediction: an unforgiving validation" | "Tuning Ray Tracing for Mm-wave Coverage Prediction in Outdoor Urban Scenarios" |

The `vitucci` case is the nastiest of the three, because the title that was
written is real. "Ray Tracing RF Field Prediction: An Unforgiving Validation" is
Vitucci, Degli-Esposti, Fuschini, Lu, Barbiroli, Wu, Zoli, Zhu and Bertoni,
*Int. J. Antennas Propag.*, vol. 2015, art. no. 184608, doi
`10.1155/2015/184608`. It is a different paper by an overlapping author group,
four years earlier, in a different journal, and it does not contain the
scattering ablation the text cites. Someone spot-checking the title alone would
have found a plausible paper and stopped.

## Claim checks on the three priority entries

`adhikari` supports its claim. The text says a rooftop site about 20 m above
surrounding buildings, serving receivers in Manhattan street canyons, showed
over-the-top propagation beating street-level scattering by 7 dB in fit error.
Table V of the paper is captioned "Path loss modeling for the UMa scenario.
Over-Top-NLOS appears to be the dominant propagation mechanism, with a 7 dB
improvement compared to Street-Clutter-NLOS", and its average column reads 4.3 dB
for Over-Top-NLOS against 11.1 dB for Street-Clutter-NLOS. The 20 m figure is the
paper's own description of sites JLG1 and JLG2, "rooftop location, 20 m higher
than nearby buildings". The colleague's DOI and table pointer were both right.

Note for anyone reading the abstract instead of Table V: the abstract quotes 6.4
against 11.9 dB. Those are the UMi numbers, for base stations *below* clutter,
and they are a different comparison. The paper's rooftop argument needs Table V,
which is what the text uses.

> **Old illumination law, see `../docs/LAW_CHANGE.md`.** The sentence this entry supports
> divides the two deployment classes by height above the roofline, which is the old
> rooftop band. The citation itself survives and is correctly verified, but the claim
> built on it has to be rewritten, because the new law puts sources on facade tips and has
> no mast above a roofline.

`duchizhik` supports its claim. Table 2 of the paper gives a fitted corner loss
of 2.2 dB for the diffraction model against 0 dB for the scattering model, and
the body reads "This may also be compared to the theoretical edge diffraction
coefficient, which at large diffraction angles (deep shadow) is on the order of
-42 dB at 28 GHz". The text's "about 2 dB against a theoretical edge coefficient
near 40 dB down" is accurate. The prior half of the sentence also holds: the
diffraction-inspired model fits at 3.4 dB RMS error against 6.6 dB for the
scattering model with the same fixed intercept, so it does fit better.

`vitucci` supports its claim. Table 2, scattering included, gives RMSE 6.2, 8.9,
10.4 and 12.4 dB at 28 GHz and 9.1, 11.0, 12.1 and 13.2 dB at 38 GHz. Table 3,
scattering excluded, gives 29.5, 30.1, 25.2 and 26.0 dB at 28 GHz and 32.2, 33.1,
37.0 and 28.5 dB at 38 GHz. The text's "6 to 13 dB up to 25 to 37 dB at 28 and
38 GHz" is exactly the span of those two tables.

## One thing to check with the author

`sam` cites Kirillov et al., "Segment Anything", ICCV 2023. That entry is
correct in itself. But the study appears to have run SAM 3, not SAM 1:
`infer_sam3_body.py`, `sam3_concepts.py` and the `_fishnet_sam3` output sets are
what produce the material masks, and `PAYLOAD.md` describes the concept masks as
"SAM 3". The surfaces and materials subsection cites `sam` for "a promptable
segmentation model is then asked for the material within those facade regions",
which is the model that actually ran.

Citing the 2023 paper for the promptable-segmentation *idea* is defensible.
Citing it for the model that produced the results is not, if that model was SAM
3. This was left alone rather than guessed at, because inventing a SAM 3 citation
is exactly the failure this pass exists to catch. Decide whether the entry should
stay as a concept citation, gain a second entry for SAM 3, or be replaced.

## Entry by entry

Status is against the entry as it stood before this pass. "Corrected" means the
fix is already applied in `paper.tex`.

| key | status | DOI | note |
|---|---|---|---|
| `icnirp` | verified | `10.1097/HP.0000000000001210` | *Health Phys.* 118(5):483-524, 2020. Authors, venue, volume, issue, pages and year all correct. |
| `leeman` | corrected | `10.1109/ACCESS.2025.3541352` | Venue, volume, pages and year were right. Three of six author initials were wrong. Read from the PDF title page: Matthias Leeman, Robin Wydaeghe, Jeroen Van der Straeten, Samuel Goegebeur, Günter Vermeeren, Wout Joseph. Was "S. Leeman, R. Wydaeghe, S. van der Straeten, Y. Goegebeur". |
| `wydaeghe2026` | verified | `10.1038/s44459-026-00031-4` | *npj Wireless Technol.* 2(1), art. no. 13, 2026. Title, all six authors and the article number match. |
| `sionna` | verified | `10.1109/GCWkshps58843.2023.10465179` | 2023 IEEE Globecom Workshops, pp. 317-321. All seven authors match. |
| `wiame` | verified | `10.1109/TVT.2023.3307226` | *IEEE Trans. Veh. Technol.* 73(1):894-908, 2024. Note the DOI carries a 2023 stem because of early access. The issue is January 2024, so the year is right. |
| `varsier` | verified | `10.1002/bem.21928` | *Bioelectromagnetics* 36(6):451-463, 2015. All eight authors match in order. |
| `veludo` | verified | `10.1016/j.envint.2025.109540` | *Environ. Int.* vol. 200, art. no. 109540, 2025. First author is Adriana Fernandes Veludo, so "A. F. Veludo" is right. |
| `mmsv` | verified | `10.1145/3570361.3613291` | MobiCom '23, pp. 1-16. Kamari, Chae, Pathak. A copy sits with the other downloaded papers as `lit/3570361.3613291.pdf`. |
| `veach` | verified | none | Read from `lit/veach_1997_thesis.pdf`. Stanford PhD dissertation, December 1997, title exact. Copyright page reads 1998, which is normal for a December filing and does not change the citation year. |
| `tregenza` | verified | `10.1177/096032718301500201` | *Lighting Res. Technol.* 15(2):65-71, 1983. |
| `sloan` | verified | `10.1145/566570.566612` | SIGGRAPH 2002 proceedings, pp. 527-536. The same paper also has a *ACM Trans. Graph.* 21(3) record at `10.1145/566654.566612` with identical pagination, so either form is citable and the proceedings form as written is correct. |
| `itu2040` | corrected | none | Number was right, title and year were not. The study uses P.2040-4, which `config/itu_p2040_4.json` and `METHOD.tex` (now `../archive/METHOD.tex`) both name explicitly. P.2040-4 is 09/2025 and is titled "Effects of building materials and structures on radio-wave propagation in the range of 1 MHz to 450 GHz". The entry carried the P.2040-3 title and the P.2040-3 year. Both fixed. Verified against the in-force PDF downloaded from `itu.int`. |
| `sam` | verified | `10.1109/ICCV51070.2023.00371` | ICCV 2023, Kirillov et al. See the flag above about SAM 3. On pagination: the entry's 4015-4026 is the CVF open-access proceedings range and is the range the paper's own BibTeX gives, while IEEE Xplore paginates it 3992-4003. The entry names the IEEE/CVF proceedings, so 4015-4026 is defensible and was left alone. |
| `ericsson` | verified | none | Read from `lit/3GPP_R1-160846_...pdf`. Cover reads "3GPP TSG-RAN WG1 #84, St Julian's, Malta, February 15-19, 2016", document R1-160846, source Ericsson, "Street Microcell Channel Measurements at 2.44, 14.8 & 58.68 GHz". The claim it supports is in the document: excess loss frequency dependence of "3.5 Log(f) for RX1" and "3.0 Log(f) for RX2", with the tdoc's own conclusion that "Reflected/scattered paths dominates over diffraction in NLOS". |
| `mmmagic` | verified | none | Read from `lit/mmMAGIC_D2.2_...pdf`. Document number H2020-ICT-671650-mmMAGIC/D2.2, delivered 12/05/2017. The deliverable title is "Measurement Results and Final mmMAGIC Channel Models" as written. Its internal document title differs, "Measurement Results and Final Channel Models for Preferred Suitable Frequency Ranges", which is a quirk of the cover page and not an error in the entry. The claim it supports is present: at the delay of the around-corner diffraction path "no signal above the noise" was found, and the strongest peak matched "four specular reflections off exterior walls". |
| `adhikari` | corrected | `10.1109/INFOCOM55648.2025.11044468` | Title was invented. Real title, all nine authors and pp. 1-10 now in place. Venue and year were right. Claim verified against Table V, see above. |
| `p526` | corrected | none | P.526-16 is dated 11/2025, not 2024. Confirmed against both `lit/ITU-R_P.526-16_2025-11_...pdf` and the ITU-R P.526 revision list. Number and title were right. |
| `duchizhik` | corrected | `10.1109/TAP.2020.3044398` | Title was invented. Volume 69, issue 6, pages 3459-3469 and year 2021 were all correct, as was the author prefix Du, Chizhik, Valenzuela. Real title now in place. Claim verified against Table 2, see above. |
| `vitucci` | corrected | `10.1029/2019RS006869` | Title belonged to a different paper, see above. Volume, issue, pages and year were correct. Third author also fixed from F. Fuschini to F. Mani, per the publisher's own citation block on page 1: "Vitucci, E. M., Degli-Esposti, V., Mani, F., Fuschini, F., Barbiroli, M., Gan, M., et al." Fuschini is the fourth author and is now covered by the *et al.* Claim verified against Tables 2 and 3, see above. |
| `karttunen` | verified | `10.1109/TWC.2019.2928810` | *IEEE Trans. Wireless Commun.* 18(10):4768-4778, 2019. All four authors match. The published title hyphenates as "5-80-GHz", which is a house-style difference and not worth changing. |
| `beckmann` | verified | none | Beckmann and Spizzichino, *The Scattering of Electromagnetic Waves from Rough Surfaces*, Pergamon Press, Oxford, 1963. Pre-DOI, no Crossref record, and no copy in `lit/`, so this rests on the standard catalogue record rather than on a title page I read. It is one of the most heavily cited books in the field and the entry matches the canonical form. A 1987 Artech House reprint also exists if a more obtainable edition is wanted. |
| `arvokirk` | verified | `10.1145/97879.97886` | SIGGRAPH '90 proceedings, pp. 63-66, Arvo and Kirk. The companion *ACM SIGGRAPH Comput. Graph.* 24(4) record at `10.1145/97880.97886` has the same pagination, so the proceedings form as written is correct. |
| `aegis` | unverified | none | Self-citation to the author's own software. `CITATION.cff` in the AEGIS repository carries an explicit placeholder, `10.00000/zenodo.placeholder`, so there is no DOI to add. Nothing to check externally and nothing to fix. If a Zenodo DOI is minted before submission it belongs here, and a version number would help. |
| `itis` | verified | `10.13099/VIP21000-04-2` | IT'IS Foundation tissue properties database version 4.2, released 04/06/2024. Version and year as written are right. One thing to decide: version 5.0 has since been released. Citing 4.2 is correct if 4.2 is what the runs used, which is the assumption made here. |

## Method

Crossref REST was queried by DOI where a DOI was supplied and by bibliographic
string where it was not, and the returned title, author list, container, volume,
issue, page range and year were compared field by field. For every entry with a
copy in `lit/` the title page was read from the PDF rather than taken from the
filename, since the filenames in that directory are descriptive rather than
authoritative. The three priority claims were checked by locating the specific
table or sentence in the source and comparing the printed values against the
text, not by reading the abstract. The two ITU recommendations were checked
against the in-force PDFs, one local and one downloaded during this pass. The
IT'IS version and date came from the DOI resolving to its own download page.

`paper.tex` rebuilds with zero undefined citations and zero undefined references
at 19 pages.
