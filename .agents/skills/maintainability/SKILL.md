---
name: maintainability
description: Use when the qlty maintainability badge drops below A, when asked to reduce technical debt, or when refactoring for code quality. Runs qlty CLI to find hotspots, triages with judgment, and fixes what matters.
user-invocable: true
---

# /maintainability - qlty-driven code quality improvement

Analyze and fix maintainability issues using the qlty CLI. Goal: keep the Qlty Cloud badge at grade A (tech debt ratio below 5%).

## Usage

```
/maintainability              # full audit and fix cycle
/maintainability src/aegis/   # scope to specific directory
/maintainability --audit-only # report without fixing
```

## What the CLI can and cannot tell you

The qlty CLI gives you raw data: smell counts, per-file/per-function complexity, duplication, linter issues. It does NOT give you the overall grade or tech debt ratio. Those are only visible on the Qlty Cloud dashboard (the badge in README links there). The user will tell you the current grade if they have it.

**Your proxy for progress:** total smell count and top-file complexity scores. Reducing these is what moves the needle on the dashboard grade. This is a serious effort. Expect to touch 10+ files across multiple tiers. Use subagents for independent refactors.

## Philosophy

qlty is a useful but imperfect tool. It catches real complexity hotspots but also flags things that are fine. You are the judge. The goal is not zero smells. The goal is a codebase where every function is easy to read, modify, and test.

**Fix what matters, ignore what does not:**
- High cognitive complexity in a function with real branching logic: fix it
- Physics naming conventions (A_ab, T0, k_hat) flagged as style violations: ignore, already triaged in qlty.toml
- Security warnings on intentional subprocess usage: ignore, already triaged
- Duplication across test files: usually fine, tests should be explicit
- Long file that is long because it has many small functions: not a real problem

## The cycle

### Phase 1: Audit

Run these commands and collect results:

```bash
qlty smells --all --quiet --no-snippets    # code smells (complexity, duplication, params)
qlty metrics --all --sort complexity --limit 30   # top 30 files by complexity
qlty metrics --all --functions --sort complexity --limit 30  # top 30 functions by complexity
qlty check --all --summary --no-fail --level medium   # linter issues at medium+ severity
```

Count total smells: `qlty smells --all --quiet --no-snippets | grep -c "Function\|High\|Duplicate"`

Parse the output. Build a table of hotspots ranked by impact:

| File | Complexity | Smells | Worst function | Worth fixing? |
|------|-----------|--------|----------------|---------------|

### Phase 2: Triage

For each hotspot, **read the actual code** before deciding. Classify into tiers. This is the most important phase. Do not skip reading the code.

**Tier 1 - Fix now** (high complexity, real readability problem):
- Functions with cognitive complexity > 20 that can be decomposed
- God functions doing 3+ distinct things
- Deeply nested conditionals (3+ levels)
- Functions over 80 lines with extractable blocks
- Files with total complexity > 60

**Tier 2 - Fix if easy** (moderate complexity, minor improvement):
- Functions with complexity 15-20 that have obvious extract targets
- Mild duplication in production code (not tests)
- Parameter counts of 6-8 where a dataclass would help

**Tier 3 - Leave alone** (not worth touching):
- Physics/math code where complexity is inherent to the algorithm
- Already-triaged patterns in qlty.toml
- Files that are long but well-structured
- Test files (complexity in tests is acceptable)
- Anything where "simplifying" would obscure the logic

Present the triage to the user before proceeding. Format:

```
## qlty audit results

**Current state:** N smells total, top file complexity: M (file.py)
**User-reported grade:** [ask if not provided]

### Tier 1 (will fix) - N items
- file.py:function_name - complexity N - plan: extract X, Y, Z into helpers

### Tier 2 (will fix if easy) - N items
- ...

### Tier 3 (leaving alone) - N items
- file.py:function_name - complexity N - reason: inherent algorithm complexity
```

### Phase 3: Fix

