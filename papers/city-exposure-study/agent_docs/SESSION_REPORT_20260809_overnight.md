# Overnight session report, 2026-08-09

One open-ended instruction: find small-to-meso improvements, add harmless
results, QA everything. This file is the index of what happened and what needs
Robin's input. Written by the Claude session that ran overnight into 2026-08-09.

## Ground truth established first

The main checkout and `master` are both stale relative to the real work. The
current production line is the worktree `/home/user/aegis-exposure-body-path`,
branch `fix/registration-cohort-mesh-resolver`, 41 commits ahead of
origin/master and in sync with its own origin branch. All audits and new work
in this session were done against that tree. `docs/CURRENT_PRODUCTION_CONTRACT.md`
there is the concise authority for the campaign state.

## Deliverables

1. **BUGS.md audit** (main checkout `docs/BUGS.md`, rewritten). Every finding
   re-checked against production code with a dated status annotation.

2. **Methods+Results paper draft**:
   `semantic_twin/paper/ROOFLINE_METHODS_RESULTS_DRAFT.tex` (476 lines, main
   checkout). Covers the `first_material_interaction_v1` contract exactly as
   implemented: exact direct + exact order-1 all-specular + stochastic next-event
   at the first blocking material vertex, no mixed suffix. 9 `\todo` markers on
   decisions only Robin can make. Known symbol clash: S_0 is used for both the
   reference power density and a source-measure symbol; flagged inline.

3. **Adversarial review of the 41 unmerged production commits.** Five verified
   findings, all confirmed first-hand in code before acting. The load-bearing
   one: the persistent transport cache identity restated algorithm constants
   (direct epsilon, min connect, broadphase tolerances) as literals, so editing
   a constant would silently serve stale cache entries.

