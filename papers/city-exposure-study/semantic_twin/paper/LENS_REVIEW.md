# Lens review

The manuscript received one full review pass after the initial draft. Separate
reviews covered scientific claims, reproducibility, citations and novelty,
IEEE Access requirements, figures and tables, cold-reader clarity, and the
author's BioEM-derived style. PaperMaker9000 also checked rule coverage for
every paragraph lens.

## Corrections applied

- The body equation now keeps direct and order-1 specular paths as exact
  directional atoms. Only first-diffuse power uses the 4,096 output cells.
- The normalized absorbed-power-density and whole-body-SAR quantities now have
  explicit symbols and units.
- The crop is identified as a 250 m radius, with its area stated.
- The validation comparators are separated: 0.0616 dB against deterministic
  quadrature for bounced transfer, 0.0621 dB against Sionna RT for bounced
  transfer, and 0.0344 dB against Sionna RT for total transfer.
- The reported component shares are recomputed whole-body-SAR shares rather
  than raw-transfer shares.
- The main paper no longer claims body self-shadowing or an unreported peak
  absorbed-power-density endpoint.
- Duplicate setup tables and the duplicate main-text convergence figure were
  removed. The complete convergence figure is in the supplement.
- Vistas, independent image-informed scene work, propagation validation,
  dosimetry, the anatomical model, next-event estimation, and the AI system
  were added to the references.
- Figure colors, grayscale encodings, labels, captions, and the graphical
  abstract were revised after visual inspection.

## Limits retained on purpose

The paper reports five fixed routes. It does not claim population exposure,
city ranking, deployment exposure, regulatory compliance, material accuracy,
complete multipath, or full city-model validation. Central route statistics
are stable at 16 replicas. Some lower-tail standpoints in Mexico City and Tokyo
Hachiko remain less stable and are reported as such.
