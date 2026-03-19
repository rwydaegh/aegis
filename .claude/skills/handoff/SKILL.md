---
name: handoff
description: Write a session handoff document for context continuity across sessions
user-invocable: true
---

# /handoff - Session context handoff

Write a structured handoff document when ending a session or when context is filling up. This lets the next session resume without losing state.

## Usage

```
/handoff                    # write handoff for current session
/handoff <slug>             # write handoff with custom name
```

## Output file

Write to `.claude/handoffs/YYYY-MM-DD-<slug>.md` where slug describes the work (e.g., `2026-03-19-te-tm-polarisation.md`).

## Required sections

```markdown
# Session handoff: <brief title>

## Intent
What the user was trying to accomplish this session. One paragraph.

## Completed
- What was done, with commit hashes where applicable
- File paths of modified files

## In progress
What was being worked on when the session ended:
- Which files were being modified
- What the next step was going to be
- Any partially-written code (file path + line range)

## Failed approaches
What was tried and did not work. Include why it failed so the next session does not repeat the mistake.

## Blockers
Anything that prevented progress. Missing data, unclear requirements, bugs in dependencies.

## Next steps
1. First thing to do (specific: file path, function name, what to change)
2. Second thing to do
3. ...
```

## Rules

- Keep it under 60 lines
- Be specific: file paths, function names, line numbers, commit hashes
- Do not summarize the entire project, only the session's delta
- Check `git log --oneline -5` and `git status` to capture the current state accurately
- If context is filling up, prioritize writing the handoff over finishing the current task

## Resuming from a handoff

The next session starts with:
```
Read the latest file in .claude/handoffs/ and resume where I left off.
```
