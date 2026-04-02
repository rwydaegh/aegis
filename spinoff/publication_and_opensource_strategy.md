# AEGIS: publication, IP, and open-source strategy

**Author:** Claude (strategic analysis for Robin Wydaeghe)
**Date:** April 2, 2026
**Status:** Working document. Update as TechTransfer and patent counsel provide guidance.

---

## Table of contents

1. [The timing problem: patent before thesis](#1-the-timing-problem-patent-before-thesis)
2. [What to publish and where](#2-what-to-publish-and-where)
3. [What NOT to publish](#3-what-not-to-publish)
4. [Open-source licensing strategy](#4-open-source-licensing-strategy)
5. [The Kuster playbook applied to AEGIS](#5-the-kuster-playbook-applied-to-aegis)
6. [Concrete timeline](#6-concrete-timeline)
7. [Risk analysis](#7-risk-analysis)

---

## 1. The timing problem: patent before thesis

### The brutal fact

The EPO enforces **absolute novelty**. There is no general grace period for an inventor's own disclosures. If Robin's PhD thesis is published (made publicly available, including in UGent's institutional repository) before a patent application is filed, the thesis becomes prior art against the patent. The invention is dead for European patent purposes.

This is different from the US, which gives inventors a 12-month grace period after their own disclosure. Europe does not. Belgium's national patent law has a narrow 6-month exception only for disclosures at officially recognized international exhibitions or disclosures made in evident abuse by a third party. A PhD thesis defense is neither.

**An IDF is not a patent application.** The IDF filed on April 1, 2026, establishes nothing legally. It is an internal UGent document that notifies TechTransfer of the invention. It does not establish a priority date. It does not protect against subsequent disclosures. It is paper in a drawer.

### The required legal sequence

```
IDF (done, April 1)
    |
    v
Patent application filed (establishes PRIORITY DATE)
    |
    v
Thesis deposited / defense (public disclosure)
    |
    v
Publish freely (journal papers, conference papers, anything)
```

The priority date is the only date that matters. Everything published after the priority date cannot be used against the patent for novelty purposes. Everything published before the priority date can destroy the patent.

### What "patent application" means here

There are three options for establishing a priority date, in order of cost and effort:

| Option | Cost | Time to prepare | Priority date? | Notes |
|--------|------|-----------------|----------------|-------|
| **Belgian national patent application** | ~500-1,500 EUR (filing + search request) | 2-4 weeks with a patent attorney | Yes | Cheapest, fastest. No substantive examination in Belgium. Good for establishing priority. Can file PCT within 12 months. |
| **European patent application (EPO direct)** | ~5,000-10,000 EUR | 4-8 weeks | Yes | More expensive, unnecessary at this stage. |
| **PCT application** | ~3,000-5,000 EUR | 4-8 weeks | Yes (but usually claims priority from an earlier national filing) | Standard route for international coverage, but you need a priority date first. |

**Recommendation:** File a Belgian national patent application as fast as possible. This is the cheapest way to establish a priority date. UGent TechTransfer (Octrooien@UGent.be) should handle this through their patent attorneys. The Belgian system does not perform substantive examination, so the bar for filing is low. You need claims and a description, not a granted patent.

Once the Belgian application is filed, you have 12 months to file a PCT application for international coverage. The PhD thesis can be published any time after the Belgian filing date.

### How urgent is this?

**Extremely urgent.** The PhD defense is planned before August 2026. If TechTransfer takes its typical pace (weeks to months for assessments, attorney engagement, drafting), you could easily miss the window. The IDF already contains suggested patent claims (section 9). The monograph contains all the technical detail a patent attorney needs. The drafting work is 80% done.

**The critical dependency chain:**

| Step | Who | Realistic timeline |
|------|-----|--------------------|
| TechTransfer reviews IDF, decides to proceed | An Van den Broecke + patent committee | 2-6 weeks |
| Patent attorney engaged and briefed | Octrooien@UGent.be | 1-2 weeks |
| Claims drafted and filed (Belgian national) | Patent attorney + Robin review | 2-4 weeks |
| **Total minimum** | | **5-12 weeks** |
| **Earliest filing** | | **Mid-May to early July 2026** |
| **PhD defense** | | **Before August 2026** |

This is tight. If TechTransfer drags, the window closes. You need to push hard in the email to An Van den Broecke this week. Make the timing constraint explicit: "My PhD defense is before August 2026. If the patent application is not filed before the thesis is publicly available, the invention loses novelty under EPO rules."

### The colleague's trade secret approach

The colleague Robin interviewed today chose trade secrets over patents. Her reasoning: patents are expensive to maintain, require full disclosure, and you have to sue infringers. All true. But her situation is different from Robin's in one critical way: **Robin's PhD thesis will be a public document containing the full theory.**

Once the monograph theory is in the thesis, trade secret protection is impossible for the method. The cat is out of the bag. The only question is whether you have a patent filing date before that happens. Trade secrets work when you can keep the secret. Robin cannot, because academic publication is a requirement of the PhD.

The software implementation details (optimizations, viewer, integrations, enterprise features) can still be trade secrets. But the core method (Sab = Sinc * T0 * ReLU[...], the exposure operator Q, the Fresnel compensation) will be public knowledge after the defense. Patent or nothing for the core method.

### What if TechTransfer decides not to file?

This is a real risk. Wout is cautious about patentability of methods/algorithms. If UGent TechTransfer decides the invention is not worth patenting:

1. **Ask them to let you file personally.** UGent's IP regulations (Codex Hoger Onderwijs, Art. II.285) give the university first right of refusal. If they decline, the IP may revert to the inventor. Get this in writing.
2. **File a Belgian national application yourself.** Cost is ~1,500 EUR with a patent attorney. This establishes a priority date and keeps your options open.
3. **If neither works:** Accept that the method will be unpatented, and shift your IP strategy entirely to trade secrets on the implementation + speed of execution + standards body influence + brand. This is not fatal. Most software companies have no patents. But it changes the competitive dynamics.

---

## 2. What to publish and where

### The publication portfolio

AEGIS generates at least 5-6 distinct publishable contributions. Each serves a different strategic purpose. The key is matching the right result to the right venue for maximum impact on both academic credibility and commercial positioning.

### Paper 1: The flagship (journal)

**Title idea:** "Geometric dosimetry: closed-form absorbed power density on 3D human bodies from 100 MHz to 100 GHz"

**Content:** The core theory. Pseudo-Brewster compensation, the geometric absorption law (Sab = Sinc * T0 * ReLU[...]), the Cauchy formula generalization, validation against Mie theory and published FDTD data. The monograph sections 4-8 condensed into 12-15 pages.

**Target venue:** Physics in Medicine and Biology (PMB) or IEEE Trans. Electromagn. Compat. (EMC)

**Why PMB/EMC:** The monograph bibliography tells the real story. The dosimetry community publishes in PMB (7 refs), EMC (7 refs), and Bioelectromagnetics (3 refs), not in TAP (4 refs, mostly antenna-side). Kodera 2024 is in MTT, Li 2019 is in PMB, Flintoft 2014 is in EMC. The reviewers and readers who matter for dosimetry are in PMB and EMC. TAP is an option but less natural.

**Alternative 1:** IEEE TAP. Less dosimetry traffic, but prestigious and standards-adjacent. An open lane with no direct competition in-venue.
**Alternative 2:** IEEE Trans. Microw. Theory Tech. (MTT). Where Kodera 2024 landed. Higher IF than EMC.

**Review timeline:** TAP typically takes 3-6 months for first decision. Plan accordingly.

**Strategic value:** This paper is the foundation of everything. It establishes Robin as the originator of geometric dosimetry. Every subsequent paper, grant application, standards contribution, and customer conversation references this. Delay this paper and you delay everything.

**When to submit:** As soon as the patent application is filed. Not one day before.

### Paper 2: Coherent MIMO dosimetry (journal)

**Title idea:** "Closed-form exposure operator for MIMO beamforming: from field channel matrix to exposure-constrained precoding"

**Content:** The exposure channel matrix G_tilde, the exposure operator Q, the ECBF precoder. Monograph Part III (sections on coherent setup, field channel, Fresnel transmission, coherent absorption law, exposure operator, ECBF). Validation against numerical reference.

**Target venue:** IEEE Transactions on Wireless Communications (TWC) or IEEE JSAC

**Why TWC/JSAC:** The MIMO/beamforming community reads TWC, not TAP. Hochwald (2014) and Ying (2015-2017) published their SAR matrix work in TWC. Robin's exposure operator Q is a direct advance on their work. It needs to be in the same venue.

**The JSAC Special Issue angle:** The JSAC SI on "Digital Twins for Wireless Networks" has a May 1, 2026, submission deadline. This IS viable despite the patent not being filed yet. Submitting to a journal is confidential peer review, NOT a public disclosure. The paper only becomes prior art when published (~September 2026). The patent application can be filed June-July, before publication. Timeline: submit May 1 (confidential) -> patent filed June/July (priority date) -> paper published ~September (after priority date, safe). This is the highest-impact venue option and should be seriously considered. JSAC IF is ~13-16, far above TAP/PMB/EMC. The digital twin framing fits AEGIS naturally: real-time exposure digital twin for wireless networks.

**Strategic value:** This paper positions AEGIS in the wireless communications community, not just the dosimetry community. It opens doors to Ericsson, Nokia, and Qualcomm researchers who work on beamforming. It directly supports the "exposure-aware beamforming" product pitch.

**When to submit:** 2-4 months after Paper 1, once the core theory paper is under review. The coherent paper depends on the incoherent theory being established.

### Paper 3: Speed benchmark + compliance (conference)

**Title idea:** "Real-time ICNIRP 2020 compliance assessment for 5G base stations: from hours to milliseconds"

**Content:** The speed benchmark (10^6-10^9x vs FDTD), the compliance module, real base station data from EU databases, the 9 fidelity levels as a computation-accuracy tradeoff. Practical, not theoretical. This is the marketing paper.

**Target venues (pick 1-2):**

| Venue | Dates | Submission deadline (est.) | Why |
|-------|-------|---------------------------|-----|
| **PIMRC 2026** | Sep 1-4, 2026, Singapore | ~April-May 2026 | Industry-focused, telecom audience. Short paper (4-6 pages). Operators and vendors attend. |
| **VTC 2026-Fall** | Sep 6-9, 2026, Boston | ~May-June 2026 | Similar audience to PIMRC. Vehicular + mobile. |
| **EuCAP 2027** | Apr 18-23, 2027, Dusseldorf | ~Oct 2026 | Core antenna/propagation community. Robin's home turf. |
| **IEEE AP-S/URSI 2027** | Jun 20-25, 2027, Kyoto | ~Jan 2027 | Prestigious. International exposure. |

**Strategic value:** This is the paper you hand to potential customers. "Here is an IEEE-published benchmark showing our method is 10^6x faster and validated to 3-8%." It is also the paper you put in VLAIO and istart applications under "scientific output."

**When to submit:** As soon as the patent filing is done. Conference papers have shorter review cycles (2-3 months). Target PIMRC 2026 or VTC 2026-Fall if timing permits, otherwise EuCAP 2027.

### Paper 4: Polarization-aware dosimetry (journal or conference)

**Title idea:** "Absorption Stokes vector: exact polarization-dependent dosimetry without simulation"

**Content:** The absorption Stokes vector formalism, polarization response of the human body, the cylinder bound, multipath convergence to the unpolarized limit. Monograph section 11.

**Target venue:** IEEE Transactions on Antennas and Propagation (TAP) or IEEE Antennas and Wireless Propagation Letters (AWPL, shorter format).

**Strategic value:** Novel contribution that no competitor has. Differentiates AEGIS from any future imitator who implements the basic Sab formula but ignores polarization. Good for citations from the antenna measurement community.

**When to submit:** After Papers 1 and 2. This is a specialty contribution, not the main story. Q1-Q2 2027.

### Paper 5: Sub-6 GHz extension (conference or journal)

**Title idea:** "Extending geometric dosimetry below 6 GHz: the flux-averaged transmission coefficient"

**Content:** The Tbar mechanism, validity from 100 MHz to 100 GHz, the traffic-light diagram showing where each approximation applies. Monograph section 12.

**Target venue:** BioEM 2027 (June 13-18, 2027, Gdansk) or IEEE Access.

**Why BioEM:** The bioelectromagnetics community cares about sub-6 GHz because that is where most real-world exposure happens today. A BioEM presentation puts Robin in front of the people who set ICNIRP guidelines. Kuster has been a BioEM regular for decades.

**Strategic value:** Removes the "but AEGIS only works above 6 GHz" objection. Essential for the Sim4Life integration pitch (Sim4Life users work across the full spectrum).

**When to submit:** H2 2026 or H1 2027, depending on BioEM 2027 abstract deadline.

### Paper 6: The PhD thesis itself

**Content:** The full monograph, plus introduction, literature review, and conclusion chapters.

**Strategic value:** The thesis is a public document. It becomes the definitive reference. Every citation of AEGIS in the next decade will trace back to this thesis. It is also the most thorough validation of the method, with golden tests, property-based tests, and Mie regression.

**Timing:** Defend before August 2026. **After patent filing.**

### Standards contributions

These are not papers but formal technical contributions to standards bodies. They have outsized strategic value.

| Body | Relevant standard | Contribution type | Access route |
|------|-------------------|-------------------|--------------|
| **IEC TC 106** | IEC 63195 (computational SAR/Sab procedures) | Technical report or informative annex proposing geometric dosimetry as a fast screening method | Through BEC (Belgian Electrotechnical Committee), which is Belgium's IEC member. Wout Joseph likely already participates. |
| **IEEE ICES TC95 SC6** | IEEE C95.1 (safety levels) | Technical contribution on closed-form compliance bounds | Through IEEE membership. Publish Papers 1 and 3 first to establish credibility. |
| **ICNIRP** | ICNIRP 2020 guidelines | Commentary or workshop contribution | By invitation. Wout Joseph has connections. Getting a paper cited in an ICNIRP document is the ultimate credibility signal. |

**How to participate in IEC TC 106:** Apply through your national standards body (BEC in Belgium, which mirrors IEC TC 106 as MC/IEC/TC 106). BEC membership for experts is typically facilitated by the employer (UGent/IMEC). Wout Joseph is the natural entry point since INTEC-WAVES already works on exposure assessment standards.

**Strategic value of standards contributions:** Getting AEGIS referenced in IEC 63195 or cited by ICNIRP is worth more than any journal publication. It creates an institutional dependency. When compliance officers worldwide look up "how to compute Sab," they find AEGIS. This is exactly what Kuster did with DASY measurement systems and Sim4Life.

### White papers and application notes (for customers, not academia)

These come after the first paying customer, not before.

| Document | Audience | Content | When |
|----------|----------|---------|------|
| "ICNIRP 2020 compliance with AEGIS" | Telecom compliance officers | Step-by-step: upload site data, run assessment, get compliance report. No theory. | After first pilot customer (2027) |
| "AEGIS vs FDTD: when to use which" | RF engineers at Sim4Life users | Positioning AEGIS as pre-screener, not replacement. Quantitative speed-accuracy comparison. | When pursuing Sim4Life integration (2027) |
| "Exposure-aware beamforming for 5G NR" | Ericsson/Nokia antenna engineers | The Q operator applied to realistic MIMO scenarios. Reference Paper 2. | When pursuing equipment vendor deals (2027-2028) |

### Summary: which results go where

| Result | Strategic purpose | Venue | Priority |
|--------|-------------------|-------|----------|
| Pseudo-Brewster compensation + geometric law | Establish the theory | IEEE TAP (Paper 1) | Highest |
| Exposure operator Q + ECBF precoder | Enter the wireless/MIMO community | IEEE TWC or JSAC (Paper 2) | High |
| Speed benchmark + compliance | Marketing + grant applications | PIMRC/VTC/EuCAP (Paper 3) | High |
| Absorption Stokes vector | Differentiation, citations | TAP or AWPL (Paper 4) | Medium |
| Sub-6 GHz extension (Tbar) | Remove objections, BioEM community | BioEM 2027 (Paper 5) | Medium |
| Full framework + validation | Definitive reference | PhD thesis (Paper 6) | Mandatory |
| Screening method for IEC 63195 | Standards influence | IEC TC 106 contribution | Strategic (long-term) |

---

## 3. What NOT to publish

This is as important as what to publish. The core theory is publishable (and must be published, because it is in the thesis). But the competitive moat is in things competitors cannot easily replicate even after reading the papers.

### Never publish

| Category | Specific examples | Why |
|----------|-------------------|-----|
| **Implementation optimizations** | JAX backend, GPU kernel design, vectorized mesh operations, precomputed body response caching | The papers describe *what* to compute. The speed of the implementation depends on *how*. A competitor reading the paper gets the equations. They do not get the 28K lines of optimized Python that make it run in milliseconds. |
| **The viewer and UX** | React/Three.js 3D viewer, HUD components, interactive compliance display | This is product, not science. It has zero academic value and massive commercial value. Nobody cites a viewer. Everyone uses one. |
| **Integration layer** | Base station data adapters (8 EU databases), CloudRF antenna pattern integration, Sionna/DiffeRT ray tracing bridge, API authentication, batch processing | The plumbing that makes AEGIS work on real data. Extremely tedious to replicate. A competitor with the theory still needs months of engineering to match this. |
| **Enterprise features** | Multi-site batch processing, PDF compliance report generation, tenant isolation, API rate limiting | These are SaaS features. They are not publishable and not interesting to academia. They are very interesting to customers. |
| **Specific numerical optimizations** | The exact Mie-series cutoff for validation, the spatial averaging algorithm, the specific ambient occlusion implementation, the triangle-ray intersection acceleration | Implementation details that affect speed and accuracy in practice. Publish the mathematical framework, not the engineering shortcuts. |
| **GOLIAT and the hybrid pipeline** | The FDTD pre-screening workflow, the hybrid spatial resolution approach | Publish the concept (Paper 3 can mention "AEGIS as pre-screener") but not the automation layer or the specific Sim4Life integration. |

### The principle

**Publish the physics. Keep the engineering.**

The pseudo-Brewster compensation is a physical insight. It belongs in a journal. The fact that your implementation precomputes a lookup table of T0 values indexed by tissue type and frequency, stored as a memory-mapped NumPy array for O(1) access, is an engineering detail. Keep it.

The exposure operator Q = integral of G_tilde^H G_tilde dA is mathematics. It belongs in a paper. The fact that you compute this integral using a specific quadrature scheme on the GPU with batched matrix operations across 10,000 triangles is implementation. Keep it.

### What about the monograph?

The monograph (6,000 lines LaTeX) is the full theory with all derivations and proofs. It will be substantially included in the PhD thesis. This means the theory is public after the defense. Accept this. The theory being public is actually good for standards adoption and academic credibility.

What is NOT in the monograph:
- The software architecture (9 fidelity levels as separate kernel files, the PropagationPaths dataclass, the DosimetryEngine dispatch pattern)
- The test suite (2,177 tests, golden tests for every monograph table, Hypothesis property tests)
- The viewer
- The integrations
- The deployment infrastructure

These remain proprietary regardless of what happens with the thesis.

---

## 4. Open-source licensing strategy

### The decision framework

There are three options. Each has different implications for adoption, revenue, and competitive positioning.

| Option | License | What is open | What is proprietary | Academic adoption | Revenue risk | Standards influence |
|--------|---------|-------------|---------------------|-------------------|-------------|-------------------|
| **A: Closed source** | Proprietary | Nothing | Everything | Low (no one can verify or cite code) | None | Low (cannot be reference implementation) |
| **B: Open-core (AGPL)** | AGPL-3.0 for core, proprietary for advanced | L0-L2 kernels (bound, aggregate, geometric) | L3-L8, viewer, integrations, enterprise | High | Medium (gives away basic compliance) | High |
| **C: Source-available (BSL)** | BSL 1.1 for core, proprietary for advanced | Source visible, production use restricted for 3-4 years | Production deployment, commercial use | Medium (can inspect, cannot deploy) | Low (time-delayed opening) | Medium |

### Recommendation: Option A now, revisit at year 2

**Do not open-source anything today.** Here is why:

1. **The thesis will be public.** Anyone who wants to implement the theory can read the thesis and the journal papers. They do not need source code. Open-sourcing the code adds convenience for competitors without adding much for academics (who will cite the papers regardless).

2. **The incoherent levels (0-6) are the revenue.** Your colleague's interview confirmed what the market analysis already showed: ~95% of real-world compliance cases today use incoherent dosimetry. Open-sourcing L0-L6 means giving away the thing customers would pay for. You would be selling the research frontier (coherent MIMO, L7-L8) to an audience that does not need it yet.

3. **AI lowers the reimplementation barrier.** In 2016, open-sourcing the code gave you a moat through community lock-in because reimplementing was expensive. In 2026, a motivated competitor with the published equations and an AI coding assistant can reimplement the core in weeks. Open-sourcing accelerates this from weeks to days. The benefit (community contributions) does not outweigh the risk for a pre-revenue company.

4. **The Kuster precedent.** Kuster never open-sourced Sim4Life. He open-sourced the *data* (IT'IS tissue database) and kept the *software* proprietary. This gave him goodwill and ecosystem dependency without giving away revenue. AEGIS can follow the same pattern: publish the theory (papers), open the data (tissue properties are already from published sources), keep the software closed.

### When to revisit (year 2-3)

Revisit the open-source question when:
- You have at least 3 paying customers and understand your revenue model
- You know which features customers actually pay for vs. which they expect for free
- You have a sense of whether academic adoption (citations, standards references) is being blocked by the closed-source nature
- The coherent MIMO market (L7-L8) has matured enough to be the paid tier while incoherent becomes the free tier

At that point, the right answer may be:

**Option B (AGPL open-core)** if:
- Academic adoption matters more than you expected
- Standards bodies want a reference implementation they can inspect
- You have enough enterprise features (API, reports, batch, SLA) that the open core does not cannibalize revenue

**Option C (BSL)** if:
- You want source transparency without competitive risk
- Cloud providers (AWS, GCP) might bundle a competing service
- You want the code to eventually become open but need a 3-4 year commercial head start

### If you do open-source (future state)

Here is what the split should look like:

**Open repository (AGPL-3.0 or BSL 1.1):**
- L0 (bound) and L1 (aggregate) kernels only
- The Fresnel coefficient computation (T0, Tavg)
- Basic mesh loading (STL reader)
- The DosimetryResult dataclass
- Example scripts reproducing the key figures from Paper 1
- Documentation referencing the papers

**Proprietary repository:**
- L2-L8 kernels
- The full DosimetryEngine with level dispatch
- PropagationPaths with coherent field data
- The exposure operator Q and ECBF solver
- The compliance module
- The viewer (React + Three.js)
- All integrations (base station databases, CloudRF, Sionna, DiffeRT)
- The API layer, authentication, batch processing
- Enterprise features (reports, multi-tenant, SLA)
- The test suite (2,177 tests are a significant asset)
- GOLIAT and the hybrid pipeline

### What to open regardless (not code, but data/knowledge)

Follow Kuster's IT'IS playbook. Open the things that create ecosystem dependency without giving away revenue:

| Asset | Format | Purpose |
|-------|--------|---------|
| Tissue dielectric properties | Published tables in papers, downloadable CSV | Every dosimetry researcher needs these. If they get them from your paper/repo, they cite you. |
| Validation datasets | Published benchmark scenarios (body + source config + expected Sab) | Lets others validate against your results. Creates the "AEGIS benchmark" that becomes the standard comparison. |
| The theory itself | Papers + thesis | This is already committed to being public. Lean into it. |

---

## 5. The Kuster playbook applied to AEGIS

### What Kuster did (1990s-2020s)

Niels Kuster built the dominant EMF dosimetry ecosystem from his PhD work at ETH Zurich. The playbook, reconstructed:

1. **Publish foundational science** (1990s). Papers on SAR measurement, exposure assessment, dosimetric phantoms. Became the most-cited author in the field.

2. **Enter standards bodies** (1990s-2000s). Member of IEC TC 106, IEEE ICES TC95 SC2, and various IEC working groups (62209, 62253). His measurement methods became THE measurement methods. When regulators say "measure SAR using method X," method X is Kuster's method.

3. **Build measurement hardware** (SPEAG, founded 1994). The DASY (Dosimetric Assessment System) became the industry standard for SAR measurement. If you need to certify a phone for SAR compliance, you buy a DASY system from SPEAG. Lock-in through standards.

4. **Build simulation software** (ZMT, founded 2006). Sim4Life, built on FDTD, using the ViP (Virtual Population) anatomical phantoms. License costs reportedly $15,000-50,000/year for commercial users. Free for students (smart: creates the next generation of users who demand Sim4Life at their employers).

5. **Maintain public goods** (IT'IS Foundation). The tissue properties database, the ViP phantoms (shared under specific terms), the Sim4Life student edition. These are not charity. They are ecosystem infrastructure that makes Sim4Life the default choice.

6. **Hold institutional positions** (ETH Professor, IT'IS Foundation Director, NFT Holding AG shareholder). Academic credibility legitimizes the commercial products. Commercial revenue funds the research. Virtuous cycle.

**Result:** Near-monopoly in EMF dosimetry tooling. SPEAG hardware + Sim4Life software + IT'IS data + standards influence = an ecosystem where every path leads back to Kuster's organizations.

### What Robin can learn

The playbook is the same. The execution speed is different.

| Kuster (1990-2020, 30 years) | Robin (2026-2030, target 4 years) | Why faster |
|------|------|------|
| Published ~200 papers over decades | Needs 3-5 papers in 18 months | AI-assisted writing, monograph already done, no funding-dependent research needed |
| Entered standards through decades of committee work | Can enter through Wout Joseph's existing IEC TC 106 connections | Wout is already in the network |
| Built DASY hardware (years of R&D + manufacturing) | No hardware needed. Pure software. | Software ships faster, iterates faster, costs less |
| Built Sim4Life from FDTD (years of solver development) | AEGIS core engine already exists (28K lines, 2,177 tests, deployed) | Already built |
| Free student edition to seed adoption | Papers + thesis + potential future open-source reference | Theory is public after thesis |
| ETH Professor position for credibility | PhD from UGent/IMEC + published papers + standards contributions | Credibility through output, not title |

### The key differences

**Kuster had hardware.** DASY systems are physical measurement devices. You cannot download a DASY system. You cannot AI-generate one. Hardware creates lock-in that software cannot. Robin does not have this. The software moat must come from speed of execution, integration depth, and standards influence rather than physical lock-in.

**Kuster had 20 years.** The modern version needs to compress this because: (a) AI accelerates software development, (b) the competitive window is shorter (competitors also have AI), (c) Belgian funding programs (VLAIO, istart) expect commercial traction in 2-3 years, not 20.

**Kuster published first, commercialized later.** Robin needs to do both in parallel. The VLAIO mandate starts in 2026. The first paying customer should be in 2027-2028. There is no luxury of a decade of pure research before commercializing.

**Kuster had FDTD (computationally expensive, hard to replicate).** Robin has closed-form equations (fast, elegant, but easier to reimplement once published). This makes the implementation layer, the integrations, and the standards influence relatively more important as moats compared to Kuster's situation.

### The modern version of the Kuster playbook for AEGIS

**Year 0-1 (2026-2027): Publish and protect.**
- File patent application (establishes priority)
- Defend PhD thesis (establishes academic credibility)
- Submit Papers 1-3 (establishes scientific foundation)
- Enter IEC TC 106 through Wout Joseph (plants the flag)
- First customer conversations (validates the market)

**Year 1-2 (2027-2028): Productize and standardize.**
- Papers accepted and published (citations begin)
- First paying customer (test lab or Sim4Life integration)
- First IEC TC 106 technical contribution (propose geometric dosimetry as screening method)
- Build the "AEGIS benchmark" dataset (like IT'IS tissue database, but for dosimetry validation)
- VLAIO mandate progress report (shows traction)

**Year 2-3 (2028-2029): Scale and lock in.**
- AEGIS referenced in IEC 63195 revision or technical report
- 3-5 paying customers
- Consider open-sourcing L0-L1 as reference implementation (if standards adoption needs it)
- Expand to equipment vendor market (Ericsson, Nokia)
- Consider seed round or continue bootstrapping with IOF/VLAIO

**Year 3-4 (2029-2030): Compound.**
- Standards body influence creates new customer demand ("the standard recommends geometric dosimetry, AEGIS is the reference implementation")
- Academic citations create inbound interest
- Enterprise features (multi-tenant, SLA, audit trails) justify premium pricing
- Consider acquisition offers or Series A

---

## 6. Concrete timeline

### Phase 1: Protect and defend (April - August 2026)

| Date | Action | Dependency |
|------|--------|------------|
| **Week of April 7** | Email An Van den Broecke + Octrooien@UGent.be. State: "PhD defense before August. Patent application must be filed before thesis is public." CC Luc + Wout. | None |
| **April** | TechTransfer reviews IDF, engages patent attorney | TechTransfer response time |
| **May - June** | Patent claims drafted. Robin reviews with attorney. | Attorney availability |
| **June - July** | **Belgian national patent application filed.** Priority date established. | Attorney completes drafting |
| **After patent filing** | PhD thesis deposited / defense scheduled | Patent filing date |
| **Before August** | **PhD defended.** Thesis becomes public. | Patent filed first |

**If TechTransfer is slow:** Escalate through Luc. If they will not file by July, ask about filing personally. The thesis defense cannot wait for TechTransfer bureaucracy.

### Phase 2: Publish (August 2026 - March 2027)

| Date | Action | Notes |
|------|--------|-------|
| **August 2026** | Submit Paper 1 (core theory) to IEEE TAP | Priority date established, safe to publish |
| **August 2026** | Submit Paper 3 (speed benchmark) to PIMRC 2026 or VTC 2026-Fall (if deadlines permit) OR prepare for EuCAP 2027 (deadline ~Oct 2026) | Conference paper, faster review |
| **September 2026** | VLAIO Innovation Mandate application. List Paper 1 as "submitted" and thesis as "defended." | Papers strengthen grant application |
| **October 2026** | Submit Paper 3 to EuCAP 2027 (if not already submitted to PIMRC/VTC). Deadline likely mid-October. | EuCAP 2027: April 18-23, Dusseldorf |
| **October 2026** | imec.istart application. Reference papers, thesis, patent filing. | istart deadline: October 1 |
| **November 2026** | Submit Paper 2 (coherent MIMO) to IEEE TWC | After Paper 1 is under review |
| **Q1 2027** | Paper 1 first review decision expected | TAP ~3-6 months |
| **Q1 2027** | BioEM 2027 abstract deadline (for Paper 5, sub-6 GHz extension) | BioEM 2027: June 13-18, Gdansk |
| **Q2 2027** | Submit Paper 4 (polarization Stokes vector) to AWPL or TAP | Lower priority |

### Phase 3: Standardize and sell (2027 - 2028)

| Date | Action | Notes |
|------|--------|-------|
| **Q1-Q2 2027** | Join BEC mirror committee for IEC TC 106 (through UGent/Wout) | Formal standards participation |
| **Q2 2027** | Present at BioEM 2027 (Gdansk) | Face time with ICNIRP/IEC community |
| **Q2 2027** | Present at EuCAP 2027 (Dusseldorf) | Core antenna/propagation community |
| **H2 2027** | First IEC TC 106 technical contribution: propose geometric dosimetry as informative annex to IEC 63195 | Requires published Paper 1 as reference |
| **H2 2027** | First paying customer (test lab or Sim4Life integration deal) | Customer discovery ongoing since April 2026 |
| **2027** | PCT patent application filed (within 12 months of Belgian filing) | If patent route pursued for international coverage |
| **Q2 2027** | IEEE AP-S/URSI 2027 presentation (Kyoto) | If paper submitted ~Jan 2027 |

### Phase 4: istart program and scaling (Late 2027 - 2029)

| Date | Action | Notes |
|------|--------|-------|
| **Late 2027** | istart program in full swing. EiR embedded. Business coaching. | If accepted October 2026 |
| **2027-2028** | IOF StarTT/ConcepTT funding for specific technical milestone | IOF August 3 or October 19 deadline |
| **2028** | Revisit open-source decision with market data | Do customers need it? Do standards bodies need it? |
| **2028** | Papers 1-3 published. Citations accumulating. | Academic credibility established |
| **2028-2029** | AEGIS referenced in IEC standard or technical report | Endgame for standards influence |

### Map: publications to funding applications

Each paper directly strengthens the next funding application:

```
Paper 1 (TAP, submitted Aug 2026)
    |
    +--> VLAIO application (Sep 2026): "journal paper submitted to IEEE TAP"
    |
    +--> istart application (Oct 2026): "scientific novelty validated by peer review"
    |
Paper 3 (conference, submitted Oct 2026)
    |
    +--> istart pitch: "real-time demo, published benchmark"
    |
Paper 2 (TWC, submitted Nov 2026)
    |
    +--> VLAIO progress report (2027): "second journal paper, MIMO market entry"
    |
PhD thesis (defended, public)
    |
    +--> All applications: "completed PhD, comprehensive validation"
    |
BioEM 2027 / EuCAP 2027 presentations
    |
    +--> IOF application (Aug 2026 or Oct 2026): "international conference presence"
    |
    +--> Customer conversations: "we presented at [venue], here are the slides"
```

---

## 7. Risk analysis

### Risk 1: Publishing too much (competitors copy)

**Severity:** Medium
**Probability:** Medium (after thesis is public)

**The scenario:** ZMT reads the thesis, implements the geometric absorption law in Sim4Life as a "fast screening mode," and sells it to their existing customer base. They have the distribution channel, the brand, and the customer relationships. Robin has the theory but limited sales infrastructure.

**Mitigation:**
- The patent (if filed) prevents direct copying of the claimed method
- Even without a patent, reimplementation takes time. The 28K lines of code, 2,177 tests, and integration layer represent 12-18 months of engineering that a competitor must replicate.
- Speed of execution matters. By the time ZMT implements a basic version, AEGIS should be at version 2.0 with coherent MIMO, enterprise features, and customer references.
- The standards play creates a second moat: if AEGIS is the reference implementation cited in IEC 63195, a competitor's reimplementation is just "another implementation of the AEGIS method." The original has credibility they cannot replicate.
- Trade secrets on the implementation details (optimizations, viewer, integrations) protect the engineering even if the physics is public.

**Honest assessment:** Some copying is inevitable and actually desirable. If ZMT implements geometric dosimetry in Sim4Life, it validates the method. If Ericsson implements it in their network planning tool, it creates the market. The goal is not to prevent all use but to be the best and most trusted implementation.

### Risk 2: Publishing too little (no credibility)

**Severity:** High
**Probability:** Low (given the existing monograph and planned papers)

**The scenario:** Robin focuses entirely on product development, skips the journal papers, and tries to sell AEGIS without academic credibility. Potential customers ask: "Has this been peer-reviewed? Is this validated? Who else uses it?" The answers are all no.

**Mitigation:**
- Paper 1 (TAP) is non-negotiable. It must be submitted within weeks of the patent filing.
- The PhD thesis itself provides comprehensive validation.
- Conference presentations (EuCAP, BioEM, PIMRC) create face-to-face credibility.
- Standards contributions create institutional credibility.

**Honest assessment:** This risk is low because Robin clearly intends to publish. The real risk is *delay*, not omission. If the patent takes too long and Papers 1-3 are delayed until 2027, the VLAIO and istart applications lack scientific output. Publish as fast as the patent timeline allows.

### Risk 3: Wrong license choice

**Severity:** Medium-High
**Probability:** Low (if you follow the "closed now, revisit later" recommendation)

**The scenarios:**

*Too open too early:* Open-source L0-L6 under AGPL. A well-funded competitor (or cloud provider) builds a commercial service on top. Your open-source code becomes the foundation of a product that competes with you, and the AGPL copyleft does not help because they offer it as SaaS (AGPL covers network use, but enforcement is uncertain and expensive).

*Too closed too long:* Stay closed-source for 3+ years. Academic researchers cannot verify or reproduce your results. Standards bodies cannot inspect the implementation. Citations are slow because there is no code to run. You win on revenue protection but lose on adoption and standards influence.

**Mitigation:**
- Start closed. This is the safe default for a pre-revenue company.
- Revisit after 12-18 months of commercial traction.
- If opening: AGPL for the core (copyleft deters commercial free-riders), proprietary for enterprise features.
- BSL is the safer alternative if you want source transparency without immediate competitive risk.

### Risk 4: Patent application delays

**Severity:** Critical
**Probability:** Medium-High (university bureaucracy is real)

**The scenario:** UGent TechTransfer takes 3 months to assess the IDF. The patent attorney takes another 2 months. The Belgian application is filed in October 2026. But the PhD thesis was deposited in July 2026. The thesis is prior art. The patent is worthless.

**Mitigation:**
- Push hard this week. The email to An Van den Broecke must be sent now, with the timing constraint explicit.
- Luc (who is helping with Octrooien@UGent.be) should be the internal champion.
- If TechTransfer cannot move fast enough: ask whether Robin can file personally if UGent declines.
- **Nuclear option:** Delay the PhD defense until the patent is filed. This is undesirable (delays VLAIO, delays istart, delays everything) but preferable to losing the patent entirely.
- Set an internal deadline: if no patent application is filed by July 1, 2026, delay the thesis defense by 2-3 months.

### Risk 5: UGent TechTransfer takes unfavorable terms

**Severity:** Medium
**Probability:** Medium

**The scenario:** TechTransfer agrees to file but demands equity or royalty terms that make the spin-off unattractive. The Fast Lane scheme (0.5% royalty + 6% equity) is predefined and relatively founder-friendly, but there may be additional conditions.

**Mitigation:**
- Ask about Fast Lane explicitly in the first meeting.
- The colleague's interview notes confirm Fast Lane has predefined terms. This avoids months of negotiation.
- If the terms are unacceptable, the alternative is declining the patent and relying on trade secrets + speed of execution. Not ideal, but not fatal.
- The IDF states "no external funding" for the invention. This simplifies the IP ownership question (no grant conditions to navigate).

### Risk 6: The JSAC SI deadline (May 1, 2026) is tight

**Severity:** Medium (JSAC SI is the highest-impact option, IF ~13-16)
**Probability:** Low-Medium (29 days to write, but monograph has the content)

**The scenario:** The JSAC SI on "Digital Twins for Wireless Networks" has a May 1, 2026, deadline. The patent will not be filed by May 1. However, journal submission is confidential peer review, NOT a public disclosure. The paper only becomes public upon publication (~September). The patent can be filed June-July, before publication.

**The real risk:** Writing a JSAC-quality paper in 29 days. The monograph contains the theory and the validation data exists, but condensing it into a focused 12-15 page JSAC paper with the right "digital twin" framing is still significant work.

**Recommendation:**
- Seriously consider submitting. JSAC IF (~13-16) dwarfs TAP (~4.5), PMB (~3.5), and EMC (~2.0). A JSAC publication would be the strongest possible line on any grant application or investor deck.
- The digital twin angle is a natural fit: AEGIS as real-time exposure digital twin for wireless network planning.
- If the May 1 deadline is too tight, watch for the next relevant JSAC SI (they run multiple per year).

### Risk matrix summary

| Risk | Severity | Probability | Action |
|------|----------|-------------|--------|
| Patent filed after thesis | Critical | Medium-High | Push TechTransfer NOW. Set July 1 internal deadline. Delay defense if needed. |
| Competitor reimplements after publication | Medium | Medium | Patent + trade secrets on implementation + speed of execution + standards influence |
| No publications, no credibility | High | Low | Submit Paper 1 immediately after patent filing |
| JSAC SI deadline tight (May 1) | Medium | Low-Medium | Submit if feasible. Journal submission is confidential, patent can be filed before publication. |
| Wrong open-source license | Medium-High | Low | Stay closed. Revisit at year 2 with data. |
| TechTransfer takes bad terms | Medium | Medium | Ask about Fast Lane. Decline and use trade secrets if terms are unacceptable. |
| JSAC SI missed | Low | Certain | Skip it. Target TWC or future JSAC SI. |

---

## Appendix: conference and journal quick reference

### Upcoming conference deadlines (2026-2027)

| Conference | Location | Dates | Submission deadline (est.) | Paper type |
|-----------|----------|-------|---------------------------|------------|
| PIMRC 2026 | Singapore | Sep 1-4, 2026 | ~Apr-May 2026 | 4-6 page |
| VTC 2026-Spring | Nice, France | Jun 9-12, 2026 | Past | 4-6 page |
| VTC 2026-Fall | Boston, USA | Sep 6-9, 2026 | ~May-Jun 2026 | 4-6 page |
| EuCAP 2027 | Dusseldorf, Germany | Apr 18-23, 2027 | ~Oct 2026 | 4-5 page |
| BioEM 2027 | Gdansk, Poland | Jun 13-18, 2027 | ~Jan-Feb 2027 | Abstract |
| IEEE AP-S/URSI 2027 | Kyoto, Japan | Jun 20-25, 2027 | ~Jan 2027 | Summary + full paper |

### Target journals

| Journal | IF (approx.) | Review time | Best for |
|---------|------|-------------|----------|
| IEEE Trans. Antennas and Propagation (TAP) | ~4.5-5.0 | 3-6 months | Paper 1 (core theory), Paper 4 (polarization) |
| IEEE Trans. Wireless Communications (TWC) | ~8-10 | 3-6 months | Paper 2 (coherent MIMO) |
| IEEE JSAC | ~13-16 | 3-4 months (SI) | Paper 2 alternative (if SI topic matches) |
| IEEE Antennas and Wireless Propagation Letters (AWPL) | ~3.5-4.0 | 1-3 months | Paper 4 alternative (shorter format) |
| Physical Medicine and Biology | ~3.0-3.5 | 2-4 months | Paper 5 (sub-6 GHz, biomedical angle) |
| IEEE Access | ~3.0-3.5 | 1-3 months | Fast publication backup for any paper |

---

*This document will be updated as patent filing progresses and TechTransfer provides guidance. The single most important action item right now is the email to An Van den Broecke establishing the timing constraint.*
