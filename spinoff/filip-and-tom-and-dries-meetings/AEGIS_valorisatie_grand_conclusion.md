# AEGIS-dosimetrie: de grand conclusion

## Kort besluit

De huidige omzettabel mag niet worden verdedigd. De aantallen lijken voorzichtig, maar verbergen in sommige rijen een bijna volledige marktpenetratie. Vooral twintig enterprisecontracten en vijfentwintig labolicenties zijn als basisscenario niet geloofwaardig.

Dat betekent niet dat dosimetrie te klein is voor een IOF-project. Het betekent dat het verkeerde businessmodel wordt gebruikt om de waarde ervan uit te leggen.

AEGIS is waarschijnlijk geen breed standalone softwarebedrijf dat tientallen grote klanten rechtstreeks bedient. De geloofwaardige route is:

1. rechtstreeks verkopen aan een klein aantal OEM's, telecomspelers en gespecialiseerde labs om de waarde en prijs te bewijzen.
2. AEGIS vervolgens als snelle dosimetrie- en APD-laag integreren in bestaande workflows van bijvoorbeeld ZMT/SPEAG, Ansys, Dassault Systèmes of een chipsetplatform.
3. de grotere omzet halen uit distributie via zulke platformen, niet uit de veronderstelling dat wij zelf bijna elke relevante onderneming en elk lab ter wereld contracteren.

Op basis van de huidige gegevens is ongeveer €0,5 tot €1,2 miljoen directe terugkerende omzet een ernstig maar ambitieus doel. Een totaal van €2 tot €3 miljoen per jaar wordt geloofwaardig als daar een echte distributie- of embedded deal bovenop komt. €5 miljoen ARR is vandaag geen verdedigbaar basisscenario. Het kan wel een upside zijn bij meerdere platformdeals of een strategische licentie- of overnametransactie.

Dat is nog steeds ruim voldoende om een IOF-investering van ongeveer €250.000 te verantwoorden. Het project hoeft geen tweede ZMT te worden om economisch zinvol te zijn. Het moet aantonen dat het een waardevolle en verkoopbare laag in een bestaande markt kan worden.

De eerdere IOF-dossiers over sensoren en paarden leggen de lat trouwens niet bij een bewezen miljoenenomzet. Ze vertrekken vooral van een herkenbaar probleem, een telbare doelgroep, een route naar de koper en een grote onderliggende kostenpost. AEGIS heeft op sommige punten al sterker bewijs, met echte FCC-dossiers, gesprekken met bedrijven en een concreet industrieel werkproces. We moeten hun commerciële helderheid overnemen, niet hun ruime vermenigvuldigingen imiteren.

## Wat de FCC-data werkelijk zegt

### Enterprisecontracten

In de recente FCC-data zijn er, afhankelijk van de precieze afbakening en normalisatie van bedrijfsnamen, slechts ongeveer 14 tot 25 organisaties die gemiddeld of in één recent jaar minstens vijf toestellen boven 6 GHz indienen. Slechts ongeveer 35 organisaties halen gemiddeld minstens drie toestellen per jaar.

Twintig enterprisecontracten betekent dus niet een bescheiden marktaandeel. Het betekent bijna volledige penetratie van de groep met een structureel hoog indieningsvolume. Bovendien zijn niet al die organisaties goede AEGIS-klanten. De lijst bevat ook makers van access points, routers en radars waarvoor lichaamsdosimetrie niet noodzakelijk het belangrijkste probleem is.

Een eerlijker direct scenario vertrekt daarom van vier tot acht grote contracten, niet van twintig of dertig. De omzet moet vervolgens komen uit een voldoende hoge waarde per contract.

### Labs

In de pilot van 163 FCC-dossiers werden zestien verschillende labmerken teruggevonden. Bij de 98 dossiers met een herkenbaar lab waren Sporton, PCTEST, SGS en UL samen goed voor ongeveer 78 procent.

