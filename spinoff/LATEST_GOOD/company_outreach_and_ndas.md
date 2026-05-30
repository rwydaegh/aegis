# Talking to companies: what for, how, and the NDA mechanics

*Claude Opus, May 2026. Written after Robin asked, very concretely, how you organise a meeting with a company like ZMT (email shape, the document, NDA, whether there's even a meeting, a "supermeeting" with many companies, mass-emailing, a pilot public site, commercial vs non-commercial tone) and admitted he doesn't actually know what he's trying to get out of it. Distilled from the current `email.txt` draft, `honest_analysis.md`, `standards_play.md`, `bioem_cairns_trip_and_azadeh_email.md`, `patent_decision_and_defense_mechanics.md`, the TechTransfer thread (`patent/meeting_email.txt`), `decisions.txt`, and `ROADMAP_12_months.md`. Opinion, not summary.*

---

## Start here: "I don't even know what we're trying to get out of it"

That is not a side-question. It is the whole question, and the reason the rest feels muddy. The line in your `email.txt` does the damage:

> Spreken met bedrijven --> Letter of Intent en businessplan validatie voor IOF

In one breath that bundles four genuinely different goals into one "talk to companies" task, and they pull in different directions. Until you split them, every tactical question (email shape, NDA, mass mail, website) has no stable answer because each goal answers it differently.

Here are the four. They are not the same activity.

**G1. Evidence for the IOF jury.** A couple of letters or documented conversations showing "market pull." This is bureaucratic, near-term, deadline-driven (3 August). The jury wants to see that someone other than you believes this is useful. `ROADMAP_12_months.md` targets 2-3 LOIs/pilot commitments, and `interview_questions.tex` line 343 confirms the jury literally asks "had je klantbewijs bijgevoegd? LOIs, gesprekken, marktonderzoek?" So this is real, but the bar is "a few credible letters," not "a sales pipeline."

**G2. Customer discovery (learning).** The 5-6 calls `honest_analysis.md` and `claude_career_advice_1.md` prescribe. The explicit instruction is *"the purpose is not to sell. It's to hear what they say when you show them a demo."* This is the kill-signal test: if you cannot make yourself do six of these in a few weeks, the spin-off is already broken. Output is notes and a sharper pitch, not a signature.

**G3. The ZMT / Sim4Life relationship.** The crown jewel, and the one you keep circling in `decisions.txt` ("do we really talk to ZMT soon, or later?"). This is a multi-year arc: matched validation -> co-present -> integrate/license -> possibly acqui-hire. `honest_analysis.md` Q8 is emphatic that the first ask to ZMT is *not* a license deal, it is a matched-validation collaboration ("we ran AEGIS against Sim4Life on Duke at 28 GHz, here are the figures, can we co-present at BioEM 2027?"). This is patient, post-patent, Wout-introduced. It is the wrong thing to rush for an August LOI.

**G4. Standards (IEC/IEEE 63195-2 2026).** Per `standards_play.md`, worth more than any single customer, and the window is 3-6 months. But this channel runs through Wout tabling a contribution to the working group, not through you cold-emailing companies. It is a different motion entirely. Mentioning it here only so you stop accidentally folding it into "talk to companies."

The punchline: **only G1 and G2 are "email companies this summer" activities.** G3 you *start* informally (face time, no transaction) and let mature. G4 is Wout's committee channel. If you keep those separate, the rest of your questions answer themselves.

---

## The tension you're actually feeling

The IOF deadline (G1) wants breadth and speed: collect a few letters before August. The ZMT play (G3) wants the opposite: patience, delicacy, nothing public before the patent, the first contact being a peer-to-peer collaboration rather than "sign my LOI."

If you let the August deadline drive, the failure mode is: you cold-approach ZMT/Sven Kühn this summer asking for an LOI to feed a grant form, before you have matched-validation figures and before the patent is filed. That is the one move that can sour the single most valuable relationship you have, and it does it for a soft bureaucratic artifact you could have gotten elsewhere.

So the resolution is to **route G1 to the safe, friendly contacts and keep ZMT on the slow track:**

- For IOF letters, go to people who can say "this is relevant and we'd be interested" cheaply and without high stakes:
  - the Ericsson contact Luc already has at NDA stage (Davide Colombi and co),
  - a national regulator (BIPT is local, ARPANSA is reachable through Carolina's grant),
  - a test lab (Eurofins, Verkotan) where a lab director can decide alone.
- ZMT gets the relationship track: informal face time at BioEM, a matched-validation collaboration proposal *after* the patent is filed and the figures exist. If an LOI from ZMT happens, it happens late and as a *consequence* of that, not as the opening move.

Your `email.txt` line 75 already gestures at this ("misschien nuttig om een meeting met NDA en LOI" with Sven Kühn). Fine, but that is a G3 meeting wearing a G1 costume. Handle it with the G3 rules below, not the quick-letter rules.

---

## Before you optimise for IOF, verify what IOF actually needs

This is a 30-minute action that could delete half the problem. Ask Filip (your IOF contact) *exactly* what evidence the jury wants for "market validation." The realistic answer is probably "2-3 letters of support or documented expressions of interest plus your discovery notes," not "signed commercial LOIs." If so, the entire "should I mass-email companies" question evaporates: you need a handful of warm letters, which is a relationship task, not a volume task.

Do not build an outreach machine for a requirement you haven't read. You have a documented pattern of researching for months before acting (the LETF thing, called out in your own files). Reading the IOF evidence bar is the cheap unlock here.

---

## The concrete mechanics: is there even a "meeting"?

There is, but "a meeting" is the wrong mental model. It's a **funnel**, and most contacts never reach the bottom of it. Each stage gates the next, and the NDA sits in the middle, not at the start.

1. **Warm intro (the highest-leverage step).** A one-line vouch from Wout or Luc beats any cold email you can write. `bioem_cairns_trip_and_azadeh_email.md` makes this point hard: get Wout to introduce you first. For ZMT specifically, Wout is in the Kuster/IT'IS orbit and can open the door. Use intros wherever they exist. Cold email is the fallback, not the default.

2. **The 30-minute intro call (no NDA).** This is "the meeting" for discovery and for most first contacts. High-level only: who you are, what the thing does, a short demo, and then you mostly listen. No confidential substance, so no NDA needed. You can do this on a video call. For pure G2 discovery, the call *is* the entire interaction. You don't escalate.

3. **The NDA (only when you need to go deeper).** If the conversation warrants showing the method, the validation internals, or the differentiability machinery, *then* you sign a mutual NDA before the technical meeting. The NDA gates technical depth, not the first handshake.

4. **The technical meeting (under NDA).** Confidential deck plus a live demo. This is where the real "what would make you use/buy this" conversation happens, and where, at the end, you make an explicit ask (collaboration, pilot, or a letter).

So: discovery contacts stop at stage 2. ZMT goes all the way to 4, slowly. IOF-letter contacts often only need stages 1-2 plus a short follow-up email.

### Who provides the NDA (concretely)

You do **not** draft your own NDA, and you do not freelance this. The IP is UGent's (Codex Hoger Onderwijs Art. II.285), and you already have a named IP adviser on the file: **Alessandro Biondi at TechTransfer (ref P2026/040).** TechTransfer has a standard mutual NDA. You ask Alessandro for it, he vets it, both parties sign.

Crucially, Alessandro has *already told you in writing* (his 11-13 May reply) not to share the monograph or draft paper externally until you've "agreed on a clear protection strategy for the assets disclosed." That is a hard constraint on this summer's outreach. **Before any technical company meeting, you need two things from him:** (a) the standard mutual NDA, and (b) explicit sign-off on what you may show and what stays back. Put that in your next email to him. It is also the honest answer to "do I talk to ZMT soon": you talk to ZMT as soon as the patent priority is filed and Alessandro clears the materials, and not before.

What a mutual NDA looks like, so it's demystified: roughly two pages, bilateral (both sides protect each other's info), a definition of "confidential information," a purpose limitation ("for evaluating a potential collaboration only"), a term (typically 3-5 years), an explicit no-license / no-IP-transfer clause, and Belgian law / Ghent courts. Standard. The university template already says all this. Your job is to send it, not write it.

### The two-document system

You need two artefacts, and conflating them is how people leak their own patent.

**Document A: the non-confidential one-pager (the teaser).** Attachable to a first email, shareable without an NDA, vetted by Alessandro. Contents:
- one line on the problem (FDTD is hours per scenario for APD pre-compliance),
- one line on what AEGIS does (per-point absorbed power density on a 3D body in milliseconds, 100 MHz to 100 GHz),
- the framing from `honest_analysis.md`: "accelerate pre-screening 100-1000x, then feed worst cases into Sim4Life for rigorous validation, then DASY for certification" (complement, not replacement),
- two or three screenshots of the viewer (it is visual and genuinely impressive, this is your best non-confidential asset),
- credentials line (Wout's group, npj Wireless Technology 2026, two BioEM prizes, Sim4Life competition win),
- *no* secret sauce: no pseudo-Brewster derivation, no Q operator, no claim internals.

**Document B: the confidential deck (NDA only, in-meeting).** The method, the validation figures, the differentiability story, the matched AEGIS-vs-Sim4Life numbers once they exist. This is what Alessandro is protecting. Never attach this to a cold email.

Note what `patent/meeting_email.txt` (Alessandro) asked you to prepare for *him*: a short deck splitting the geometric/non-coherent framework from the coherent MIMO framework, focused on which technical steps are essential and how they're implemented. That internal deck is closer to Document B and is a useful base for the confidential version, not the public one.

---

## What the email actually looks like

The model is the Azadeh rewrite in `bioem_cairns_trip_and_azadeh_email.md`. The lessons there generalise to every company email: lead with credibility, narrow to one specific ask, do not overclaim, treat the patent as administrative not mysterious, and (your Q7) **lean non-commercial.** In this community, "I have a method, here is validation, I'd value your perspective" outperforms "I'm launching a startup, want to buy a license" by a wide margin. The Kuster/BioEM/standards world trusts papers and validation, not landing pages and sales decks.

### Template 1: discovery + soft LOI (test lab, regulator, friendly contact)

> Subject: Fast APD pre-compliance method, would value 20 minutes
>
> Dear [name],
>
> I'm Robin Wydaeghe, a final-year PhD with Wout Joseph at UGent (INTEC-WAVES). I work on EM exposure assessment for 5G/6G, with first-author work in npj Wireless Technology (2026) and two BioEM prizes.
>
> Over the last months I've built a method that computes absorbed power density on a 3D body surface in milliseconds, across 100 MHz to 100 GHz, validated against published numerical results to within a few percent. It's meant as a fast pre-screening layer ahead of full-wave tools, not a replacement for them.
>
> I'm trying to understand whether this is useful to teams like yours, and I'd genuinely value 20-30 minutes to show a short demo and hear how [APD pre-compliance / site compliance] actually works on your side. One-page summary attached.
>
> Would a short call in the next two weeks work?
>
> Best,
> Robin

The LOI ask does *not* go in this email. It comes at the *end of the call*, once they've seen the demo and said something positive: "would you be open to a short letter that this is relevant to your work? It would help an innovation-fund application I'm preparing." Asking for a letter before they've seen anything is what makes you look like you're farming signatures.

### Template 2: ZMT / Sim4Life (peer, collaboration, not license)

> Subject: Closed-form APD method, possible matched validation against Sim4Life
>
> Dear [Sven / name],
>
> I'm Robin Wydaeghe, PhD with Wout Joseph at UGent. You may know our group through the IEC TC 106 / 63195-2 work. I previously placed in a Sim4Life competition with a 42k-line automation pipeline (GOLIAT), so I work inside your ecosystem rather than against it.
>
> I've developed a closed-form surface formulation for absorbed power density at mmWave that runs in milliseconds and matches published numerical results to a few percent. I see it as a fast pre-screening complement to Sim4Life: find the worst-case beam/grip/position scenarios in seconds, then run those rigorously in Sim4Life.
>
> Before anything else, I'd like to do a clean matched validation against Sim4Life on a standard 63195-2 reference scenario (e.g. a defined phone, Duke or Ella, 28 GHz). If the figures hold up, I think there's a natural joint contribution, possibly co-presented at BioEM 2027. Would you be open to a short call?
>
> Best,
> Robin

What this does (straight from `honest_analysis.md` Q8 and `standards_play.md`): establishes you as an ecosystem member (GOLIAT), frames AEGIS as complement not threat, opens with collaboration not a sale, and ties to the standards process which is a legitimate shared interest. The license conversation is deliberately absent. It comes years later, after trust.

Note the deliberate split Wout already proposed and you recorded in `email.txt`: Sven Kühn is the spin-off / ZMT-partner contact, Azadeh Peyman is kept for the competition/jury side because that's direct competition. Keep those people in separate lanes. Don't pitch partnership to the jury-side and don't pitch competition to the partner-side.

### During the meeting

A 30-minute structure that works:
- 5 min: who you are, the credibility line, why you're talking to *them* specifically.
- 8-10 min: the demo. Let the viewer do the work. It's fast and visual and that's your edge.
- 12-15 min: shut up and listen. Their workflow, their pain, what would make them actually use it, what they pay for today. For discovery this is the whole point. Talk less than them.
- 3-5 min: one explicit next step. Discovery: "can I follow up in a month?" LOI: "would you write a short letter?" ZMT: "shall we scope a matched validation?"

Follow up same day with a thank-you and the ask in writing.

---

## Your specific questions, answered crisply

**A "supermeeting" with many companies at once? No.** Three reasons. Competitors and partners can't speak freely in the same room (ZMT will never discuss a partnership in front of Nokia and Ericsson). NDAs are bilateral, so a group meeting muddies confidentiality. And you learn far less, because discovery is intrinsically 1:1. The *one* exception is a conference: BioEM is the natural "supermeeting" where you do many 1:1s in parallel without the awkwardness, in a room where your two prizes give you 10x signal-to-noise. That's your breadth venue, not a synthetic group call.

**Mass-email, infinite ambition, see everyone? No, and this is the most important reframe.** Your total addressable universe is ~200 organisations worldwide (`external_briefing.md`). This is a relationship game, not a volume game. Mass cold-emailing does three bad things: it burns the warm intros (Wout/Luc) that are your actual asset by going cold instead, it creates disclosure and reputational risk for a pre-patent deep-tech method, and it directly contradicts the explicit advice (5-6 quality calls, *not* 20+ blasts). "Infinite ambition" spent on email volume is ambition pointed the wrong way. The highest-ambition move available to you is *not* 50 emails. It is the matched AEGIS-vs-Sim4Life validation figure plus the ZMT relationship, which is a single deep relationship, not a broadcast.

**A pilot public website to look professional? Not yet.** Two problems. Disclosure: anything substantive on a public page is prior art and can sink the patent before it's filed. Smell: to an academic EM audience, a thin startup landing page reads as premature commercialisation, which is exactly the credibility you can't afford to spend. Your viewer is password-protected for precisely this reason, and that's correct. What to do instead: keep the password-protected demo and hand the link out selectively after an intro. *After* the patent is filed and a paper is public, a clean, academic-flavoured project page (method, validation, papers, "request access") is fine. A salesy product site is not, certainly not now.

**Commercial or non-commercial tone? Non-commercial, decisively, for this community.** This answers your Q7 directly. Peer-to-peer, validation-led, "I'd value your perspective" lands. Sales-led "want to license this" repels the exact people (Kuster orbit, standards committee, BioEM) whose trust is the whole game. You eventually need them to arrive at a commercial conclusion ("we'd use/pay for this"), but you get there by leading non-commercial and letting them get there themselves. The IOF letter is the same trick: lead with the method, let the interest become the letter.

---

## The hard constraint sitting over all of it: disclosure

You already worked this out in `decisions.txt` ("NDA customer calls are fine"), and you're right. Make it explicit so you don't trip:

- **Safe before the patent is filed:** 1:1 private calls and meetings under implicit professional confidentiality or an NDA, showing the password-protected demo to a named individual, listening, asking. EPO does not treat these as public disclosure.
- **Not safe before the patent is filed:** a public website with substance, mass cold emails describing the method, a conference poster/booth/demo, handing out figures, sharing the monograph or draft paper (Alessandro explicitly asked you not to).

So the patent timeline gates the *public* surface of your outreach, but it does *not* block the private NDA conversations. You can run all six discovery calls now. You cannot put the method on a public site now. That distinction is the whole game.

---

## What I'd actually do this summer

1. **This week: email Alessandro.** Ask for (a) the standard mutual NDA template and (b) written sign-off on what you may show companies before priority filing. This unblocks every technical meeting and is the honest gate on the ZMT timing.
2. **This week: ask Filip what the IOF jury actually needs** for market validation. Read the bar before building for it.
3. **Build Document A** (the non-confidential one-pager) and get Alessandro to clear it.
4. **Run the 6 discovery calls** through warm intros: 1 ZMT-orbit person (via Wout, informal, no LOI ask), 2 OEM/test-lab, 1 Ericsson (via Luc's existing contact), 1 regulator (BIPT or ARPANSA via Carolina), 1 spare. Not to sell. To listen. This is the kill-signal test. If you can't do six in four weeks, that tells you something true.
5. **Get 2-3 soft letters** from the friendly end of those calls for IOF. Not from ZMT.
6. **Treat ZMT as a relationship, not a transaction this summer.** Informal face time at BioEM (attend-only until the patent is filed), then the matched-validation proposal once the figures and the priority filing exist.

## The one thing that makes all of it work

The matched AEGIS-vs-Sim4Life validation figure on a standard 63195-2 scenario (`honest_analysis.md` Q3/Q8, `standards_play.md` step 2). Two to four weeks of focused work, GOLIAT drives the Sim4Life side. With it, every conversation in this doc is 10x stronger and the standards contribution becomes real. Without it, you're pitching a claim. If you have surplus ambition and energy this summer, that figure and the near-field paper are where it should go, not into outreach volume. The emails are downstream of having something undeniable to show.
