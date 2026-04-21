# Public repo strategy: stars without losing the moat

*Claude Opus, April 2026. Written after Robin asked how to reconcile a public-facing GitHub presence (stars, tutorials, notebooks, SEO, eventual Electron distribution) with the fear of giving up the moat. Distilled from `LATEST_GOOD/honest_analysis.md`, `LATEST_GOOD/standards_play.md`, `LATEST_GOOD/patent_decision_and_defense_mechanics.md`, `publication_and_opensource_strategy.md`, `commercial_moats_and_strategy.md`, `AEGIS_feature_inventory.md`, and the current repo layout.*

---

## TL;DR

1. **Yes, build a public repo.** Structure it as "SDK + docs + demo", not open-core. The physics moat is leaving the building anyway via thesis, JSAC, and monograph. Public educational surface does not cost anything the publication pipeline does not already cost.
2. **Create it before JSAC publishes and before the 63195-2 2026 draft closes.** Those two artefacts need a real URL to cite. Both windows close roughly together.
3. **Private repo (`rwydaegh/aegis`) does not move.** Full kernels (L2-L8), viewer source, ingest pipeline, integrations, and the 2,469-test suite stay behind the API seam. Zero changes there.
4. **Public repo (new, `openaegis/openaegis` or similar) contains:** runnable notebooks reproducing published figures, a thin Python SDK that calls the hosted API, 2-3 standalone interactive frontend toys, MkDocs tutorials, and the "AEGIS benchmark" dataset. Nothing that implements L2+ or exposes the ingest plumbing.
5. **One seam, one sentence:** public code asks the private backend to compute things. That is the entire mechanism.

---

## 1. The reframe: what the moat actually is

The internal documents are already explicit on this. Collecting the key claims in one place so they can be acted on:

From `honest_analysis.md` Q4:

> The moat is execution speed, base-station-database plumbing, viewer, partnership with ZMT, and standards-body recognition. Not the physics.

From `commercial_moats_and_strategy.md`:

> First closed-form spatial absorption map on arbitrary 3D human body geometry. First closed-form exposure operator Q for MIMO beamforming. First interactive real-time dosimetry viewer with live ICNIRP compliance feedback. First platform combining real base station databases + ray tracing + body dosimetry.

From `publication_and_opensource_strategy.md` §3:

> Publish the physics. Keep the engineering.

The physics goes public on a schedule you do not control: patent priority, then thesis, then JSAC, then PMB or MTT. Anybody who wants the equations will have them by late 2026. Keeping the current codebase private does not defend the equations. It defends six things:

1. **Iteration speed.** The 2,469-test suite, the nine-level fidelity ladder as separate kernel files, the differentiable JAX pipeline. A re-implementer starts at zero. You are already at v0.28.
2. **Base-station ingest pipeline.** 14 government APIs, ~293k antennas, spatial deduplication, provenance tracking. This is tedious integration work. It is not derivable from any paper.
3. **Viewer.** 21k lines of TypeScript with MIMO, optimization, coverage maps, guided tour. Nobody cites a viewer. Everybody uses one.
4. **3D scene reconstruction.** OSM-to-mesh with facade decomposition, Google 3D Tiles with material inference, dual export to DiffeRT and Sionna. Operational, not theoretical.
5. **Stochastic channel integration.** 91 QuaDRiGa presets wired into the dosimetry engine. Not in any paper.
6. **Enterprise and deployment.** Modal serverless GPU, Hetzner production, Caddy, authentication, rate limiting, Sentry, Umami. The running system is a moat because a fresh implementation has to rebuild all of it.

A public repo in the shape proposed below touches none of these. That is the whole point.

---

## 2. What a public repo actually buys

Three jobs, one repo, different front doors.

### 2.1 Standards credibility (time-bound, highest priority)

`standards_play.md` is blunt: IEC/IEEE 63195-2 2026 edition is in draft right now, realistic window for inserting new computational content is 3-6 months, next opportunity is a 2028-2029 amendment. Standards contributions are written documents with proposed standard text, technical justification, and matched validation evidence. They cite URLs.

A public repo containing runnable notebooks that reproduce the Fresnel, Brewster, Mie, and Stokes figures from Paper 1 gives the IEC contribution a citable implementation. "Reference implementation available at github.com/openaegis/openaegis/notebooks/brewster.ipynb, reproducing Table 6 of Wydaeghe 2026." This is the Kuster move, transposed. Kuster opened tissue data and the student edition, not the full Sim4Life source. Same pattern here.

