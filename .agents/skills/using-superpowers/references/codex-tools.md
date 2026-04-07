# Codex tool mapping

Use this file when a ported Superpowers skill mentions Claude Code specific tools or workflows.

## Skill access

- Claude `Skill` tool -> Codex `/skills` or `$skill-name`
- Claude session-start skill injection -> Codex `SessionStart` hook or explicit `$using-superpowers`

## Agent and delegation concepts

- Claude `Task` or `Agent` tool -> Codex subagents and custom agents
- Claude specialist agent markdown files -> Codex `.codex/agents/*.toml`
- Claude "dispatch a fresh subagent" -> in Codex, explicitly ask for subagents or spawn them from tool-enabled environments

## Tooling differences

- Claude `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash` map cleanly to Codex file reads, patches, ripgrep, and shell commands
- Claude `WebSearch` and `WebFetch` map to Codex web search or configured MCP/web tools
- Claude `PostToolUse` hooks for `Edit|Write` do not port directly. Current Codex hook matching is mainly Bash-oriented.

## Workflow translation notes

- If a skill says "invoke another skill", do that in Codex by mentioning `$skill-name`
- If a skill assumes manual explicit invocation, keep using explicit invocation. Most ported repo skills disable implicit activation on purpose.
- If a skill requires a subagent and the current environment cannot spawn one, follow the skill locally as closely as practical and note the limitation.
