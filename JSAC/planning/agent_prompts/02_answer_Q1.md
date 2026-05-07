# Q1 — Brussels arrêté: primary-source findings

The Brussels-Capital EMF regime is two-layered: a parliamentary *ordonnance*
(1 March 2007, as amended 3 April 2014 and 2 March 2023) sets the immission
limits; implementing *arrêtés* of the Brussels-Capital Government (30 October
2009 and 8 October 2009, as amended 1 July 2021) set measurement method,
per-operator quotas, and simulation parameters.

## 1. Numerical limit and frequency scaling

Ordonnance du 1 mars 2007, art. 3, § 1er/1 (as replaced by art. 3 of the
Ordonnance du 2 mars 2023, MB 8 March 2023, NUMAC 2023041147; in force
1 May 2023):

> « Dans toutes les zones accessibles au public à l'intérieur et à
> l'extérieur, les densités de puissance du rayonnement des radiations non
> ionisantes ne peuvent dépasser, à aucun moment, les valeurs suivantes
> dans les zones accessibles au public à l'intérieur (S_int, correspondant
> aux locaux d'un bâtiment dans lesquels des personnes peuvent ou pourront
> séjourner régulièrement) et dans les zones accessibles au public à
> l'extérieur (S_ext) […]. À titre indicatif, à 900 MHz, la norme S_int =
> 0,2243 W/m² correspond à un champ électrique E_int = 9,19 V/m ; tandis
> que la norme S_ext = 0,5635 W/m² correspond à un champ électrique
> E_ext = 14,57 V/m. »

Gloss: "In all publicly accessible zones inside and outside, the power
density of non-ionising radiation may never, at any moment, exceed the
following values: S_int indoors and S_ext outdoors […]. For reference, at
900 MHz, S_int = 0.2243 W/m² corresponds to E_int = 9.19 V/m; S_ext =
0.5635 W/m² corresponds to E_ext = 14.57 V/m."

The 2007 original used a `f/40 000` scaling in the 400 MHz–2 GHz band (see
the 2007 text at faolex.fao.org/docs/pdf/bel70379.pdf, art. 3 al. 3); the
2014 amendment used `f/9375` (ord. du 3 avril 2014, art. 3). The 2023
amendment removes the single-scalar form and replaces it with an explicit
table for three bands (0.1–400 MHz, 400 MHz–2 GHz, 2–300 GHz) for both
S_int and S_ext (ord. du 2 mars 2023, art. 3; parliamentary file A-654/1,
2022/2023, p. 13).

## 2. Averaging window

The statutory limit is phrased **instantaneously**: the ordonnance says
`« ne peut dépasser, à aucun moment »` — "cannot exceed, at any moment"
(ord. du 1 mars 2007, art. 3, § 1er/1, quoted above; identical wording
already appeared in the 2014 text, see ord. du 3 avril 2014, art. 3).
There is no "6 min" or "30 min" averaging clause in the ordonnance itself.

The implementing measurement *arrêté* (arrêté du GRBC du 8 octobre 2009
fixant la méthode et les conditions de mesure du champ électromagnétique
émis par certaines antennes, MB 20 October 2009, modified by the arrêté du
1er juillet 2021) prescribes a per-protocol measurement duration of
**2 minutes**. The official Bruxelles Environnement expert-committee report
(2023, p. 4–5) summarises the arrêté: « l'"arrêté fixant la méthode et les
conditions de mesure du champ électromagnétique émis par certaines
antennes" impose de mesurer 2 minutes par protocole utilisé » ("imposes a
measurement of 2 minutes per protocol used"). The committee proposed
replacing this with a 6-minute full-bandwidth measurement — a proposal, not
current law (environnement.brussels/media/15974, §1.1.1).

I was not able to obtain the verbatim French article of the 8 October 2009
arrêté that fixes this 2-minute window; `etaamb.openjustice.be` and
`refli.be` return the 30 October 2009 arrêté (a sister instrument) under
similar titles, and the direct Moniteur belge page (NUMAC 2009031525, MB
20 Oct 2009) is behind a session wall.

> NEEDS_CONTEXT: verbatim article of the arrêté du 8 octobre 2009 (MB
> 20 Oct 2009, as modified by the arrêté du 1er juillet 2021) fixing the
> 2-minute measurement window. Robin may need to download the Moniteur
> belge PDF directly (ejustice.just.fgov.be).

