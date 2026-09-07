# OJ-COMS revision artifacts

The current manuscript source is assembled from the PaperMaker tree in
`../main/`. The review artifacts in this directory were generated on
2026-08-27 after the final local QA pass.

| Artifact | Purpose | SHA-256 |
|---|---|---|
| `../build/main.tex` | Final assembled OJ-COMS source | `10b29e28ce601e70a814df5154d2920360ec36ff3e955e53904b95480d442b9f` |
| `../build/main.pdf` | Final eight-page OJ-COMS PDF | `6ae79047f970a73d45527009a41c87118dc5328e2f0ce2a4775b0f128e0b9499` |
| `ojcoms_20260827_latexdiff.tex` | Color-marked diff source | `93f4ef90849ff63acd2b70c703b014dc9070a1203dd31a4d9a16b2a50d2a6fff` |
| `ojcoms_20260827_latexdiff.pdf` | 12-page visual diff | `6dca4e709131a653ed2f20bf12f53b23a86aaa0f0466910d50774c733bb8747f` |
| `flow_20260827_latexdiff.tex` | Flow-pass diff source | `aef5a25f1ae4780482fc25cceadddc08197cb8f2e6549ea3c898c5e02d2dd9fc` |
| `flow_20260827_latexdiff.pdf` | Nine-page flow-pass visual diff | `781225c8d7e71258e36ef0c749355024869922c00146730bceb03942a3906a9d` |

`main_an_almost_correct_mint_of_v1.tex` is the preserved manuscript baseline
for the paper diff. The old baseline uses the IEEE Access class, so the diff
shows template and front-matter replacement in addition to scientific and
prose edits.

The latexdiff source has one documented mechanical repair. Latexdiff 1.3.1a
wrapped the optional argument of `cmidrule` in change macros and produced
invalid LaTeX. The generated line was restored to `cmidrule(lr){2-4}`. The
table contents remain fully marked.

Graphics markup is disabled in the paper diff because the ORCID package loads
Hyperref, whose PDF-string handling conflicts with Latexdiff's temporary
`includegraphics` wrapper. Current figures and author portraits are still
included, while all textual changes remain color marked.

## Protected flow-pass state

`flow_20260827_before/` preserves the exact paper and flowchart state before
the final flow pass. Its assembled source has SHA-256
`88d4a309e9847581d0a9b8d27bf56a87fbe03938489469899a18d05de99ca5c1`,
and its PDF has SHA-256
`2ae58414c0a995c4ea2386705f87afa51cac2058d909b5e51dee0169fb792114`.
The protected flowchart source, PDF, and PNG hashes are respectively
`bcd5939e9aa4c257bb4213d39bcf7180a86680e68a654d3de8e531f60e5b25b9`,
`eb0f336235a8552510d16de75506885a3c576cc121e4045e3ca4dcd880b72fde`,
and `18b1ee40a535f615743a696823f705c555a43bfd6fc75bfc7005f79dde6b56c2`.

The final flowchart source, PDF, and PNG hashes are respectively
`04ea578def203eacec380786593f58d48fd3661056dd982a7cce0921cbcb9afd`,
`aa68e31a964135b1dae5632b9186bb4ee9007b8a848e970d56ed9687d287146e`,
and `cc214b7fad7b8d702b2e711870fd70d7d296ec3763fb49a8f0e39c3e162cd6ea`.

Additional review records:

- `response_to_notes.md` answers the author's revision brief point by point.
- `flow_20260827_report.md` records the final flow, synchronization, layout,
  and QA pass.
- `verb_audit.md` records the complete manuscript verb review.
- `claude_opus_review.md` preserves the first external-review attempt.
- `claude_opus_flow_review.md` records the completed Claude Opus 4.6 review and
  the disposition of its findings.
- `../QUESTIONS_BANK.md` contains the remaining submission decisions.
