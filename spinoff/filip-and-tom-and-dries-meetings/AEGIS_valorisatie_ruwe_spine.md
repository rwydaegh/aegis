# AEGIS valorisatie, schrijfspine

## 1. Centrale stelling

AEGIS wordt geen afzonderlijke vervanger van HFSS, Sim4Life, CST of een fysieke meting. Het wordt de snelle laag in een bredere workflow voor RF-blootstelling:

- GOLIAT automatiseert de betrouwbare full-wave berekeningen in Sim4Life.
- AEGIS verkent snel grote aantallen ontwerp- en gebruiksvarianten.
- De meest kritieke en onzekere gevallen gaan terug naar FDTD, FEM of meting.
- Het eindresultaat is een reproduceerbaar technisch dossier, geen los solverresultaat.

Deze positionering houdt de formele conformiteitsbeoordeling bij reeds geaccepteerde methodes. De commerciële waarde van AEGIS ligt eerder in ontwerpiteratie, prioritering en doorlooptijd.

## 2. Het product

De workflow vertrekt van toestel-, antenne- en gebruiksgegevens:

1. GOLIAT bouwt een gecontroleerde Sim4Life-referentie op.
2. Een beperkte set full-wave berekeningen kalibreert de snelle screening.
3. AEGIS rangschikt varianten van positie, oriëntatie, afstand, antenneconfiguratie en eventueel beamstate.
4. Een onzekerheidsmodel markeert gevallen die buiten het gevalideerde domein of te dicht bij de limiet liggen.
5. GOLIAT of een andere full-wave solver bevestigt de geselecteerde gevallen.
6. De workflow bewaart invoer, softwareversies, resultaten, onzekerheden en beslissingen in een technisch rapport.

De eerste commerciële vorm hoeft nog geen volledig self-service softwarepakket te zijn. Een betaalde pre-compliance dienst of een gekwalificeerde labworkflow kan dezelfde technische keten gebruiken en tegelijk de productvereisten blootleggen.

## 3. Waarde voor de klant

De klant betaalt voor een efficiëntere ontwikkel- en conformiteitsketen:

- minder herhaalde full-device simulaties na wijzigingen aan antenneplaatsing, module, chassis of industrieel ontwerp;
- snellere identificatie van kritieke configuraties;
- minder handmatige opbouw, extractie en rapportering;
- reproduceerbare overdracht tussen ontwerpteam, solver en testlaboratorium;
- duidelijke escalatie van onzekere gevallen naar full-wave verificatie of meting;
- een versieerbare workflow die bij wijzigingen aan normen kan worden bijgewerkt.

De waarde moet worden gemeten in vermeden solverruns, engineeringuren, kalenderweken en laattijdige redesigns. De snelheid van één AEGIS-berekening is op zichzelf geen voldoende prijsargument.

## 4. GOLIAT als productruggengraat

GOLIAT vormt een operationeel vertrekpunt in plaats van een nog te bouwen ondersteunende tool. De software bevat reeds:

- automatische opbouw van near-field en far-field scenario's in Sim4Life;
- lokale, parallelle en cloudgebaseerde FDTD-uitvoering;
- config-gedreven en reproduceerbare studies;
- extractie van SAR- en SAPD-resultaten;
- analyse, visualisatie, rapportering en monitoring;
- documentatie, tutorials en een publieke Apache-2.0-codebasis.

De derde prijs in de Sim4Life Student Competition levert externe bevestiging van de technische kwaliteit en de aansluiting bij het ZMT-ecosysteem.

Voor commerciële inzet zijn nog bijkomende elementen nodig:

- duidelijke exploitatierechten voor UGent-, EU-project- en eigen bijdragen;
- een commercieel model dat verenigbaar is met Apache-2.0;
- beheer van de afhankelijkheid van een Sim4Life-licentie;
- vastgezette en gekwalificeerde softwareversies;
- verificatiecases, regressietests en een audit trail;
- standaardspecifieke rapporttemplates en procedures voor modelreview.

GOLIAT kan daardoor zowel een directe workflow voor bestaande Sim4Life-gebruikers worden als de referentieomgeving waarin AEGIS wordt gevalideerd en aangeboden.

## 5. Technische afbakening van AEGIS

De huidige point-source module gebruikt een gekend vrij-ruimte-antennepatroon en inverse-square spreiding. Zij bevat nog geen volledige toestel-lichaam-koppeling en geen detuning van de antenne door het lichaam.

