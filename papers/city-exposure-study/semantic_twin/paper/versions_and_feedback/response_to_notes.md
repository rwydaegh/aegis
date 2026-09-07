# Point-by-point response to `notes.md`

## Journal and submission format

1. **Target journal changed from IEEE Access to IEEE OJ-COMS.** The manuscript
   now uses the official `IEEEoj.cls`, OJ-COMS front matter, logo, running head,
   author block, correspondence block, and date placeholders. The assembled
   source is `build/main.tex` and the compiled paper is `build/main.pdf`.

2. **OJ-COMS requirements checked.** The paper uses the official January 2024
   template assets. The remaining submission-specific items are recorded in
   `QUESTIONS_BANK.md`: final journal dates, the active submission portal, a
   stable code and data DOI, and the final AI-use disclosure detail.

3. **Result QA completed.** The paper compiles in eight pages with no undefined
   references or citations and no overfull horizontal boxes. All fonts are
   embedded. PaperMaker reports 0 lint flags, 0 style hits, and 166 of 166 lens
   checks covered. Thirteen numerical claims pass, and the focused result test
   suite passes 11 of 11 tests.

## Title and abstract

4. **Title replaced exactly as requested.** The title is now *Human-Centric 6G
   RF-EMF Exposure with AI-Assisted Digital Twins in Ten Cities*.

5. **Abstract opens with exposure.** Its first sentence connects the city field
   to absorbed human-body power. The next sentence names exposure monitoring
   and epidemiological research, followed by the ten-city exposure goal.

6. **The abstract is within the word limit.** It is 249 words after the final
   exposure-context sentence, below the 250-word maximum.

7. **Old five-city scope removed.** The current manuscript contains ten cities,
   ten selected routes, 163 observation points, and 64 independent runs. No
   five-city claim remains.

8. **City language used where it reads naturally.** The abstract, title,
   introduction, and conclusion emphasize cities. Route language remains where
   it is scientifically necessary to prevent whole-city or population claims.

9. **Validation differences converted to percentages.** The abstract, Results,
   figure, and conclusion report 1.43% against deterministic quadrature and
   0.80% against the independent Sionna RT calculation. The reflected-component
   and total-power comparisons are explicitly distinguished.

10. **Concrete SAR result added and ordered first.** The abstract reports the
    normalized route-median whole-body SAR range of 0.00902 to
    0.129 m² kg⁻¹ per unit source-density and EIRP product, then the factor of
    14.31, component dominance, convergence, and validation.

11. **Human-centric and agentic-AI framing added.** The abstract names the
    human-centric digital twin and SAM 3 Agent. Robin's 2026-08-27 correction is
    treated as authoritative: SAM 3 Agent performs the production agentic AI
    step for material and vegetation assignment.

## Introduction

12. **Exposure-first introduction written.** The opening paragraph states why
    realistic RF-EMF exposure assessment must connect environmental fields to
    absorbed body power, including monitoring and epidemiological use.

13. **Literature arc rebuilt.** The introduction moves from exposure methods,
    to source normalization, to multimodal scene evidence, to the remaining
    environment-to-body gap. It follows the PaperMaker problem, prior work, gap,
    response, goal, and contributions sequence.

14. **The npj Wireless Technology paper is cited.** The introduction cites the
    28 GHz body-exposure work, and the source-model paragraph cites it again for
    the future distributed architecture context.

15. **The requested obsolete paragraph was removed.** The old prose beginning
    with image-derived material projection no longer appears.

16. **Special-issue framing is explicit.** Human-centric wireless systems,
    multimodal fusion, AI-assisted digital twins, SAM 3 Agent, and retained body
    direction appear without expanding the supported scientific claim.

17. **Goal and contributions are literal.** The introduction contains the
    exact signal sentence “The goal of this study is...” and a three-item
    contribution list covering the digital twin, exposure calculation, and
    ten-route results.

## Methods

18. **Section structure simplified.** The paper now has the standard top-level
    sections Methods, Results, Discussion, and Conclusion. Methods contains
    Study configuration, AI-assisted digital twin, Exposure calculation, and
    Numerical settings and route statistics.

19. **Banned wording removed from manuscript prose.** Standalone *map*,
    *mapped*, *mapping*, *registration*, *replica*, *audit*, *nested*, and
    propagation *transport* terminology were removed. *Mapillary* remains only
    as the proper name of the Vistas data set. *Transport* remains only inside
    a cited publication title.

20. **Figure introductions use the requested plain form.** The text says
    “Fig. 1 shows the configuration,” “Fig. 2 shows the flowchart of the
    method,” “Fig. 3 shows the difference from forward sampling,” and
    “Fig. 4 shows the comparison.” Each reference precedes the figure.

21. **Early figures placed near Methods.** Figures 1 and 2 use `[!htb]` and
    appear together on the following page. The compiled layout was inspected
    directly.

22. **Adjoint ray tracing is defined and cited.** The term is italicized and
    explained as launching rays from the observation point and testing source
    visibility from the first hit. It cites two adjoint ray-tracing references
    and a next-event-estimation reference.

23. **DMaMIMO wording is explicit and bounded.** The paper considers a future
    distributed massive MIMO architecture only to define possible access-point
    locations. Visible rooflines provide those possible locations. The next
    sentence states that coordinated transmission and beamforming are not
    modeled.

24. **Equations were compacted.** The source measure, reference scale,
    directional distribution, body coupling, and normalized endpoints use five
    numbered equation blocks. The angular-cell count appears in prose rather
    than as a separate displayed definition. All displayed equations are
    punctuated through their surrounding sentences.

