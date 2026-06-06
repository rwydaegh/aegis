# Alessandro email — drafts and merge analysis

Working notes on the email to Alessandro Biondi (UGent TechTransfer) asking for permission to start outreach before the patent draft is finalised.

Three versions exist. This file captures all three, the diff, and the merge recommendation.

## Version 1: original baseline (on disk at `mail.txt`)

```
Dear Alessandro

Find attached a list of things we say and do not say to any parties. A list of parties is also included with e-mail addresses.

The meetings should be over 70% listening and 30% pitching (roughly), while remaining relatively short and vague on the details of the IP. This allows us to gather informa

You recommend ensuring first drafting the patent application, but given the deadline of IOF 3rd of August and an intake meeting before, me and Wout would find it ideal if either the draft is finished relatively soon, or we are permitted to share without reaching a draft application. This allows enough time to plan these calls.

Kind regards
Robin
```

Note: line 5 cuts off mid-word at "informa" (was probably "information").

## Version 2: chat draft (Claude, mid-session)

```
Dear Alessandro,

Find attached a draft bundle:
- a one-pager describing AEGIS at the level we are comfortable showing externally,
- two short cover notes (one for academic recipients, one for Ericsson via Luc),
- a say / don't-say matrix capturing the disclosure boundary.

A separate list of parties with emails follows.

The meetings will be over 70% listening and 30% pitching, short, and vague on the details of the IP. The discipline is in the matrix.

A concrete proposal on NDA, for your decision. Tiered approach. For academic recipients (Sapienza, CNR-IEIIT, Shanshan Wang with Wiart in cc, Onishi, Schmid, later Hirata), no NDA. The one-pager is calibrated to abstract-level disclosure, the matrix handles the rest, and per-recipient SharePoint turnaround would push us past the IOF deadline of 3 August. For industry (Ericsson first, through Luc; Nokia and device OEMs later), NDA before the call, since joint roadmap content needs a confidentiality envelope. We hold to the matrix in both cases.

I will also record a curated 90-second demo (Ghent base station, phantom, APD heatmap, ICNIRP compliance check, frequency sweep — no MIMO/ECBF/operator panels). Hosted password-gated on our own waves-ugent.be infrastructure, not on YouTube or any third-party platform, viewing logged and revocable at any time. I send it to you for sign-off before any external share.

On sequencing: given the August deadline, we would prefer to run the call schedule in parallel with the patent draft rather than serial. The Ericsson call would be first and would not happen until you are comfortable.

Three questions:
- Are you comfortable with the tiered NDA proposal, or do you want an NDA for every recipient?
- Would you like to be on any of the first calls, in particular Ericsson?
- Rough ETA on the patent draft, so we can plan around it?

Happy to meet on this if easier than email.

Kind regards,
Robin
```

## Version 3: Robin's current direction (with body filled in)

```
Dear Alessandro,

In your previous e-mail you mentioned waiting for the patent application draft before contacting external parties.

However, the IOF intake conversation is currently being considered for mid-to-late June rather than late July, as Nancy let me know several people are on holiday during July. Depending on the progress of the draft, this may not leave enough time to schedule these conversations before the intake meeting.

Would it be possible to proceed under NDA without waiting for the application draft to be complete? Concretely, I would like to meet or correspond with:

- Ericsson EMF Research: Christer Törnevik and Davide Colombi
- Nokia EMF: Christophe Grangeat
- Télécom Paris (leading academic group): Shanshan Wang, Joe Wiart in cc
- CNR-IEIIT Milan (leading academic group): Marta Parazzini
- Nagoya Institute of Technology (leading academic group): Akimasa Hirata and colleagues, current ICNIRP Chair, co-chair IEEE ICES SC6
- IEC TC106 (standards): Teruo Onishi, Chair
- Verkotan (test lab, FR2 OTA specialty): Kai Niskala, co-convener IEC/IEEE 63195

The content of the first e-mail would be along these lines:

> Dear [Name], I am Robin Wydaeghe, finishing my PhD with Wout Joseph at IMEC/Ghent University. Together with the WAVES group we have built AEGIS, a JAX-based forward model for absorbed power density in the 6 to 100 GHz regime. It is closed-form on the surface and end-to-end differentiable, which collapses the inner loop of an exposure study from hours to seconds. A one-page summary is attached. I would value a short call to hear how the speed and differentiability would change the studies your group does, and what you would want to see validated to take the method seriously. I am not asking for adoption, only for an honest read.

The opening line is lightly tailored per recipient. For Ericsson, the hook is the Bern in-situ matched-validation opportunity with Luc Martens as the bridge. For Nokia, Wout's standing relationship through Mike Wood and the IEEE ICES committee. For Verkotan, the IEC/IEEE 63195 standards-committee tie. The disclosure boundary is identical across all recipients and follows the say/don't-say matrix in the attached bundle.

Kind regards,
Robin
```