De analytisch duidelijke lokaal-vlakke-golfgrens ligt rond drie golflengtes, ongeveer 3,2 cm bij 28 GHz. Commerciële FR2-dossiers evalueren toestellen vaak op 2 mm. Betrouwbaarheid op zulke afstanden mag daarom niet vooraf worden verondersteld.

De initiële productclaim blijft beperkt tot een empirisch gevalideerd domein:

- screening en rangschikking van configuraties waarvoor de bronbeschrijving voldoende is;
- kalibratie met een beperkte set full-wave ankers;
- automatische escalatie bij korte afstanden, sterke koppeling of grote modelonzekerheid;
- geen zelfstandige certificatieclaim voor toestellen buiten dat domein.

De commerciële validatie moet daarom verder gaan dan gemiddelde APD-fout. Relevante maten zijn:

- recall van de full-wave top-\(k\)-configuraties;
- aantal gemiste worst cases;
- false-clearance rate na toepassing van een guard band;
- hotspotlocatie en rangorde;
- aantal vermeden full-wave berekeningen;
- totale end-to-end doorlooptijd.

Een goede ranking met een betrouwbare onzekerheidsmarge kan commercieel nuttig zijn, zelfs wanneer AEGIS niet in ieder scenario de absolute APD met certificatieprecisie voorspelt.

## 6. Bestaande markt, gemeten via FCC-data

De officiële FCC-extractie bevat 3.900 FCC-ID's boven 5,925 GHz sinds 2019. In 2025 kwamen 764 nieuwe toestellen in dit frequentiebereik op de Amerikaanse markt.

De segmenten verschillen sterk:

- Wi-Fi 6E/7: 448 nieuwe toestellen in 2025 en ongeveer 480 op jaarbasis in 2026.
- FR2: momenteel slechts ongeveer 16 tot 20 nieuwe toestellen per jaar, maar met zeer omvangrijke simulatie- en meetdossiers.
- 60 GHz: 118 toestellen in 2025 en een grote long tail, maar veel daarvan gebruiken een eenvoudige MPE-berekening of vallen onder een test exclusion.

Het documentencorpus bevat 2.239 succesvol opgehaalde filings en 10.491 exposure-documenten. De pilot met 163 filings toont onder meer:

- Sim4Life vermeld in 50 filings;
- HFSS/Ansys vermeld in 28 filings;
- een sterk geconcentreerde groep testlaboratoria;
- grote verschillen tussen eenvoudige MPE-dossiers en complexe APD-, PD- en simultane-transmissiedossiers.

Deze data dient vier doelen:

1. de technisch relevante toestelklassen onderscheiden van het totale aantal draadloze toestellen;
2. terugkerende OEM's, laboratoria en solverworkflows identificeren;
3. publieke benchmark- en regressiegevallen opbouwen;
4. prospects benaderen met hun eigen gedocumenteerde workflow als vertrekpunt.

De FCC-data is geen sterke zelfstandige softwaremoat. De bron is publiek en algemene compliance-intelligence wordt ook door partijen zoals MarkReady ontwikkeld. De belangrijkste waarde ligt in marktselectie, bewijs en acquisitie van klanten voor de exposure-workflow.

## 7. Het Samsung-dossier als concreet workloadbewijs

FCC-ID A3LSMS921U behoort bij de Galaxy S24, model SM-S921U. Het publieke Power Density Simulation Report beschrijft:

- twee mmWave-antennemodules;
- drie frequentiebanden;
- 63 beams of beamparen per module-bandcombinatie;
- in totaal 378 input power limits;
- een volledig HFSS-toestelmodel;
- Qualcomm-gerelateerde verwerking van de opgeloste velden;
- een beperkte selectie configuraties voor fysieke validatie.

Het dossier toont dat simulatie reeds de primaire motor is voor het bepalen van de vermogenslimiet per beam. De meting valideert vervolgens een selectie en ondersteunt de finale conformiteitsbeoordeling.

De 378 limieten staan niet gelijk aan 378 afzonderlijke HFSS-solves. De full-device oplossing wordt over beams geamortiseerd. De kost ontstaat vooral wanneer een ontwerpwijziging een nieuwe toesteloplossing vereist. AEGIS moet daarom worden gepositioneerd in de iteratieve ontwerplus, niet als snellere uitvoering van een reeds goedkope beamcombinatie.

## 8. Klanten en marktnoemers

### Grote toestel-, chipset- en modulebedrijven

