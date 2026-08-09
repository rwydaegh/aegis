# The great consolidation, 2026-08-09

Everything that happened when Robin said "hand you the keys, give me one clean
master, no data loss". Written for future sessions and for Robin. Short
sections, one idea each.

## TLDR

- **One worktree** now: `~/aegis`, on `master`, in sync with `origin/master`.
- **One local branch**: `master`. Remote: `master` + `bug-screenshots` (functional) + 29 old automation branches (documented below, zero local impact).
- Master now contains: the roofline production line (PR #925), the report-integrity fixes (PR #932), and **all 451 studio-branch commits via a true merge** (not squashed), plus the archived five-city export.
- Tagged **v0.40.0**. Release workflow is running the full test matrix.
- Nothing was lost. Every deletion below was proven-safe first, and the one scary moment (worktree removal deleting gitignored outputs) was checked and cleared: the five-city export lives in the main checkout AND is now committed to master, byte-exact, manifest-verified.

## What master looks like now

```
06632c7e Store archived campaign exports byte-exact
ae17c8b3 Archive the five-city campaign export as the durable copy
fa394bbf Merge feature/coherent-exposure-studio (451 commits preserved)
dda88333 Harden roofline report integrity (#932)
199b497a Harden multicity semantic campaign operations (#925, the production line)
```

## The merge order and why

1. **PR #925 first** (production roofline line, 41 commits, squashed per repo convention). It was MERGEABLE/CLEAN.
2. **PR #932 second** (my report-integrity fixes). GitHub auto-retargeted it to master after #925, showed CONFLICTING because my branch carried the 41 pre-squash commits. Fixed by rebasing **just my one commit** onto master (`git rebase --onto`), force-with-lease on my own branch only. Re-ran the 34 focused tests on the rebased commit before merging.
3. **Studio branch last, as a TRUE MERGE** (`fa394bbf`, two parents). Robin explicitly wanted the 451 commits on master, not a squash. Merge commits are disabled in the GitHub UI but direct push is fine (no branch protection).

## The studio merge: 129 conflicts, resolved with proof

The hard part. `semantic_twin/` was committed **independently** on both lines
(production bootstrapped from a snapshot of the studio checkout), so git saw
add/add conflicts with no common ancestor — 129 files.

**The trick that made it safe**: for each conflicted file, check whether one
side's exact blob appears anywhere in the other side's history. If studio's
version is an old production state → master wins, provably nothing lost (and
vice versa). Results:

- **113 files → master** (studio's copy was a stale production snapshot)
- **7 files → studio** (master's copy was the stale one: the fishnet review from today, both .gitignores, semantic_twin pyproject, uv.lock)
- **9 needed real thought**:
  - `report.tex`/`make_report.py` rename triangle: content byte-identical both sides, pure location dispute. Kept studio's `archive/report/` placement (the report is retired).
  - `BUGS.md`: studio's version (the dated status audit) is a strict superset of master's — zero deletions in the diff. Took it.
  - Microenvironments doc: **both** arms wrote different audits of the same sites. Kept production's strict audit as canonical and appended the studio walk-arm audit with an attribution header. Both survive.
  - Root `pyproject.toml`: master had dependabot version bumps, studio had the CPU-first extras split (`body` into `all`, torch CPU index, `gpu` opt-in). Orthogonal → union. **One real incompatibility**: dependabot's `mpmath>=1.4.1` cannot coexist with `body` in `all` (torch → sympy caps mpmath < 1.4). Reverted that single bump with a comment. `uv lock` re-resolved and `uv lock --check` passes.

**Why no data can be lost even where master won**: `fa394bbf` is a real merge,
so the studio branch's every commit and every file version remains reachable
forever via the second parent. Conflict resolution only chose the *current*
content.

## Test gates before the push

- Core aegis fast suite on merged master: **3544 passed, 0 failed**.
- semantic_twin suite: **52 failed / 2920 passed** — the failure list is
  **byte-identical** to the pre-merge baseline on the untouched production
  tree (environment-dependent tests: missing `mapbox_earcut`, `skimage`, etc.
  in this venv). Zero new failures, +29 newly passing tests.
- `ruff check src/` clean. Merged `pyproject.toml` parses, `uv lock --check` passes.

## What got deleted, with the proof used

| Deleted | Proof it was safe |
|---|---|
| Worktrees `~/aegis-body-path`, `~/aegis-portable-binding` | Branch tips byte-equal to merged PR heads (#912, #913) |
| Worktree `~/aegis-master-ro` | My own read-only snapshot from tonight, clean |
| Worktree `~/aegis-report-integrity` | My branch squash-merged as #932; clean |
| Worktree `~/aegis-exposure-body-path` | Tip == PR #925 head; clean; gitignored outputs checked afterwards (see scare below) |
| 7 local branches (prague-cdf, visibility-distal-gate, cdf-portable-body-path, exposure-body-path, panorama-preview-render, portable-binding-paths, self-shadow-route-corrections) | Each tip matched its merged PR head; the one mismatch (self-shadow) was proven content-equivalent: its extra tip commit is patch-identical to a master commit, and its other two commits were exactly PR #842 |
| Local + remote `feature/coherent-exposure-studio` | Fully contained in master via the true merge (`git branch --merged`) |
| Local `fix/roofline-report-integrity`, `fix/registration-cohort-mesh-resolver` | Merged via #932 / #925; remotes auto-deleted |
| Remote `fix/repr-empty-sab`, `refactor/maintainability-scene-components` | 0 content-unique commits vs master |
| Remote `claude/fix-compliance-summary-na-display`, `agent/code-review-agent-1927200`, `agent/code-review-agent-2187173` | PRs #414/#421/#434 MERGED |

## The one scare, and the save

`git worktree remove` on the production worktree silently deleted its
**gitignored** files — including what I believed was the only local copy of
the five-city campaign export (source campaign dirs are on the dead GPU box).
Immediate check: the export also lives in the main checkout's `outputs/`
(that's the copy the figures work hash-verified). To end this fragility, the
export is now **committed to master** (`ae17c8b3`), with a `.gitattributes`
`-text` rule (`06632c7e`) so the archived bytes stay exact — all four files
re-verified against the manifest sha256 from the committed blobs.

Lesson recorded: before removing a worktree, list its gitignored files, not
just `git status`.

## Uncommitted work: what was found and what happened to it

Swept every worktree before merging. Only the main checkout was dirty (32 files):

- **Committed** (on the studio branch pre-merge, now on master): the BUGS.md status audit, the microenvironments audit addition, the CPU-first pyproject/uv.lock split, self-shadowing venv path fixes + dependency freeze, the roofline paper draft, 13 supplementary-figure scripts + numbers, session reports (`agent_docs/`), campaign street-route JSONs. (Figure PDF/PNGs are gitignored by repo policy; the committed scripts regenerate them.)
- **Restored, not committed** (judgment call): three uncommitted *deletions* — `INVENTORY.md`, `README.md` (paper dir), and `spinoff/custorix/custorix_valtorix_dossier.md`. The `_AGENTS.md` that seemed to replace the first two is an empty template (abandoned mid-reorg), and the custorix dossier is unrelated business content. Restoring is reversible; a wrong deletion on master is not. **Robin: re-delete if intended.**
- **Left untracked** (scratch/stale): `_AGENTS.md`, `old_agents_md.md`, `CODEX_PROMPT.md`, `HANDOFF*.md` in the main checkout. Four stale doc copies that collided with master-tracked files were moved to `~/aegis-untracked-stale-20260809/` (not deleted).

## What remains on disk and why

| Path | What | Keep? |
|---|---|---|
| `~/aegis` | The one checkout, on master | Yes |
| `~/aegis-roofline-results-20260807T015530Z` (410M) | Historical two-city hybrid result package | Yes (archive) |
| `~/aegis-roofline-stage-20260809-brussels-preflight` (94M) | **Completed Brussels campaign** (16/16 replicas, hash-verified, EXIT=0) — not yet integrated anywhere | Yes until integrated |
| `~/aegis-roofline-stage-20260807T015530Z-oret` (292M) | Old staged tree from the two-city era | Probably retirable — Robin's call |
| `~/aegis-branch-backup-2026-05-30.bundle` (234M) | May git bundle backup | Robin's call |
| `~/aegis-untracked-stale-20260809/` | 4 stale doc copies moved aside during checkout | Delete after a glance |

## Remote branch debris (documented, not deleted)

29 remaining `agent/*` / `claude/*` branches from the April automation era:
**6 with CLOSED PRs** (rejected work — deleting discards it for real) and
**23 with no PR at all** (content never reviewed). They have zero local
footprint. Kill-list with per-branch verdicts:
`git ls-remote --heads origin | grep -E "agent/|claude/"` and the session
scratch verdicts said 3 MERGED (already deleted), 6 CLOSED, 23 NO_PR.
Bulk-delete anytime with
`git push origin --delete <branch>...` if the CLOSED/NO_PR work is confirmed
worthless. `bug-screenshots` is functional (bug-reporter storage) — keep.

## For codex (V2 campaign)

Dust has settled. Work from `master` (`origin/master` == local, tag v0.40.0).
The brief is at `papers/coherent-exposure-operator/V2_CAMPAIGN_BRIEF.md`.
Everything the production line had is on master, including the transport
cache identity fix — note that fix intentionally invalidates persistent
transport cache entries (runtime-only; first re-run repopulates).

## Open items for Robin

1. The three restored deletions — re-delete if they were intentional.
2. The 29 debris remote branches — bulk-delete or ignore.
3. `~/aegis-roofline-stage-20260807T015530Z-oret` + the May bundle — retire?
4. Brussels results (city #6) — review and decide whether it joins the multicity export.
5. Release workflow for v0.40.0 — watch for the full-matrix result on GitHub.
6. Everything in `agent_docs/SESSION_REPORT_20260809_overnight.md` NEEDS_CONTEXT still stands (Krakow quota, Toulouse, Milan, dead GPU boxes, roughness decision).
