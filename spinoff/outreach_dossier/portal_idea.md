# AEGIS outreach portal: the idea

A per-recipient web portal that bundles the AEGIS pitch artifacts and the recipient response actions into one password-gated landing page on `demo.aegis.waves-ugent.be`.

## Vision

When you reach out to a PI, regulator, or industry contact, they receive a personalised link to a single page that holds everything they need to engage:

- A short welcome line addressed to them
- The 90-second curated demo video, embedded
- The shared one-pager PDF, downloadable
- An NDA, signable in-portal (industry recipients only, post-patent)
- A letter-of-support template, pre-filled with their institution
- A Calendly embed for booking a 30-minute call
- A short feedback field

Each action is logged. You see who watched the demo, who downloaded the one-pager, who scheduled, who signed, who left feedback. Per-recipient analytics drive your follow-up timing.

The pattern is standard for B2B startup outbound (DocSend, PandaDoc, custom deal rooms). It works because it compresses the recipient's decision into one place and gives the sender real signal about engagement.

## Why this is a v2, not v0

The portal vision is correct strategically. The v0 build is wrong for August 3.

1. **Build cost.** Full v1 with embedded e-signatures is two to three weeks of focused work (auth, signature provider integration, recipient personalisation, LoS template engine, deal-room state, audit trail). That competes with patent draft, IOF application, demo video production, and call execution.
2. **NDA signing is TT's flow.** UGent TechTransfer runs NDAs through their SharePoint template and their eIDAS-compliant provider. Building an alternative signing flow in our portal is a process change Alessandro and UGent legal would have to authorise. That conversation slows August down rather than speeding it up.
3. **LoS signing is institutionally fragmented.** Academic letters of support happen as "PDF on institutional letterhead, signed by PI, scanned, emailed back." Some recipients need dean co-sign or legal review. A click-to-sign flow that bypasses their internal process may be rejected by their TT office. Friction is dominated by the PI's calendar, not the signing UX.
4. **The current bottleneck is upstream of the portal.** What slows August is the NDA decision from Alessandro, Hirata's email reply, the Luc-T\"ornevik activation. A nicer UI does not move those.

## Phased rollout

### MVP, this week or next (4 hours of work)

Sufficient for August 3.

- Static landing page at `demo.aegis.waves-ugent.be`, password-gated via Caddy basic auth
- One password per recipient batch (academics, industry, regulators)
- Embedded 90-second video, hosted as MP4 on the same server
- One-pager PDF download
- Letter-of-support Word template download with institution name pre-filled per batch
- Calendly embed for booking a call
- Reply-by-email footer
- Caddy access log as the analytics layer

### V1.5, mid-June if useful

Better recipient targeting.

- Per-recipient token URLs replace the shared password
- Each PI lands on a page with their name on it
- Finer-grained access log: per-recipient view counts, time on page, downloads
- Optional soft CTA differentiation by recipient tier (letter vs joint validation vs process consultation)

### V2, post-patent, autumn at earliest

Full portal once the patent is filed, the BV is set up, the sales pipeline starts, and there is a legal provider relationship outside of UGent TT.

- Embedded DocuSign (or eIDAS-compliant equivalent) for NDA signing, but only after Alessandro and UGent legal sign off on the workflow change
- Structured feedback intake with categorised fields
- Scheduled-call status tracking (booked, confirmed, completed, notes)
- Multi-stage funnel tracking and pipeline visualisation
- Integration with whatever CRM the spin-off settles on
- Optional per-recipient personalised content (e.g. one-pager footnote referencing their own work)

## Legal and process notes

- **eIDAS tiers.** Belgium and EU recognise three e-signature tiers: SES (checkbox), AES (DocuSign-equivalent), QES (eID-based, itsme). For academic NDAs, SES is plenty. For industry NDAs, AES is the realistic standard. QES is overkill outside Belgian-operator conversations.
- **TT provider preference.** Ask Alessandro what e-sig provider TT uses before designing any portal NDA flow. Build to integrate with their choice, not around it.
- **LoS authority.** Some institutions restrict LoS signature authority to the dean or the legal office, not the PI directly. Provide a Word template the PI can route internally, not a click-to-sign that bypasses their chain.
- **GDPR.** A portal that logs viewer behaviour processes personal data. A short data-processing notice on the landing page is enough for the MVP. For V2, the spin-off BV needs a proper DPA with any third-party signing or analytics provider.

## What the MVP is NOT trying to do

- Replace TT's NDA flow
- Standardise the LoS process across institutions
- Run a CRM
- Track conversion funnels
- Look like enterprise software

It is a tidy, professional landing page that holds the artifacts and a couple of CTAs. The point is to keep IP discipline tight, to look serious, and to give recipients somewhere obvious to act from.

## Open questions

- Does Alessandro have a preferred e-sig provider for when V2 NDA signing becomes relevant?
- For LoS, do we provide one template or one per recipient tier (academic, regulator, industry)?
- Calendly is convenient but US-hosted SaaS. Acceptable for academic outreach, or do we prefer a self-hosted scheduling tool (Cal.com)?
- Do we want per-recipient analytics in the MVP (token URLs) or is a shared-password access log enough?
- Branding: AEGIS, waves-ugent.be, or the spin-off BV name (once registered)?

## Where this lives in the timeline

- MVP build: weeks 1 to 2 of the 60-day plan, alongside demo video production
- V1.5 build: weeks 3 to 6, only if the MVP shows real engagement and we have spare capacity
- V2 build: post-patent, autumn 2026 or later, only if the spin-off enters real sales conversations
