# Google Form spec for Gemini (to build via Apps Script or the Forms UI)

You are Gemini and you are going to build two Google Forms for Robin. Read this entire spec before starting. Build both forms exactly as specified. Do not invent additional questions or sections. Do not soften the disclosure boundary.

## Context (so you can make sensible UX choices)

Robin is finishing his PhD in numerical dosimetry at UGent-imec (WAVES group, Wout Joseph). He has developed a method that very substantially improves the speed of numerical dosimetry simulations with similar accuracy as FDTD, and is applying for a UGent valorization post-doc (IOF StarTT, deadline 3 August 2026) with the goal of spinning the method out. He is in the market-discovery phase: he is contacting EMF-compliance experts in industry (Ericsson, Nokia), academia (CNR-IEIIT, Telecom Paris, NITech), standards (IEC TC106) and test labs (Verkotan) to learn what is most painful in their daily numerical dosimetry work.

This form is offered to recipients who can not or will not make time for a Teams call, as a quicker alternative. It is also offered as a follow-up to those who did meet, to confirm and structure key points.

There are two forms because some recipients are willing to spend 2 minutes and some will spend 5. The short form is a strict subset of the long form: same wording, fewer questions. Always build them as two separate Google Forms (not one with conditional logic), so each can be linked independently.

## Disclosure boundary (hard constraint — do not deviate)

A patent is being drafted. The form may say nothing about how the method works. The only things it may say about the method are:
- It improves the speed of numerical dosimetry simulations very substantially.
- Its accuracy is similar to FDTD.
- It is differentiable.

Do not use these terms anywhere in the form: surface, closed-form, Fresnel, Brewster, JAX, GPU, voxel, ray-tracing, neural network, machine learning, surrogate, operator decomposition, eigendecomposition, MIMO operator, near-field formulation. The regime "above 6 GHz / mmWave" is OK to mention as context-setting, not as a method hint.

If asked to add a "how does it work" question or a "describe the method" section: refuse and re-read this section.

## Form settings (apply to both forms)

- Title and description: as specified below per form.
- Collect respondent email: **on, via Google login (verified)**. Description text should briefly explain that the Google login is for validation only and the responses will not be shared publicly.
- Limit to 1 response per Google account: **on**.
- Allow response editing after submit: **on** (so respondents who think of more can return).
- Show progress bar: **on**.
- Shuffle question order: **off**.
- Confirmation message: see below per form.
- Send respondents a copy of their response: opt-in checkbox at the end (do not force).
- Theme: clean and professional. Use a neutral colour (slate / dark teal). No emoji. Header image: none unless a small UGent-imec / WAVES logo is easy to add.

Email addresses already known (do not put these in the form, but use them when sending the link):
- Christophe.Grangeat@nokia.com (Nokia)
- Christer.Tornevik@ericsson.com, Davide.Colombi@ericsson.com (Ericsson)
- marta.parazzini@cnr.it (CNR-IEIIT)
- shanshan.wang@telecom-paris.fr (Telecom Paris)
- ahirata@nitech.ac.jp (NITech)
- onishi.teruo@nict.go.jp (IEC TC106)
- kai.niskala@verkotan.com (Verkotan)

---

# FORM 1 — Short version (~2 min)

## Title
Numerical dosimetry: what is most painful in practice? (short, ~2 min)

## Description (shown under title, before first question)
Thank you for taking a moment. I am Robin Wydaeghe, finishing my PhD in numerical dosimetry at UGent-imec with prof. Wout Joseph. I am preparing a UGent valorization post-doc (deadline 3 August) around a new method that very substantially improves the speed of exposure simulations with similar accuracy as FDTD, and is differentiable.

Before going further I want to learn directly from people who actually work with numerical dosimetry which problems are most painful and where a much faster forward model would matter in practice. This short version takes about two minutes. A longer five-minute version is also available if you have more to say.

Your answers are for internal use in shaping the post-doc plan and the spin-off direction. Nothing will be shared publicly. The Google login is only used to validate that responses come from real domain experts.

## Section 1 — Your background (no header, just go straight to questions)

