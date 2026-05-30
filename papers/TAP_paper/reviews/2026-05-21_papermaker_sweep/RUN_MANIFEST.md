# PaperMaker9000 sweep run — 2026-05-21

- Paper: TAP_paper, branch paper/tap-presweep
- Lens coverage: 153/153 rules claimed (clean)
- Agents dispatched: 398 task files generated; 398 verdicts collected
- Dispatch shape: vision (9 figures + 14 pages), 4 global passes, 21 section-flow, 86 sentence-craft (dedicated opus), 86 paragraphs x {voice-tells, lexical-spotcheck, latex-micro} (one opus agent each, separate per-lens verdicts), 8 tables, 1 abstract, 1 heading batch, 1 adversarial.
- Result: 315 clean / 83 flagging verdicts; 105 flags across 40 distinct rules.
- Raw per-leaf verdicts: build/sweep/results/*.yaml (gitignored); written into each leaf's ## reviews block.

## Incremental re-sweep — 2026-05-22
- Corpus update: coverage 153 -> 157 (+4 rules). Re-checked only the changed rules.
- kiss_simple_verbs (edited): 83 paragraphs -> 1 flag ("delivers" -> "gives").
- no_danger_mongering (new): 83 paragraphs + abstract -> all clear.
- conservative (new): 3 paragraphs -> all clear (safe-direction usage).
- no_titled_remark_corollary (new): 0 candidate leaves (N/A).
- section_economy (new): 20 sections -> 2 fragment flags + paper-level note (8 top-level sections vs ~6 target).
- Report regenerated markdown-safe (LaTeX spans in code spans + macro legend).