Bruxelles Environnement's continuous sensor network uses **6-minute
averaging at 4 m above ground** (environnement.brussels, page
"Comment les normes d'exposition aux ondes sont-elles contrôlées?":
« Les capteurs réalisent 12 mesures par jour du champ électrique,
moyennées sur 6 minutes à 4 m du sol ») — but this is the monitoring
protocol, not the statutory averaging.

## 3. Measurement-point definition

Ordonnance du 1 mars 2007, art. 2, § 1er, 2° (as modified 3 April 2014),
defines « zones accessibles au public » as:

> « – les locaux d'un bâtiment dans lesquels des personnes peuvent ou
> pourront séjourner régulièrement, en particulier les locaux
> d'habitation, hôtels, écoles, crèches, hôpitaux, homes, bureaux […]
> les lieux situés à l'extérieur ou apparentés accessibles au public, en
> particulier les jardins, intérieurs d'îlots, zones de parcs, les cours
> de récréation et les balcons, les terrasses couvertes ou non de
> bâtiments, les boxes garages, les cabanes, les jardins d'hiver, les
> serres et autres vérandas similaires. »

Gloss: rooms where persons may stay regularly (dwellings, hotels, schools,
nurseries, hospitals, homes, offices), plus gardens, courtyards, parks,
playgrounds, balconies, terraces, garages, sheds, conservatories.

I did **not** find an explicit "1.5 m above floor" or "head-height" clause
in the Brussels ordonnance. Such a clause exists in the Walloon decree
(art. 3, §2, e) of the décret wallon du 3 avril 2009, quoted in
Cour constitutionnelle, arrêt n° 110/2024, p. 13: « 1° dans les locaux,
1,5 mètre au-dessus du niveau du plancher; 2° dans les autres espaces,
1,5 mètre au-dessus du niveau du sol »), but this is Walloon, not Brussels,
law.

> NEEDS_CONTEXT: verify whether the Brussels arrêté du 8 octobre 2009 (or
> its 2021 amendment) fixes a measurement height. Robin may need the
> Moniteur belge PDF.

## 4. Cumulative clause (multiple operators)

Pre-2023: arrêté du GRBC du 30 octobre 2009 relatif à certaines antennes
émettrices d'ondes électromagnétiques, art. 5, § 1er (as replaced by the
arrêté du 5 septembre 2013, art. 1):

> « Sans préjudice de l'article 7, le champ électrique émis par les
> antennes classées exploitées par un même opérateur ne peut pas
> dépasser 25 % de la norme en vigueur. Le champ électrique sera calculé
> par opérateur et non tous opérateurs confondus. »

Gloss: each operator's classified antennas may not exceed 25 % of the
applicable norm, computed per operator (not summed across operators). In
field units this was 1.5 V/m per operator under the 3 V/m norm (2009–2014)
and 3.45 V/m under the 6 V/m norm (2014–2023) (parliamentary file A-654/1,
2022/2023, p. 4).

