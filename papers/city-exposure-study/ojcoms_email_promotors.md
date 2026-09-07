# Voorstel e-mail aan promotoren

Dag Wout en Emmeric,

Ik zou de paper over de tien steden liever indienen bij de special issue van IEEE OJ-COMS, *Orchestrating Computing, Communication, and Agentic AI for Human-Centric Wireless Systems*, dan bij IEEE Access:

https://www.comsoc.org/publications/journals/ieee-ojcoms/cfp/orchestrating-computing-communication-and-agentic-ai-human

Na mijn correspondentie met de Guest Editor en de EiC blijkt de deadline opnieuw met twee weken te zijn verlengd. Daardoor is er nog tijd om de framing, en eventueel een beperkt deel van de methode, op de special issue af te stemmen.

De inhoudelijke aansluiting zie ik voornamelijk op twee punten:

- **Human-centric wireless systems:** de propagatieberekening is receiver-centric en behoudt de invalshoeken van de straling tot op een anatomisch lichaamsmodel. De uiteindelijke grootheid is whole-body SAR langs voetgangersroutes, niet alleen ontvangen vermogen in de omgeving.
- **Multimodal sensor fusion for wireless perception:** de methode combineert 360°-straatbeelden, fotogrammetrische geometrie, AI-gebaseerde materiaal- en scènesegmentatie, ray tracing en anatomische dosimetrie tot één stedelijke RF-reconstructiepipeline.

De huidige pipeline gebruikt Mask2Former en SAM 3, maar is strikt genomen nog niet agentic. Ik onderzoek momenteel of we daar een beperkte SAM 3 Agent-uitbreiding van kunnen maken, waarbij een VLM zelfstandig RF-relevante objecten en materialen inventariseert, segmentatieprompts selecteert en de gevonden maskers controleert. Dat zou ik alleen als bijdrage opnemen als we het nog degelijk kunnen implementeren en evalueren.

De paper kan daarnaast worden gepositioneerd als een image-informed radio-environment component voor human-aware network planning en toekomstige digital twins. Ik zou echter geen claims maken rond remote health monitoring, semantic communications of real-time distributed digital twins, omdat die niet rechtstreeks door de huidige studie worden gedekt.

OJ-COMS is Q1 en heeft momenteel een Journal Impact Factor van 6,1 (5-year JIF 8,2). Zien jullie voldoende inhoudelijke aansluiting voor deze pivot?

Met vriendelijke groeten,

Robin

## Inhoudelijke notities

De volgende termen uit de call for papers zijn geen goede claims voor de huidige paper:

- **Remote health monitoring:** de studie berekent blootstelling, maar monitort geen gezondheid of patiënten op afstand.
- **Hyper-realistic and responsive environments:** dit verwijst hoofdzakelijk naar immersieve en real-time interactieve omgevingen.
- **Distributed Digital Twin Systems:** het huidige model is niet real-time, gedistribueerd of continu gesynchroniseerd. Het kan wel als bouwsteen voor een toekomstige RF digital twin worden omschreven.
- **Semantic and intent-aware communications:** semantische beeldsegmentatie is niet hetzelfde als semantic communications.

De kerninschatting is dat *human-centric wireless systems* en *multimodal sensor fusion for wireless perception* een natuurlijke en verdedigbare aansluiting vormen. Agentic AI is momenteel een mogelijke uitbreiding en nog geen bestaande bijdrage.

Bron voor de journalmetrics: https://www.comsoc.org/publications/journals/ieee-ojcoms
