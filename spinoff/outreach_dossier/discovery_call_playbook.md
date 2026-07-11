# Discovery call playbook

For the warm/expert calls in the IOF run-up. Primary worked example: **Marta Parazzini (CNR-IEIIT), tomorrow 10:30**. Reusable for **Nokia (Fri), Ericsson (this week), Hirata (questionnaire), Shanshan/Wiart, test labs, BIPT**. You will not ask everything. Pick 6-10 questions that fit the person and let the conversation breathe.

---

## 0. The frame before you dial (30 seconds in your head)

**Your three goals, in order:**
1. **Listen.** Genuinely learn their pain, their numbers, who pays. This is real, not a pretext.
2. **Land a support letter** (lightest ask, costs them nothing, highest IOF value).
3. **Soft license-interest** (only where it fits, and only as a non-binding note). Drafts are ready in `letters/`.

**The disclosure guardrail (Filip's rule, do not cross it):** you may only describe the method as *"a method that very substantially improves the speed of exposure simulations, with accuracy similar to FDTD, and is differentiable."* No mechanism, no "closed-form", no "Fresnel", no equations. Patent is pending. If anyone pushes on *how*, deflect warmly: *"that's exactly the part still under patent drafting, so I have to keep it closed for now, but happy to talk about what it does."*

**The ask ladder (climb only as far as the warmth allows):**
support letter → soft note of license interest → (industry only) a future pilot / alpha test → a referral to someone else. Always get at least the referral.

**Tone dial:**
- *Peer / chill* (Marta, Shanshan): you know them, skip the throat-clearing, talk shop.
- *"You may remember me"* (Ericsson, Nokia): light, small-favour framing, generous on their time.
- *Formal* (Hirata, Onishi): self-introduction, defer to their seniority, accommodate timezone.

---

## 1. Opening (1-2 min)

- Thank them, restate the purpose: *"This isn't a sales call, I genuinely want to learn what's painful for you and what the field actually needs, to point the project the right way and strengthen the application."*
- Set the clock: *"I have ~30 min in mind, tell me if you need to drop earlier."*
- Ask permission to take notes (and, if useful and they're comfortable, to capture a quote for the application later, you'll confirm wording).

---

## 2. The question bank (the core, grouped by theme)

### A. Their world and workflow
- Walk me through what a typical dosimetry study looks like for you, end to end.
- Which tools and solvers are in your daily pipeline? (Sim4Life? in-house FDTD? something else?)
- Where does the time actually go, setup, solve, post-processing, or interpretation?
- How much of it is one-off research vs. work that has to satisfy a standard or a sponsor?

### B. The pain (this is the gold, dig here)
- What is the single most painful or slow part of numerical dosimetry for you today?
- Is there a study you *wanted* to run but couldn't, because it was too slow or too expensive?
- How long does one high-frequency configuration take you? And how many do you run in a typical project, or per year?
- What do you currently approximate, coarsen, or skip purely because of compute limits?
- If your compute budget were effectively unlimited, what would you do tomorrow that you can't do now?

### C. Scale and volume (this sizes the value of speed)
- How many configurations, body models, postures, or frequencies in a typical sweep?
- For stochastic or population studies, how many runs does one study need, and how long does that take wall-clock?
- Where is the real bottleneck, the cost of a *single* run, or the *number* of runs you need, or both?

### D. Accuracy and trust (what would they need to believe?)
- What accuracy relative to FDTD would a fast method need before you'd actually trust it in your work? A few percent? Ten?
- What kind of validation would convince *you*, and what would convince your reviewers, regulators, or sponsors?
- In which regimes or geometries do you most distrust today's fast or approximate methods?

### E. Optimisation and design (your unique angle, stay needs-level)
- Do you ever do any kind of optimisation, antenna placement, beam configuration, exposure minimisation? How do you do it today?
- Would it change your work to have the *sensitivity* of exposure to design parameters available directly, rather than re-running a sweep?
  *(Probe the need only. Do not explain how you provide it.)*

### F. Market and who pays (IOF valorisation gold, ask everyone)
- In your view, who in the field or industry would actually *pay* for a fast tool like this, and why them?
- Where's the real budget, academia, OEMs, operators, test labs, regulators?
- Honestly, for a group like yours, would something like this be a license you'd buy, or only something you'd use if it came bundled in a grant or a collaboration?
- Which organisations do you think feel this pain most acutely right now?

### G. Competitive landscape
- Are you aware of anyone else building fast, surrogate, or ML-based dosimetry? (Listen for: Split/Kapetanovic, Ansys SimAI, ML surrogates, in-house tools.)
- How do people get around FDTD's slowness today, coarser meshes, fewer cases, surrogates, just waiting?
- What do you find missing or untrustworthy in the fast approaches that already exist?

### H. Standards and regulation (especially Marta, Hirata, Ericsson, Wiart)
- Where do you see the standards heading on computational and fast methods? (IEC/IEEE 63195-2 Ed.2, IEC 62232.)
- What would it realistically take for a fast method to be *accepted or referenced* in a standard?
- Is the move toward aggregate / total exposure (uplink device + downlink network) real and coming, in your view?

---

## 3. Tailored add-ons per contact

**Marta Parazzini (CNR-IEIIT, GOLIAT peer, stochastic + ML dosimetry, the 2025 *Sensors* shape+skin-layering paper):**
- Your ML/surrogate work is data-hungry, would a fast forward model to generate training data change how you build surrogates?
- In GOLIAT's population/stochastic studies, what's the run-count that hurts?
- The "one physics from device to base station" idea, does that resonate with where you see RIS / mmWave going?
- (Warmest path to the support letter, she already said "sure" to the call.)

**Ericsson (Colombi, Tornevik) / Nokia (Grangeat):**
- Walk me through how compliance actually gets done for a new base-station / massive-MIMO product, where's the slow step?
- Exclusion zones and time-averaged EIRP, where does conservatism cost you, and would faster body-aware assessment help defend tighter zones?
- Build vs. buy: when your team needs a capability like this, do you build internally or license?
- Would you ever pilot something like this on a real internal scenario?

**Hirata (NITech, ICNIRP):**
- You mentioned, unprompted, whole-body / large-scale exposure at higher frequencies, can you say more about why that direction matters?
- Who do you think pays for fast dosimetry, academia or industry?
- (Mostly via the questionnaire already, this call/quote is about standards weight and the market signal.)

**Test labs (Verkotan, Eurofins, CETECOM):**
- What's the turnaround-time pressure on your measurement / pre-compliance work?
- Would a fast pre-screening step (find worst cases before measuring) save you real time and money?

---

## 4. Landing the asks (the close, 3-4 min)

**Step 1, the support letter (everyone you have any rapport with):**
> "This really helps. Would you be willing to write a short letter of support for the application, just saying the need is real for the field? I actually have a draft you can start from and change however you like, so it's a five-minute thing. No pressure at all."

**Step 2, the soft license interest (only where it felt warm):**
> "And if you'd be comfortable, a single line that you'd be interested in possibly using or licensing it if it ever becomes available, fully non-binding, would be really valuable. But only if that feels right to you."

**Step 3, quote permission (for the IOF text):**
> "If something you said ends up shaping a sentence in the application, may I paraphrase it? I'll send you the exact wording for approval first."

**Step 4, the referral (always, even if everything else is a no):**
> "Who else do you think I should talk to about this?"

**Step 5, next step:** agree a concrete follow-up (you'll send the letter draft today / they'll reply by X / a second call).

---

## 5. Capture template (fill in during and right after the call)

```
Contact / date:
Pain points (verbatim where possible):
Numbers: run time per config = ___ | runs per project/year = ___ | willingness to pay = ___
Who pays / market signal:
Competitors or alternatives mentioned:
Standards / regulatory signal:
Accuracy bar they'd need to trust it:
Asks landed:  support letter [ ]  license interest [ ]  quote permission [ ]  referral [ ]  pilot [ ]
Referrals (names):
Follow-up actions + by when:
```

---

## 6. Quotable evidence for the IOF application

Tag every strong quote to where it would land in the proposal:
- **Opportunity / problem** ← "the slow part is...", "we can't run X because..."
- **Target market / who pays** ← "the people who'd pay are..."
- **USP / competitive** ← "nothing out there does..."
- **Standards tailwind** ← "the standards are heading toward..."
- Hirata's unprompted line ("whole-body / large-scale exposure at higher frequencies for mmWave dosimetry") is already a strong **opportunity** quote, pending his permission tier.

---

## 7. Don'ts

- Don't reveal methodology. Ever. ("Patent drafting, has to stay closed for now.")
- Don't pitch or sell, you're listening. Selling now reads as pushy and weakens the favour framing.
- Don't promise validation collaborations or joint papers (per your decision, those are off the table).
- Don't oversell "real-time", talk batch throughput and turnaround, which is what they actually need.
- Don't overstay. End on time unless they pull you longer.
- Don't push the license-interest line on anyone hesitant, the support letter alone is already a win.
