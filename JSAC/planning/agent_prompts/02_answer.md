# Answer — Brussels arrêté text + BR-based audit in practice

Research prompt: [02_brussels_arrete_and_BR_audit_practice.md](02_brussels_arrete_and_BR_audit_practice.md).
Full sections with primary-source quotes:

- **Q1 (Brussels arrêté):** [02_answer_Q1.md](02_answer_Q1.md)
- **Q2 (BR-based audit):** [02_answer_Q2.md](02_answer_Q2.md)

## Material finding — the paper's §I hook needs reframing

The prior draft treats the **14.57 V/m cap** as the mmWave blocker. That is only half the story. The Ordonnance du 1 mars 2007, art. 3 §3 (as inserted by the Ordonnance du 2 mars 2023, MB 8 March 2023) states:

> « Les antennes émettrices stationnaires des réseaux mobiles publics générant un rayonnement électromagnétique dans la gamme des fréquences comprise entre 20 GHz et 300 GHz ne sont pas autorisées. »

Brussels prohibits **20–300 GHz mobile-network transmitting antennas outright**. For mmWave, the binding constraint is a statutory ban, not a tight reference-level cap. The 14.57 V/m / 9.19 V/m caps apply below 20 GHz only.

## Corrections to earlier claims

| Earlier (wrong) | Actual |
| --- | --- |
| "Enforced instantaneously every second" | Statute says `« à aucun moment »` (instantaneous in law); arrêté du 8 oct 2009 fixes **2 min per protocol**; continuous sensors use **6 min** at 4 m above ground |
| "14.57 V/m summed across all operators" | **Per-operator field quotas** (Proximus 29.5 %, Orange 26.5 %, Telenet 25 %, Citymesh 19 %), sum-of-squares ≤ 100 % of the S-norm; not summed across sources |
| "14.57 V/m blocks 5G mmWave" | **Outright ban** on 20–300 GHz mobile antennas; 14.57 V/m binds sub-20 GHz bands only |
| "References ICNIRP 2020" | Operative articles do not reference ICNIRP 2020 or any BR pathway; Rec. 1999/519/CE cited only to cap the emergency-derogation regime |

## Recommendation paragraph

**For §I (deployment hook):** reframe Brussels as the extreme-case jurisdiction with a two-pronged blocker — a statutory ban on 20–300 GHz mobile antennas (Ordonnance 1 March 2007 art. 3 §3, inserted 2 March 2023) *and* a tight sub-20-GHz reference-level regime (14.57 V/m outdoor / 9.19 V/m indoor at 900 MHz, scaling across three bands in the 2023 amendment, phrased instantaneously in the statute but enforced via 2-min-per-protocol measurement under the arrêté du 8 octobre 2009 and 6-min continuous-sensor monitoring, with per-operator field quotas totalling 100 %). The paper should not claim the 14.57 V/m cap blocks mmWave — the statute does that directly. The paper should claim the 14.57 V/m regime blocks sub-20-GHz deployment density, and that the body-centric twin is exactly the technical artefact a regulator would need to entertain raising the 20-GHz ban (i.e., to accept BR-based evidence that the ban is over-conservative). **For §VII (BR framing):** cite IEC/IEEE 62232:2022 Clause 1(e), Annex B.7.4 "Full wave SAR computation", and Annex E.9 "Establishing compliance boundaries using numerical simulations of MIMO" — plus the normative reference to the IEC/IEEE 62704 FDTD/FEM body-SAR family and the stated ICNIRP-2020 compatibility — to position the twin as an *instance* of an existing standards-permitted numerical BR pathway, not a new standards invention; but explicitly acknowledge that no regulator (FCC, BIPT, Brussels Environment, Ofcom, Japan MIC) has accepted a BR-audit dossier for any deployed base station, and that the nearest legal precedent is 47 CFR §1.1310(d)(2), which makes MPE and whole-body SAR legally alternative for US base stations from 300 kHz to 6 GHz but has always been used in MPE mode in practice, so the twin should be framed as a *proposed* audit protocol that fits an existing standards slot rather than a *proven* regulatory practice.

## Open gaps (NEEDS_CONTEXT)

Three primary-source items Robin may need to pull directly from Moniteur belge (ejustice.just.fgov.be) and one from IEC:

1. Verbatim French of the arrêté du 8 octobre 2009 (NUMAC 2009031525, MB 20 Oct 2009, as modified by the arrêté du 1er juillet 2021) fixing the 2-min measurement window.
2. Whether the Brussels arrêté fixes a measurement height (Walloon decree fixes 1.5 m above floor/ground; Brussels text not directly accessed).
3. Verbatim text of the 2023 implementing "arrêté de classement" that sets the per-operator quotas.
4. Verbatim sentence-level text of IEC/IEEE 62232:2022 Annex B.7.4 and Annex E.9 (paywalled; clause titles and TOC confirmed from VDE-Verlag and iTeh previews, but the inside-clause language is not in the preview).