De FCC-data bevat 18 organisaties met minstens vijf relevante filings per jaar. Dit is een bovengrens voor de groep terugkerende high-cadence prospects, geen garantie dat iedere organisatie technisch bij AEGIS past.

Een volwassen directe marktpositie betekent eerder vier tot zes betekenisvolle enterprisecontracten dan tientallen rechtstreekse klanten. De interessantste klanten combineren:

- meerdere complexe toestelprogramma's per jaar;
- herhaalde ontwerpiteraties;
- interne HFSS-, CST- of Sim4Life-capaciteit;
- een duidelijke eigenaar van exposure- of compliancebudget;
- behoefte aan on-premise integratie wegens vertrouwelijke CAD en antennegegevens.

### Testlaboratoria

De pilot observeert 16 labmerken in 163 publieke dossiers. De vier meest voorkomende merken verzorgen ongeveer 77% van de filings waarin een labo kon worden geïdentificeerd.

Laboratoria zijn daardoor vooral een distributiekanaal:

- één integratie kan meerdere toestelprogramma's bereiken;
- usage- of projectinkomsten passen beter dan een groot aantal losse seats;
- een labo kan de workflow als vroege pre-compliance dienst aan klanten aanbieden;
- de onafhankelijkheid tussen designadvies en finale certificatie moet contractueel en procedureel worden bewaakt.

### Kleinere toestelontwikkelaars

Kleinere OEM's en integratoren kunnen per project kopen wanneer zij geen eigen gespecialiseerde dosimetrist of full-wave workflow hebben. De relevante doelgroep bestaat uit complexe portable en body-near toestellen, niet uit de volledige 60 GHz-long tail.

### Solver- en platformleveranciers

Sim4Life en HFSS zijn rechtstreeks zichtbaar in de publieke dossiers. ZMT, Ansys en mogelijk andere solverleveranciers bieden daarom een aantoonbaar distributiekanaal. Qualcomm beheert een nog dichter bij het product liggende beam-limit workflow, maar die markt is proprietary en patentintensief.

Het bestaan van deze platformen bewijst de integratiemogelijkheid, niet hun willingness to pay. Een embedded overeenkomst blijft een afzonderlijke commerciële validatie.

## 9. Concurrentie en differentiatie

SPEAG biedt met DASY8 reeds:

- Forward Transformation Evaluation;
- Maximum Exposure Optimizer;
- test-case reduction;
- API-integratie;
- automatische rapportering;
- meetgebaseerde evaluatie van complexe phased arrays.

Sim4Life biedt reeds parameter sweeps, optimizers, meta-modelling, clouduitvoering, Python-automatisering en een pluginframework. Ansys RF Advisor toont bovendien een commercieel model waarbij CAD wordt aangeleverd en de klant een geautomatiseerd simulatierapport ontvangt.

De differentiatie kan daarom niet rusten op algemene claims over codebook sweeps of test-case reduction. De specifieke positie van de gecombineerde workflow is:

- GOLIAT als reproduceerbare full-wave orchestratie;
- AEGIS als exposure-specifieke low-fidelity fysica;
- kalibratie op een kleine set full-wave ankers;
- expliciete onzekerheid en een guard band;
- automatische keuze van volgende full-wave gevallen;
- rapportering van zowel snelle screening als finale verificatie;
- inzet vóór CAD freeze en vóór de fysieke labcampagne.

De meest verdedigbare technische term is een multi-fidelity exposure-workflow, niet een universele snellere dosimetriesolver.

## 10. Standaarden en conformiteit

IEEE/IEC P63195-4 specificeert FDTD en FEM voor computationele APD van toestellen dicht bij het lichaam. ISED RSS-102.IPD.SIM vereist een reproduceerbare technische brief met toestelconfiguratie, CAD, antennegegevens, simulatiemethode, onzekerheid en meetvalidatie.

De productarchitectuur sluit hier rechtstreeks op aan:

- GOLIAT en andere full-wave engines leveren het formele computationele bewijs.
- Metingen blijven beschikbaar voor validatie en finale conformiteit.
- AEGIS werkt vóór deze formele stap als screening- en prioriteringsmethode.
- De snelle methode hoeft niet onmiddellijk als zelfstandige conformity method te worden erkend.

Een standaardenbijdrage blijft waardevol voor vertrouwen en zichtbaarheid. Een realistische bijdrage behandelt benchmarks, onzekerheid, screening en escalatie, zonder formele acceptatie van AEGIS als eerste commerciële voorwaarde te maken.

## 11. Regelgevend momentum bij testlaboratoria