Post-2023, Bruxelles Environnement publishes the following per-operator
quotas against the current 9.19 V/m indoor norm (source:
environnement.brussels, page "Quelles sont les normes légales d'exposition
aux ondes électromagnétiques?"): Proximus 29.5 % (4.99 V/m), Orange Belgium
26.5 % (4.73 V/m), Telenet Group 25 % (4.60 V/m), Citymesh Mobile 19 %
(4.01 V/m). Sum-of-squares < 100 % of the S-norm is the compliance rule.

> NEEDS_CONTEXT: verbatim text of the implementing arrêté that sets these
> post-2023 per-operator percentages (the arrêté "de classement" following
> the 2023 ordonnance, identified in the 2023 expert-committee report as
> published in 2023). Robin may need the Moniteur belge PDF.

## 5. Frequency scope

Ordonnance du 1 mars 2007, art. 2 (original): « les rayonnements
électromagnétiques dont la fréquence est comprise entre 0,1 MHz et
300 GHz ». 5G mmWave above 20 GHz is in fact banned outright: art. 3, § 3
(as inserted by the ordonnance du 2 mars 2023): « Les antennes émettrices
stationnaires des réseaux mobiles publics générant un rayonnement
électromagnétique dans la gamme des fréquences comprise entre 20 GHz et
300 GHz ne sont pas autorisées » (quoted in Cour constitutionnelle, arrêt
n° 110/2024 of 24 October 2024, p. 13 — note: that ruling quotes the
parallel *Walloon* provision, which is textually identical; the Brussels
prohibition is discussed in HV-A's commentary on the 21 November 2024
Brussels ruling).

## 6. Indoor cap: 9.19 V/m

Same clause as Q1 above: art. 3, § 1er/1 of the ordonnance du 1 mars 2007
(as replaced 2 March 2023) gives E_int = 9.19 V/m at 900 MHz (S_int =
0.2243 W/m²), with the same "à aucun moment" phrasing.

## 7. ICNIRP 2020 / BR references

The ordonnance does **not** reference ICNIRP 2020 in the operative
articles. It references Recommendation 1999/519/CE only in the exemption
regime: art. 3, § 1er/4 caps the emergency derogation at the 1999/519/CE
values (i.e., ICNIRP 1998 reference levels), not at BR-based compliance.
The exposé des motifs (A-654/1, 2022/2023, p. 12) cites ICNIRP 2020 only as
background. No BR (basic-restriction, SAR-based) compliance path is
provided; the Brussels regime is a pure reference-level regime.

## Summary table

| Item | Brussels value / clause |
| --- | --- |
| Outdoor limit (900 MHz) | 14.57 V/m (S_ext = 0.5635 W/m²) — ord. 1 mars 2007 art. 3 §1/1 (2023) |
| Indoor limit (900 MHz)  | 9.19 V/m (S_int = 0.2243 W/m²) — same article |
| Averaging in statute    | "à aucun moment" (instantaneous) |
| Averaging in practice   | 2 min per protocol (arrêté 8 oct 2009); 6 min on sensor network |
| Measurement points      | "zones accessibles au public" inside/outside per art. 2 §1 2° |
| Height rule in Brussels text | Not found (Walloon decree has 1.5 m; Brussels arrêté not accessed) |
| Cumulation rule         | Per-operator quotas; 4 operators total 100 % (29.5+26.5+25+19) |
| Frequency scope         | 0.1 MHz–300 GHz; 20–300 GHz mobile-network antennas forbidden |
| ICNIRP 2020 / BR        | Not referenced; BR-path not provided; 1999/519/CE caps emergency exception only |

## Sources consulted

- faolex.fao.org/docs/pdf/bel70379.pdf (Ordonnance 1 mars 2007, original)
- faolex.fao.org/docs/pdf/bel134303.pdf (Ordonnance 3 avril 2014)
- refli.be/fr/lex/2007031104 (consolidated ordonnance, up to April 2023)
- etaamb.openjustice.be/fr/ordonnance-du-01-mars-2007_n2007031104.html
- etaamb.openjustice.be/fr/arrete-du-gouvernement-de-la-region-de-bruxellescapit_n2009031544.html (arrêté 30 oct 2009)
- etaamb.openjustice.be/fr/arrete-du-gouvernement-de-la-region-de-bruxellescapit_n2012031047.html (arrêté 12 janv 2012)
- etaamb.openjustice.be/fr/arrete-du-gouvernement-de-la-region-de-bruxellescapit_n2013031754.html (arrêté 5 sept 2013)
- weblex.brussels/data/crb/doc/2022-23/146676/images.pdf (parl. file A-654/1)
- environnement.brussels/citoyen/reglementation-et-inspection/textes-de-loi/quelles-sont-les-normes-legales-dexposition-aux-ondes-electromagnetiques
- environnement.brussels/citoyen/reglementation-et-inspection/prevention-et-inspection/comment-les-normes-dexposition-aux-ondes-sont-elles-controlees
- environnement.brussels/media/15974/download (Rapport comité d'experts 2023)
- wallex.wallonie.be/files/pdfs/23/DCCO_Cour_constitutionnelle_-_Arrêt_n°_110-2024.pdf (Cour const. 110/2024; binary-encoded, used for context only)
- hv-a.be (law-firm commentary on Cour const. ruling of 21 Nov 2024 — used only as pointer, not as primary source)
- shs.cairn.info/revue-courrier-hebdomadaire-du-crisp-2016-21 (Crisp 2016 review, pointer only)
- Not accessed directly: Moniteur belge PDF of the arrêté du 8 octobre 2009 (NUMAC 2009031525, MB 20 Oct 2009), and the 2023 "arrêté de classement" that replaces the 25 % quota with the current per-operator quotas.
