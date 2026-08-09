# ZMT endgame and the barbell

Written 2026-08-09, after a full read of spinoff/, the custorix dossier, career.txt, plus fresh web research on ZMT. The question asked: patent lands in a few months, then a big meeting with ZMT, work there as an employee, integrate AEGIS as a Sim4Life module proven against FDTD, salary plus royalties. Cooking or not?

Verdict: right destination, wrong vehicle. The ZMT-as-counterparty direction is the most repeated conclusion in this whole folder (honest_analysis wanted the ZMT partnership as the primary path, decisions.txt already contained "acqui-hire to ZMT", Wout suggested it, Ericsson said "drop-in replacement" and "it has to be in the standard"). The employee-plus-personal-royalties shape breaks on facts listed below. The fix keeps 90% of the plan and flips which side of the table Robin sits on.

## Why the employee-plus-royalty shape breaks

1. The IP is UGent's, automatically, from the moment of invention (Codex Hoger Onderwijs Art. II.285). The IDF notified them of property they already held. Nobody can "give the patent back" on request. The paths are license (Fast Lane or negotiated), purchase, or reversion if UGent formally declines to protect. Reversion is standard TTO practice elsewhere but unverified as written UGent policy. Ask Alessandro, it is the BATNA and nobody has stated it.
2. Swiss law: Art. 332 CO assigns employee inventions to the employer with no extra compensation. Employers paying royalties to their own employees is rare everywhere because it creates a permanent conflict of interest over the roadmap.
3. Z43 already has a template for outside IP and it is not an employment contract. TI Solutions AG: patent owned by MIT, developed jointly with IT'IS, commercialised through a separate company on the campus.
4. Money arithmetic. ZMT is ~15 people doing ~$2.3M ARR after twenty years (scraped estimate, treat with care). Royalties on a module inside that cannot be "rich". The rich outcome per honest_analysis is the 35% modest exit at 3-10M, most likely to ZMT, reached by owning the thing they buy.

The legal version of the original idea does exist: ZMT pays UGent license fees, Robin receives the inventor share of that income, ZMT pays salary separately. That is deal shape A below, the floor, not the plan.

## Ownership and money mechanics, verified

- Inventor share: the UGent valorisatiereglement gives 25% of net valorisation income to the researchers. Source: Schamper 19/12/2017, quoting the reglement. A 30/50/20 split (inventors/lab/TTO) circulated from a now-dead ASTP page and is unverified. The exact current number lives in the internal reglement (RvB 30 March 2012, as amended) on the intranet.
- AOSR AUGent 2020, art. 9, read from the PDF: valorisation income includes license income, sale, and proceeds from shares acquired in valorisation (9.03, so plausibly the Fast Lane equity on exit). Net means after all patent and maintenance costs (9.02, 9.04). The personal share is paid directly to the researchers (9.05). Named inventors must receive a share pro rata inventive contribution (9.07). Payout is blocked until the inventors sign a written mutual split agreement (9.08), for AEGIS that is the ~99/1 with Wout, trivial but mandatory.
- Fast Lane: two template contracts at incorporation. License: exclusive, UGent stays owner at least 5 years, terminates if the company dies, royalty on revenue (the interviewed founder paid 0.5% in the no-patent tier, the with-patent tier is higher, get the number). Shareholder agreement: ~6% UGent equity, non-dilutive up to a ceiling, no board seat, UGent may sell at 1 euro any time. imec.istart stacks another 6% and requires immediate incorporation, which conflicts with IOF.
- The royalty loop: the BV royalty paid to UGent is itself valorisation income there, and ~25% of the net comes back to the inventor personally. Effective leakage is tiny. At 300k/yr BV revenue the royalty is 1.5-9k/yr, a hosting fee for an exclusive worldwide license.
- The real Fast Lane costs to read in the term sheet: the 6% equity in exit scenarios (300k on a 5M exit), diligence and milestone obligations, and the field-of-use definition. The license field must cover whatever ZMT would ship.

## The deal menu

| | Structure | Income | Ceiling | Kills other options |
|---|---|---|---|---|
| A | ZMT employs Robin, UGent licenses ZMT directly | CHF 110-135k plus inventor share of UGent net license income | Comfortable, capped | Yes, kills B, C, D |
| B | BV holds Fast Lane license, ZMT is customer and channel | NRE fee plus per-seat revenue share plus consulting. 150-300k/yr one-man BV plausible per the folder's own pricing (OEM licence 80k/yr plus royalty) | Exit preserved, 35% at 3-10M per honest_analysis | No, A stays available forever |
| C | TI Solutions template, joint newco with Z43 equity | Salary from newco plus real equity | Highest | Usually reached through B |
| D | Early acquisition | One-time | Small now, unproven. 3-10M only after standards plus validation | Ends the game early |
| E | Salaried science bridge: UGent postdoc via IOF StarTT or VLAIO innovation mandate. Variants: ZMT-sponsored bilateral research agreement at UGent, IT'IS visiting scientist (read the visitor IP terms) | UGent salary | This is the runway, not the deal | No |

