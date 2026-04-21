# AEGIS spin-off roadmap: April 2026 - April 2027

No fluff. Actions, dates, owners.

---

## Critical path

```
PhD defense --> VLAIO Innovation Mandate --> imec.istart --> First paying customer
     |                  |                        |
  Q2-Q3 2026      Sep 2026 deadline         Feb/Jun/Oct 2027
```

Everything else is support for this sequence.

---

## Immediate (April - June 2026)

### 1. Defend the PhD

- **Deadline**: Before September VLAIO call
- You cannot apply for Innovation Mandate without a PhD diploma
- Everything else is blocked until this is done
- If defense is after September: you miss the 2026 call and wait until March 2027. That costs 6 months. Avoid this.

### 2. Talk to UGent TechTransfer NOW

- **Contact**: techtransfer@ugent.be
- **Ask about**: The new [Fast Lane scheme](https://techtransfer.ugent.be/en/news/fast-lane-scheme-approved-ugent-speeds-spin-creation-new-standard-pathway) (approved March 2025)
  - Predefined standard conditions for IP licensing
  - Two tracks: Fast Lane (equity participation) and Fast Lane Mini (royalty + success fee only)
  - Avoids months of IP negotiation
- **Ask about**: IOF Stepstone funding for spin-off-oriented projects (iof@ugent.be)
  - Continuous submission, 4 fixed dates per year
  - Can fund pre-spin-off product development
  - Intake meeting is obligatory before submission
- **Get clarity on**: What UGent takes (equity %, royalty %, success fee). Know this number before you plan anything else.

### 3. Talk to Wout Joseph about the Innovation Mandate

- He needs to be your academic supervisor on the VLAIO application
- The application requires a "declaration of intent by the knowledge centre"
- INTEC-WAVES is the host lab. Wout signs off. Get his commitment in writing.

### 4. Find an industrial mentor

- VLAIO Innovation Mandate spin-off track **requires** cooperation with an industrial mentor
- This can be a VC fund, consultancy firm, or industry expert
- Ideal: someone from telecom/RF who has done enterprise B2B sales
- Where to look: imec.istart mentor network, UGent Ghent Entrepreneur Network, ETNO/GSMA contacts
- Do this BEFORE the application. The mentor goes on the form.

### 5. Start customer discovery NOW

Not after the mandate. NOW.

- **Target list** (20 conversations, not sales pitches):
  - 3-5 telecom operators (Proximus, KPN, Orange Belgium, Telenet)
  - 2-3 network planning vendors (ATDI, Forsk, iBwave)
  - 2-3 infrastructure vendors (Ericsson, Nokia local offices)
  - 2-3 national regulators (BIPT, BNetzA)
  - 2-3 EMF consultancies
- **Questions to ask** (from [YC's "How to Talk to Users"](https://www.startupschool.org/curriculum)):
  - What is the hardest part about EMF compliance for you today?
  - How do you currently compute exclusion zones / compliance boundaries?
  - How much time/money does this cost per site?
  - What would change if you could do it in real-time?
  - Who makes the buying decision for compliance tools? (you need to know the buyer)
- **Output**: Written notes from each conversation. Patterns will emerge. These go into the VLAIO application and the istart pitch.

---

## VLAIO Innovation Mandate application (July - September 2026)

### Key dates

| Item | Date |
|---|---|
| 2026 first call deadline | **10 March 2026** (MISSED - already past) |
| 2026 first call results | 16 July 2026 |
| 2026 second call deadline | **~September 2026** (exact date TBD, check [VLAIO website](https://www.vlaio.be/en/subsidies/innovation-mandates/how-apply-innovation-mandate)) |
| 2026 second call results | ~March 2027 |

You missed the March 2026 call. The September 2026 call is your target. Results come ~6 months later (March 2027). Plan accordingly.

### Application components

The VLAIO form requires:

1. **Innovation goal**: Emphasis on objectives and intended results. Write this as: "Develop AEGIS into a commercial EMF dosimetry platform for telecom operators, targeting ICNIRP 2020 compliance at 5G/6G frequencies."
2. **Project description**: Positioning, reasons, objectives. Lean on the IDF. The 10^6-10^9x speedup over FDTD is your hook.
3. **Academic supervisor fit**: How AEGIS fits INTEC-WAVES expertise (Wout Joseph's research group literally does EMF exposure assessment).
4. **Industrial mentor commitment**: Letter from your mentor.
5. **Spin-off plan**: Provisions to set up the company in Flanders.
6. **IP situation**: IDF filed, sole inventor, zero disclosures. Clean.

### Tips from people who got funded

- The panel is mixed: technical experts + business evaluators
- They want to see **market pull**, not just cool tech. Your customer discovery notes from step 5 are critical.
- Show that you know who the buyer is (not just "telecom companies" but "the RF planning team lead at Proximus who currently uses ATDI ICS Telecom")
- Show you know the business model (API pricing? Per-site license? Annual subscription?)
- Show you have a mentor who has done this before

---

## Product changes needed (parallel track, April - December 2026)

The product is a research tool today. It needs to become a commercial product. These are different things.

### Must-have for first pilot customer

| Change | Why | Effort |
|---|---|---|
| **API layer** | Customers integrate via API, not Python imports | Medium. Flask routes exist, formalize into documented REST API with auth. |
| **Multi-site batch processing** | Operators have 10,000+ sites | Medium. Parallelize the computation pipeline. |
| **Report generation** | Compliance officers need PDF reports, not 3D viewers | Medium. Auto-generate ICNIRP compliance certificates per site. |
| **Antenna pattern import** | Customers have their own patterns, not just CloudRF | Small. Support .msi, .csv, planet format. |
| **Regulatory output format** | Match what IXUS/MVG output so you can slot into existing workflows | Research needed. Talk to customers first. |

### Nice-to-have (defer until after first customer)

| Change | Why | When |
|---|---|---|
| GPU acceleration (JAX backend) | Speed at scale, but single-site is already milliseconds | After product-market fit |
| Mobile/indoor propagation | Currently far-field only; indoor is a different market | After outdoor is proven |
| Multi-body scenarios | Crowds, not individuals | After single-body is sold |
| 6G-specific features | 6G is 3+ years from deployment | Follow the market |

### Do NOT build

- A prettier 3D viewer (customers don't buy viewers, they buy compliance reports)
- An ML layer on top (your physics is your moat, don't dilute it)
- A consumer-facing "check your exposure" app (wrong market, wrong business model)
- Multi-language support (B2B enterprise, English only)

---

## imec.istart application (target: October 2026 or February 2027)

### Call dates

| Call | Deadline | Results |
|---|---|---|
| Spring 2026 | 1 February 2026 | Past |
| Summer 2026 | **1 June 2026** | Possible if PhD is done |
| Autumn 2026 | **1 October 2026** | Most likely target |
| Spring 2027 | 1 February 2027 | Fallback |

### What you submit

- Team presentation with CVs
- Executive summary (max 2 pages)
- Business pitch (max 12 slides)

### What they evaluate (from istart alumni and manual)

1. **Team**: Technical depth + commercial potential. Solo founder is a weakness. Mitigate by having a strong industrial mentor and a concrete plan to add a co-founder.
2. **Market**: Size, growth, urgency. Your pitch: "$2.1B RF planning market, 13% CAGR, regulatory tailwind from ICNIRP 2020."
3. **Product differentiation**: "10^6x faster than FDTD, closed-form, validated to 3-8% against published data." This is strong.
4. **Traction**: Any customer conversations, LOIs, pilot commitments from your discovery calls.
5. **Scalability**: SaaS/API model, not consulting. Show ARR potential.

### Acceptance rate: 20% (1 in 5)

Not guaranteed. If rejected:
- Ask for feedback
- Reapply next call (many successful alumni were rejected first time)
- Meanwhile, bootstrap with IOF Stepstone funding and VLAIO mandate salary

---

## Co-founder search (ongoing, start immediately)

This is your biggest weakness and your biggest leverage point.

### What you need

- Someone who has sold B2B enterprise software to telecom companies
- Ideally: 5-10 years in telecom/network planning industry
- Bonus: knows the IXUS/ATDI/Forsk competitive landscape
- Not: another PhD researcher (you have enough technical depth)

### Where to look

- imec.istart mentor network (ask them directly)
- UGent Ghent Entrepreneur Network
- LinkedIn: search for ex-Proximus, ex-Orange, ex-Ericsson people in Belgium who are "looking for their next thing"
- Telecom conferences: Mobile World Congress (Barcelona, late Feb), EuCNC (European Conference on Networks and Communications)
- Ask Wout Joseph and Luke Martens if they know anyone in their industry network

### How to structure it

- Do NOT give 50% equity to someone you just met
- Start with an advisor agreement (0.5-1% equity, 1 year cliff)
- If they prove themselves during the Innovation Mandate period, convert to co-founder (15-25% equity with 4-year vesting)

---

## Month-by-month checklist

### April 2026

- [ ] Schedule UGent TechTransfer meeting (Fast Lane + IOF Stepstone)
- [ ] Confirm Wout Joseph as academic supervisor
- [ ] Start customer discovery: email 10 targets this week
- [ ] Read [YC Startup School curriculum](https://www.startupschool.org/curriculum) (7 weeks, 1-2 hours/week)
- [ ] Read [B2B Sales for Founders](https://www.higherlevels.com/blog/b2b-sales-for-founders)

### May 2026

- [ ] PhD defense preparation (if not already defended)
- [ ] 5+ customer discovery conversations completed
- [ ] Identify 3 candidate industrial mentors
- [ ] Start formalizing API layer in AEGIS

### June 2026

- [ ] PhD defended (hard deadline if targeting September VLAIO call)
- [ ] Industrial mentor confirmed
- [ ] 10+ customer discovery conversations completed
- [ ] If PhD done: consider istart Summer call (June 1 deadline) - probably too tight, but check
- [ ] Write first draft of VLAIO Innovation Mandate application

### July 2026

- [ ] Refine VLAIO application with mentor feedback
- [ ] Continue customer discovery (target: 15+ conversations)
- [ ] API layer functional with basic auth
- [ ] Start compliance report generation feature

### August 2026

- [ ] VLAIO application finalized
- [ ] Get academic supervisor sign-off
- [ ] Get mentor declaration of intent
- [ ] Prepare istart pitch deck (12 slides)

### September 2026

- [ ] **Submit VLAIO Innovation Mandate application** (exact deadline TBD)
- [ ] 20+ customer discovery conversations completed
- [ ] Patterns documented: who buys, what they need, how much they pay, what the workflow looks like

### October 2026

- [ ] **Submit imec.istart Autumn application** (deadline: October 1)
- [ ] API + report generation demo-ready
- [ ] At least 1 LOI or pilot commitment from a customer

### November - December 2026

- [ ] VLAIO panel defense (if invited)
- [ ] istart pitch day (if selected)
- [ ] Continue product development
- [ ] Start co-founder conversations seriously

### January - March 2027

- [ ] VLAIO results (March 2027)
- [ ] If istart accepted: start 12-month program
- [ ] If both: you have full salary (VLAIO) + 50-250K pre-seed (istart) + mentor + coaching. You're funded for 2 years with <6% equity dilution.

---

## What success looks like at 12 months (April 2027)

| Metric | Target |
|---|---|
| VLAIO Innovation Mandate | Secured |
| imec.istart | Accepted (or reapplying Spring 2027) |
| Customer discovery conversations | 30+ |
| LOIs or pilot commitments | 2-3 |
| Co-founder or strong commercial advisor | Identified, in trial period |
| Product state | API + compliance reports + batch processing |
| Revenue | 0 (still pre-commercial, that's OK) |
| IP | Patent application filed (UGent TechTransfer handles this) |

---

## What success looks like at 24 months (April 2028)

| Metric | Target |
|---|---|
| First paying customer | Yes (even if small: 20-50K/year) |
| Pipeline | 5-10 qualified opportunities |
| ARR | 50-200K |
| Team | You + co-founder + 1 engineer (or contractor) |
| BV incorporated | Yes (Innovation Mandate ends at incorporation) |
| Next funding | Seed round conversations started, or bootstrapping with VLAIO R&D grant |

---

## Resources to consume (in priority order)

1. **[YC Startup School](https://www.startupschool.org/curriculum)** - Free, 7 weeks. The basics. Do this first.
2. **[How to Talk to Users - YC](https://www.startupschool.org/curriculum)** - The single most important skill for the next 6 months.
3. **[B2B Sales for Technical Founders - Higher Levels](https://www.higherlevels.com/blog/b2b-sales-for-founders)** - Actionable playbook.
4. **[Founder-Led Sales Guide - Startup Project](https://startupproject.org/guides/b2b-sales/)** - Discovery, demos, proposals, closing.
5. **[The Mom Test](https://www.momtestbook.com/)** (book, Rob Fitzpatrick) - How to talk to customers without bullshitting yourself. Short book. Read it in a day.
6. **[VLAIO Innovation Mandate application guide](https://www.vlaio.be/en/subsidies/innovation-mandates/how-apply-innovation-mandate)** - Read the official docs, not summaries.
7. **[imec.istart manual](https://www.imec-int.com/drupal/sites/default/files/inline-files/imecistart_manual_0.pdf)** - Know what they evaluate.

---

## Traps to avoid

1. **Building instead of talking.** You are a builder. Your instinct is to add features. For the next 6 months, talking to potential customers is 10x more valuable than any code you write. Force yourself: 2 customer conversations per week minimum.

2. **Perfecting the viewer.** The 3D viewer is impressive for demos but it is not the product. The product is an API that outputs compliance numbers. Build what people will pay for.

3. **Waiting for the mandate to start.** Customer discovery, mentor search, and product changes can all start now. The mandate is funding, not permission.

4. **Solo hero mode.** You built 42,000 lines of code with AI agents in 2 weeks. You cannot sell enterprise software to telecom companies alone. Find commercial help early.

5. **Saying yes to everything.** Someone will ask you to build a consumer exposure app. Someone will ask about indoor coverage. Someone will want a consultancy engagement. Say no. You are building a compliance API for outdoor telecom. Stay focused until you have 500K ARR.

6. **Zombie drift.** After 3 years, if you have <500K ARR and no clear path to it, make a deliberate choice: pivot, sell, or close. Do not drift into a lifestyle consultancy.

---

*Last updated: April 2026*
