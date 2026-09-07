# AEGIS-dosimetrie: marktlogica en haalbaarheid van validatie

## Vooraf: de beslissing die nu voorligt

Mijn voorstel is om AEGIS verder te valideren en te valoriseren binnen dosimetrie. De eerste toepassing is snelle screening en optimalisatie van lokale absorbed power density (APD) voor toestellen en antennes boven 6 GHz. AEGIS onderzoekt grote aantallen bundels, afstanden, houdingen en antenneconfiguraties. Alleen de geselecteerde worstcases en twijfelgevallen gaan daarna naar FDTD/FEM of fysieke meting.

Dit is geen voorstel om AEGIS vandaag als certificatiemethode of algemene vervanger van full-wave simulatie te verkopen. Het is een voorstel om met EUR 250.000 in twee jaar de technische en commerciële onzekerheid weg te nemen die nog tussen de huidige technologie en een licentie, spin-off of strategische samenwerking staat.

## Waarom de markt niet gelijk is aan een fractie van ZMT

De redenering "ZMT haalt ongeveer EUR 2 tot 3 miljoen omzet, dus een nieuw product haalt daar later 1 tot 5% van" vertrekt van twee onbewezen aannames. De vaak genoemde omzetinschatting voor ZMT is niet gestaafd door een publieke jaarrekening. Belangrijker is dat AEGIS niet noodzakelijk hetzelfde product aan dezelfde gebruikers verkoopt.

Een losse softwarelicentie voor een individuele dosimetrist is inderdaad een kleine markt. De grotere propositie is een design-to-conformance workflow voor een volledig toestel- of antenneprogramma:

- batchscreening van antennestanden, codebooks, lichaamsposities en afstanden

- selectie van de echte worstcases met een onzekerheidsmarge

- differentiabele optimalisatie van het ontwerp

- reproduceerbare rapporten per standaardversie

- on-premise integratie via SDK of API

- overdracht van geselecteerde gevallen naar FDTD/FEM en meting

De budgethouder is dan een device-, chipset- of antenneteam, een testlabo of een leverancier van simulatietools. Dat is een andere economische eenheid dan één dosimetriezetel.

### Concrete omvang van de onderliggende activiteit

De eigen analyse van de officiële FCC Equipment Authorization-data telt 3.900 unieke toestel-ID's boven 5,925 GHz sinds 2019. Het jaarlijkse aantal steeg van 218 in 2019 naar 764 in 2025. Binnen die stroom groeiden Wi-Fi 6E/7-toestellen van 4 in 2020 naar 448 in 2025 en 60 GHz-toestellen van 36 naar 118 per jaar. Niet elk van die toestellen is geschikt voor AEGIS of vereist APD. Dit is de bovenliggende stroom van ontwikkel- en conformiteitsprogramma's waaruit het adresseerbare deel tijdens het IOF-project wordt bepaald.

