# Goal: native LaTeX rendering in Zed's markdown preview

## What we want

I'm migrating to **Zed** as my daily editor. I work heavily with formulas, so I need to open a markdown file and see LaTeX (`$...$` and `$$...$$`) rendered **inline, instantly, right in the editor's markdown preview** — no external tools, no browser, no friction at use-time.

Zed does **not** ship this yet. So the plan is to **build Zed from source with the in-flight community PR that adds it**, run that custom binary as my editor, and tolerate rough edges.

## The source of the feature

- Upstream tracking issue: **zed-industries/zed#40813** (open, unshipped).
- The PR to build: **zed-industries/zed#57339** — "Render LaTeX math in Markdown previews." Renders each formula to SVG via a KaTeX-compatible Rust engine (`ratex`) and draws it with Zed's existing SVG renderer. Small, contained change (mostly in `crates/markdown` and `crates/markdown_preview`).
- Note: the PR is stale vs `main` (conflicts) and has known minor rendering bugs. That's acceptable.

## Target machine

- **Windows.** This is the hardest platform to build Zed on — expect the initial toolchain setup to be the painful part.

## Definition of done

- A self-built Zed binary launches on Windows.
- Opening a markdown file with `$...$` / `$$...$$` and showing the preview renders the formulas inline.
- The build is repeatable (documented enough that re-pulling upstream + rebuilding is a quick, known process).

## Constraints / preferences

- **Do not uninstall or clobber my existing Zed install** — the custom build should coexist as a separate binary.
- Bugs are fine; I'm willing to hack on the rendering code myself (the math logic lives in the new `crates/markdown/src/katex.rs`).
- Use-time must stay zero-friction. Build-time / occasional-rebuild friction is accepted.
- Figure out the exact steps yourself (prereqs, branch checkout, optional rebase onto `main`, build, run). This doc is intent only, not instructions.