Without a public URL the contribution still goes in, but it is weaker. Standards bodies look more favourably on methods they can inspect.

### 2.2 Mindshare and discoverability

Stars are a weak signal individually but a strong one at scale. The specific buyers for device mmWave pre-compliance (Apple, Samsung, Xiaomi, Qualcomm, Sim4Life applications engineers) google things. Tutorials and interactive toys are what rank. A single Fresnel-visualizer page ranking on the first page of results for "mmWave skin transmission coefficient" is worth more than twenty cold emails.

A public repo is also how the Reddit, Hacker News, and LinkedIn channels can be fed. "Here is an open notebook reproducing Figure 4 of our new JSAC paper" is postable. "Here is a password-protected viewer" is not.

### 2.3 Academic funnel

Kuster's student edition of Sim4Life seeded twenty years of compliance engineers at every OEM. The compressed AI-era version: runnable Colab notebooks that PhD students cite from their 2027 theses. Today's grad student is tomorrow's compliance engineer at Apple. Total addressable academic population is maybe 200 groups worldwide, but the throughput into industry is the point, not the raw count.

### 2.4 What is not a priority

**External community contributions.** Pre-revenue, one developer (two counting an istart co-founder), zero capacity to triage external PRs and issues. A `CONTRIBUTING.md` that says "issues for the papers and benchmarks welcome; product feedback via the hosted viewer" manages expectations. Revisit at year 2 if a contributor ecosystem becomes attractive.

---

## 3. Shape: SDK + docs + demo, not open-core

Open-core was rejected in `publication_and_opensource_strategy.md` §4 for sound reasons:

- L0-L6 is the revenue (~95% of real-world compliance).
- AI-assisted reimplementation collapses the copyleft moat.
- Kuster kept Sim4Life closed.

Do not revisit that decision now. The model below is different: the public repo contains a *client* that asks the private backend to compute things, plus educational material the papers already license into the public. No public file implements L2 or above. No public file exposes the base-station ingest plumbing.

### 3.1 Public repo contents (concrete)

Proposed name: `openaegis/openaegis` under a new GitHub organization `openaegis`. Alternatives: `aegis-community`, `aegis-sdk`. Organization owns the namespace so the private repo can stay at `rwydaegh/aegis` untouched.

