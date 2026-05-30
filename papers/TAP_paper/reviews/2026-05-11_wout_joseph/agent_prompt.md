# TAP Wout Review Agent Prompt

You are working on the TAP paper review intake at `/home/user/aegis/papers/TAP_paper/reviews/2026-05-11_wout_joseph/`.

Goal:
Recover Wout's handwritten review marks as accurately as possible, then convert them into a clean, source-backed Markdown review ledger. This is not naive OCR. It is interpretive recovery: read the handwriting, but anchor every guess in the printed paper context, Wout's shorthand style, and the marked location on the page.

Important:
The previous pass was incomplete. Treat it as draft-only. Do not trust low-confidence rows without re-checking the image.
Do not be lazy. Work page by page, then region by region. Read the page at normal scale first, then zoom in, then zoom in again if needed. If a mark is unclear, zoom until it is stupidly close. If the text is still unclear, mark it as unresolved instead of guessing blindly.
The PaperMaker instance must be self-contained. Treat `/home/user/aegis/papers/TAP_paper/` as the complete world for code, scripts, prompts, review files, and generated artifacts. Do not import helper code or rely on sibling repos outside this directory. If a needed dependency or data file is missing, stop and ask Robin instead of silently reaching outside the instance.

Files:
- Source paper: `/home/user/aegis/papers/TAP_paper/v1_to_coauthors/paper.tex`
- Images: `/home/user/aegis/papers/TAP_paper/v1_to_coauthors/feedback_wout_extracted/feedback_wout/`
- Existing review intake folder: `/home/user/aegis/papers/TAP_paper/reviews/2026-05-11_wout_joseph/`

What to do:
1. Inspect the handwritten review pages page-by-page.
2. Recover every edit mark you can find:
   - insertions
   - deletions
   - circles
   - arrows
   - underlines
   - brackets
   - margin notes
   - cross-outs
   - `ok` approvals
3. For each mark, record:
   - exact image and page location
   - the printed text it refers to
   - the literal handwriting as best as you can read it
   - the smart interpretation of what Wout means
   - the concrete action for the paper
   - confidence level
4. Separate observation from inference. Do not blur them together.
5. If you are unsure, zoom in more. Use the smallest crop that still preserves context, then zoom further if needed.
6. Do not use the old 4x4 tiling as the main workflow. It cuts off context and encourages shallow reads. Instead, work page-by-page with interactive zoom and panning.
7. Read arrows, circles, strikeouts, brackets, and underlines as first-class marks. If an arrow points to a specific line, table, or sentence, capture that relation explicitly instead of summarizing it away.

Required reading style:
- Use the printed paper context to make smart guesses.
- Wout's shorthand often mixes Dutch and English.
- He often means structural edits, not just wording tweaks.
- He may write `fig 1 in method`, `future work`, `method section`, `definieer T0`, `ref`, `ok`, or strike out whole sentences.
- When he asks for a location or reference, preserve that location detail in the transcription.

Specific known patterns to verify and refine:
- top-right page 1: `soms AI tekst aanpassen`
- top-right page 1: `Fig 2 verwijderen` may or may not really be Fig. 2
- top-right page 1: `Future work max 2 zinnen bij conclusie`
- abstract: `nog iets inkorten; ik verwijderde enkele zinnen`
- abstract margin: `AEGIS`
- abstract: change singular `simulation` to plural `simulations`
- abstract lower-left: `wat bedoeld? local? beschrijf zin`
- abstract middle: struck sentence about the formula extending the classical projected-area identity and the ambient-occlusion/self-shadowing sentence
- before `Sim4Life FDTD`: there are four validations, not a laundry list
- remove `at 5.8 GHz` if Wout struck it
- Wout wants the abstract validation phrase to become a cleaner 4-way validation summary
- introduction:
  - write out `Finite-Difference Time-Domain` the first time
  - `simulation` -> `simulations`
  - `a regulatory campaign` -> `a simulation campaign`
  - `become infeasible` -> `become difficult`
- next page:
- `IT'IS Cole-Cole catalog` needs a ref and the `data/model?` note needs interpretation
- if Wout strikes through `IT'IS Cole-Cole catalog`, preserve the struck text and record the replacement request exactly
  - write out APD in full on first use
  - do not write `IT'IS` where Wout says not to
  - move the paragraph starting `The empirical scalars...` all the way to the end of that paragraph out of the introduction, and preserve the arrow note about `Method section X_1`
  - add refs at:
    - Kodera transmission
    - Bamba efficiency
    - 3 GHz dip
    - Bamba, Flintoft, Zhang
    - Diao, Kodera
  - decide whether `3 GHz dip` should stay in the paper if it is interesting
  - section 2 title needs `II. Method: stuk X_1` style meaning, not `Local absorption law` if that is what the marks imply
  - `The derivation below is exact; all approximations are introduced in subsequent sections` should be interpreted as `dit is al conclusie => verder zetten`
  - `A monochromatic plane wave` has `monochromatic` struck
- fig 1 caption is marked as good, but for methods, and needs `psSAR`, `SARwb`, `APD` defined
- page 4 has several literal notes that must stay literal: `Fig. 3a`, `Fig. 3b`, `The maximum deviation is`, `set Table I here: bottom`, and the SI note about Transactions

Output requirements:
- Create or update a Markdown transcription file and a Markdown action queue file.
- Make the transcription exhaustive.
- Include every confident mark you can recover.
- Include page/region references for every row.
- Include a confidence column.
- For uncertain marks, say so clearly and do not overstate them.
- Do not silently skip anything important.
- If a mark is an approval like `ok`, record it too.
- If a sentence is crossed out, preserve the exact struck sentence in the transcription and mark it as deleted/rejected.

Tone and standard:
- Be brutally honest.
- Be detailed.
- Prefer precision over speed.
- If a mark is unclear, zoom further instead of guessing lazily.
- If the handwriting remains unclear after close inspection, say so and leave it unresolved.

Before finishing:
- Summarize the highest-confidence edits separately from the low-confidence leftovers.
- Do not claim certainty where there is none.