## Diff: Version 2 to Version 3

What V3 dropped from V2:
- Tiered NDA proposal (academic no-NDA, industry NDA). V3 accepts NDA for all.
- 70/30 listening/pitching frame.
- Demo video paragraph (Ghent scene, self-hosted, sign-off).
- "Happy to meet if easier" closing offer.
- Three questions for Alessandro (tiered NDA / attendance / patent ETA).

What V3 added on top of V2:
- Explicit acknowledgement of Alessandro's prior position (wait for draft).
- New timing fact: intake meeting moved to mid-to-late June because of July holidays.
- Explicit 7-name list with one-line roles.
- "Content of first e-mail would be:" quoted body paragraph.
- Per-recipient hook tailoring note (Ericsson via Luc, Nokia via Mike Wood, Verkotan via 63195).

## Direction call

V3 is the right direction. It meets Alessandro where he is (TT defaults to NDA-everywhere) and asks for one specific thing (don't gate on patent draft). Cleaner than V2's negotiation posture.

## What's worth merging from V2 into V3

Five items, in priority order.

### 1. Bundle attachment reference (essential)
Without it, Alessandro reads about the disclosure boundary instead of seeing it. One line, anywhere near the top:
> The disclosure boundary is captured in the attached bundle: the one-pager, two cover notes (academic and Ericsson), and the say / don't-say matrix.

### 2. Demo video paragraph (high value)
Gives Alessandro a concrete artifact he can pre-approve. Strengthens the "let me share now" ask.
> I will also record a curated 90-second demo (Ghent base station scene, phantom, APD heatmap, ICNIRP compliance check, frequency sweep, no MIMO/ECBF panels). Hosted password-gated on our own waves-ugent.be infrastructure, not on YouTube or any third-party platform, viewing logged and revocable. I send it to you for sign-off before any external share.

### 3. Patent-draft ETA question (cheap, useful)
Alessandro probably has a date in mind but won't volunteer it. Cheap to ask, sets the planning horizon for everything else.
> What is your rough ETA on the patent draft, so we can plan around it?

### 4. "Happy to meet if easier than email" (small but useful)
One-line offer, signals you're not trying to corner him into a written commitment.

### 5. Attendance question (optional)
> Would you like to be on any of the first calls, in particular Ericsson?

## What to leave out of V3

- Tiered NDA proposal. Robin pivoted. Don't relitigate.
- 70/30 listening/pitching frame. Lives in the bundle. Not essential in the email.
- The "draft is finished soon OR permitted to share" either-or framing from V1. V3's "proceed under NDA without waiting" is sharper.

## Merged-version skeleton (not written yet)

Section order, in order to flow naturally:
1. Acknowledge prior position
2. New timing fact (June intake)
3. Ask: NDA without waiting for draft
4. Bundle attachment reference
5. List of 7 recipients with roles
6. Content of first e-mail (quoted body)
7. Per-recipient hook tailoring note
8. Demo video paragraph
9. Three small questions: ETA, attendance, anything else
10. Happy to meet, sign-off

## Open questions before sending

- Attach the bundle PDF (`one_pager_bundle.pdf`) explicitly or send separately
- Whether to send today and start Alessandro's clock, or wait until the demo video exists
- Whether to mention the Verkotan/Niskala 63195 angle in the body or save for the call (it's a quiet asset, may be worth not surfacing in writing if Alessandro routes the email to colleagues)