| Directory | Content | Notes |
|---|---|---|
| `notebooks/` | Colab-runnable Jupyter notebooks reproducing every published figure. One notebook per paper figure. | Mostly auto-generatable from existing golden tests. Each notebook has a paper citation in the first cell. |
| `sdk/` | Tiny Python SDK, `pip install aegis`. Authenticated client for `api.waves-ugent.be`. Ten files. Not a solver. | Think `openai` package shape. API key pattern. |
| `widgets/` | 2-3 standalone interactive frontend toys. Fresnel/Brewster explorer, skin-depth visualizer, polar-pattern viewer. | React + TypeScript. MIT-licensed. Shares zero code with the main private viewer. Each is a single-page demo. |
| `benchmark/` | The "AEGIS benchmark" dataset: standard scenarios (body + source config + expected S_ab) for matched validation. JSON + small meshes. | Kuster IT'IS playbook transposed. Open the data, keep the software. Gives the field a standard comparison set. |
| `docs/` | MkDocs site. Physics background, tutorials, API reference, standards pointers. | Derived from the monograph and existing internal docs. |
| `README.md` | Overview, links to hosted viewer, papers, standards contributions. Explicit "not a supported product, companion to the papers" line. | Kills the maintenance-pressure problem in one sentence. |
| `.github/ISSUE_TEMPLATE/` | Two templates: "notebook or figure issue" (we triage) and "product issue" (routed to hosted viewer's in-app bug reporter). | Manages expectations. |
| `LICENSE` | Apache-2.0 for code, CC-BY-4.0 for data and docs. Explicit attribution clause. | Apache-2.0 over MIT for the patent grant, which matters given the filed priority. |

### 3.2 Private repo contents (unchanged)

Everything currently at `rwydaegh/aegis`:

- Full kernels L0 through L8 (including L7-L8 coherent MIMO and the Q operator).
- Viewer source (21k TypeScript, 34 React components).
- Base station ingest pipeline (14 country adapters, CloudRF integration, MSI parsers).
- 3D scene reconstruction (OSM, Google 3D Tiles, SRTM, GeoJSON).
- Stochastic channel (TR 38.901, 91 QuaDRiGa presets).
- Ray tracing integrations (DiffeRT, Sionna, Modal deployment).
- Compliance module (ICNIRP 2020, spatial averaging, margin computation).
- Flask API layer (40+ endpoints, auth, SSE, binary protocols).
- The 2,469-test suite.
- Deployment stack (Hetzner, docker-compose, Caddy, Gunicorn).
- GOLIAT.

License stays `LicenseRef-Proprietary`.

### 3.3 The seam

Public notebooks and the SDK call `api.waves-ugent.be`. Public code never contains a full implementation of L2 or above. A motivated reader can re-derive from the published paper. They always could. The seam is identical to how `openai` clients call OpenAI's servers.

Rate limiting and API keys on the backend are the enforcement mechanism. Free tier throttles to demo-sized scenarios. Paid tier unlocks real base-station data, coherent MIMO, and batch. The public SDK handles both transparently.

### 3.4 What the public repo does NOT contain

To be explicit. These are hard no's, not "we'll figure it out later":

- Implementations of L2 or above.
- The Q operator or ECBF solver.
- Any base-station ingest code.
- Any Sionna or DiffeRT integration code.
- The main 3D viewer (`aegis-web/`).
- The test suite.
- Compliance-report PDF generation.
- Modal deployment configuration.
- Credentials, environment files, or deployment secrets.

---

## 4. Serves every business model in `external_briefing.md` §7

Structure is model-agnostic because the seam is "client hits private backend". Whatever the backend becomes, the public surface keeps working.

| Business model | Role of public repo |
|---|---|
| A. Direct SaaS / API | Funnel. Notebooks drive traffic to hosted viewer. SDK is the paid API's public face. |
| B. OEM licensing (ZMT, Sim4Life) | Non-competitive. Public repo is research demo, Sim4Life license is the commercial integration. Nothing in the repo threatens ZMT. |
| C. Consulting | Portfolio. Pointable artefact during discovery calls. |
| D. Open-core | Skipped, for reasons already adopted. |
| E. Acquire-hire target | Asset. An acquirer values a public repo with citations and stars higher than an equivalent closed codebase, because it shortens their post-acquisition standards and community work. |

The Electron desktop variant is orthogonal. Same seam, different client. Build when an enterprise customer says "air-gapped, cannot hit your API". Until then it is wasted work. Electron shell plus license check plus locally cached base-station data is 2-3 weeks when a buyer is pushing.

---

## 5. Sequencing

Ordered by what locks downstream decisions and what has a hard external deadline.

1. **Patent priority filed first** (unchanged from `patent_decision_and_defense_mechanics.md`). Any public repo content that touches patentable methods waits until after the priority date. Notebooks reproducing published theory are fine after priority.
2. **Create empty public repo and organization** the week the JSAC manuscript goes to typesetting. The paper's "Code availability" section needs a real URL. Placeholder README is enough; content can land later.
3. **First commits** are the notebooks reproducing Paper 1 and Paper 3 figures. These are mostly auto-generatable from existing golden tests (`tests/golden/`). Estimated 2-3 focused days.
4. **AEGIS benchmark dataset.** Export the matched-scenario cases from the golden suite into `benchmark/`. JSON format, versioned. This is what the IEC contribution points at and what enables external matched validation against Sim4Life. 2-3 days.
5. **SDK.** Thin Python client wrapping the existing API. Do only after the API endpoints you want public are documented and stable. Target ten endpoints, not forty. 1 week.
6. **MkDocs docs.** Port relevant sections from the monograph and internal docs. 1-2 weeks.
7. **Frontend widgets.** Fresnel/Brewster explorer first (highest mindshare per hour). Skin-depth visualizer and polar-pattern viewer after. Each is 3-5 days. Do only after a paper or a post would directly benefit from them.
8. **Revisit at 12 months:** should L0 and L1 reference implementations be added as readable Python? Reversible decision. Depends on whether standards adoption needs it.

Dependencies on external milestones:

| Milestone | Triggers |
|---|---|
| Patent priority filed | Unlocks all public repo publication. |
| JSAC acceptance | Hardens the URL deadline. Empty public repo must exist before online early access. |
| 63195-2 2026 draft close | Hardens the notebook and benchmark deadline. If the IEC contribution cites the repo, the repo must exist and be citable by the contribution date, not after. |
| First paying customer | Triggers SDK polish and documentation push. |
| First standards citation | Triggers whether L0-L1 reference implementation lands as readable Python. |

---

## 6. Risks and mitigations

### 6.1 Competitor reads notebooks, reimplements faster

Already accepted risk in `publication_and_opensource_strategy.md` §7 Risk 1. A reader who wants the method gets it from the paper regardless of the notebook. Notebooks accelerate understanding by days, not by the months of engineering a full reimplementation actually requires. Trade is good.

### 6.2 Accidental disclosure of unpublished work

The public repo must not contain material the papers have not already published. Specifically: no near-field implementation, no coherent MIMO Q operator, no ECBF solver, no ambient occlusion algorithm, until the relevant paper is in peer-reviewed publication. Enforce with a pre-commit hook or a lightweight checklist: "does this file reference a published equation or theorem? If not, it does not belong in the public repo."

### 6.3 Maintenance pressure from issues and PRs

Mitigated by explicit README disclaimer, issue-template routing (product issues go to hosted viewer bug reporter), and the fact that the content is notebooks and demos, not a production library. If a user files a bug against a notebook, fix is scoped to that notebook. If a user files a bug against the hosted viewer through the public repo, close with a pointer to the in-app reporter.

### 6.4 Staleness

Notebooks go stale when the API changes. Pin SDK version in notebook first cell. Run a weekly CI that re-executes notebooks against the current API and opens an issue on drift. This is GitHub Actions, free.

### 6.5 Dilution of the "serious product" message

Risk: enterprise buyer looks at the public repo and concludes "this is a student project". Mitigated by explicit framing in the README: "AEGIS is a commercial platform at aegis.waves-ugent.be. This repo is the academic companion to the peer-reviewed papers. For production use, contact us." Link prominent to the paid platform.

---

## 7. What this does not solve

Being honest about the limits.

1. **Does not solve customer discovery.** A public repo attracts inbound traffic but does not replace 20 outbound calls to test labs, Sim4Life applications engineers, and regulators. `honest_analysis.md` Q5 is right that this is the real bottleneck.
2. **Does not solve the ZMT relationship.** That starts with matched-validation evidence and a Wout-routed introduction, not with a public repo. Repo helps after the conversation is opened.
3. **Does not solve the co-founder gap.** Commercial B2B sales cycle is still 12-18 months and still needs someone who has done enterprise sales. Stars do not close deals.
4. **Does not replace the hard 18-month kill date.** `honest_analysis.md` sets that for a reason. A public repo with 500 stars and no paying customers at mid-2027 is still a no-go.

---

## 8. Action list

Near-term (within 30 days):

- Reserve the GitHub organization name. `openaegis` if available; `aegis-foundation` or `waves-ugent-aegis` as fallbacks.
- Reserve `pip` package name `aegis` or `aegis-sdk` on PyPI.
- Decide: Apache-2.0 or MIT for code. Recommend Apache-2.0 (patent grant).
- Draft the README, specifically the "not a supported product" framing and the links to hosted viewer and papers.

Medium-term (before JSAC online early access):

- Public repo populated with:
  - README.
  - 3-5 notebooks reproducing Paper 1 figures.
  - Benchmark dataset (first version).
  - Issue templates.
  - CI that re-executes notebooks weekly.
- Add "Code availability" line to JSAC manuscript: `github.com/openaegis/openaegis, DOI Zenodo:…`.
- Tag v0.1.0 and archive to Zenodo for a citable DOI.

Longer-term (after patent priority, after first standards contribution):

- Python SDK published to PyPI.
- MkDocs site live at a subdomain (`docs.aegis.waves-ugent.be` or similar).
- First interactive frontend widget live as its own static page, embedded in docs.
- Revisit decision on whether L0-L1 reference implementations land as readable Python.

---

## Decision in one sentence

Build the public repo as an SDK-and-docs surface that sits on top of the unchanged private backend, ship it before the JSAC "Code availability" URL and the 63195-2 2026 contribution need it, and never put anything in it that was not already shipped to a peer-reviewed journal.
