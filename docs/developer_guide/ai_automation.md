# AI automation

AEGIS runs several Claude agents on GitHub Actions. They find bugs, fix them, build features, and test the production viewer around the clock. Every agent uses Claude Opus (`claude-opus-4-6`) via the `anthropics/claude-code-action` GitHub Action.

## How the pieces fit together

```
                          ┌─────────────────┐
                          │  Production app  │
                          │  aegis.waves-    │
                          │  ugent.be        │
                          └────────┬─────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼               ▼
              Real users     QA agent (2h)    QA swarm (manual)
                    │              │               │
                    ▼              ▼               ▼
               JS error?     Found a bug?    Found bugs?
                    │              │               │
                    ▼              ▼               ▼
                 Sentry      gh issue create  gh issue create
                    │         label: qa-bot    label: qa-bot
                    ▼              │               │
              Auto-create         ▼               ▼
              GH issue      ┌─────────────────────┘
              label: sentry │
                    │       ▼
                    ▼   claude.yml (qa-fix job)
              claude.yml    │
              (sentry-fix)  ▼
                    │    Fix → PR → squash merge
                    ▼
              Fix → PR → squash merge
                    │
                    ▼
              deploy.yml → Docker → Hetzner
              Sentry release tracking
```

Two additional agents work directly on the codebase without going through the issue pipeline:

- **Code review agent** reads code every 2 hours looking for bugs
- **Feature agent** picks high-value improvements every 3 hours

Both create PRs on `claude/*` branches. The `auto-merge-claude.yml` workflow squash-merges them automatically.

## Agents

### QA agent

**Workflow:** `qa-agent.yml`
**Schedule:** every 2 hours
**What it does:** Opens the production site in Playwright, picks a random focus area (antenna placement, MIMO mode, dosimetry HUD, etc.), and interacts with the app like a real user. Takes screenshots, reads them, and files GitHub issues for visual bugs or behavioral oddities.

The QA agent does not report JavaScript errors. Sentry catches those separately.

Each issue gets the `qa-bot` and `bug` labels, which triggers the fix pipeline (below).

### QA swarm

**Workflow:** `qa-swarm.yml`
**Trigger:** manual only

A two-job pipeline. The manager job reads recent commits, explores the codebase, and divides the testing surface into 5 non-overlapping scopes. Then 5 parallel tester jobs each run Playwright against the production site, focusing on their assigned scope. Same issue-filing behavior as the QA agent.

### Code review agent

**Workflow:** `code-review-agent.yml`
**Schedule:** every 2 hours (offset 30 minutes from QA agent)

Reads recently changed code, runs the test suite, and looks for bugs through static analysis. Checks for logic errors, edge cases, array shape mismatches, floating point issues, and inconsistencies between the code and the physics in the monograph.

When it finds a bug, it fixes it, adds or updates a test, and creates a PR. When something looks suspicious but uncertain, it files an issue with the `needs-investigation` label instead.

### Feature agent

**Workflow:** `feature-agent.yml`
**Schedule:** every 3 hours (offset 15 minutes from other agents)

Reads the codebase and open issues, then picks one high-value improvement to implement. Prioritizes fixing open issues over inventing work. Focuses on tests for untested code paths, performance in hot paths, error messages, input validation, and analysis utilities.

Creates one PR per change. Scope-limited by design: ship one clean thing rather than start three.

## Fix pipelines

### Sentry auto-fix

When a JavaScript or backend error hits Sentry in production, two things happen:

1. Sentry creates a GitHub issue via webhook with the stack trace, breadcrumbs, simulation state, and browser info. The issue gets the `sentry` label.
2. `sentry-autofix.yml` adds an `@claude` comment if the webhook body did not already contain one.
3. The `sentry-fix` job in `claude.yml` picks it up, reads `.claude/rules/sentry-issues.md`, fixes the bug, and creates a squash-merged PR.

After the PR merges, `deploy.yml` builds a Docker image, pushes to the Hetzner server, and registers a Sentry release. If the fix works, the Sentry issue auto-resolves when the error stops recurring.

### QA bot fix

When the QA agent or QA swarm files an issue with the `qa-bot` label:

1. The `qa-fix` job in `claude.yml` triggers.
2. Claude reads the reproduction steps from the issue body, fixes the bug, and creates a squash-merged PR referencing the issue.
3. The issue auto-closes on merge via the `Fixes #N` reference.

### @claude mentions

Any issue or PR comment containing `@claude` triggers the `claude` job in `claude.yml`. This is the general-purpose entry point for human requests. No specific prompt is injected. Claude reads the issue or PR context and responds.

## Auto-merge

`auto-merge-claude.yml` watches for PRs opened by `claude[bot]` on branches matching `claude/*`. It squash-merges them immediately using a PAT token (the default `GITHUB_TOKEN` cannot trigger downstream workflows).

The fix pipelines (`qa-fix`, `sentry-fix`) merge their own PRs explicitly within the same job. The auto-merge workflow is a safety net that catches PRs from the code review and feature agents.

## Deployment

`deploy.yml` runs on every push to master. It:

1. Runs CI (lint + tests)
2. Builds the React frontend with Sentry source maps
3. Builds and pushes a Docker image to `ghcr.io`
4. Deploys to Hetzner via SSH
5. Runs a health check (3 retries, 10s apart)
6. Registers a Sentry release with auto-associated commits
7. Deploys Modal serverless functions (GPU ray tracing)

The full test matrix (Linux/Windows, Python 3.11-3.13) only runs on tag pushes via `release.yml`.

## Configuration

All agents authenticate via `CLAUDE_CODE_OAUTH_TOKEN` (OAuth, not API key). The model is set in `claude_args`:

```yaml
claude_args: '--model claude-opus-4-6 --allowedTools "Bash(*)" "Read" "Write" "Edit" "Glob" "Grep"'
```

Agent concurrency groups prevent overlapping runs of the same agent. Different agents can run in parallel.

| Secret | Purpose |
|--------|---------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code authentication |
| `PAT_TOKEN` | PR merge + downstream workflow triggers |
| `SENTRY_AUTH_TOKEN` | Sentry release tracking |
| `HETZNER_SSH_KEY` | Production deployment |
| `MODAL_TOKEN_ID/SECRET` | Modal serverless deployment |
