  You are taking over the remaining results work for the city-exposure paper in:

  /home/user/aegis/papers/city-exposure-study

  Use subagents for independent audits, implementation, and testing. Read the applicable AGENTS.md files before acting. Preserve all unrelated dirty and untracked files.

  ## Objective

  Strengthen the existing IEEE Access paper with a small number of decisive, reproducible results. Do not reopen the settled scientific scope. Do not start another broad refactor, ten-city campaign, masonry model, RCWA
  model, agentic-AI addition, or Blender track.

  The paper already works as a focused five-route study. Your job is to close the most important remaining evidence gaps, starting with ray-reached semantic coverage and current-topology convergence.

  Keep the paper simple. A new result belongs only if it materially strengthens a reviewer-facing claim.

  ## Git state

  Current branch:

  feature/ojcoms-paper-spine

  Current relevant commits:

  - a217380e: Build verified IEEE Access manuscript
  - eb9a9a2b: Normalize IEEE Access template asset modes

  Existing PR:

  https://github.com/rwydaegh/aegis/pull/934

  The working tree contains unrelated user changes and untracked files. Do not modify, delete, stage, or commit them. Stage specific files only.

  ## Read these first

  In this order:

  1. semantic_twin/paper/READ_THIS_FIRST.md
  2. semantic_twin/docs/RESULTS_INVENTORY.md
  3. semantic_twin/docs/CURRENT_PRODUCTION_CONTRACT.md
  4. semantic_twin/paper/spine.md
  5. semantic_twin/paper/LENS_REVIEW.md
  6. semantic_twin/paper/QUESTIONS_BANK.md
  7. semantic_twin/paper/code/claims/current_results.py
  8. semantic_twin/docs/instructions_pm9k.md
  9. ~/PaperMaker9000/README.md and its relevant rules

  The canonical manuscript is:

  semantic_twin/paper/main/

  The current PDFs are:

  - semantic_twin/paper/build/main.pdf
  - semantic_twin/paper/build/supplement_wrapper.pdf

  The older paper.tex, body.tex, methods.tex, si.tex, eleven-city figures, hybrid three-bounce results, masonry results, and RCWA results are superseded. Do not use them as current evidence.

  ## Current scientific contract

  The reliable result set contains:

  - Five fixed routes: Korenmarkt, Prague, Madrid, Mexico City, and Tokyo Hachiko
  - 73 standpoints
  - 16 replicas per standpoint, seeds 7 through 22
  - 1,168 directional body fields
  - 200,000 IID primary rays per replica
  - 4,096 first-diffuse angular output cells
  - 15 GHz
  - A 250 m-radius support mesh
  - A route-aligned roofline source measure
  - Source weights based on physical three-dimensional roofline arc length
  - Results normalized per unit rho_A P_EIRP
  - Duke body with 56,024 surface elements and route-tangent yaw

  The production topology is `first_material_interaction_v1`:

  1. Exact direct directional atoms
  2. Exact order-1 specular directional atoms
  3. Stochastic first-diffuse next-event transport
  4. A first-diffuse path terminates at that interaction
  5. No higher specular order
  6. No diffuse-to-specular suffix

  The 4,096 cells contain only first-diffuse output. They are not launch strata. Direct and specular paths retain their exact directions and masses.

  Do not change this production contract silently.

  ## Current headline evidence

  - The selected-route medians span a factor of 13.3412.
  - Direct transport is largest at all 67 nonshadowed points.
  - Mexico points 0, 1, and 3 and Tokyo points 13, 14, and 15 have zero direct and zero order-1 specular transport.
  - First diffuse is the only nonzero modeled contribution at those six points.
  - Current central route statistics are stable at 16 replicas.
  - The Mexico and Tokyo lower tails are less stable.
  - Pooled median whole-body-SAR component shares are:
    - Direct: 77.6619447%
    - Order-1 specular: 21.3908505%
    - First diffuse: 0.4189504%
  - Controlled depth-1 validation gives:
    - 0.061565 dB maximum bounced error against deterministic quadrature
    - 0.062140 dB maximum bounced difference against Sionna RT
    - 0.034439 dB maximum total difference against Sionna RT
  - Madrid and Mexico have completed atlas-evidence versus geometric-fallback controls.
  - These controls do not establish material accuracy.

  Do not describe normalized wbSAR as physical W/kg. Do not call the five routes population samples or city rankings.

  ## Priority 1: Ray-reached semantic-evidence coverage

  This is the most important unfinished result.

  Quantify how much of the propagation-relevant surface support is actually informed by registered panorama evidence. Do not report only the fraction of the entire city mesh covered by imagery. That denominator is
  scientifically weak.

  Measure coverage conditioned on surfaces reached by the retained transport:

  - For order-1 specular interactions, classify the reached interaction support as:
    - panorama-atlas interface
    - nonblocking woody atlas state
    - geometric fallback
    - any other explicit production state
  - For first-diffuse next-event contributions, calculate:
    - event-weighted coverage
    - contribution-weighted coverage
  - Keep direct transport separate because it has no material interaction.
  - Where possible, retain per-site and per-standpoint results.
  - Reconcile all categories exactly.
  - Preserve the difference between “no panorama evidence,” “evidence refused,” and “atlas evidence accepted” if the stored provenance supports it.
  - Do not invent distinctions that the production data cannot support.

  The most useful paper quantity is probably:

  “Of the modeled non-direct body-coupled contribution, X% interacts with panorama-informed surface state and Y% uses geometric fallback.”

  However, derive the best defensible formulation from the actual data. Also report unweighted interaction counts so the energy-weighted result cannot hide sparse high-weight paths.

  If the compact production output no longer contains interaction provenance, add an audit-only rich-record path or replay mode. Do not change production transport behavior. Use identical route, source, material, body,
  seeds, and topology. Prove parity between the audit replay and the existing scalar and field outputs.

  Deliver:

  - A compact authenticated JSON and CSV
  - A simple PDF and PNG figure or table
  - A manifest with source hashes and exact configuration
  - Focused tests for category closure, contribution closure, and replay parity
  - A concise methods/results interpretation
  - A recommendation on whether this belongs in the main paper or SI

  Preferred output location:

  semantic_twin/outputs/experiments/ray_reached_evidence_coverage_v1/

  Add a tracked reporter and tests in the established `semantic_twin/report`, `semantic_twin/cli`, and test structure. Do not commit huge raw replay files unless necessary.

  ## Priority 2: Current-topology 64-replica convergence

  The current paper uses 16 replicas. Historical 64-replica work used a different hybrid topology and is not evidence for the current model.

  Run a current-contract diagnostic to 64 replicas. Prefer a complete comparable five-site extension if it is operationally straightforward. A full extension should remain inexpensive on one A6000. Use seeds 7 through
  70 and nested looks such as:

  16, 24, 32, 48, 64

  Do not overwrite or mutate the sealed 16-replica campaigns. Use new output directories and identities.

  Keep fixed:

  - Routes and standpoints
  - Source curves and source weights
  - Mesh and material atlas
  - Body and yaw
  - 15 GHz
  - 200,000 IID rays
  - 4,096 first-diffuse cells
  - `first_material_interaction_v1`
  - Exact direct and order-1 specular support

  Report:

  - Route q10, q50, and q90 changes at every look
  - Pointwise total-transfer and normalized-wbSAR changes
  - Whole-replica bootstrap intervals
  - The six shadowed points as an explicit stratum
  - Direct, specular, first-diffuse, and total components
  - Per-site timing
  - Whether the Mexico and Tokyo lower tails stabilize, remain uncertain, or show rare-event behavior

  Do not declare convergence merely because route medians are stable. Also do not let one near-zero relative statistic invalidate otherwise stable central results. Report central and lower-tail behavior separately.

  Do not automatically replace the paper’s sealed 16-replica result. First produce a strict comparison report. Promote the 64-replica result only if:

  - all manifests and identities pass,
  - common inputs are exact,
  - component closure passes,
  - the interpretation becomes clearly stronger,
  - and the manuscript can be updated without adding complexity.

  ## Priority 3: Ray and angular-cell budget sensitivity

  Do this only after Priorities 1 and 2 are complete.

  The current 200,000-ray and 4,096-cell settings are production choices, not fully justified optima. Test whether they are conservative.

  Use paired seeds and common random numbers where possible. Suggested diagnostic budgets are:

  Primary rays:
  - 25,000
  - 50,000
  - 100,000
  - 200,000
  - optionally 400,000 as a reference

  First-diffuse cells:
  - 1,024
  - 2,048
  - 4,096
  - optionally 8,192 as a reference

  Use at least:

  - Madrid as a regular nonshadowed route
  - Mexico City as a route with shadowed points
  - Prague if a third scene is inexpensive

  Evaluate more than scalar total transfer:

  - Normalized whole-body SAR
  - Absorbed power
  - Direct/specular invariance
  - First-diffuse component
  - Route q10/q50/q90
  - Shadowed-point values
  - Directional first-diffuse field after comparison on a common angular support
  - Body-field error or a justified directional-spectrum metric
  - Wall time and variance-time efficiency

  Do not change the production baseline merely because a cheaper budget barely changes a route median. A reduced setting must preserve directional and shadowed-point behavior too.

  Produce a recommendation, not a forced migration.

  ## Explicitly out of scope

  Do not:

  - acquire ten new cities,
  - rerun panorama acquisition without a demonstrated need,
  - revive masonry or RCWA,
  - restore the historical mixed suffix,
  - implement “complete multipath,”
  - add agentic AI,
  - use fake data,
  - turn Blender into a numerical dependency,
  - optimize seconds that do not change end-to-end cost materially,
  - weaken assertions,
  - overwrite sealed outputs,
  - infer missing facts from stale Markdown,
  - or expand the manuscript simply because new diagnostics exist.

  A complete cold-stage timing ledger is lower priority. Only do it if all higher priorities are done and it can be measured honestly. The paper currently makes only ready-scene numerical timing claims.

  ## Paper-integration rule

  Do not edit the paper before the result is verified.

  After verification:

  - Prefer adding technical detail to `semantic_twin/paper/si_new/`.
  - Add at most one short main-text paragraph or one compact table/figure if the new evidence materially addresses a reviewer concern.
  - Keep the main manuscript simple.
  - Add executable `@claim` checks for every new number used in prose.
  - Regenerate parent PaperMaker files.
  - Rebuild and visually inspect the complete paper and SI.
  - Update `RESULTS_INVENTORY.md`, `CURRENT_PRODUCTION_CONTRACT.md` only when appropriate, and write a concise execution report.

  Suggested report:

  semantic_twin/docs/REMAINING_RESULTS_EXECUTION_REPORT.md

  The report must distinguish:

  - completed production evidence,
  - new diagnostics,
  - rejected approaches,
  - promoted results,
  - and remaining limitations.

  ## GPU and external-resource rules

  This dev PC is CPU-only. If GPU execution is needed, use the BlueLobster API credentials already stored in the environment. Never print secrets.

  - Inspect existing instances first.
  - Never delete the persistent CPU `devpc`.
  - Create a clearly named temporary A6000 instance.
  - Reuse cached data and transfer only required files.
  - Record the hardware and commands.
  - Verify outputs before deletion.
  - Delete the paid GPU instance immediately when GPU work finishes.
  - Confirm through the API that no paid GPU remains.

  If an API key, download, browser step, or other tool is missing, stop and ask Robin. Do not silently substitute an inferior method.

  ## Engineering rules

  - Use `uv`, the existing `pyproject.toml`, and `uv.lock`.
  - Do not use system Python or `pip install --user`.
  - Use `apply_patch` for edits.
  - Use `rg` for searches.
  - Preserve unrelated changes.
  - Use feature branches or the existing PR workflow for large changes.
  - Stage specific files only.
  - Use subagents for independent audit, implementation, and testing.
  - Have one subagent independently challenge every proposed result interpretation.
  - Never weaken a scientific or numerical assertion to make a test pass.

  ## Required verification

  At minimum:

  - Authenticate every source and output manifest.
  - Verify component and body-field closure.
  - Verify finite values and exact shapes.
  - Verify route and standpoint ordering.
  - Verify common-input equality for paired studies.
  - Run focused unit and integration tests.
  - Run Ruff check and format check.
  - Run `uv lock --check`.
  - Run all PaperMaker claims.
  - Run PaperMaker lint and style scans for the main paper and SI.
  - Rebuild the IEEE Access PDF and SI.
  - Check for undefined citations and references.
  - Rasterize and inspect every changed figure and every affected paper page.
  - Run `git diff --check`.
  - Inspect the final staged diff.
  - Report whether a paid GPU remains.

  Useful existing commands are documented in:

  semantic_twin/paper/README.md
  semantic_twin/paper/code/README.md

  ## Definition of done

  Stop when:

  1. Ray-reached semantic coverage is measured and authenticated.
  2. Current-topology convergence is characterized beyond 16 replicas.
  3. Any budget study attempted has a clear promotion or rejection decision.
  4. The paper contains only the smallest useful integration.
  5. Every new manuscript number has an executable claim.
  6. All verification is fresh and green.
  7. Outputs, commands, limitations, and rejected paths are documented.
  8. Changes are committed and pushed to the existing PR or a clearly linked follow-up PR.
  9. No paid GPU remains running.

  Lead with evidence. If a result fails, report the failure clearly and retain it as a negative result rather than quietly changing the experiment.