25. **Flowchart redesigned.** The flowchart now combines three inputs into an
    AI label-check stage, joins pedestrian and possible-roofline information,
    computes radio paths, applies each arrival direction to the body, and ends
    at whole-body SAR. The labels use plain language and the output is exposure.

26. **Validation methods moved under a clear Results subsection.** Numerical
    settings remain in Methods. The controlled comparison and validation scope
    now appear under Results, subsection Validation.

27. **Hash and manifest prose removed.** No checksum, hash verification,
    artifact-manifest, or internal run-history text remains in the manuscript.

28. **Fibonacci terminology removed.** The manuscript states the number of
    fixed angular cells and does not foreground the sphere-construction method.

## Results, figures, and table

29. **Table II uses scientifically correct normalized units.** The requested
    grouped header was added over q10, q50, and q90. The header reads
    “Normalized whole-body SAR [m² kg⁻¹].” It does not say W kg⁻¹ because no
    deployment-specific source density or EIRP is assumed. Calling these values
    W kg⁻¹ would be dimensionally and scientifically wrong.

30. **The highest and lowest medians are stated.** Mexico City has the largest
    selected-route median, 0.1291 m² kg⁻¹, and Milan has the smallest,
    0.009016 m² kg⁻¹. Their ratio is 14.31.

31. **Figure 5 was simplified and retained.** Panel (a) keeps the raw ten-route
    empirical CDFs and marks the six fully shadowed points. Panel (b) keeps the
    simple component shares because it supports the paper's key direct,
    specular, and diffuse interpretation and fits without displacing the main
    result. The axes have no decorative top or right ticks, and the colors and
    fills are plain.

32. **A material-sensitivity subsection was added.** It reports the paired
    Madrid and Mexico City comparison, including the 5.9% increase and 3.6%
    decrease in route medians and the reason for the large Mexico City lower-tail
    ratio. It explicitly states that the control does not establish material
    accuracy or isolate reflectance.

33. **Diffuse terminology simplified and bounded.** The manuscript uses
    “single-reflection diffuse component” and explains that each sampled path
    ends after the diffuse reflection. It avoids the earlier *first-diffuse
    transport* wording.

34. **Reader-facing numerical precision applied.** Component medians are 78%,
    20%, and 0.5%. Validation and convergence use percentages. Route quantiles
    retain enough digits to reproduce the factor and lower-tail behavior.

## Discussion, conclusion, and prose

35. **Limitations rewritten with direct subjects and verbs.** The Discussion
    states the one-frequency, one-body, one-route-per-city, roofline-source,
    surface-label, one-reflection, uncertainty, validation, and timing limits.
    The complete city calculation is explicitly unvalidated.

36. **Future work appears only in the Conclusion.** A duplicated Discussion
    paragraph was removed. The conclusion retains the required sentence
    “Future work will consist of...” followed by field validation, measured
    transmitter distributions, higher reflection orders, and broader route,
    frequency, body, and orientation tests.

37. **Conclusion quantifies contributions and results.** It names SAM 3 Agent,
    the source model, body coupling, the 14.31 factor, component dominance, both
    validation percentages, 0.32% convergence, and paired material changes.

38. **Every manuscript verb was audited.** The complete lemmatized table and
    decisions are in `verb_audit.md`. The pass replaced several vague or
    technically inaccurate constructions and found no remaining metaphorical
    action verbs.

39. **Therefore and However were checked.** Every retained *Therefore* begins
    its sentence. No sentence-internal *therefore* or *however* remains.

40. **AI-style punctuation and filler were checked.** Manuscript source contains
    no em dash, semicolon, TODO, TBD, or generic promotional filler. PaperMaker's
    style scan has no hits.

## Chapter 6 mirror and preservation

41. **An exact pre-edit Chapter 6 snapshot was frozen first.** The directory
    `/home/user/phd/chapter6/versions_and_feedback/ojcoms_20260827_before/`
    contains the dirty wrapper, application text, references, and the flowchart
    and validation figure assets as they existed before this revision.

42. **Changes were mirrored manually, not by a bulk synchronization script.**
    Chapter 6 now reflects the OJ-COMS title, SAM 3 Agent, DMaMIMO scope,
    simplified adjoint explanation, compact directional equations, percentage
    validation, ten-route results, convergence, material sensitivity, and the
    revised limitations. Thesis-specific transitions and cross-chapter logic
    were preserved.

43. **Recent PhD-agent changes were preserved.** The thesis kept its current
    route q10 values, added Chapter 6 references, existing part-one validation,
    and thesis-specific chapter structure. No checkout or destructive reset was
    used.

44. **The full thesis compiles.** The current electronic thesis has 230 pages,
    no undefined citations or references, and no Chapter 6 overfull horizontal
    boxes. Existing overfull lines remain only in older Chapters 1, 3, and 4.
    Chapter 6 pages and figures were visually inspected.

## Review artifacts and open items

45. **Paper latexdiff produced.** `ojcoms_20260827_latexdiff.tex` and its
    12-page PDF compare the preserved pre-OJ-COMS manuscript with the current
    assembled paper. The table header required one mechanical repair because
    latexdiff 1.3.1a cannot parse `cmidrule` safely.

46. **Chapter 6 latexdiff produced.** The PhD versions directory contains a
    37-page color-marked diff built from the frozen snapshot and current wrapper,
    application text, and references. It compiles without undefined citations.

47. **Question bank retained and extended.** Submission items and the confirmed
    SAM 3 Agent correction remain in `QUESTIONS_BANK.md`.

48. **Claude Opus 4.6 review attempted but blocked.** The local Claude CLI has
    an expired OAuth session and rejects `opus-4-6` as a model identifier. No
    weaker model was substituted. The exact prompt and error are preserved in
    `claude_opus_review.md`, and the required re-authentication is question 24.