Dit bewijst een sterke marktconcentratie. Het bewijst niet dat er wereldwijd exact zestien geschikte labs bestaan. De dataset is een steekproef, en één merk kan meerdere sites hebben. De uitspraak dat vijfentwintig licenties letterlijk meer zijn dan het aantal bestaande labs gaat dus te ver.

Wat wel standhoudt: vijfentwintig merklicenties zijn niet onderbouwd. Een direct model met ongeveer vijf tot acht labgroepen is geloofwaardiger. Een hoger aantal kan alleen worden gebruikt wanneer expliciet per site wordt verkocht en het aantal relevante sites eerst wordt geteld. Labs zijn mogelijk nog waardevoller als verkoop- en validatiekanaal dan als eindklant.

### 60 GHz en Wi-Fi

De grote aantallen boven 6 GHz zitten niet bij mmWave-smartphones. Ze zitten vooral bij Wi-Fi 6E/7 en 60 GHz. De FCC-data bevat 468 unieke 60GHz-toestellen van 376 aanvragers, met veel nieuwkomers.

Dat is nuttig als bewijs dat de wereld boven 6 GHz breder is dan een tiental smartphonefabrikanten. Het is nog geen bewijs voor twintig betaalde ontwerptrajecten per jaar. In de onderzochte 60GHz-steekproef steunde het merendeel op eenvoudige MPE-beoordeling. Slechts een kleine minderheid bevatte gesimuleerde of gemeten power density. Veel van deze bedrijven hebben dus niet automatisch het complexe lichaamsdosimetrieprobleem waarvoor AEGIS waardevol is.

Ontwerptrajecten blijven een mogelijke aanvullende inkomstenbron, maar mogen niet als vaste kernomzet worden opgeteld zonder eerst de complexe subset en de betalingsbereidheid te kwalificeren.

## Het Samsung-dossier bewijst waarde, geen groot klantenaantal

Het onderzochte toestel is de Galaxy S24 met FCC ID `A3LSMS921U`, niet de S25. Document 6902432 is het Part 0 PD Report. Het afzonderlijke simulatierapport is document 6902428. Die details moeten juist staan voordat het voorbeeld extern wordt gebruikt.

Het dossier toont wel een bijzonder relevant werkproces. Samsung en zijn partners bepalen voor honderden beamconfiguraties vermogenslimieten met simulatie en valideren vervolgens een geselecteerde subset met metingen. Voor drie banden, twee antennemodules en afzonderlijke beams en beamparen ontstaan 378 configuraties of limieten. Kanalen, oppervlakken en fasecombinaties vergroten de onderliggende zoekruimte nog verder.

De juiste commerciële conclusie is niet dat Samsung 378 afzonderlijke HFSS-simulaties of 378 volledige meetcampagnes uitvoert. De full-wave velden worden hergebruikt en scripts verwerken veel combinaties. De dure lus zit in ontwerpiteraties: een wijziging aan antenneplaatsing, module, behuizing of industrieel ontwerp kan een nieuwe full-device analyse en nieuwe selectie van worst cases veroorzaken.

AEGIS moet daarom worden verkocht als een snelle exploratie- en screeningslaag die:

- vroeg in het ontwerp slechte varianten uitsluit.
- poses, scenario's en configuraties veel sneller doorzoekt.
- betrouwbaar de worst cases aanwijst voor de dure FDTD-, FEM- of meetstap.
- bestaande complianceflows aanvult zonder zelf onmiddellijk de formele eindmethode te moeten worden.

Dit ondersteunt ook het antwoord op de bezorgdheid over standaarden. De klant kan de uiteindelijke certificatie blijven uitvoeren met geaccepteerde FDTD/FEM-berekeningen of metingen. AEGIS hoeft niet eerst in een norm te staan om tijd en geld te besparen. Het moet wel aantonen dat het de relevante worst cases betrouwbaar rangschikt. Normopname is een latere commerciële versneller, geen voorwaarde voor de eerste verkoop.

