# Aandachtspunten bij de IOF-overzet

## Afbakening van dit bestand

Het officiële StarTT-sjabloon verwacht een volledige projectbeschrijving. De valorisatiesectie bestaat uit drie afzonderlijke delen:

1. intellectuele-eigendomsstrategie, maximaal één pagina;
2. contractuele afspraken, maximaal een halve pagina;
3. valorisatiestrategie, maximaal twee pagina's.

Het opgeleverde Word-bestand vult alleen de derde rubriek. Het is dus een invoegbaar onderdeel van een IOF-aanvraag, geen volledige projectbeschrijving.

## Inhoud die formeel elders hoort

De onderbouwing van marktvolume, doelgroepen, technologie-impact en concurrentie hoort volgens het sjabloon grotendeels onder `Opportuniteit`. Een korte versie blijft nodig in de valorisatiestrategie omdat omzet en markttoegang anders geen zichtbare noemer hebben. In een volledige aanvraag kan dit deel worden ingekort en met een verwijzing naar de opportuniteitssectie worden vervangen.

Technische validatie, solvernauwkeurigheid en werkpakketten horen onder `Projectplan`. In de valorisatiestrategie blijven alleen de commerciële mijlpalen en de te meten klantwaarde staan.

## Verschillen tussen de twee bronbestanden

De oudere tekst `AEGIS_dosimetrie_valorisatie.tex` bevat twee problemen die niet letterlijk zijn overgenomen:

- FCC-ID A3LSMS921U is de Samsung Galaxy S24, niet de S25.
- Het scenario met 20 enterprisecontracten en 25 labolicenties overschrijdt vrijwel de aantoonbare populatie van terugkerende kopers en laboratoriummerken.

De nieuwe Word-versie gebruikt daarom de gecorrigeerde S24-case en de omzetlogica uit `AEGIS_valorisatie_kader.tex`: EUR 0,7 tot 1,2 miljoen directe omzet, EUR 2 tot 3 miljoen met distributie, en meer dan EUR 5 miljoen alleen als breakoutscenario.

## Nog onbewezen commerciële aannames

De omzetniveaus zijn bottom-up scenario's, maar nog geen forecast. De volgende schakels ontbreken:

- betaalde pilots;
- schriftelijke klantinteresse;
- prijsvalidatie bij de werkelijke budgeteigenaar;
- gemeten besparing in engineeringuren, solverruns en kalenderweken;
- een realistische salescyclus en acquisitiekost;
- brutomarge en personeelsbehoefte per leveringsmodel;
- bevestiging dat een solver- of platformleverancier wil distribueren.

De prijs van EUR 150.000 tot EUR 250.000 per enterprisecontract is een value-based hypothese. Bestaande solver- en labuitgaven tonen budgetcapaciteit, maar bewijzen niet dat AEGIS dat bedrag kan innen.

## Beperkingen van de marktdata

De FCC-data is een sterke prospectie- en workloadbron, maar geen volledige wereldwijde TAM:

- één filing is geen klant en niet ieder dossier vereist complexe dosimetrie;
- meerdere filings kunnen tot hetzelfde toestelprogramma of dezelfde organisatie behoren;
- de telling van 18 high-cadence organisaties is een bovengrens voor terugkerende prospects;
- de 16 labmerken komen uit een pilot van 163 filings, niet uit een officiële wereldwijde census;
- labmerk en labsite zijn niet hetzelfde;
- de Samsung S24 is een bruikbaar workloadvoorbeeld, maar blijft één toestelprogramma;
- de 378 vermogenslimieten staan niet gelijk aan 378 afzonderlijke HFSS-berekeningen.

Vier tot zes directe enterprisecontracten is daardoor commercieel betekenisvol marktaandeel. Het document presenteert dit bewust niet als een vanzelfsprekende uitkomst.

## Product- en kanaalrisico

Het sterkste omzetpad boven EUR 1 miljoen steunt op distributie. Dat creëert afhankelijkheid van ZMT, Ansys, een ander platform of een geconcentreerde groep testlaboratoria. Zonder embedded partner blijft AEGIS waarschijnlijk een kleinere specialistische activiteit met meer dienstverlening per klant.

GOLIAT is technisch waardevol, maar voor commerciële inzet moeten nog enkele zaken worden uitgeklaard:

- exploitatierechten op UGent-, EU-project- en eigen bijdragen;
- verenigbaarheid van de Apache-2.0-codebasis met het gekozen verdienmodel;
- afhankelijkheid van een commerciële Sim4Life-licentie;
- onderhoud, validatie en aansprakelijkheid van een gekwalificeerde workflow;
- scheiding tussen pre-compliance advies door een labo en zijn onafhankelijke certificatierol.

## Standaarden en aansprakelijkheid

AEGIS hoeft niet onmiddellijk als zelfstandige certificatiemethode in een standaard te staan. Finale conformiteit kan met FDTD, FEM of meting worden aangetoond. Dat verwijdert het zwaarste standaardisatierisico, maar niet alle frictie. OEM's en laboratoria kunnen nog steeds formele validatie, conservatieve guard bands, versiebeheer en duidelijke aansprakelijkheid eisen voordat zij AEGIS in een beslissende ontwerpworkflow opnemen.

## Exploitatievorm

Spin-off, licentie, embedded distributie en strategische overdracht vragen verschillende teams en kostenstructuren. De huidige tekst houdt deze routes bewust open. Een definitieve IOF-aanvraag moet wel vastleggen:

- wie na het project eigenaar en trekker van de commerciële activiteit wordt;
- welke route als basisscenario geldt;
- welk beslismoment een spin-off activeert of uitsluit;
- hoe GOLIAT, AEGIS en eventuele achtergrond-IP contractueel samen worden aangeboden.

## Vormvereisten

De rubriek `Valorisatiestrategie` heeft een limiet van twee pagina's in UGent Panno 10,5 pt. Het Word-bestand gebruikt de stijlen en bladinstellingen uit het aangeleverde StarTT-sjabloon. De uiteindelijke paginering kan licht verschuiven wanneer UGent Panno niet op de computer beschikbaar is. De bronnenlijst kan in een volledige aanvraag naar een algemene referentielijst worden verplaatst als de sectie te lang wordt.