This is the ambitious part. Tier 1 alone may be 5-15 files. Use the `$dispatching-parallel-agents` skill to send independent file refactors to subagents. Each subagent gets:
- The file to refactor
- The specific smells/functions to address
- The refactoring patterns to apply (see below)
- Instructions to run `python -m pytest tests/ -m "not slow" -x` and `python -m ruff check src/ tests/` after changes

For each item (whether you or a subagent):

1. **Read the full function and its callers.** Understand what it does before touching it.
2. **Refactor for readability, not for qlty score.** Extract helpers that have clear names and single responsibilities. Do not create abstractions just to lower a number.
3. **Preserve behavior exactly.** No feature changes, no "improvements" beyond the refactor.
4. **Run tests after each file.** `python -m pytest tests/ -m "not slow" -x`
5. **Run ruff.** `python -m ruff check src/ tests/ && python -m ruff format --check src/ tests/`

Then do Tier 2 items, skipping any where the fix feels forced.

### Phase 4: Verify

After all fixes:

```bash
qlty smells --all --quiet --no-snippets | grep -c "Function\|High\|Duplicate"  # compare total
qlty metrics --all --sort complexity --limit 10   # check top files improved
qlty metrics --all --functions --sort complexity --limit 10  # check top functions improved
```

Report the before/after:

```
## Results

| Metric | Before | After |
|--------|--------|-------|
| Total smells | X | Y |
| Top file complexity | X (file.py) | Y (file.py) |
| Top function complexity | X (func) | Y (func) |
| Files touched | - | N |
```

The Qlty Cloud dashboard updates after push. Tell the user to check the badge after CI runs.

## Refactoring patterns that actually help

**Split large files into packages:** Qlty heavily penalizes large files via "High total complexity" smells. A 1000+ line file with complexity 300 split into 5 files of ~200 lines each eliminates the "High total complexity" smell entirely and often drops the per-file complexity below the threshold. This is the single highest-impact refactor for the dashboard grade. Convert `module.py` to `module/__init__.py` (re-exports public API) + topic-specific submodules. Callers see the same import paths.

**Extract-and-name:** Pull a block into a well-named helper. The function name replaces a comment.

**Early return:** Replace nested if/else with guard clauses that return early.

**Dict dispatch:** Replace long if/elif chains on a string/enum with a dictionary mapping.

**Dataclass parameter objects:** When a function takes 6+ related parameters, group them.

**Split by responsibility:** A function that validates, computes, and formats should be three functions.

## What NOT to do

- Do not rename variables just because qlty flags naming conventions. Physics notation is intentional.
- Do not add type annotations, docstrings, or comments to code you did not change.
- Do not refactor test files for complexity. Tests should be explicit and readable as-is.
- Do not create abstract base classes or strategy patterns just to reduce measured complexity.
- Do not "fix" duplication by creating a shared helper that is harder to understand than the duplicated code.
- Do not chase the score. If grade A requires butchering readable code, stop and explain why.

## Shipping

This is typically a large refactor (10+ files). Use the PR workflow:

```bash
git checkout -b refactor/qlty-maintainability
# ... commits ...
git push -u origin refactor/qlty-maintainability
gh pr create --title "Reduce cognitive complexity across hotspot files" \
  --body "..." --base master
gh pr merge --squash --delete-branch
git checkout master && git pull origin master
```

## Quick reference

| Command | Purpose |
|---------|---------|
| `qlty smells --all --quiet` | All code smells |
| `qlty smells --all --quiet --no-duplication` | Smells without duplication |
| `qlty metrics --all --sort complexity` | Files ranked by complexity |
| `qlty metrics --all --functions --sort complexity` | Functions ranked by complexity |
| `qlty metrics --all --dirs --max-depth 3` | Directory-level overview |
| `qlty check --all --summary --no-fail` | Full linter run with summary |
| `qlty check --all --fix` | Auto-fix what can be auto-fixed |