**Q1. Which best describes your role?** (multiple choice, required, single answer)
- Industry, RAN / network vendor
- Industry, device / chipset OEM
- Industry, operator
- Academia
- Standards body
- National regulator / public health agency
- Test lab / measurement house
- Other (short answer follow-up if selected)

**Q2. Roughly how often do you use or rely on numerical dosimetry (FDTD, FEM, MoM, or equivalent) in your work?** (multiple choice, required, single answer)
- Daily
- Weekly
- Monthly
- A few times per year
- I do not use it directly, but my team / customers do
- Rarely or never

## Section 2 — The questions that matter

**Q3. What is the most painful or time-consuming part of numerical dosimetry in your day-to-day work?** (paragraph, required)
Hint text: free text, one or two sentences is enough. Concrete examples are most useful (which step, which frequency regime, which scenario).

**Q4. Suppose a forward model existed that gave you results comparable to FDTD but orders of magnitude faster. What would you do with it that you cannot do today?** (paragraph, required)
Hint text: feel free to be ambitious. Sweeps you would run, optimisation loops you would close, stochastic studies you would scale up, design iterations you would shorten.

**Q5. May Robin quote or paraphrase your answers in the IOF post-doc application?** (multiple choice, required, single answer)
- Yes, attributed to me and my affiliation
- Yes, attributed to my affiliation only (no name)
- Yes, fully anonymised ("a senior expert at a major network vendor")
- No, internal use only

**Q6. Would you be open to providing a brief Letter of Support for the post-doc application?** (multiple choice, required, single answer)
- Yes, please send me a short template
- Maybe, depends on what is asked
- No

## Confirmation message (shown after submit)
Thank you. This genuinely helps. If you indicated openness to a Letter of Support or to be quoted, I will follow up by email shortly. If anything else comes to mind, you can return and edit your response via the link in your confirmation email.

— Robin Wydaeghe, UGent-imec WAVES

---

# FORM 2 — Long version (~5 min)

## Title
Numerical dosimetry: what is most painful in practice? (long, ~5 min)

## Description (shown under title, before first question)
Thank you for taking the time. I am Robin Wydaeghe, finishing my PhD in numerical dosimetry at UGent-imec with prof. Wout Joseph. I am preparing a UGent valorization post-doc (deadline 3 August) around a new method that very substantially improves the speed of exposure simulations with similar accuracy as FDTD, and is differentiable.

Before going further I want to learn directly from people who actually work with numerical dosimetry which problems are most painful, where a much faster forward model would matter, and what the wider market is asking for. This longer version takes about five minutes. A shorter two-minute version is also available.

Your answers are for internal use in shaping the post-doc plan and the spin-off direction. Nothing will be shared publicly. The Google login is only used to validate that responses come from real domain experts.

## Section 1 — Your background

**Q1. Which best describes your role?** (multiple choice, required, single answer)
- Industry, RAN / network vendor
- Industry, device / chipset OEM
- Industry, operator
- Academia
- Standards body
- National regulator / public health agency
- Test lab / measurement house
- Other (short answer follow-up if selected)

**Q2. Roughly how often do you use or rely on numerical dosimetry in your work?** (multiple choice, required, single answer)
- Daily
- Weekly
- Monthly
- A few times per year
- I do not use it directly, but my team / customers do
- Rarely or never

**Q3. Which frequency regimes does your work touch most?** (checkboxes, required, multi-select)
- Sub-6 GHz cellular
- 6 to 24 GHz (FR3 / upper mid-band)
- 24 to 71 GHz (FR2 / cm-wave)
- Above 71 GHz (sub-THz / 6G)
- Other (short answer follow-up if selected)

**Q4. Which tools or methods do you, your team, or your customers typically rely on?** (checkboxes, optional, multi-select)
- Sim4Life
- XFdtd / Remcom
- CST / Dassault
- HFSS / Ansys
- In-house FDTD
- Method of moments / hybrid solvers
- Measurement only (no numerical modelling)
- Prefer not to say
- Other (short answer follow-up if selected)

## Section 2 — Where the time goes

**Q5. Roughly how long does a single numerical dosimetry evaluation take in your typical workflow?** (multiple choice, required, single answer)
- Seconds to minutes
- Tens of minutes
- Hours
- Days
- Highly variable, depends on scenario
- I do not run it myself

