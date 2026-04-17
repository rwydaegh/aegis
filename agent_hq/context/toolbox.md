# Your toolbox

Beyond the usual Edit/Read/Write/Glob/Grep/Bash, you have:

## Skills (use the `Skill` tool)

Project skills are loaded at session start. Lean on them when relevant:

- **brainstorming** — before any creative/design work
- **writing-plans** — when spec is clear but implementation is multi-step
- **test-driven-development** — before writing implementation code
- **systematic-debugging** — any bug, test failure, unexpected behavior
- **verification-before-completion** — before claiming anything is done/fixed/passing
- **receiving-code-review** — when reading review feedback
- **ship** — full PR workflow (issue, branch, commit, PR, merge)
- **qa** — exercising the viewer for bugs
- **simplify** — review changed code for reuse/quality/efficiency
- **maintainability** — reduce tech debt, qlty hotspots
- **security-review** — review pending changes for security issues
- **release** — build changelogs and tag releases
- **docs** — write AEGIS documentation pages
- **claude-api** — Anthropic SDK / Claude API work

Only invoke a skill whose name appears in the available-skills list of this
session. Never invent a skill name.

## Subagents (use the `Agent` tool)

Dispatch to specialized agents when the work is a clean handoff:

- `Explore` — fast codebase exploration (glob/grep/read over many files)
- `Plan` — architecture-level implementation planning
- `general-purpose` — multi-step research or implementation
- `max-think` — the hardest problems (subtle bugs, architectural decisions)
- `code-reviewer` — independent review of completed work

Run independent subagents in parallel by issuing multiple Agent calls in a
single response.

## Task tracking (TaskCreate / TaskUpdate / TaskList)

Use these for any multi-step run where progress tracking helps you stay
coherent across 30-90 minutes of work. Not for trivial one-step jobs.

## Web and community research

- `mcp__perplexity__perplexity_search` — URLs, facts, recent news with citations
- `mcp__perplexity__perplexity_ask` — quick AI-answered questions with citations
- `mcp__perplexity__perplexity_research` — deep multi-source investigation (slow, 30s+)
- `mcp__perplexity__perplexity_reason` — complex step-by-step analysis
- `mcp__reddit__*` — honest community opinions for library/tool evaluation
  (per CLAUDE.md, Reddit is the best source for unfiltered developer opinions).
  `WebFetch` cannot access Reddit or Twitter; use the MCP.

Prefer these over raw `WebFetch` / `WebSearch` when you need cited,
synthesized answers rather than raw pages.
