# Sources and citations

Every claim of substance in this dossier traces back to one of these. When
this file conflicts with what Grangeat says on the call, trust him and update
the dossier.

## Local files (in this repository)

- **`../Grangeat_GSMA_EMFForum_2024_IEC-TC106-MT3-62232-TR62669-Tutorial.pdf`**
  — the 30-slide tutorial. Every figure and slide reference in this dossier
  is from here. Primary source for standards structure, actual-max approach,
  case study map, TR 62669 Ed. 3.0 plans, MT3 composition.
- **`../standards_brief.tex`** — Robin's own standards primer. The four
  core standards, national implementations, economic case.
- **`../discovery_call_playbook.md`** — the generic playbook. This dossier
  extends it for Grangeat specifically.
- **`../contact_sheet.md`** — the Nokia row (previously "owner not
  identified") is now Grangeat. Critical notes at the bottom on Split
  (Kapetanović) prior art.
- **`../materials/company_outreach_and_ndas.md`** — funnel stages and the
  four goals (G1 IOF evidence, G2 discovery, G3 ZMT, G4 standards).
- **`../outreach_emails.md` §1** — the email Robin sent, promising 30 min
  and "not a call to sell you anything."
- **`../alessandro/one_pager_bundle.tex`** — the one-pager + say/don't-say
  matrix awaiting Alessandro sign-off. Do NOT send.
- **`../../differentiability/SYNTHESIS.md`** — the 13-agent study. Does not
  say "drop differentiability," says "not a business moat on its own." Fock
  finite-Lipschitz survives, uncertainty-axis certificate survives, rank-8
  compressed-sensing survives.
- **`../../before-tom-meeting/generalization_map.md`** — the "one physics
  from device to base station" framing. Useful language if the call goes
  strategic.

## Grangeat publications (chronological)

- Baracca, Weber, Wild, Grangeat (2018). "A Statistical Approach for RF
  Exposure Compliance Boundary Assessment in Massive MIMO Systems."
  arXiv:1801.08351, WSA Bochum. Foundational — 50% compliance distance
  reduction vs traditional method.
- Rybakowski, Bechta, Grangeat, Kabacik (2023). "Impact of Beamforming
  Algorithms on the Actual RF EMF Exposure From Massive MIMO Base Stations."
  IEEE Access. Grid-of-beams, eigen-beamforming, zero-forcing. 95th
  percentile per-beam power = 7-22% of theoretical max.
- Rybakowski, Bechta, Grangeat, Kabacik (2024). "Statistical Analysis of the
  Actual RF Exposure from Massive MIMO Base Stations Serving Moving User
  Equipment." IEEE Xplore document 10693600 (Sept 2024). Moving UE gives
  -1.5 to -3.5 dB additional PRF headroom vs static UE.
- Rybakowski, Bechta, Grangeat, Kabacik (2024). "Evaluation of the Actual
  EMF Exposure from Extreme Massive MIMO Base Stations Around 10 GHz Using
  Channel Modelling." Referenced in EDAS program 2024. 7-15 GHz FR3, arrays
  from 192 to 796 antenna elements, 6G targeted.
- Maggi, Herzog, Zejnilagic, Grangeat (2024). "Smooth Actual EIRP Control
  for EMF Compliance with Minimum Traffic Guarantees." arXiv:2404.06624.
  Drift-Plus-Penalty control theory for the EIRP budget.
- Mandelli, Maggi, Zheng, Grangeat, Zejnilagic (2024). "EMF Exposure
  Mitigation via MAC Scheduling." arXiv:2404.06830. Water-filling power
  allocation at the MAC scheduler level.

## Nokia adjacent (non-Grangeat but same ecosystem)

- Bechta (2020). "Impact of Effective Antenna Pattern on Radio Frequency
  EMF Exposure." URSI GA 2020 presentation. Available at
  `ursi.org/proceedings/procGA20/presentations/Bechta_Kamil_Impact_of_Effective.pdf`.
  WebFetch returned binary; open in browser for content.
- Nokia (2019). "On the road to 5G — Use cases, technology & EMF
  standardization." ANFR workshop presentation. Available at
  `anfr.fr/fileadmin/mediatheque/documents/expace/workshop-5G/20190417-Workshop-ANFR-NOKIA-presentation.pdf`.
- Nokia FCC filing 2AD8UAWKUCD01 — 5G RF Exposure Compliance Report.
  Product-side compliance dossier example.
- US patent 12395250, "EMF strength control method and communication
  apparatus" — could not fetch (403). Google Patents search
  `assignee:Nokia RF exposure EIRP` for the full list.

## Ericsson (competitor context — same problem, different vendor)

- Ericsson White Paper GFTL-21:000987, "Accurately assessing exposure to
  radio frequency electromagnetic fields from 5G networks." October 2021.
  Available at `ericsson.com/495136/assets/local/reports-papers/white-papers/5g-and-emf.pdf`.
  Colombi + Thors are the empirical-evidence leads for actual-max.
- Colombi et al., "A Monte Carlo Analysis of Actual Maximum Exposure From a
  5G Millimeter-Wave Base Station Antenna for EMF Compliance Assessments."
  Frontiers in Public Health 2021, PMC8777231. Establishes actual-max
  applies at mmW.

## ML surrogate wave (adjacent competition)

- Bilson, Loh, Heliot, Thompson (2024). "Physics-Informed Machine Learning
  Modelling of RF-EMF Exposure in Massive MIMO Systems." IEEE Access, DOI
  10.1109/ACCESS.2024.3396179. Gradient-boosted decision trees, R² = 0.86.
  NPL + Surrey.
- Phy2-ExposNet (arXiv 2605.03207). Physics-informed neural network for
  EMF exposure mapping in complex urban environments.

## Standards documents (the actual specs)

- IEC 62232:2022 Ed. 3.0 (widely available via IEC webstore, national
  standards bodies).
- IEC 62232:2024 Ed. 4.0 — publication expected end 2024. Same technical
  content, editorial cleanup.
- IEC TR 62669:2019 Ed. 2.0 — webstore `webstore.iec.ch/en/publication/62014`.
- IEC TR 62669 Ed. 3.0 — publication planned 2025 per Grangeat's tutorial
  slide 30. Not on webstore at time of writing.
- IEC/IEEE 63195-2:2022 — device APD computation, complementary standard.
- ITU-T K.52 (08/2024), K.100 (08/2024) — updated in 2024.
- IEC TC 106 dashboard: `iec.ch/dyn/www/f?p=103:29::::::FSP_ORG_ID:1303`
  (structure page, member details behind login).

## GSMA venue context

- 13th GSMA EMF Forum 2024, Brussels, 1 October 2024. Recording available at
  `gsma.com/solutions-and-impact/connectivity-for-good/public-policy/gsma_events/the-gsma-13th-emf-forum-2024/`.
- GSMA OUTREACH initiative — Robin met Grangeat there ~2 years ago. Public
  info scarce; ask him about continuity.
- BioEM 2025 Tutorial 3 — Grangeat delivered the same material at BioEM.
  Bioem.org/bioem2025/tutorial-3/.

## Things I could not resolve

- Full IEEE Xplore author page for Grangeat (37546201600) — server blocks
  WebFetch with HTTP 418. Open in browser.
- Full text of the Rybakowski/Bechta/Grangeat 2024 Statistical Analysis
  paper — IEEE Xplore returned empty. Open in browser.
- Full member list of IEC TC106 MT3 — requires IEC dashboard login. Ask
  Grangeat directly, or ask Wout who has committee access.
- The FCC compliance report PDF — WebFetch returned binary. Open in browser
  if the compliance-methodology detail matters.
- Nokia's internal EM tool stack (Sim4Life, CST, HFSS, internal) — no public
  disclosure found. Direct question to Grangeat.
