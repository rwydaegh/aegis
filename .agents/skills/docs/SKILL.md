---
name: docs
description: Write or update AEGIS documentation pages. Use when creating new docs, rewriting existing docs, or adding content to the documentation site.
user-invocable: true
---

# Documentation skill

You are writing documentation for AEGIS, a geometric dosimetry engine for wireless exposure assessment.

## Before writing

1. Read `.claude/rules/docs-style.md` for the full style guide (includes writing rules, MkDocs formatting, banned patterns)
2. Read `.claude/ai_writing_tells.md` for the AI writing tells checklist
3. Read `mkdocs.yml` to understand the current site structure
4. Read relevant source code to understand the API you're documenting

## Style rules (critical)

- Sentence case headings only (first word + acronyms/proper nouns)
- No em dashes, no semicolons, no AI buzzwords
- No promotional language ("new", "improved", "enhanced")
- No inline-header vertical lists (`**Header:** description`)
- Active voice, short paragraphs (3-4 sentences max)
- Be specific ("0.35% error") not vague ("small error")
- Sound like a senior developer, not a marketing department

## Content rules

- Physics-first. Equations and physical reasoning before API details.
- Use MathJax: `$inline$` and `$$display$$`
- Link to other docs instead of re-explaining
- Show working code examples with real values
- Use admonitions (`!!! note`, `!!! warning`) sparingly
- Use `-` for bullets, not `*`
- Always include language tags on code blocks

## API reference pages

Use mkdocstrings directives. Organize by functional area.

```markdown
::: aegis.tissue.TissueModel
    options:
      show_root_heading: true
      show_source: true
```

## After writing

1. Check all headings are sentence case
2. Grep for banned patterns (em dashes, semicolons, AI words)
3. Verify MathJax renders (check for unescaped underscores in prose)
4. Run `python -m mkdocs serve` to preview if possible
5. Update `mkdocs.yml` nav if you added new pages