De internationale certificatie-activiteit bevestigt dat deze markt niet uit enkele telefoonfabrikanten bestaat. GCF vermeldt [meer dan 1.000 smartphonecertificaties over vijf jaar](https://www.globalcertificationforum.org/gcf-certified-products/smartphone-certifications.html), [728 modulecertificaties over drie jaar](https://www.globalcertificationforum.org/gcf-certified-products/module-certifications.html) en [225 router- en fixed-wireless-certificaties over vijf jaar](https://www.globalcertificationforum.org/gcf-certified-products/router-fwa-certifications.html). [CTIA heeft meer dan 100 geautoriseerde testlabo's](https://www.ctia.org/certification/eval_criteria/index.cfm), waarvan slechts een deel vandaag relevante APD-capaciteit heeft.

Ook de timing is concreet. IEC/IEEE 63195-2 definieert sinds 2022 computationele procedures voor invallende vermogensdichtheid bij toestellen op maximaal 200 mm van het lichaam. De computationele procedure voor geabsorbeerde vermogensdichtheid wordt nu ontwikkeld in het actieve [IEEE/IEC P63195-4-project](https://standards.ieee.org/ieee/63195-4/11782/). De markt is dus niet alleen een bestaand softwaresegment. Er ontstaat ook een nieuw, nog niet volledig vastgelegd conformiteitsproces.

### Een proportionele omzetcase

Onderstaande cijfers zijn hypotheses die het project moet valideren. Het zijn geen gecontracteerde inkomsten. Om dubbeltelling te vermijden, bedient een embedded partner andere klanten of regio's dan de rechtstreeks gefactureerde accounts. Data-abonnementen tellen alleen klanten zonder enterprise- of labolicentie.

| Inkomstenlaag | Jaar 5 | Uitbraakscenario, jaar 7 tot 9 |
|---|---:|---:|
| Device-, chipset- en moduleprogramma's | 12 x EUR 120k = EUR 1,44M | 20 x EUR 175k = EUR 3,50M |
| APD-capabele testlabo's | 18 x EUR 30k = EUR 0,54M | 30 x EUR 35k = EUR 1,05M |
| Embedded solver- of compliancekanalen | 1 x EUR 400k | 2 x EUR 500k = EUR 1,00M |
| Validatiedata en conformiteitsupdates | 20 x EUR 15k = EUR 0,30M | 25 x EUR 20k = EUR 0,50M |
| Regulatoren en specialistische infrastructuurcases | 4 x EUR 40k = EUR 0,16M | 6 x EUR 50k = EUR 0,30M |
| **Totaal gemodelleerde recurrente omzet** | **EUR 2,84M** | **EUR 6,35M** |

De EUR 2,84 miljoen-case vereist geslaagde validatie, betaalde pilots en bevestiging van programmaprijzen. De EUR 6,35 miljoen-case vereist bovendien twee distributiepartners en een professionele internationale supportfunctie. Het is dus een geloofwaardig schaalpad, geen basisprognose.

Voor de beslissing over een IOF-investering is ook de downside relevant. Een gespecialiseerde softwareactiviteit met EUR 1 miljoen recurrente omzet, een betekenisvolle OEM-licentie of een strategische overname kan de investering al verantwoorden. Ter vergelijking: de toegekende Unisens-StarTT-aanvraag projecteerde EUR 780.000 omzet in jaar vijf. De toegekende paardenaanvraag werkte met een toestelprijs van EUR 72,50 en een nog niet geprijsd abonnement, zonder bottom-up omzetprognose over vijf jaar. Dit is geen kritiek op die projecten. Het toont dat de normale IOF-drempel een aannemelijk valorisatiepad met toetsbare mijlpalen is, niet vooraf bewezen dominantie over een bestaande markt.

## Tekst voor de IOF-aanvraag: technische validatie en industriële proof of concept

### Doel en beoogd gebruik

Het project bepaalt of AEGIS kan worden ingezet als een snelle, auditeerbare pre-screening- en ontwerpoptimalisatielaag voor piek ruimtelijk gemiddelde APD in het radiating-field-regime. AEGIS screent grote aantallen antenne-, bundel-, afstands- en lichaamsconfiguraties. Gevallen dicht bij de conformiteitslimiet of buiten het gevalideerde domein worden doorgestuurd naar gekwalificeerde FDTD/FEM-simulatie of fysieke meting.

De eerste productclaim is bewust smaller dan finale certificatie. Reactive-near-field-koppeling, detuning van de bron door het lichaam, diepe-weefselgrootheden en totaal geabsorbeerd vermogen vallen erbuiten, tenzij zij een afzonderlijke validatiegate halen. De doelgrootheid is piek-APD gemiddeld over 4 cm² en, boven 30 GHz, 1 cm². Het eerste frequentiedomein is 10 tot 60 GHz.

### Uitgangspositie

AEGIS is analytisch geverifieerd tegen Fresnel- en Mie-referentieproblemen en vergeleken met gepubliceerde studies op vrijwilligers en anatomische fantomen. Een eerste Sim4Life-vergelijking op Thelonious leverde voor piek-APD over 4 cm² in drie 7 GHz-vlakke-golfgevallen verhoudingen van 1,057, 1,196 en 0,830 op, met een richtingsgemiddelde verhouding van 1,027.

Dit is bemoedigend, maar nog geen industriële validatie. In dezelfde campagne werd totaal geabsorbeerd vermogen niet gevalideerd. Slechts drie richtingen en één polarisatie werden voltooid. Een blinde 28 GHz device-to-body-benchmark en fysieke APD-meting ontbreken nog. Deze hiaten vormen het onderzoekswerkpakket. Zij vereisen geen nieuw fysisch principe.

### Waarom de validatie haalbaar is

De volledige referentieketen bestaat reeds:

- analytische half-space-, gelaagde-medium- en Mie-oplossingen voor onafhankelijke codeverificatie

- gekwalificeerde FDTD/FEM-tools voor geconvergeerde referenties met identieke geometrie, materiaaleigenschappen, excitatie en APD-middeling

- commercieel beschikbare, traceerbare APD-fantomen, bronnen en meetsystemen voor FR2 en FR3. De huidige meetonzekerheid van dergelijke systemen ligt rond 1,5 tot 1,7 dB, wat een realistische onzekerheidsgebaseerde acceptatietest mogelijk maakt. Zie de [DASY APD-validatie](https://speag.swiss/news-events/news/measurement/dasy8-module-apd-v1) en de [geaccrediteerde APD-kalibratie](https://speag.swiss/news-events/news/measurement/2026/speag-lab-expands-iso-17025-accreditation-to-apd-probe-and-dak-r-calibrations)

- een bestaande AEGIS-codebasis met fysische kernels, anatomische meshes, solverbruggen, geautomatiseerde tests en een reproduceerbare resultatenketen

De IOF-middelen financieren daarom onafhankelijke bewijsvoering, afbakening van het geldige modeldomein en industriële toepassing. Zij financieren geen ongedefinieerde softwarebouw.

### Werkplan en beslissingscriteria

**Maand 1 tot 2: claim en protocol bevriezen.** Definieer het beoogde gebruik, de uitgesloten regimes, APD-middeling, kalibratiegevallen, blinde holdouts en vaste versies van software, fantomen, materiaaldata en referentiesolvers.

**Maand 1 tot 4: referenties kwalificeren.** Voer grid-, domein-, grensvoorwaarde- en convergentiestudies uit in Sim4Life, met een onafhankelijke FEM- of FIT-implementatie op een representatieve subset. Een simulatie geldt alleen als referentie wanneer energiebalans, gridsensitiviteit en numerieke onzekerheid gekwantificeerd zijn.

**Maand 3 tot 9: blinde full-wave-validatie.** Vergelijk AEGIS met de gekwalificeerde referenties op canonieke vormen en vier anatomische fantomen bij 10, 28, 40 en 60 GHz. Thelonious dient voor ontwikkeling. Duke, Ella en Eartha zijn holdouts. Meet absolute APD, oppervlaktekaarten, hotspotlocatie, worstcase-ranking en end-to-end-rekentijd.

**Maand 6 tot 12: onafhankelijke fysieke meting.** Bevries de AEGIS-voorspellingen vóór ontvangst van de meetresultaten. Gebruik een traceerbaar APD-fantoom en minstens zes gekarakteriseerde bronnen rond 28 GHz, met verschillende afstanden, oriëntaties en polarisaties. Bouw een volledige onzekerheidsbegroting op.

**Maand 9 tot 24: industriële proof of concept.** Voer betaalde of gecofinancierde pilots uit met device-, chipset-, testlab- of solverpartners. Meet hoeveel full-wave-runs worden vermeden, hoe goed de worstcases worden teruggevonden, hoeveel doorlooptijd wordt gewonnen, wat integratie kost en welke betalingsbereidheid bestaat. Dien de reproduceerbare validatie-evidentie in voor technische bespreking binnen P63195-4.

De voorgestelde projectcriteria zijn geen normatieve IEC-grenzen:

- mediane fout voor piek-APD over 4 cm² binnen 0,5 dB

- minstens 90% van de blinde scenario's binnen 1,0 dB

- minstens 95% recall van de full-wave-worstcases en geen onveilige vrijgave in de vooraf geregistreerde testset na toepassing van de onzekerheidsmarge

- minstens 100 maal versnelling op een identieke end-to-end-screeningtaak

- bij fysieke meting een genormaliseerde fout van maximaal één in minstens 90% van de primaire gevallen, zonder systematische bias buiten de gecombineerde meetonzekerheid

- minstens twee betaalde pilots, of één betaalde pilot en één getekende embedded-licentie- of OEM-evaluatieovereenkomst, vóór volledige productopschaling

### Risico's en fallbacks

Als AEGIS alleen in een stabiel deelgebied slaagt, wordt de productclaim beperkt op basis van frequentie, bronafstand, geometrie of excitatie. Als de hotspot-ranking slaagt maar absolute APD niet, blijft AEGIS een prioriteringstool en wordt elk resultaat doorgestuurd naar full-wave-validatie. Als totaal vermogen opnieuw faalt, verdwijnen totaal geabsorbeerd vermogen en whole-body SAR uit de productclaim.

Als zowel de APD-nauwkeurigheid als de worstcase-ranking falen, stopt het commercialisatietraject. Het project levert daardoor ook bij een negatieve uitkomst een duidelijke beslissing op. Bij succes resulteert het in een gekwalificeerde benchmarkset, een onafhankelijk meetrapport, een onzekerheidsgebonden productclaim, industriële pilots en een onderbouwde licentie- of spin-offbeslissing.