## Waar de waarde per klant vandaan kan komen

De huidige externe en interne prijsankers rechtvaardigen geen willekeurige prijs van €150.000 tot €250.000 per klant. Ze maken wel duidelijk dat €50.000 tot €100.000 voor een grote team- of sitelicentie mogelijk verdedigbaar is zodra de tijdswinst is bewezen.

- Een RF-compliance-ingenieur bij een grote OEM kost alleen al aan basissalaris ruwweg $150.000 tot $270.000 per jaar.
- HFSS- en bredere Ansys-contracten kosten organisaties tienduizenden tot ongeveer honderdduizend pond per jaar, afhankelijk van de bundel.
- Gespecialiseerde meetinfrastructuur kost veel meer dan gewone engineeringsoftware.
- De gesprekken met Ericsson tonen inhoudelijke interesse en een concreet probleem, maar nog geen betalingsbereidheid.
- Nokia rapporteerde minder dan €10.000 jaarlijkse uitgaven aan de huidige EMF-tooling. Dat is een belangrijk tegenbewijs tegen een uniforme hoge prijs.
- De CNR-interesse ondersteunt academische prijzen van enkele duizenden euro's per gebruiker, niet automatisch een industriële prijs van €20.000 per lab.

De prijs moet dus uit gemeten klantwaarde volgen. Als een pilot minstens een kwart tot een halve FTE per programma bespaart, een ontwerpiteratie voorkomt of de doorlooptijd met weken verkort, wordt een contract van €50.000 tot €100.000 rationeel. Een contract van €150.000 tot €250.000 kan later kloppen voor een grote site, meerdere programma's of een strategische OEM, maar is nog geen gevalideerd uitgangspunt.

## Het echte schaalmechanisme

Sim4Life wordt in ongeveer 31 procent van de onderzochte FCC-dossiers genoemd. HFSS/Ansys komt eveneens vaak voor, vooral in FR2-dossiers. Dat bewijst dat ZMT/SPEAG en Ansys zichtbaar aanwezig zijn in de workflows die AEGIS wil verbeteren.

Het bewijst nog niet dat elke vermelding een betalende softwaregebruiker is. Sommige vermeldingen komen uit standaardrapporten, verificatieprocedures of werk van een extern lab. Het bewijst evenmin dat een partner vanzelf €500.000 per jaar zal betalen.

De embedded route is niettemin de sterkste schaalhypothese. ZMT verkoopt al gespecialiseerde modules bovenop Sim4Life en heeft een bestaande dosimetrie-installatiebasis. Een partnerdeal moet alleen anders worden berekend:

`relevante actieve klanten × attach rate × moduleprijs × aandeel voor AEGIS`

Zonder deze vier getallen is “twee embedded licenties van €500.000” geen prognose maar een placeholder. Het belangrijkste commerciële gesprek met ZMT, Ansys of een andere platformpartij gaat daarom niet over een mooie forfaitaire licentie. Het gaat over:

- hoeveel relevante actieve gebruikers zij werkelijk hebben.
- hoeveel daarvan met mmWave-, APD- of lichaamsdosimetrie bezig zijn.
- welke moduleprijs de markt al aanvaardt.
- welk aandeel een externe technologiehouder krijgt.
- of de partner AEGIS zelf verkoopt, bundelt, acquireert of het team in dienst neemt.

Die laatste uitkomsten zijn geen mislukking. Voor een gespecialiseerde technologie met een kleine directe kopersgroep kan een licentie, overname of aanwerving door een incumbent rationeler zijn dan jarenlang een volledig verkoopkanaal uitbouwen.

## Een financiële voorstelling die wel standhoudt

De onderstaande bedragen zijn geen voorspelling. Ze tonen welke voorwaarden nodig zijn om elk niveau geloofwaardig te maken.