The decision rule is asymmetry, not preference. A taken now destroys B, C and D (improvements assign to ZMT, the negotiating counterpart becomes the boss, UGent's licensing officer stops fighting). B taken now preserves A completely, a company that wants the module can always still hire the author. A is a fine floor and the last door to walk through.

## ZMT, outside view (web, Aug 2026)

- Sim4Life V9.0 (June 2025) shipped an open plugin framework for third-party solvers. The showcase examples are FEniCS and NVIDIA Sionna RT. The socket for an AEGIS module exists, and the first question in any meeting will be "why not Sionna". Answer: Sionna gives fields, AEGIS gives dose on bodies.
- V9.2 added the broadband skin model (Christ 2025, 10-110 GHz) for APD compliance. All of it FDTD, single device, one body. No scene-scale product.
- The 2026 roadmap (V9.4, V9.6, V10.0) is neurostimulation, thermal, AI-assisted workflows. Wireless looks like a maintained cash line, not the growth story.
- Kuster is 69 and listed as President of the Board and interim CEO. A founder-chairman holding the CEO seat on an interim basis is a leadership gap signal, and companies in that phase buy things that slot in.
- Entry points per the outreach dossier: Esra Neufeld (CSO), Sven Kühn (Product Safety). Wout's routing note: talk to Sven in the spin-off context.
- Belgium-resident telework for a Swiss employer is legal up to 49.9% under the CH-EU framework with an A1 opt-in. Full remote needs an EOR or a Belgian entity.

## Most likely outcome, honestly

Nobody in this folder knows ZMT's appetite because the relationship has never been opened. Best honest read: the most likely single outcome of a first approach is polite scientific interest followed by slowness. Roughly half odds of no money on a 12-month horizon, maybe a third that the arc matures into the license-then-exit at 3-10M, decent unknown odds they would simply hire on request. The plans on the table do not differ in who predicts ZMT correctly. They differ in how expensive it is to be wrong.

What converts maybe into yes is not the pitch, it is external pull: the Ericsson full-day demo (invited, after summer) and a 63195 standards presence. The standards play is the lever on ZMT, not a side quest. The entry ticket is still missing: the matched AEGIS-vs-Sim4Life validation on a 63195-2 scenario, 2-4 weeks with GOLIAT driving the Sim4Life side. And per company_outreach_and_ndas, a cold commercial approach is the one move that can sour the most valuable relationship. First contact is science.

## The barbell

1. This week: questions to Alessandro. Current inventor share percentage and whether equity proceeds count. Reversion if UGent does not file. Fast Lane with-patent royalty tier. OER Art. 27 par. 4 (NDA the thesis jury) plus Art. 30 par. 8 (repository embargo), which moves the disclosure wall from the August submission to the ~November public defense and was never invoked. The actual critical path to priority filing. Resolved 2026-08-09: the "20-60 page document" is the patent specification, the full description with figures, embodiments and fallback language that the external patent attorney writes around the claims. This is normal, the claims are always a fraction of the application. The 5-12 week figure in patent_decision_and_defense_mechanics is exactly this drafting. Mitigations: the enabling disclosure largely exists already (the monograph, the 18-page IDF, the claims doc, flowchart.png), so the attorney mines rather than invents. And the priority text does not need to be perfect, the PCT at month 12 is the rewrite opportunity, it only needs to enable everything that will later be claimed, since no matter can be added after filing (Art. 123(2) EPC).
2. Thursday 14 Aug, Custorix: execute the negotiation brief. Founding-partner equity (target 3%, anchor 5%), the AEGIS IP carve-out in writing as the walk-away line, the 4/5 contract with one day for UGent and AEGIS, the UGent work package in the consortium text. A one-year Custorix commitment is compatible with the ZMT license arc and incompatible with ZMT employment.
3. 17 Aug, Filip returns: file at dosimetry scope. See the email skeleton below.
4. Autumn: thesis, defense, the validation artefact on the AEGIS day, the Ericsson demo, then the first Neufeld/Kühn contact as science.
5. Q1-Q2 2027, with the defense done, the patent filed, Custorix paying, and ZMT's temperature known: pick the vehicle. BV plus Fast Lane if there is commercial pull from ZMT or Ericsson. The ZMT job as the comfortable floor if tired. Incorporate the BV the month there is something to put in it. A BV takes days and is never the bottleneck. The scarce assets are the filed patent, the validation artefact, the warm relationship, and salary runway.

## The Filip email, post-retraction version

The Valtorix LOI argument from the custorix negotiation brief is retracted (2026-08-09). Valtorix sells lens reflector hardware for RCS calibration and enhancement. They do not buy simulation, and the feasibility sweep had already killed RCS certification as an AEGIS market (explore-not-certify wall plus ITAR). An LOI from them would be a favour dressed as evidence and Filip would probe it in one question.

The email is stronger without it: I tried to find the generalisation story you asked for. I ran it hard, thirteen feasibility reports, a differentiability study, a military study. It is not there, nothing came back a strong bet. Meanwhile the dosimetry side produced real pull: an Ericsson team asking for a full-day demo, drafted support letters from CNR-IEIIT and Verkotan, a live window in 63195-2. I am reversing my own July hold recommendation. File at dosimetry scope now, keep one genericised independent claim so the door stays open, and let the evidence decide the rest. Plus the Art. 27 par. 4 ask and an IOF status check (was the 3 Aug submission made, or is 19 Sep the live call).

One honest scrap survives from Custorix: they said dosimetry becomes relevant to them for certification in a few years, and a shoulder-fired HPM emitter puts an operator in the reactive near field with EU 2013/35 obligations. A short Custorix letter expressing interest in exposure assessment supports the dosimetry story truthfully. Low priority, trade nothing real for it.

## Who the patent is really for (2026-08-10 musing)

Robin's actual attitude: loves open source, wants to publish, shrugs at the patent, tolerates it because it dresses up the IOF file, wants it quick. The claims have known defects (independent claim anchored on "surface integration reduces dimensionality", which is near-anticipated, with the real novelty demoted to dependents). The observation: a patent is worth more to ZMT, who can afford to defend it and file worldwide, than to Robin, who never will. So should ZMT co-draft it?

The endgame is right, the timing is the trap.

- Never involve ZMT before the priority filing. Pre-filing disclosure of the mechanism, even under NDA, means that if they pass they walk away knowing exactly how it works, in the solver domain where they are the world experts. And anyone who contributes to the claims becomes a co-inventor, which converts a wholly-owned asset into a joint one. The leverage structure assumes filed first, talk second.
- The legitimate version of "ZMT carries the patent" is sequenced and standard: file the cheap priority now (UGent pays). During the 12-month priority year, an interested licensee takes over prosecution costs and directs claim strategy as part of a license or option deal. The month-12 PCT is the rewrite where the known claim defects get fixed, by attorneys paid by the party who actually cares about scope. UGent's default is to drop at national phase absent a commercial commitment, and a ZMT deal is exactly that commitment. So ZMT ends up drafting and funding the worldwide family after all, just one year later and on the right side of the table.
- Concrete instrument: an option agreement. UGent grants ZMT a 6-12 month option on an exclusive license, ZMT pays an option fee and the patent costs during evaluation. Common TTO structure, and it converts the patent from Robin's chore into ZMT's expense at the earliest legitimate moment.
- The publish-everything appetite is compatible with all of this, with one asymmetry to know: after the priority filing, publish freely, the filed claims are safe (Wout already proposed submitting TAP and TWC immediately after filing). But everything published becomes prior art against any FUTURE filing. The pandora's box of follow-on research means this one filing is probably the only patent there will ever be, which raises, not lowers, the value of getting its text right at the PCT stage.
- Robin's detachment is a negotiating asset. No emotional attachment to prosecution control means it can be traded away for money without pain. The thing to never trade is ownership before the deal exists.

### The option agreement, and who holds it

The option is the right-sized first commercial step with ZMT: for them it is cheap exclusivity (a modest option fee plus the patent costs while they evaluate, typically a fraction of a license), for us it converts interest into money, covers the PCT, and puts a deadline on their decision. It is a second-conversation instrument. The first conversation stays scientific.

The fork nobody should miss: the option can be granted by UGent or by the BV, and that choice sets Robin's cut.

- UGent grants ZMT the option directly: Robin receives the inventor share of the net income, ~25%.
- The BV takes the Fast Lane license first, then the BV grants ZMT the option or sublicense: the BV (Robin at ~94% after UGent's 6%) captures nearly everything, minus the Fast Lane royalty, of which ~25% of UGent's net comes back anyway.

An exclusive option to ZMT and a Fast Lane license to the BV compete for the same exclusivity, so sequencing is everything. If ZMT interest materialises, that is precisely the trigger to incorporate and take the Fast Lane license BEFORE anything is granted to ZMT. Serious ZMT option interest = incorporate now.

Two actions that follow today: tell Filip and Alessandro that the intended path is an option-to-license with an industrial partner during the priority year (TechTransfer's own default requires a commercial commitment before national phase, this is that commitment, and it makes the IOF valorisation story concrete). And when the Fast Lane term sheet is read, check the sublicensing clause: if the BV's license cannot sublicense, the BV cannot grant ZMT anything, and the whole upside-capture route dies on a boilerplate term.

Calendar fit: priority filed ~Oct-Nov 2026, PCT decision ~Oct-Nov 2027. Scientific contact autumn 2026, validation plus Ericsson demo through winter, commercial conversation spring 2027, option signed by summer, ZMT's attorneys direct the PCT rewrite before month 12. This matches the existing PCT criterion in the patent notes ("file only if ZMT conversation advancing, JSAC accepted, LOI, or VLAIO approved").
