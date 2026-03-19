# AEGIS documentation writing guide

Complete reference for writing and maintaining AEGIS documentation. Consolidates style rules, MkDocs formatting, and content patterns.

## Core principles

1. **Concise and direct.** No fluff. Get to the point.
2. **Sound like a senior developer.** Confident, intelligent, efficient. No AI-like verbosity.
3. **Professional and factual.** Describe what exists, not what's "new" or "improved".
4. **Subtle expertise.** Drop occasional non-obvious details that show deep understanding.
5. **Physics-first.** AEGIS is a dosimetry engine. Equations and physical reasoning come before API trivia.

## Voice and tone

- Academic and professional. Direct, present tense.
- Use simple, direct language. Avoid jargon unless necessary.
- Less is more. If a sentence adds no value, remove it.
- Use "you" naturally. Use "AEGIS" or "the engine" in third person.
- Keep paragraphs to 3-4 sentences max.
- Active voice preferred.
- Be specific ("0.35% error", "O(MN)") not vague ("small error", "efficient").

## Capitalization

Sentence case only. First word capitalized, everything else lowercase except proper nouns and acronyms.

Acronyms that stay uppercase: AEGIS, SAR, ICNIRP, MIMO, ECBF, QCQP, GUI, API, STL, EM, BVH, SH, TE, TM, MRT, PSD, GO, GELU, ReLU, FDTD, IT'IS, UE.

Good: `## Running the simulation`
Bad: `## Running The Simulation`

## Banned patterns

These are AI writing tells. Never use them.

### Formatting

- No em dashes or en dashes. Use hyphens, commas, or parentheses.
- No semicolons. Split into two sentences.
- No excessive boldface. Bold sparingly for actual emphasis.
- No inline-header vertical lists (`**Header:** description` on every item).
- No emojis in technical documentation pages.

### Language

| Instead of | Use |
|------------|-----|
| utilize | use |
| leverage | use |
| in order to | to |
| it is important to note | (delete) |
| delve into, deep dive | (rewrite) |
| embark, journey | (rewrite) |
| seamlessly, effortlessly | (delete or rewrite) |
| robust, comprehensive | (only if technically accurate) |
| landscape, ecosystem | (only if literal) |
| harness, unlock, empower | (rewrite) |
| at this point in time | now |
| due to the fact that | because |
| by means of | by, using |

### Structure

- No "from X to Y" constructions for listing things
- No rhetorical questions as headers
- No "As a [profession]" openings
- No unnecessary transitions ("Moving forward", "It's important to note")
- No promotional language ("new", "improved", "enhanced", "amazing", "powerful")
- No trailing summaries ("In conclusion, we've seen that...")
- No repeating the question back before answering

## How to sound human

- Vary sentence length. Mix short and long.
- Skip the preamble. Start with the answer.
- Leave some things unsaid when the context is obvious.
- Occasional sentence fragments are fine.
- Reference specifics ("the 0.35% error in Table 6") not generalities.
- Perfectly parallel list items are an AI tell. Vary your phrasing slightly.

## Mathematics

AEGIS documentation uses MathJax for LaTeX rendering.

- Inline math: `$S_{ab}$`
- Display math: `$$S_{ab}(\mathbf{r}) = T_0 \cdot [\hat{n} \cdot (-\hat{k})]_+$$`
- Use `\mathbf{}` for vectors, `\hat{}` for unit vectors
- Use `\text{}` for operator names in equations (e.g., `\text{ReLU}`)
- Keep equations close to the monograph notation

## Code and examples

- Focus on concepts, not boilerplate.
- Show actual commands and paths, not placeholders.
- Keep code snippets short and focused.
- Always include language tags on code blocks (`python`, `bash`, `json`).
- Show realistic, working examples.

Good: `results/dosimetry/skin_28ghz/`
Bad: `results/{tissue}/{frequency}/`

## MkDocs formatting rules

### Lists

- Use `-` for all bullets (not `*`)
- Nested numbered lists: 4-space indentation, NO blank line before them
- Code blocks in lists: 8 spaces indentation
- Blank lines between distinct top-level list items
- Blank line before top-level lists after paragraphs

### Admonitions

Use sparingly to maintain impact.

```markdown
!!! note
    Brief, useful information.

!!! warning
    Something that could cause problems.

!!! tip
    A helpful shortcut or technique.

!!! example
    A concrete example.
```

### Tabbed content

```markdown
=== "Incoherent (levels 0-6)"
    Uses scalar power per path.

=== "Coherent (levels 7-8)"
    Uses complex amplitudes and MIMO structure.
```

### Abbreviations

Define domain-specific acronyms in `docs/includes/abbreviations.md`. They auto-expand on hover throughout the site.

```markdown
*[SAR]: Specific Absorption Rate
*[ICNIRP]: International Commission on Non-Ionizing Radiation Protection
```

### Cross-references

Link to other pages instead of re-explaining concepts.

Good: "For the full parameter list, see [configuration](../reference/configuration.md)"
Bad: [re-explaining the entire configuration in the tutorial]

## Document types

### Landing page
- Grid cards with icons linking to major sections
- Brief project description with the core equation
- Quick start code snippet

### Getting started
- Installation steps (minimal)
- First working example
- Where to go next

### User guide
- Workflow-focused, explains how things work from a user perspective
- Conceptual explanations before technical details
- Code examples showing common usage patterns

### Developer guide
- Architecture, module structure, data flow diagrams
- Testing strategy and how to run tests
- Design principles and conventions

### API reference
- Auto-generated via mkdocstrings
- Organized by functional area (tissue, geometry, kernels, coherent)
- Minimal manual text, mostly mkdocstrings directives

### Theory pages
- Link to the monograph for full derivations
- Show the key equation for each concept
- Explain the physical intuition, not just the math

## Checklist before publishing

- [ ] Sentence case headings
- [ ] No em/en dashes
- [ ] No semicolons
- [ ] No AI buzzwords
- [ ] Short paragraphs (3-4 sentences max)
- [ ] Active voice
- [ ] Specific numbers, not vague language
- [ ] Links to other docs instead of re-explaining
- [ ] Code blocks have language tags
- [ ] Equations render correctly with MathJax
- [ ] Navigation works (links not broken)
