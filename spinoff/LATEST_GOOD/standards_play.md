# The standards play: IEC, IEEE, ITU-R, and why it's more urgent than any customer

*Claude Opus, April 2026. Explainer of the standards landscape for EMF exposure assessment, why getting AEGIS cited is structurally more valuable than any single commercial customer, who's on the committees, what the 2026 window specifically looks like, and the concrete 60-day action plan.*

---

## The standards that matter

There are four interlocking documents that decide what "acceptable" means for EMF exposure assessment. Learn these four names and you understand the field.

**[IEC 62232:2025](https://webstore.iec.ch/en/publication/89073) — base stations, 110 MHz–300 GHz.** Just published (4th edition, September 2025). Covers product compliance, installation compliance, and in-situ assessment. This is *the* standard for base-station EMF compliance globally. Explicitly updated for time-varying beam-steering (massive MIMO / 5G NR) which is exactly AEGIS territory. Developed by [IEC TC 106](https://www.iec.ch/dyn/www/f?p=103:7:0::::FSP_ORG_ID,FSP_LANG_ID:1303,25). Next edition likely 2027-2028.

**[IEC/IEEE 63195-2:2022](https://webstore.iec.ch/en/publication/62754) — devices, 6–300 GHz, computational procedure.** This is the one that matters most for AEGIS. It specifies how you *compute* absorbed power density for a device near the body (up to 200 mm). Current version permits FDTD and FEM. **The [2026 edition is in draft](https://standards.ieee.org/ieee/63195-2/7717/) right now.** This is the specific open window. Parallel document 63195-1 covers measurement procedures (DASY-world).

**[ITU-R Report SM.2452-1 (July 2022)](https://www.itu.int/pub/R-REP-SM.2452) — 5G EMF measurement methodology.** ITU-R reports aren't hard standards but they're globally referenced by national regulators who don't want to write their own methodology from scratch. It covers 5G NR specifics: TDD, SS/PBCH, beamforming, small cells. Every national spectrum authority cites this. [ATDI contributed to it](https://atdi.com/emf-exposure/), which tells you who plays this game.

**[IEEE C95.3-2021](https://sagroups.ieee.org/ices/standards/) — "Recommended Practice for Measurements and Computations."** The US-centric sister to IEC 62232 / 63195. Blessed computational practices for 0 Hz to 300 GHz. Maintained by [IEEE ICES](https://www.ices-emfsafety.org/), specifically SC4 (Safety Levels and Human Exposure), currently chaired by Bailey & Lapin. IEEE C95.1-2019 is the sister "safety levels" standard (the IEEE parallel to ICNIRP 2020).

---

## Why "getting cited" in these is worth more than any single customer

The Niels Kuster playbook, compressed:

1. **Publish foundational research.** Credibility and citations.
2. **Get the method named in the standard.** Every lab, regulator, and OEM now has a reason to own a tool that implements it.
3. **Ship the tool that implements it.** Your company becomes the de-facto reference.
4. **Own the tissue data, the measurement hardware, the anatomical phantoms.** Ecosystem lock.

Kuster did this over 20 years with IT'IS (tissue data), SPEAG (DASY measurement hardware), and ZMT (Sim4Life software). The IT'IS Gabriel/Hasgall tissue database is cited by name in IEC 62704 and IEC 63195-2 as the reference dielectric dataset for simulations. Every FDTD tool in the field reads IT'IS data. That's not a coincidence, that's 20 years of standards work.

The AEGIS-compressed version: get the closed-form geometric method listed in IEC/IEEE 63195-2 (2026 edition) as **an acceptable fast computational method for APD pre-compliance** alongside FDTD and FEM, with matched validation evidence. Once it's in the standard:

- Test labs can quote "AEGIS-based pre-compliance per IEC/IEEE 63195-2 section X" to OEM customers.
- Regulators can accept reports based on it.
- ZMT has a reason to integrate it into Sim4Life.
- The monograph becomes the citation in every subsequent paper in the field.

---

## Who's actually on these committees

The political reality:

**IEC TC 106.** Chaired by Mike Wood (ex-Telstra, now consultant). Membership mixes mobile operators (Orange, Telefonica, KDDI), OEMs (Ericsson, Nokia, Samsung, Huawei, Apple, Qualcomm), test labs (TÜV, UL, SPEAG-affiliated), academia (ETH Zurich / IT'IS people around Kuster, UGent INTEC-WAVES via Wout, NIST, AIST Japan, KTH, Chalmers, Telecom Paris), and national regulators (BNetzA, ARCEP, BIPT, Ofcom, FCC, ANFR). Belgium has a mirror committee under NBN where national positions are coordinated.

**IEEE ICES SC4.** Chaired by Dr. William Bailey and Dr. Gregory Lapin. US-heavy but internationally attended. Runs parallel to IEC TC 106. Many people sit on both.

**Working groups inside TC 106.** Different WGs handle measurement (DASY-world), computation (FDTD-world), and exposure assessment methodology. IEC/IEEE 63195-2 sits in the joint IEC TC 106 / IEEE ICES working group. Wout is a known contributor in this space.

**The politics.** ZMT/SPEAG/IT'IS people will not be enthusiastic about a new computational method entering their standard. That's why the pitch to the committee has to be "AEGIS is a *fast pre-screening* method that complements FDTD, not a replacement." Same message as for the ZMT commercial conversation. Done well, you get Kuster's people on your side because it makes their tools more valuable (more pre-screens → more rigorous FDTD runs on worst cases). Done badly, you have the incumbent lobbying against you during the review vote.

---

## What Wout's position actually buys

Concrete mechanics:

1. **Wout can table a contribution** to the IEC/IEEE 63195-2 2026 working group proposing closed-form computational methods as an accepted approach for fast pre-compliance. This is a written document with proposed standard text, a technical justification, and matched validation evidence. It goes to the working group, gets reviewed, amended, voted on.
2. **Belgium, via BIPT, can submit contributions to ITU-R WP 5A/5C** (the working parties behind ITU-R SM.2452 and follow-ons). ITU-R is more permissive than IEC; sector members can submit directly.
3. **Wout can nominate Robin as an expert member** of the relevant national mirror committee (NBN). That gets Robin into the room.
4. **Wout co-authors standards-adjacent papers** (IEEE TEMC, PMB, Bioelectromagnetics). These are the papers working group members actually cite when they draft standard text.

---

## The time pressure

Standards go through stages:

NP (New Proposal) → WD (Working Draft) → CD (Committee Draft) → CDV (Committee Draft for Voting) → FDIS (Final Draft International Standard) → published standard.

Once a document passes CDV, substantive new content is very hard to introduce without pushing to the next edition (which is years out).

IEC/IEEE 63195-2 2026 edition is already at draft stage, meaning probably CD or CDV right now. Realistic window to get new computational content in: **3-6 months from today**, and only if Wout tables the contribution soon. Past that, the next opportunity is a 2028-2029 amendment or the edition after.

IEC 62232:2025 just went final this year. Window for that is 2027+ (5th edition).

ITU-R reports are easier: WP 5A/5C meets annually and can absorb new contributions more flexibly. ITU-R SM.2452-2 is probably in draft now.

---

## The 5G-PPP whitepaper angle

Sort of a back door into European standards influence. [5G-PPP Beyond 5G/6G EMF Considerations (2023)](https://5g-ppp.eu/wp-content/uploads/2023/07/EMF-TF-white-paper_v1.2__.pdf) is an EU-funded position paper that identifies gaps. Its working group is a who's-who of European EMF researchers, and the successor document (likely a 6G-IA EMF TF or a Horizon Europe SNS project deliverable) is the venue where EU-funded research gets recognized before it filters into IEC text. Getting AEGIS cited in the next iteration is lower-stakes and higher-probability than getting it into IEC on first try.

---

## The actions to take in the next 60 days

1. **Wout emails the IEC/IEEE 63195-2 2026 working group secretary** to ask the current draft stage and whether computational-method additions are still in scope. Tone: collegial, "I have a student with a fast computational APD method, want to understand the right process to propose it."
2. **Produce the one piece of evidence that makes the contribution stick.** Matched AEGIS-vs-Sim4Life validation on a standard IEC 63195-2 reference scenario (a defined phone + Duke/Ella phantom + 28 GHz + specific antenna pattern). Report the error bound and runtime. GOLIAT can drive the Sim4Life side. 2-4 weeks of focused work.
3. **Submit a short paper to IEEE EMC Symposium 2026 or BioEM 2027** describing the method + validation. Once Sim4Life-matched numbers exist in a peer-reviewed venue, they become citable in the standards contribution.
4. **Wout nominates Robin to the NBN mirror committee** for TC 106. Gets him into the room.
5. **Separately, draft a BIPT-routed ITU-R contribution** using the base-station capability (real pattern data, real 3D environments, fast compliance computation). ITU-R is the easier early win.
6. **Schedule a call with one friendly ZMT/Sim4Life person** (through Wout's IT'IS/Kuster orbit) to float the idea of a joint standards contribution. If they're on board, committee politics get 10x easier. If they're cool on it, you learn that early.

---

## Why this is genuinely urgent

Most of the "do this now" items in the roadmap can slip a quarter without consequence. This one cannot.

If the 63195-2 2026 draft closes at CDV without AEGIS-class methods mentioned, Robin waits 3-5 years for the next edition, during which (a) someone else's method might get cited instead, or (b) LLM-assisted competitors publish the same method and claim priority in the standards discussion.

The absolute-novelty window on the **patent** side is August 2026. The absolute-novelty window on the **standards** side is honestly now.

---

## Links to bookmark

- [IEC TC 106 dashboard](https://www.iec.ch/dyn/www/f?p=103:7:0::::FSP_ORG_ID,FSP_LANG_ID:1303,25) — committee scope, structure, publications
- [IEC 62232:2025 overview](https://www.iec.ch/blog/iec-approves-new-5g-emf-exposure-assessment-methods-standard-base-stations) — plain-English blog post
- [IEC/IEEE 63195-2:2022 scope page](https://webstore.iec.ch/en/publication/62754) — the device computational standard
- [IEEE P63195-2 2026 draft record](https://standards.ieee.org/ieee/63195-2/7717/) — the draft being prepared
- [ITU-R SM.2452-1 download (PDF)](https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-SM.2452-1-2022-PDF-E.pdf) — the 5G measurement methodology report
- [IEEE ICES TC95 subcommittee list](https://www.ices-emfsafety.org/committees/tc95-subcommittees/) — who runs what
- [Free access to IEEE C95 standards](https://beyondstandards.ieee.org/c95get/) — download C95.1-2019 and C95.3-2021 without paying
- [5G-PPP Beyond 5G/6G EMF Considerations whitepaper](https://5g-ppp.eu/wp-content/uploads/2023/07/EMF-TF-white-paper_v1.2__.pdf) — EU position paper with gap analysis
- [IT'IS Foundation tissue database](https://itis.swiss/virtual-population/tissue-properties/) — the tissue dielectric reference every standard cites
- [IEC e-tech feature on TC 106](https://etech.iec.ch/issue/2022-05/safety-empowers-sustainability) — readable context piece
- [ATDI on their ITU-R EMF contribution](https://atdi.com/emf-exposure/) — example of a commercial player playing this game

---

## TL;DR

IEC 62232:2025 was just published. IEC/IEEE 63195-2 2026 is in draft right now. Both explicitly permit computational methods. Wout sits on these committees, a rare non-transferable asset. Getting AEGIS named as an acceptable computational method for fast APD pre-compliance in the 2026 edition is a 3-6 month window, and it is worth more than any individual customer because every test lab, regulator, and OEM downstream has to align to the standard. The mechanical steps are small (one matched validation, one written contribution, one friendly conversation with ZMT). The window is narrow.