FCC 26-28 vermeldt dat 23 laboratoria hun erkenning reeds verloren of niet vernieuwd kregen wegens eigendom door of controle van verboden entiteiten. De order introduceert ook een fast-track PAG-route voor trusted labs in de Verenigde Staten en in economieën met een relevante MRA of wederkerige handelsovereenkomst.

Een ruimere uitsluiting van laboratoria in alle niet-reciproque economieën bevindt zich nog in een Second FNPRM. Zij is nog geen geldende algemene phase-out.

De bruikbare marktimplicatie is:

- regulatorische voorkeur voor een kleinere groep trusted labs;
- potentieel meer concentratie van complexe dossiers;
- grotere waarde van first-time-right en goede voorbereiding vóór reservatie van labcapaciteit;
- extra commerciële relevantie voor workflows die ontwerp, simulatie en labhandoff verbinden.

## 12. Commerciële aanbiedingen

### Gekwalificeerd lab workflow pack

- GOLIAT-deployment op de bestaande Sim4Life-infrastructuur;
- vastgezette configuraties, modellen en softwareversies;
- automatische SAR- en APD-extractie;
- regressietests, auditlog en onzekerheidsrapport;
- standaardspecifieke technische brief;
- AEGIS-screening als optionele accelerator;
- implementatiefee, jaarlijkse support en eventueel usage pricing.

### OEM design workflow

- on-premise verwerking van vertrouwelijke CAD en antennegegevens;
- ondersteuning van meerdere productiteraties;
- beperkte full-wave kalibratieset;
- snelle rangschikking van varianten;
- automatische full-wave verificatie van kritieke gevallen;
- programma- of enterprisecontract in plaats van een individuele seat.

### Pre-compliance projectdienst

- afgebakend project voor een kleinere OEM of integrator;
- levering via een testlab of complianceconsultancy;
- vroeg omzet- en klantbewijs;
- systematische verzameling van integratie- en productvereisten;
- mogelijke overgang naar een terugkerend workflowcontract.

### Embedded module

- AEGIS-engine en GOLIAT-workflow als plugin, module of template;
- ZMT/Sim4Life als technisch natuurlijke eerste integratiehypothese;
- licentie, royalty, revenue share of strategische overdracht;
- schaalroute bovenop de directe specialistische business, niet de directe base case.

## 13. Pricing en omzet

### Enterprise pricing

Een prijs van EUR 150.000 tot EUR 250.000 per jaar kan alleen worden verdedigd voor een multi-programma workflow met on-premise integratie, support, kwalificatie en aantoonbare besparing.

De relevante prijsankers zijn:

- engineeringtijd voor setup, herhaalde full-device solves en rapportering;
- vertraging bij redesign of first-pass failure;
- bestaande uitgaven aan hoogwaardige solverlicenties;
- bestaande kapitaalinvesteringen en supportkosten van DASY-systemen;
- het aantal toestelprogramma's dat één implementatie ondersteunt.

Solver- en laboratoriumprijzen tonen dat de sector budget heeft. De uiteindelijke prijs moet worden gedragen door gemeten klantwaarde en een geïdentificeerde budgeteigenaar.

### Direct specialistisch niveau

Een directe jaaromzet van ongeveer EUR 0,7 tot 1,2 miljoen past bij:

- vier tot zes grote enterprise- of labcontracten;
- een beperkt aantal betaalde pre-compliance projecten;
- implementatie, kwalificatie en jaarlijkse support;
- een kleine wereldwijde populatie van technisch passende klanten.

Dit vormt de geloofwaardige zelfstandige basis.

### Niveau met distributie

Een jaaromzet van ongeveer EUR 2 tot 3 miljoen vereist boven op de directe omzet:

- één embedded solver- of platformpartner;
- twee tot vier laboratoria die projecten aanbrengen;
- usage-, royalty- of revenue-share-inkomsten;
- een gevalideerde workflow die zonder intensieve founderinzet kan worden uitgerold.

### Breakoutniveau

Een omzet boven EUR 5 miljoen vereist een brede platformintegratie, een internationaal labnetwerk, opname in een chipset- of OEM-standaardworkflow, of een strategische overname. Dit is schaalpotentieel, geen directe verkoopprognose.

## 14. Validatieprogramma

### Technische gate

Drie matched scenariofamilies:

1. een radiative of far-field situatie ruim binnen het theoretische domein;
2. een toestel op middelgrote afstand;
3. een moeilijke FR2-situatie rond 2 mm.

Voor ieder scenario:

- vooraf vastgezette AEGIS-voorspelling;
- gekwalificeerde GOLIAT/Sim4Life-referentie;
- absolute en relatieve APD-fout;
- hotspotlocatie en rangorde;
- top-\(k\)-recall;
- expliciete detectie van domeinfalen;
- onzekerheidsmarge en false-clearance test.

### Workflowgate

- aantal onderzochte designvarianten;
- aantal vereiste full-wave ankers;
- aantal vermeden solverruns;
- end-to-end wall time;
- menselijke setup- en rapporttijd;
- reproduceerbaarheid op een tweede machine of bij een externe partij.

### Commerciële gate

- één pilot met een testlaboratorium;
- één pilot met een OEM, chipset- of solverpartij;
- minstens één betaalde pilot of evaluation agreement;
- prijsinterview met de werkelijke budgeteigenaar;
- beslissing tussen direct product, labkanaal, embedded route of stopzetting.

## 15. Proportionaliteit van het IOF-project

De IOF-investering bedraagt EUR 250.000 over twee jaar. Zij financiert geen algemene zoektocht naar nieuwe EM-toepassingen, maar een afgebakende technische en commerciële beslissing:

- AEGIS kwalificeren als screeninglaag binnen een expliciet domein;
- GOLIAT productiseren als reproduceerbare full-wave workflow;
- de reductie in full-wave workload en doorlooptijd meten;
- pilots uitvoeren met partijen die reeds een exposurebudget hebben;
- de directe, labgebaseerde en embedded route vergelijken;
- stoppen of vernauwen wanneer ranking, onzekerheid of willingness to pay onvoldoende blijkt.

Een specialistische business rond EUR 1 miljoen jaarlijkse omzet, een embedded licentie of een strategische overdracht kan de investering reeds verantwoorden. Meerdere miljoenen omzet vormen de mogelijke schaaluitkomst via distributie.

## 16. Investeringsconclusie

De sterkste commerciële vorm van AEGIS is een multi-fidelity exposure-workflow:

- dosimetrie als duidelijk afgebakende markt;
- GOLIAT als bestaande full-wave basis;
- AEGIS als snelle accelerator binnen een bewezen domein;
- finale verificatie met geaccepteerde FDTD/FEM of meting;
- FCC-data als concreet bewijs van workload, spelers en workflows;
- ongeveer EUR 1 miljoen als geloofwaardige directe specialistische basis;
- EUR 2 tot 3 miljoen bij succesvolle distributie;
- meer dan EUR 5 miljoen uitsluitend als partnergedreven breakout.

Het IOF-project moet aantonen hoeveel full-wave werk deze combinatie werkelijk vermijdt en welke partij voor die besparing wil betalen.

## Bronnen en werkbestanden

- FCC-studie: `/home/user/fcc6ghz/REPORT.md`
- FCC-corpus: `/home/user/fcc6ghz/data/meta/corpus_filings.jsonl`
- FCC-pilot: `/home/user/fcc6ghz/data/meta/pilot_extractions.parquet`
- prospects: `/home/user/fcc6ghz/prospects.csv`
- GOLIAT-documentatie: `https://docs.goliat.waves-ugent.be/`
- GOLIAT lokaal: `/home/user/goliat/`
- SoftwareX-notities: `/home/user/aegis/papers/softwarex.md`
- AEGIS near-field kernel: `/home/user/aegis/src/aegis/nearfield/phone.py`
- AEGIS-theorie: `/home/user/aegis/theory/monograph_v2.tex`
- matched FDTD-plan: `/home/user/aegis/validation/fdtd_validation_plan.md`
- Samsung HFSS-rapport: `https://fcc.report/FCC-ID/A3LSMS921U/6902432.pdf`
- Samsung finaal PD-rapport: `https://fcc.report/FCC-ID/A3LSMS921U/6959656.pdf`
- FCC 26-28: `https://docs.fcc.gov/public/attachments/FCC-26-28A1.pdf`
- IEEE P63195-4: `https://standards.ieee.org/ieee/63195-4/11782/`
- ISED RSS-102.IPD.SIM: `https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/rss-102ipdsim-simulation-procedure-assessing-incident-power-density-ipd-compliance-accordance-rss`
- SPEAG DASY8 mmWave: `https://speag.swiss/products/dasy8/m-mmwave`
- Sim4Life V9 pluginframework: `https://forum.zmt.swiss/topic/720/sim4life-v9.0-release`
- Ansys RF Advisor: `https://www.ansys.com/campaigns/rf-advisor`
