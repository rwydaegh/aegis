---
title: Patent vs. publish — paraphrased Sunday-night conversation
date: 2026-04-19
context: Robin frustrated about the perceived patent push, considering whether to skip and just publish/market instead. Sunday before walking into TechTransfer Monday morning.
---

# Patent vs. publish — paraphrased conversation

Sunday night, April 19 2026. Robin venting about feeling pressured into the patent path and wondering whether to ditch it for an explosive publish-and-market strategy instead. Paraphrased back-and-forth so the reasoning survives.

---

## Robin (opening rant)

People keep pushing me to get the patent and I'm getting frustrated. It feels like waiting X amount of time so some lawyer can produce a stupid bureaucratic piece of paper, and the thing is — this is only a hedge. In three or four years I'd have the *option* to spend €40-100K to actually lock in a real patent, and it's kind of useless before that.

Meanwhile, I read this classic SaaS business advice piece. Companies don't fail because of competition. Competition is way down the list. The real reason is that they never find clients or the market just isn't there.

So I'm thinking: why bother with the patent at all? Why don't I publish ten papers, make the website public for a year before I start charging, post a million LinkedIn posts, get as many citations and GitHub stars as possible, just go nuts and explosive about it? When you actually look at this repo, it's low-key revolutionary. It has the ability to do that.

Be brutally honest both ways. Don't follow my assumptions if they aren't grounded. Could be agreement, disagreement, or nuance.

---

## Claude (first response)

Read the LATEST_GOOD set, the older publication/moats/TLDR/career-advice docs, and the Anniek interview. Here's the read.

**Where the gut is right.** Most of what's in the rant is *already the plan* in the docs:

- "Publish ten papers" → that's literally Papers 1-6 in `publication_and_opensource_strategy.md`.
- "Public website, LinkedIn, GitHub stars" → that's the entire `public_repo_strategy.md`. Open notebooks, MkDocs, Fresnel widgets, Apache-2.0, the AEGIS benchmark dataset.
- "Competition isn't why companies fail" → `honest_analysis.md` Q5 says the same thing. The dominant failure mode flagged for AEGIS is **zombie at year 4 with no customers**, not "ZMT clones it." Zero customer-discovery calls done as of April 2026. That's what every external review keeps circling.
- "This thing is low-key revolutionary" → it's strong, but `honest_analysis.md` Q4 is also right that the *physics* is less novel than the integrated execution. Real moat is the 2,469 tests + ingest pipeline + viewer + ZMT relationship + standards seat, not the equations.

So the impulse to flip into publish/market/grow mode is correct. The docs already endorse it.

**Where the framing is materially wrong.** The "€40-100K for a stupid lawyer's paper, 3-4 year wait" framing mixes three different timelines. Decomposed:

| Stage | When | Who pays | Cost to Robin | Reversible? |
|---|---|---|---|---|
| Priority application (the only ask now) | Before defense (~Aug 2026) | UGent pays entirely | **€0** | Yes |
| Search report | Month 6 | UGent | €0 | Yes |
| PCT placeholder | Month 12 | UGent typically | €0 | Yes |
| **National phase entry ← the €40-100K thing** | Month 30 | Only continues with commercial commitment | Only if both sides want to | UGent's default is **drop** without traction |
| Grant | Year 4-6 | n/a | n/a | n/a |

The "3-4 year wait to spend €40-100K" is real, but it's at the end of a staircase with three off-ramps before any real money is spent, and UGent is contractually predisposed to take those off-ramps unless a customer materializes. The thing being asked of Robin *now* is a €0 filing on a hard EPO deadline. Not filing it doesn't save €40-100K — it permanently closes the option, because EPO has no grace period and the public defense is a disclosure.

The patent attorney is not "a lawyer with a stupid bureaucratic paper." For a Belgian deep-tech exit-to-strategic in the €3-15M range (Feops, Caliopa, Gatewing all went this way), an issued or pending priority is a line item in acquisition diligence and materially moves the price. Not a litigation tool. A deal-value artifact. Anniek's "you'd have to sue infringers" critique is for businesses whose model is enforcement; not Robin's.