| Niveau | Wat moet er materieel waar zijn? | Ordegrootte |
|---|---|---:|
| Eerste bewijs | 2 tot 5 betaalde industriële pilots of contracten, aangevuld met academische gebruikers | €0,1 tot €0,4 miljoen per jaar |
| Specialistische directe business | 4 tot 8 grote team- of sitecontracten aan gemiddeld €50.000 tot €100.000, plus enkele labs en onderzoeksgroepen | €0,4 tot €1,2 miljoen ARR |
| Schaal via platform | De directe business plus minstens één partner met aantoonbare installatiebasis, attach rate en revenue share | €1,5 tot €3 miljoen totale jaaromzet |
| Strategische upside | Meerdere platformen, een brede OEM-uitrol, of een licentie- of overnametransactie | mogelijk €3 tot €5 miljoen of meer, maar niet gevalideerd |

Dit model is geloofwaardiger dan een tabel waarin klantenaantallen en prijzen onafhankelijk van elkaar worden gekozen. Elk omzetniveau is gekoppeld aan een observeerbare commerciële mijlpaal.

## Wat het IOF-project daadwerkelijk moet bewijzen

De twee jaar moeten niet worden verkocht als tijd om de hele markt te veroveren. Ze dienen om de onzekerheden te reduceren die een koper of partner vandaag nog terecht ziet.

1. **Betaalde waarde:** minstens twee industriële pilots, met een vooraf afgesproken prijs of betaalde vervolglicentie.
2. **Meetbare besparing:** voor en na meten hoeveel ingenieursuren, full-wave ontwerpiteraties en meetconfiguraties nodig zijn.
3. **Betrouwbare screening:** aantonen dat AEGIS over echte ontwerpwijzigingen dezelfde relevante worst cases selecteert als FDTD/FEM of metingen.
4. **Prijsbewijs:** minstens één conversie naar een jaarlijkse team- of sitelicentie van €50.000 of meer.
5. **Partnerbewijs:** van minstens één platformpartij de actieve relevante installatiebasis, realistische attach rate, moduleprijs en revenue share verkrijgen.
6. **Go/no-go:** als er na 18 tot 24 maanden geen betaalde industriële conversie en geen concrete partnereconomie is, niet blijven volhouden dat een standalone business van meerdere miljoenen vanzelf ontstaat. Dan doelgericht kiezen voor technologielicentie, overname, acqui-hire of integratie in een bestaand productteam.

## Wat Fable juist zag, en waar de analyse te ver ging

Fable zag de belangrijkste structurele fout juist: de huidige tabel maskeert extreme marktpenetratie en de grotere omzet moet waarschijnlijk via distributie komen. Ook de concentratie bij een handvol labs en het belang van het Samsung-werkproces zijn reële, sterke inzichten.

Enkele claims moeten echter worden afgezwakt of gecorrigeerd:

- De achttien high-cadence ondernemingen hangen af van periode en naamnormalisatie. De richting is juist, het exacte getal is geen natuurconstante.
- Zestien waargenomen labmerken zijn geen officiële wereldwijde telling van alle relevante labs.
- Veel 60GHz-nieuwkomers hebben eenvoudige MPE-dossiers. Zij zijn niet automatisch twintig jaarlijkse AEGIS-projecten.
- Een Sim4Life-vermelding is geen bewijs van een directe licentiehouder of bereikbare koper.
- €150.000 tot €250.000 per tier-one klant is een te valideren prijs, niet een reeds bewezen prijs.
- De Amerikaanse FCC heeft bredere beperkingen voor Chinese en Hongkongse labs voorgesteld, maar de algemene uitfasering over twee jaar is nog geen definitief ingevoerde regel. De FCC heeft wel al erkenningen ingetrokken en de controle op labs aangescherpt.
- Het toestel en de documentnummers in de Samsung-casus moeten worden gecorrigeerd zoals hierboven beschreven.

De onafhankelijke analyse versterkt dus het verhaal, maar alleen wanneer we haar ook zelf kritisch behandelen.

## De boodschap voor Filip

