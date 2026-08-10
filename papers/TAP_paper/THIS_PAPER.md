# THIS_PAPER.md

Per-paper notes for using PaperMaker9000 on the TAP paper. The existing
`.circa/` folder is Robin's older live feedback layer from the v1 drafting
process and is not an action source for this review pass.

## This paper

- **Working title**: Closed-Form Absorbed-Power Dosimetry from 1 to 100 GHz
- **Author**: Robin Wydaeghe (Ghent University and imec)
- **Target journal**: IEEE Transactions on Antennas and Propagation
- **Historical source draft for the PaperMaker intake**: `v1_to_coauthors/paper.tex`
- **Canonical current source**: `main/`
- **Current phase**: v4 coauthor feedback follow-up

## PaperMaker state

- `papermaker grind v1_to_coauthors/paper.tex --target .` populated `main/`
  from the coauthor version.
- `reviews/2026-05-11_wout_joseph/manifest.json` registers the 13 source
  images with SHA-256 hashes.
- `reviews/2026-05-11_wout_joseph/transcription.md` holds the image-by-image
  handwriting transcription.
- `reviews/2026-05-11_wout_joseph/actions.md` distills the transcription into
  paper-edit tasks and explicitly keeps low-confidence readings out of the
  confirmed queue.

## Review discipline

- Do not use `.circa/` comments as pending Wout feedback.
- Do not edit `paper.tex` directly from low-confidence handwriting.
- Keep each feedback-driven edit traceable to a source image and page region.
- Prefer structural edits first: introduction/method relocation, definitions,
  figure references, section naming, and conclusion compression.
