# Documentation style guide

This guide covers all documentation, code comments, and docstrings in AEGIS.

## Core principles

- **Concise and direct.** No fluff. Get to the point.
- **Sound like a senior developer.** Confident, intelligent, efficient. No AI-like verbosity.
- **Professional and factual.** Describe what exists, not what's "new" or "improved".
- **Subtle expertise.** Drop occasional non-obvious details that show deep understanding.

## Voice and tone

- Academic and professional. Direct, present tense. No humor, no overly casual language.
- Use simple, direct language. Avoid jargon unless necessary.
- Less is more. If a sentence adds no value, remove it.
- Use "you" naturally. Use "AEGIS" or "the engine" in third person.
- Keep paragraphs to 3-4 sentences max.

## Capitalization

Only the first word of titles gets capitalized. Everything else lowercase, except proper nouns and acronyms (GUI, SAR, ICNIRP, AEGIS, MIMO, ECBF).

Good: `## Running the simulation`
Bad: `## Running The Simulation`

## Banned patterns

These are tells that an AI wrote the text. Never use them.

- **No em dashes** (use hyphens, commas, or parentheses)
- **No semicolons** (split into two sentences)
- **No "from X to Y"** constructions for lists
- **No rhetorical questions** as headers
- **No "As [profession]"** openings
- **No unnecessary transitions** ("Moving forward", "It's important to note")
- **No promotional language** ("new", "improved", "enhanced", "amazing", "powerful")
- **No excessive boldface** (bold sparingly for actual emphasis)

### Banned words

| Instead of | Use |
|------------|-----|
| utilize | use |
| leverage | use |
| in order to | to |
| it is important to note that | (delete) |
| delve into, deep dive | (rewrite) |
| embark, journey | (rewrite) |
| seamlessly, effortlessly | (delete or rewrite) |
| robust, comprehensive | (only if technically accurate) |
| landscape, ecosystem | (only if literal) |
| harness, unlock, empower | (rewrite) |

## Code and examples

- Focus on concepts, not boilerplate.
- Show actual commands and paths, not placeholders.
- Keep code snippets short and focused.

## Markdown rules for MkDocs

- Nested numbered lists: 4-space indentation, NO blank line before them
- Code blocks in lists: 8 spaces indentation
- Blank lines between distinct top-level list items
- Use `-` for all bullets (not `*`)
- Blank line before top-level lists after paragraphs
- Use admonitions (`!!! note`, `!!! warning`) sparingly

## Checklist

- [ ] Sentence case headings (only first word capitalized)
- [ ] No em/en dashes
- [ ] No semicolons
- [ ] No AI buzzwords
- [ ] Short paragraphs
- [ ] Active voice
- [ ] Specific, not vague