De markt is niet groot omdat er honderden identieke grote softwareklanten bestaan. De markt is groot genoeg omdat een kleine groep bedrijven en labs een duur, terugkerend en verplicht engineeringprobleem heeft, terwijl enkele gevestigde platformen toegang tot bijna de hele gespecialiseerde markt hebben.

Het eerlijke verhaal is daarom:

> Ik geloof nog steeds in dosimetrie, maar niet in de huidige vermenigvuldigingstabel. Met directe klanten kunnen we binnen het IOF-project de waarde en een serieuze specialistische omzet bewijzen. De route naar enkele miljoenen loopt vervolgens via integratie in bestaande simulatie-, meet- of chipsetplatformen. Daarvoor hebben we geen onmiddellijke normopname nodig: klanten kunnen finaal blijven certificeren met FDTD/FEM of metingen, terwijl AEGIS de dure zoek- en ontwerplus veel sneller maakt.

Dit is minder spectaculair dan “dertig klanten maal honderdduizend euro”, maar commercieel veel sterker. De inkomsten hangen niet langer af van fictieve totale marktpenetratie. Ze hangen af van een klein aantal toetsbare deals, aantoonbare besparing per klant en één distributiepartner. Precies dat kan een IOF-project van twee jaar uitzoeken.

## Bronnen en controleerbare aanknopingspunten

Lokale data en gesprekken:

- FCC-dataset: `/home/user/fcc6ghz/robin/eas_grants_classed.csv`
- FCC-pilotextracties: `/home/user/fcc6ghz/data/meta/pilot_extractions.parquet`
- Ericsson-notities: `spinoff/outreach_dossier/Ericsson/resulting_meeting_notes.txt`
- Nokia-notities: `spinoff/outreach_dossier/Nokia/resulting_meeting_notes.txt`
- CNR-letter of intent: `spinoff/outreach_dossier/letters/parazzini_letter_of_intent_combined.tex`

Publieke bronnen:

- Samsung Galaxy S24, Part 0 PD Report, document 6902432:
  https://fccid.io/A3LSMS921U/RF-Exposure-Info/A3LSMS921U-Part0-PD-Report-R4-6902432.pdf
- Samsung Galaxy S24, PD Simulation Report, document 6902428:
  https://fccid.io/A3LSMS921U/RF-Exposure-Info/A3LSMS921U-PD-Simulation-Report-R1-6902428.pdf
- IEC/IEEE 63195-2, computation of incident power density from 6 GHz to 300 GHz:
  https://webstore.iec.ch/en/publication/62754
- FCC Laboratory Division publications and KDB guidance:
  https://apps.fcc.gov/oetcf/kdb/forms/FTSSearchResultPage.cfm?id=20676&switch=P
- FCC 26-28, adopted laboratory integrity measures and proposed further rules:
  https://docs.fcc.gov/public/attachments/FCC-26-28A1.pdf
- FCC press release clarifying the proposed two-year phaseout:
  https://docs.fcc.gov/public/attachments/DOC-421311A1.pdf
- Sim4Life licensed-module model:
  https://zmt.swiss/assets/downloads/Flyers/1810S4Lbookletweb.pdf
- Sim4Life 9.2 APD skin model:
  https://zmt.swiss/news-and-events/news/sim4life/sim4life-v92-update-release
- SPEAG DASY8 APD module:
  https://speag.swiss/products/dasy8/m-apd
- SPEAG, 1.000 verkochte DASY-robots:
  https://speag.swiss/news-events/news/corporate/2023/celebration-of-1000-dasy-robots-sold
- UKRI HFSS Electronics Desktop procurement:
  https://www.find-tender.service.gov.uk/Notice/038320-2025
- UKRI Ansys TECS procurement:
  https://www.contractsfinder.service.gov.uk/notice/da2ab314-ea89-4591-aa15-07daa8d932d1
- Apple RF-compliancefunctie en salarisrange:
  https://jobs.apple.com/en-us/details/200627988-0836/wireless-rf-compliance-systems-engineer-sar-mpe