**Who's actually pushing.** Reread the cast:

- Wout is *cautious* about patentability of methods/algorithms. Not pushing.
- Anniek explicitly recommended trade secrets *over* patents. Pushing the opposite direction.
- Luc is more pro-patent.
- TechTransfer has a routine Fast Lane process. Not pushing — processing.

There's no cabal pushing the patent down anyone's throat. There's a hard EPO deadline before the defense, a €0 filing being teed up by UGent, and a structural off-ramp at every later step. The pressure being felt is the deadline, not the people.

**The actual question worth being frustrated about.** Patent-vs-publish is a false dichotomy and fits the pattern the personal advice files flagged: rabbit-holing on the meta-decision instead of doing the work. The actual sequence:

1. File priority (€0, 2-4 months, parallel to everything else)
2. *Then* publish massively, ship the public repo, target IEC 63195-2 2026, JSAC, the standards play

Sequential by ~3 months, not alternatives. Once filed, the patent doesn't gate anything.

The thing that's actually time-pressured isn't the patent and isn't LinkedIn — it's `standards_play.md`. **IEC/IEEE 63195-2 2026 is in CD/CDV right now. Window to insert AEGIS as a named acceptable computational method: 3-6 months. Next opportunity: 2028-2029.** Wout sits on the committee. One matched AEGIS-vs-Sim4Life validation + Wout tabling the contribution would be worth more than 500 GitHub stars or any single customer. That window is the quiet one most likely to slip.

**One-line answer.** Right that publishing aggressively, building mindshare, racking up stars is the right strategy — and to do it. Wrong that the patent is the alternative. The €0 priority filing on a hard PhD-defense deadline is the cheapest hedge that'll ever exist on a structurally-off-rampable staircase, and skipping it doesn't fund the explosive plan, doesn't simplify life, doesn't accelerate anything — it just permanently closes a door for no compensating gain. File the priority, then immediately do everything in the rant: papers, LinkedIn, stars, JSAC, public repo, standards contribution. Same plan, separated by 8 weeks.

---

## Robin (follow-up)

Okay, but that means I cannot defend until this thing is done. I cannot make a public GitHub repo. I cannot publish in fast journals like AWPL. None of that is possible until the priority is filed, correct? JSAC is probably possible because review takes a while.

The real question is: is it worth being in this paralysis mode?

Today is Sunday. Tomorrow is Monday. I'll probably literally just walk into TechTransfer's office. I already emailed them over the weekend, no response yet. This is pressing because everybody says it's two to four months — and it's a mystery to me whether it's *actually* two to four months.

---

## Claude (second response)

**What's actually blocked during the 2-4 months.** Less than it feels like.

*Blocked* (public disclosure under EPO):
- Public PhD defense
- arXiv / any preprint posting
- Pushing technical content to a public GitHub repo (notebooks reproducing equations, the SDK, the widgets)
- AWPL, IEEE Letters, MDPI rolling-pub, conference camera-ready — anything where acceptance-to-online is days/weeks
- LinkedIn posts that disclose the method (the *equation* posts; generic "we're working on dosimetry" is fine)
- Public press, demos, talks describing the method

*Not blocked* (already explicit in `patent_decision_and_defense_mechanics.md` §"Journal papers"):
- JSAC submission — confidential peer review is *not* a disclosure. Submit May 1, file June-July, Early Access Sept. Safe.
- Other slow journals (PMB, TAP, TWC) — same logic, more slack.
- AWPL is technically possible if the editor agrees to hold online publication until priority is filed. Routine request in patent-active fields. Riskier than slow journals, not categorically blocked.
- Reserving the GitHub org `openaegis`, pushing an empty placeholder README
- Reserving the PyPI name
- Customer discovery calls under NDA — every one of the 6 calls career-advice #2 prescribed. Start Monday. None of this is blocked.
- ZMT outreach under NDA about a matched-validation collaboration
- Wout emailing the IEC 63195-2 secretary asking scope (no method disclosure)
- Building the Sim4Life-vs-AEGIS matched validation
- Writing the thesis (depositing it is the disclosure, not writing it)
- Internal product work, viewer features, ingest pipeline, the entire 2,469-test private repo

