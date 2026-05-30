# Outreach dossier

One folder for everything about **finding and contacting external people** for AEGIS: company outreach + NDAs (customers, LOIs for IOF) and prestigious academic collaborators (postdoc mobility). Built 2026-05-27.

## Why this exists
Deep market/people research is a browser rabbit hole that the Claude Code box cannot do (no LinkedIn login, no email-finding, no interactive clicking). So that work is split to two external tools, and their output gets pasted back here.

## Workflow
1. Run **`prompt_gemini_deep_research.md`** in Gemini Deep Research -> maps the landscape (collaborators, customers, competitors, standards, RIS gaps) from the public web. Paste its report into `results_gemini.md`.
2. Run **`prompt_claude_for_chrome.md`** in Claude for Chrome -> turns the shortlist into per-person contact intelligence (verified title, public email, LinkedIn, warm-intro path) using your logged-in browser. Optionally feed Gemini's new names into it. Paste its output into `results_chrome.md`.
3. Paste both back into the main Claude Code session -> I synthesise into an updated target list + outreach plan, and we refine the email/NDA package.

The two tools are scoped so they do not overlap: **Gemini = broad public synthesis** (no logins, no private emails); **Chrome = authenticated per-person lookup** (LinkedIn, directories, warm paths), collect-only, no messaging.

Optional: you may attach `materials/external_briefing.md` to Gemini as extra grounding (it was written to be read externally). Do not attach anything from the keep-out list below.

## Confidentiality boundary — do NOT paste these into Gemini / Chrome / any external tool
The patent is pre-filing, and TechTransfer asked that nothing be shared externally before drafting is under way. The prompts here are deliberately written at the published-physics / pitch level (no secret sauce), which is fine. Keep these OUT of any external paste:
- **The IDF** (`spinoff/patent/IDF/…`) — it contains the invention description and draft patent claims. Its *list of target organisations* is reused above (org names are not IP), but the document itself never goes out.
- **The monograph and the TAP / TWC paper drafts**, and the patent slides — pre-publication IP.
- **`honest_analysis.md`** — internal candour (founder/strategy/kill-dates). Fine as a local reference; the safe market facts from it already live in `external_briefing.md`. Not copied into this dossier on purpose.

## Files in this folder
- `prompt_gemini_deep_research.md` — paste into Gemini Deep Research.
- `prompt_claude_for_chrome.md` — paste into Claude for Chrome.
- `results_gemini.md` — landing pad for Gemini's output.
- `results_chrome.md` — landing pad for Chrome's output.
- `materials/` — snapshot copies of the relevant existing files (see manifest). Snapshots taken 2026-05-27; canonical versions live where noted.

## materials/ manifest
| File | What it is | Canonical location |
|---|---|---|
| `email.txt` | Robin's chronological PhD/spin-off/GOLIAT planning email (mentions the "spreken met bedrijven" workstream + this attachment) | `spinoff/email.txt` |
| `other_email.txt` | TechTransfer (A. Biondi, 26 May) email defining the NDA + disclosure process | `spinoff/other_email.txt` |
| `company_outreach_brief.tex` / `.pdf` | The attachment for colleagues: what TT requires, what/how to email companies, draft emails, contact table | `spinoff/company_outreach_brief.*` |
| `company_outreach_and_ndas.md` | The strategy note: 4 goals, the funnel, two-document system, tone, NDA-via-TT, disclosure gate | `spinoff/LATEST_GOOD/company_outreach_and_ndas.md` |
| `meeting_playbook_classics.md` | Generic classic playbook for discovery/sales/partnership meetings | `spinoff/LATEST_GOOD/meeting_playbook_classics.md` |
| `external_briefing.md` | Factual venue/market/competition/tech briefing (written for an external validator) — best grounding doc, OK to attach to Gemini | `spinoff/LATEST_GOOD/external_briefing.md` |
| `standards_play.md` | IEC TC 106 / IEEE ICES / EU 6G-EMF landscape + key people — feeds the standards research question | `spinoff/LATEST_GOOD/standards_play.md` |
| `collaboration_targets.md` / `.pdf` | Prestige-ranked academic collaboration conclusions (5-agent sweep) | `spinoff/presti_collabs/collaboration_targets.*` |
| `Prestigious-University Authors (BioEM + EuCAP).md` | The BioEM/EuCAP top-50-university author scan | `spinoff/presti_collabs/` |
| `RIS_exposure_aware_DiRenzo_2022.pdf` | The Di Renzo/Phan-Huy exposure-aware-RIS paper (evidence for that collaboration thread) | `spinoff/presti_collabs/` |

## Related, not copied here
- Funding stack (VLAIO + IOF, deadlines, the StarTT template): `spinoff/LATEST_GOOD/funding_stack.md` — relevant because company LOIs feed the IOF application, but it is a separate subject.