4. **Report-integrity fixes**: PR #932
   (https://github.com/rwydaegh/aegis/pull/932), branch
   `fix/roofline-report-integrity` (worktree `/home/user/aegis-report-integrity`,
   commit 0a3a6f13 on production head 7cacdd2f). Opened against
   `fix/registration-cohort-mesh-resolver`, deliberately NOT merged (codex's
   active line). Verified zero regressions: the full suite fails on exactly the
   same 52 pre-existing environment-dependent tests on both my branch and the
   untouched base tree (2891 vs 2885 passed; the +6 are my new tests). Content:
   - `illumination/sources.py` + `transport/next_event.py`: canonical
     `DIRECT_EPSILON_M` constant, all defaults read it.
   - `transport/persistent_cache.py`: identity now imports the live constants
     (direct epsilon, MIN_CONNECT_M, broadphase inside tolerance and round-off
     multiplier). Note: this intentionally invalidates existing persistent
     cache entries (runtime-only cache, excluded from campaign identity, so
     science is unaffected; first re-run repopulates).
   - `report/multicity_roofline_results.py`: each pooled campaign now exports
     its sealed `site`; the writer refuses missing/duplicate sites and
     heterogeneous route_contract or material_mode; route CDFs report
     defined/excluded-nonfinite standpoint counts; manifest sources include
     the site.
   - `report/roofline_topology_sensitivity.py`: route quantiles now include
     paired per-standpoint dB-change quantiles with defined/excluded counts and
     explicit definitions. The pre-existing values are per-arm quantile ratios
     (unpaired); both are now labelled.
   - Tests added for all of the above (multicity refusals, live-constants
     identity, paired quantiles).

5. **Supplementary figures**:
   `semantic_twin/FIGURES/two_city_supplementary/` (main checkout). 13 figures
   PDF+PNG, scripts, numbers JSONs, README. C1-C6 use the current five-city
   first-material-interaction export; S1-S7 use the historical two-city hybrid
   package and are labelled superseded. Every published headline number was
   independently reproduced before plotting. Standout findings:
   - Mexico City route spans 59.3 dB and Tokyo 39.3 dB, while the three closed
     squares (Korenmarkt, Prague, Madrid) span 0.90-1.56 dB.
   - All six zero-direct standpoints have exactly zero order-1 specular too:
     they are carried entirely by first diffuse.
   - Replica quadrupling cuts per-standpoint SE by only ~1.31x median (heavy
     tails at shadowed points); look-16 p90 SE is 2.4e-4 dB at Prague but
     0.146 dB at Mexico City.
   - Three of six retained body endpoints are exact fixed multiples of
     area-mean Sab (constant to 5.6e-16): no independent information.

6. **Brussels Grand-Place campaign (sixth city) unblocked and running.** The
   doc claim that Brussels was blocked on a semantic rebuild is stale. Staged
   coherent tree at `/home/user/aegis-roofline-stage-20260809-brussels-preflight`,
   preflight `ready_to_trace: True` (needed screening.json + per-pano metadata
   staging and the Tokyo-precedent 320M specular candidate budget; exact bound
   277,740,960). 16-replica llvm CPU campaign running (14 standpoints, seeds
   7-22, log `campaign_llvm.log`). COMPLETED during the session: EXIT=0, all
   16 replica shards committed with verified hashes. Wall pattern: ~75 min for
   the first replica (one-time 278M-candidate deterministic broad phase),
   minutes per replica after via the persistent transport cache. Headline
   numbers (16-replica means, per unit rho_A P_EIRP):
   - no zero-direct standpoints; route span of total transfer 9.19 dB over 14
     standpoints (between the closed squares at 0.90-1.56 dB and the open
     sites at 39-59 dB, consistent with corridor legs leaving the square)
   - multipath surplus q10/q50/q90 = 1.138 / 1.348 / 1.566 dB (Madrid-like)
   - median specular share 21.7%, first-diffuse share 4.3%
   - wbSAR route median 0.0314 m2/kg (q10 0.0270, q90 0.0337)
   - 12-to-16 replica route-median wbSAR shift 0.000052 dB (well converged)
   Nothing consumes this output automatically; it awaits review before any
   integration into the multicity export.

Deliverables 1, 2, 5 and this report live uncommitted in the main checkout on
purpose: that checkout is shared with a concurrent agent line and carries
unrelated dirty state, so committing there risked bundling someone else's
in-progress work. Everything code-shaped went through PR #932 instead.

## NEEDS_CONTEXT (decisions or resources only Robin has)

- **Five-city per-replica shards are unrecoverable here.** The campaign dirs
  live on the dead GPU box; all GPU hosts unreachable ("compute" shows
  REMOTE HOST IDENTIFICATION CHANGED, IP likely reused, do not connect). The
  437KB export JSON retains per-point scalars but not per-replica body fields.
  Decide: recover from the box, re-run, or accept the export as the archive.
- **Krakow**: Street View quota exhausted during acquisition; needs quota or
  another key.
- **Toulouse**: single usable panorama; needs re-acquisition.
- **Route caches** need GOOGLE_API_KEY to rebuild if extended.
- **Milan**: identity mismatch between staged inputs and screening; needs a
  decision on which is canonical.
- **Tokyo**: `semantics_sam3` dirs are empty in the retained package, so that
  campaign is not re-verifiable end-to-end from local artifacts.
- **Roughness closure**: finish-only RMS rule gives brick 0.9996 specular
  share at 15 GHz (independently reproduced). If intended, fine; if masonry
  texture should matter, the closure needs a texture term. Decision is
  scientific, not a bug.
- **Near-source floor** (finding 12 in BUGS.md) and the missing partition
  invariant test (total == sum of components) remain open, low risk.

## Where things are

- My PR branch: `fix/roofline-report-integrity` (worktree
  `/home/user/aegis-report-integrity`).
- Figures + numbers: `semantic_twin/FIGURES/two_city_supplementary/`.
- Paper draft: `semantic_twin/paper/ROOFLINE_METHODS_RESULTS_DRAFT.tex`.
- Brussels stage: `/home/user/aegis-roofline-stage-20260809-brussels-preflight`.
- Historical two-city package: `/home/user/aegis-roofline-results-20260807T015530Z/`.