The 2-4 month "blackout" is a *publication* blackout, not a *work* blackout. Most of what `honest_analysis.md` and the personal advice files say is most urgently needed — customer calls, ZMT, matched validation, IEC contribution prep — is unblocked.

**Is 2-4 months actually real.** It's the lazy estimate. Decomposed:

| Sub-step | Best case | Lazy default | What compresses it |
|---|---|---|---|
| TT reviews IDF, decides | 1-2 wk | 4-6 wk | Walking in Monday with hard EPO deadline in writing; Wout & Luc co-signing |
| Patent attorney engaged & briefed | 1 wk | 2-3 wk | Pick the one with EM/software experience and zero backlog |
| Claims drafted (IDF §9 already has drafts, monograph has the technical content) | 2-3 wk | 4-6 wk | Robin available same-day for attorney questions; iterate in days not weeks |
| Inventor review + filing | 1 wk | 2-3 wk | Don't haggle scope at priority stage — narrow claims now, broaden in PCT |
| **Total** | **5-7 wk** | **12-16 wk** | |

So 2-4 months is what happens by default. **6-8 weeks is what happens if it's treated like a sprint with a hard deadline**, which it is. The IDF is already 60K and v1.1, the prior-art differentiation vs Kodera/Li/Bamba is done, the monograph has the equations and validation. The creative work for the attorney is mostly translating IDF §9 into formal claim language. Few-weeks job if everyone moves.

The slip risk is *queueing*, not work. The variable that matters: how high in TT's queue. Walking in Monday with a printed one-pager — "PhD defense July 2026, EPO absolute novelty, what does the fast path look like?" — is exactly how you get queue priority. Email gets read in 3 days; in-person gets a calendar slot.

**The paralysis question** — already self-answered ("tomorrow's Monday"). Patent decision doesn't need more thinking. Priority filing is structurally right regardless of which path the company takes (SaaS, ZMT license, acquisition, even wind-down). The thing worth being paralyzed about is whether to do the spin-off at all, and the files have answered that one too: yes, kill date 18 months.

What deserves thought — *Monday-action thought, not Sunday-rumination thought* — is the parallel track during the 8-16 weeks the patent is being drafted:

1. Walk into TT Monday. (Confirmed.)
2. Email Wout this week to coordinate Art. 27 §4 (jury NDA) + Art. 30 §8 (Biblio embargo) with the Valorisatiecel. Routine.
3. Email 5 customer-discovery targets this week. None require the patent. None disclose anything. This is the actual gating activity for the entire spin-off.
4. Reserve `openaegis` org and `aegis` PyPI names. Push empty repos with placeholder READMEs. Costs nothing, discloses nothing, and the JSAC "Code availability" line has a real URL when needed.
5. Wout emails the IEC 63195-2 working-group secretary asking scope. Quietest most-time-pressured item across all the docs.

Walk in Monday. The 2-4 month estimate is a default, not a destiny.

---

## Bottom line

- The patent isn't an alternative to the publish-explosive plan; it's the 8-week prefix that unlocks it.
- "€40-100K in 3-4 years" is at month 30 with three off-ramps before it; the *now* cost is €0.
- 2-4 months is the lazy default. With a Monday in-person push and a hard PhD-defense deadline, 6-8 weeks is achievable.
- The blackout window blocks publication, not work. Customer calls, ZMT outreach, matched validation, standards prep, thesis writing, internal product work — all unblocked, all more important to the company's survival than the patent itself.
- The standards window (IEC 63195-2 2026 in CD/CDV) is the quieter, more time-pressured deadline than either the patent or the publish-plan.
