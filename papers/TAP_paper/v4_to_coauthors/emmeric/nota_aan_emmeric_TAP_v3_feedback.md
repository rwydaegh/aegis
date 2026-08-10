# Verwerking feedback op de TAP-paper v3

Dag Emmeric,

Merci nog voor de feedback op de TAP-paper. Hieronder staat per opmerking wat
ik heb aangepast en wat ik bewust heb behouden. De wijzigingen zelf zijn ook
zichtbaar in de latexdiff.

Bij twee gemarkeerde tussentitels stond geen commentaar. Daarover staat hieronder
nog één korte vraag.

| Opmerking | Verwerking |
|---|---|
| `geometry scalar` | Aangepast naar `geometry-dependent scalar`, zoals je voorstelde. |
| `polarization-aware` of `polarization-inclusive` | Ik heb `polarization-aware` behouden. De berekening houdt expliciet rekening met de lokale TE- en TM-fracties. `Polarization-inclusive` zou ook kunnen betekenen dat verschillende polarisaties alleen in de validatieset zijn opgenomen. |
| Ongeveer 20% verschil tussen FDTD-implementaties vermelden in het abstract | Niet toegevoegd aan het abstract. Ik vond geen rechtstreekse primaire bron die dit getal als algemeen verschil tussen implementaties onderbouwt. De vergelijking met de onzekerheid op de gemeten weefseleigenschappen is hier beter afgebakend. De spreiding tussen FDTD-richtingen blijft wel in de validatiesectie staan. |
| `exposure on the human body` | Aangepast naar `exposure of the human body`. |
| `validated four independent ways` | Goed gezien. `in` is toegevoegd. |
| Zin over de twee scalars | Korter gemaakt: `Whole-body absorbed power reduces to a flux-weighted transmission scalar and a single ambient-occlusion scalar.` |
| Zin over de matrixvermenigvuldiging en rekentijd | De grammatica is aangepast en de timing blijft staan: `For a body mesh under many incident paths, the absorbed-power map is a single matrix-vector multiplication, evaluated in under 10 ms.` |
| Sectie- en vergelijkingsnummers in het stroomdiagram | Ik heb dit geprobeerd, maar het diagram werd te druk. De caption koppelt de stappen al aan de relevante afleidingen, dus ik heb de eenvoudigere versie behouden. |
| `polarization-independent value` | Verduidelijkt dat dit alleen bij normale inval geldt: `At normal incidence, $\mu=1$ and $\xi=\tilde n$, giving the polarization-independent normal-incidence value...` |
| `circular illumination` en `linear illumination` | Aangepast naar `circularly polarized illumination` en `linearly polarized illumination`. De volledige zin is nu: `The polarization correction vanishes pointwise for circularly polarized illumination, in expectation for randomly oriented linearly polarized illumination, and to within 2.5% under multipath averaging with at least 20 paths.` |
| Figuur 3 uitbreiden en Tabel I inkorten | Figuur 3 loopt nu door tot $90^\circ$ en Tabel I is verwijderd. De kern staat nu kort in de tekst: `$T_{\mathrm{avg}}/T_0$ is at most 1.056 across $[0^\circ,90^\circ]$ on skin at 28 GHz. Below $20^\circ$, the deviation stays below 0.2%.` |
| Gemarkeerde tussentitels zonder commentaar | Je markeerde `Method: pseudo-Brewster compensation` en `Generalized Cauchy formula`, maar ik zag daar geen commentaar bij. Bedoelde je nog een aanpassing aan een van die titels? |
| Resultaten als theorem formuleren | Mee eens dat dit wat zwaar was. Ik heb beide theorem-omgevingen verwijderd en de resultaten rechtstreeks in de gewone tekst gezet. Ook de proof-titels en QED-vakjes zijn weg. De zin over de 10 g-kubus sluit nu meteen aan op de inleidende zin. |
| Intuïtie achter de integraal over $S^2$ | Hier heb ik de tekst niet uitgebreid. $S^2$ is de bol van alle invalrichtingen, niet het lichaamsoppervlak. Als je de lokale normaal als poolas kiest, wordt dit gewoon de cosinusintegraal over één hemisfeer, met waarde $\pi$. |
| Referentie van Wydaeghe et al. | Aangepast naar `accepted for publication, 2026`, met DOI `10.1088/1361-6560/ae97ac`. |

Merci nog!

Met vriendelijke groetjes,

Robin
