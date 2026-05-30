# Prompt for Claude for Chrome

*Paste everything below the line into Claude for Chrome (the extension that drives your real, logged-in browser). This tool is for the per-person actionable layer that needs interaction and authenticated sessions: verifying current roles, finding public professional emails, locating LinkedIn profiles, and spotting warm-intro paths. It is the complement to the Gemini Deep Research prompt (which maps the landscape but cannot log in anywhere).*

**Run the Gemini Deep Research prompt first if you can, then feed its shortlist into the "extend" step at the bottom of this one.**

---

You can drive my logged-in browser (LinkedIn, university and lab sites, IEEE, etc.). I need you to turn a shortlist of named research and industry contacts into **actionable contact intelligence** for legitimate academic collaboration and business-development outreach that I will do myself.

## Hard guardrails (read first)
- This is **research and preparation only**. Do **NOT** send messages, connection requests, emails, InMails, or fill in any contact/lead forms. **Collect and report only. I decide and perform all outreach myself.**
- Gather only **public professional information** — the kind I could find by clicking around manually (lab pages, university directories, public profiles, official rosters).
- Do **not** scrape at scale or use automation tricks; look people up one at a time as a person would.
- Do **not** guess or fabricate an email address. If you cannot find one, say so and note the most likely official source (e.g. "EPFL directory" or "lab contact page").
- Cite the exact page (URL) you took each datum from.

## Context (the venture)
AEGIS is a Ghent University spin-off (founder Robin Wydaeghe, finishing his PhD with Prof. Wout Joseph, INTEC-WAVES). It computes RF absorbed power density / SAR on 3D human bodies in milliseconds (fast analytical method, differentiable, ~100 MHz-300 GHz), for 5G/6G mmWave device pre-compliance, base-station EMF compliance, and exposure-aware MIMO/RIS beamforming. I am looking for (A) prestigious academic collaborators for a postdoc and (B) the right named people at a few companies/labs/regulators for market-validation conversations.

## For EACH person below, find and report
- **Current exact title + affiliation** (confirm they have not moved institutions)
- **Best public professional email** (from their university/lab page or official directory) — or "not found, likely source: X"
- **LinkedIn profile URL**
- **Warm-intro path**: do I share a connection in my LinkedIn network, a co-author, a standards committee (IEC TC 106 / IEEE ICES), the EuCAP/BioEM community, or my supervisor **Wout Joseph**? Note any plausible path.
- **One line**: their most relevant recent work / why they would care about AEGIS
- **Source URL** for each datum

## Shortlist A — academic collaborators (prestige-ranked)
1. **Anja Skrivervik** — EPFL (antennas in lossy tissue / implantable, near-field body models)
2. **Marco Di Renzo** — CentraleSupélec / Paris-Saclay / CNRS (exposure-aware RIS)
3. **Andreas Christ** — IT'IS Foundation / ETH Zürich (mmWave skin dosimetry, IEC/IEEE 63195)
4. **Niels Kuster** and **Esra Neufeld** — IT'IS Foundation / ETH Zürich
5. **Thomas Eibert** — TU Munich (near-field antenna / inverse-source)
6. **Mats Gustafsson** — Lund (electromagnetic physical bounds)
7. **Joe Wiart** — Télécom Paris / IP Paris (stochastic + ML dosimetry, Chair C2M)
8. **Emil Björnson** — KTH (massive MIMO / cell-free, EMF trade-offs)
9. **Romain Fleury** — EPFL (wave physics / RIS scattering models)
10. **Akimasa Hirata** — Nagoya Institute of Technology (>6 GHz APD dosimetry)
11. **Dinh-Thuy Phan-Huy** — Orange Innovation (EMF-aware / RIS, co-author with Di Renzo)

## Shortlist B — companies / labs / regulators (find the right NAMED person + contact path)
- **ZMT / Sim4Life** (Zürich MedTech): **Sven Kühn**, and Niels Kuster. (Note: partner track, handle as collaboration, not a hard sales pitch.)
- **Ericsson Research** (EMF / massive-MIMO compliance): **Davide Colombi**, **Christer Törnevik**.
- **Nokia**: find the named person who leads EMF exposure / RF compliance for mobile networks.
- **Test labs**: Eurofins, CETECOM, Verkotan — find who runs RF / SAR / APD device compliance.
- **Regulator**: BIPT (Belgium) — the EMF / non-ionising-radiation contact.

## Broader target universe (from the invention disclosure) — look up only if time permits
These are the org categories that are plausible customers/partners. Don't exhaust them; use them to widen Shortlist B if the focused set is done, finding the one named person who owns RF/EMF exposure compliance at each:
- **Device OEMs**: Apple, Samsung, Xiaomi, OPPO, Vivo, Huawei, Google, Motorola/Lenovo, Nothing.
- **Chipset vendors**: Qualcomm, MediaTek.
- **Simulation vendors**: ZMT/Sim4Life, Dassault/CST, ANSYS HFSS, Remcom.
- **Test labs**: SPEAG, Eurofins E&E, UL, TÜV, PCTEST, Verkotan, CETECOM.
- **Infrastructure vendors**: Ericsson, Nokia, Huawei, Samsung Networks.
- **Network-planning software**: ATDI, Forsk/Atoll, iBwave, InfoVista.
- **Operators**: Proximus, Telenet (BE), KPN, Orange, Deutsche Telekom, Vodafone, Telefonica.
- **Regulators**: BIPT (BE), BNetzA, ARCEP, Ofcom, ANFR, FCC.

## Extend step (after Gemini)
If I paste you a shortlist from Gemini Deep Research, run the same per-person lookup (title, email, LinkedIn, warm path, source) for any new names it surfaced that are not already covered above.

## Output
One markdown table per shortlist, columns: **Person | Title + Org | Email (or "likely source") | LinkedIn | Warm-intro path | One-line relevance | Source URL**. Put anything you could not verify in a short "gaps / needs manual check" list at the end. I will paste your output back into my main workflow.
