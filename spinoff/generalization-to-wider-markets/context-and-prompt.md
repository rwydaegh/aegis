So, we have aegis here. Big repo, lots of features. We're trying to spin-off with IOF, a type of postdoc at UGent, for which im talking to Tech Transfer with Filip Louagie (business dev) and Alessandro (patent middleman).

I have submitted an IDF, of when the whole thing was somewhat in its early days, but is broadly accurate. Then, I have written a TAP paper draft of it. I am also working on a TWC paper of it, baasically done.
spinoff/patent/IDF/IDF_geometric_dosimetry.md
papers/coherent-exposure-operator/build/main.tex
papers/TAP_paper/paper.tex

Alessandro gave me back the patent claims draft. spinoff/patent/32471 claims and advantages v1.docx (convert to md pls)

Tbh, there is blatant error with it and big problems (you will notice immediately, i think), but Alessandro has a huge ego and basically already thinks it's perfect lmao.
I frankly dont care (seriously, trust me) but I pretend to care since it helps my IOF application. Anyways. I'd publish anyways. Besides the point.
-- Drafty email
Dear Alessandro,

I have carefully reviewed yesterday and the day before all the claims in the draft document, taking into account your guidance on how to read them.

I have found no significant issues with these at all regarding any matters on the technical aspects. Occasionally I would find myself wondering why certain things were done in a particular way (for example, those I mentioned in our meeting), but in hindsight always realize that in the 'patent-lingo', it is entirely justified to write it in that manner. Perhaps one minor point: "asd" is written in the patent draft. My guess is that this ...

In conclusion, I am very satisfied with it if we were to stick to the current scope (dosimetry).

Naturally, as discussed with Filip, the patent draft requires some changes if it were to generalize to applications in radar engineering and microchip design. I can offer the following technical points, and some suggestions that may or may not make sense in the patent.

Kind regards
Robin
--

SO I had the famous intake convo with Filip. Email to wout after intake (lowkey a summary):
--
Al bij al ging het wel goed, ik mag indienen. Het grootste probleem was dat ik teveel soorten klanten voorstelde (onvoldoende focus), en dat de monopolie van ZMT slechts een opbrengst had van $M 2.3 per jaar. 

De markt voor operatoren, RAN providers (Ericsson, Nokia,...) is veel groter om in te groeien. Overheden werden afgeraden omdat onvoorspelbaar. Bedrijven in near-field pre-compliance betalen het meest, maar is risicovoller omdat je dan zeker in de standaard moet geraken.

Hierover en nog zaken wilt Filip een meeting hebben deze week voor hij op verlof gaat. Ik mail hem sowieso al hiervoor. 
--
if you wanna see the slides, they are in spinoff/IOF/AEGIS_Intake_Meeting_IOF_v2, honestly quite worth a look. in particular spinoff/IOF/AEGIS_Intake_Meeting_IOF_v2/Slide9.JPG
spinoff/IOF/AEGIS_Intake_Meeting_IOF_v2/Slide10.JPG
spinoff/IOF/AEGIS_Intake_Meeting_IOF_v2/Slide17.JPG
other useful slides are in presentations/, including those of briefing people (Filip, Alessandro) for the patent

Conclusion of the SECOND meeting after intake, much more import:

-we were just mulling over things and by the end Filip was like 'omg cant u generalize' and im like uhhh i guess.
-"like radar and perhaps microchips and stuff"
-filip was like bro, its about the meeeethod dude. That it's so much faster, and differentiable, that's a moat that we can use in a bigger market... 
- we put the patent on hold for 1 week, i decide the technical feasibility, and then, we make a decision to either generalize or keep it to what we have

So now I have to "explore to what extent we can generalize the patent and the IOF itself to a broader market" in order to **license it to big EDA players like Keysight Ansys COMSOL etc**

Claude, im sorry for this big context dump, do write this to md somewhere, but let's now get to focussing. No patent yet or other stuff, but I wanna then try to work on physics only. So frankly, your home here is theory/ 

You'll find the humongeous monograph tex file, which can be useful if you wanna dig into some concepts, but also the TAP and TWC papers in general are nice. You'll notice that ive flirted already with the idea of radar, at least a bit.

I need you to get the creative juices flowing to the max in all directions, especially those where you can find a business case, and where some patch work, small OR large, can be created from my theory and software to be bigger and better.

It would be really impressive if you find OTHER usecases besides radar or chips ya know. 

Oh and BTW I am havin a meeting with Tom D'haene (sumolab, ugent) soon, feel free to look that guy up. Filip recommended him, in-house guy, prof, but also a startup kinda guy, that we wanna meet with and discuss this exact thing for. See this email:
--
Dag Tom,

Ik bereid samen met mijn promotor Wout Joseph een IOF StarTT voor. Deze ging initieel uitsluitend over de dosimetrie van RF-EMF straling op mensen. Na het intake gesprek en een follow-up, stelde @Filip voor om te onderzoeken of dat de methode een breder toepassingsgebied zou kunnen hebben dan de niche die dosimetrie is, en om jou hiervoor te contacteren gezien je expertise hierin. Hierdoor zouden we een sterkere case kunnen maken m.b.t. de valorizatie.

In parallel is Alessandro bezig geweest met het draften van een patent dat we zonet 1 week op hold zetten, tot als de onderliggende business case zeker is. Idealiter spreken we dus binnen de week af, zodat we bij een negatief advies van de meeting ook nog ons initieel plan kunnen behouden om in te dienen tegen 24 juli. Bij een positief advies dienen we in bij de september-call (9 oktober) en zouden we LoI's vragen van grote EDA spelers vragen wanneer een (verbreed) patent gefiled zou zijn.

In bijlage staat heel wat referentiewerk die je vrijblijvend kunt lezen maar vrij groot is. De details van de methode zal ik presenteren op de meeting. In het kort:
Ik beschouw een menselijk lichaam dat toevallig 
Elektrisch groot is t.o.v. de golflengte 
Op elk punt bestaat uit één enkel of een laagstructuur aan dielektrica met hoge effectieve refractieindex ñ 
Glad genoeg is dat features en curvature kleiner dan de golflengte een minimale rol spelen
Op basis van de Fresnel coëfficienten bereken ik de absorptie op elk punt
Het geheel is differentieerbaar met respect tot alle input parameters zoals antennespecificaties of precoding schemas.
In de loop van deze week bekijk ik ook welke applicaties toepasbaar zijn, i.h.b. radar applicaties bij vliegtuigen.

Zou je (min.) een drie-/viertal momenten kunnen voorstellen dat je vrij bent volgende week? Zo kunnen agendas samengelegd worden.

Met vriendelijke groetjes,

Robin
--


Claude, in your response be scrupulous in exactly what files (or parts of) you have read. Do read a good bit, but be intelligent about it. Feel free to grep around for context that I would have missed (although a lot in spinoffs/ could be stale/brainstormy, feel free to pop quick questions if confused)