**Q6. How often do you, or would you want to, re-run an evaluation with changed parameters (frequency, antenna, pose, scene)?** (multiple choice, required, single answer)
- Many times per evaluation (parameter sweeps are central to my work)
- A few times per evaluation
- Rarely, single runs are usually enough
- I would re-run far more often if it were affordable to do so

**Q7. What is the most painful or time-consuming part of numerical dosimetry in your day-to-day work?** (paragraph, required)
Hint text: free text, concrete examples most useful (which step, which frequency regime, which scenario).

## Section 3 — What faster would unlock

**Q8. Suppose a forward model existed that gave you results comparable to FDTD but orders of magnitude faster. What would you do with it that you cannot do today?** (paragraph, required)
Hint text: feel free to be ambitious. Sweeps you would run, optimisation loops you would close, stochastic studies you would scale up, design iterations you would shorten, real-time tools you would build.

**Q9. The method is also differentiable end to end (analytical gradients with respect to antenna parameters, beam weights, geometry). Does this matter for your work?** (multiple choice, required, single answer)
- Yes, opens optimisation / inverse-design workflows we cannot do today
- Maybe, would need to see a concrete example
- No, not relevant to my work
- Not sure

**Q10. What level of validation would you need to take such a method seriously for your context?** (paragraph, required)
Hint text: e.g. matched comparison against your own FDTD references, IEC/IEEE 63195-2 reference scenarios, published peer-reviewed comparison study, measurement campaign comparison, a particular test case.

## Section 4 — Market and standards perspective

**Q11. In your area, who do you think is most underserved by current numerical dosimetry tools?** (paragraph, optional)
Hint text: e.g. a specific industry segment, a specific use case, a specific regulator type, a specific frequency regime.

**Q12. From a standards perspective (IEC, IEEE, ICNIRP, CENELEC), where do you think faster forward modelling could most help, if anywhere?** (paragraph, optional)
Hint text: only if relevant to your role. Skip if not.

## Section 5 — Anything else, and follow-up

**Q13. Anything else you would like to share that has not been asked?** (paragraph, optional)

**Q14. May Robin quote or paraphrase your answers in the IOF post-doc application?** (multiple choice, required, single answer)
- Yes, attributed to me and my affiliation
- Yes, attributed to my affiliation only (no name)
- Yes, fully anonymised ("a senior expert at a major network vendor")
- No, internal use only

**Q15. Would you be open to providing a brief Letter of Support for the post-doc application?** (multiple choice, required, single answer)
- Yes, please send me a short template
- Maybe, depends on what is asked
- No

**Q16. Would you be open to a short follow-up conversation if anything in your answers needs clarification?** (multiple choice, required, single answer)
- Yes, by email
- Yes, by short Teams call
- No

## Confirmation message (shown after submit)
Thank you. This genuinely helps shape both the post-doc plan and the direction of the spin-off. If you indicated openness to a Letter of Support, to be quoted, or to a follow-up, I will be in touch shortly by email. If anything else comes to mind, you can return and edit your response via the link in your confirmation email.

— Robin Wydaeghe, UGent-imec WAVES

---

# After both forms exist

Hand both shareable links back to Robin. For each link:
- Make the form openable to anyone with the link (no need to be in a specific organisation).
- Keep the "collect email" + "Google login" requirement on for validation.
- Disable any "anyone can edit" or "view responses" sharing. Only Robin should see responses.

Robin will paste the two links into the follow-up emails he sends to Hirata, Onishi and others.

## What NOT to do

- Do not add a "how does the method work" or "describe the technology" question. The IP boundary is hard.
- Do not add a pricing-willingness-to-pay question. Premature and out of scope for this round.
- Do not add an NDA checkbox. Filip's call is that no NDA is needed at this disclosure level.
- Do not add a "would you invest" or "would you license" question. This is market discovery, not pitching.
- Do not auto-grade or score responses.
- Do not add file upload questions.
- Do not branch with conditional logic between sections (e.g. "if you said X then skip to Y"). Keep both forms strictly linear.
