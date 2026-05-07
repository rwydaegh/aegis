# Style Analysis of *Geometric Dosimetry* (monograph\_v2)

A comprehensive catalogue of recurring writing patterns, from individual word choices up to the global document architecture.

---

## 1. Document-Level Architecture

### 1.1 Two-Part Split with a Dedicated "Part Heading"
The monograph is divided into two named Parts, each introduced by a `\partheading` that gives the part a title *and* a subtitle summarising which sections it covers. The subtitle is clearly scoped ("Sections X–Y: a self-contained dosimetry framework for the 10–60 GHz band"). This makes the document feel like two loosely coupled, self-contained units rather than a monolithic text.

### 1.2 Preface in First Person
An unnumbered `\section*{Preface}` precedes section 1. The preface is the *only* place in the document written in the first person singular ("I set out … I did not expect … I believe …"). It functions as a personal intellectual narrative — discovery story first, then rigour. The rest of the document is impersonal.

### 1.3 Abstract Mirrors the Conclusion
The abstract is structured in two paragraphs mirroring the two parts. Paragraph one summarises Part I; paragraph two ("The framework extends in two directions") summarises Part II. The conclusion section at the end likewise mirrors this two-part structure. This creates a tight bookend.

### 1.4 Systematic "Structure of This Work" Subsection
Section 1 contains a dedicated `\subsection{Structure of this work}` that reads through every numbered section and appendix in order, giving a one-sentence synopsis of each. This is exhaustive and serves as a navigational map. It is unusually thorough — even appendices are named.

### 1.5 Relationship to Prior Work as a Closing Subsection of the Introduction
The "Relationship to prior work" subsection comes *last* in the introduction, after the approach summary, accuracy scope, and structure guide. This ordering places the contribution frame after the reader already understands the framework, rather than before.

### 1.6 Appendices Mirror the Main Text
Each appendix expands exactly on a claim or derivation cited in the main text with a `\cref{app:…}`. Appendices are not supplementary in the loose sense; each is tightly coupled to a specific claim. The Fresnel derivation appendix even has sub-subsections with TE and TM treated symmetrically.

---

## 2. Section and Subsection Structure

### 2.1 Every Major Section Follows the Pattern: Motivation → Exact Result → Simplification → Consequence
For example, Section 2 (Local absorption law):
- Setup and notation (motivation and definitions)
- Power flux and absorption (exact result)
- Fresnel coefficients (supporting algebra)
- Exact polarisation-aware law (exact result)
- Decomposition (structural insight)
- TM excess / polarisation ellipse (generalisation)
- Unpolarised and circular limiting cases (simplification)

This drill-down pattern is consistent across all major sections.

### 2.2 Subsections Move from General to Specific to Numerical
Almost every subsection opens with the general claim, derives or states it precisely, and then immediately follows with a concrete numerical example or table. This three-beat rhythm (claim → derivation → numbers) is the dominant local structure.

### 2.3 Short Orientating First Paragraph
A major section always opens with a one- or two-sentence paragraph that contextualises the section before any mathematics. Examples: "The absorbed power density at a point on the body surface follows from first principles. The derivation below is exact; all approximations are introduced in subsequent sections." This paragraph is always purely prose.

### 2.4 Named Definitions, Propositions, Theorems, Lemmas, Corollaries, Remarks
Formal environments appear throughout Part I and Part II. The hierarchy is used consistently:
- **Definition**: introduces a new quantity with a name in \emph{}
- **Proposition**: a statement that is true but not the main theorem  
- **Theorem**: the main structural results (Cauchy formula, generalised Cauchy)  
- **Lemma**: a supporting technical result  
- **Corollary**: immediate consequence  
- **Remark**: an aside, caveat, or motivational explanation

Remarks are the most frequent informal device. They are always separated from the main argument and set in the remark environment, never embedded inline.

### 2.5 Proof Environments Are Concise and End with "Hence"
Proofs appear where a claim is non-trivial but short enough to include in-text (Cauchy's theorem proof, TM excess proof, sphere symmetry proof). They end with a standard "$\blacksquare$" without a separate QED. The Fubini argument in the Cauchy proof is annotated ("valid since the integrand is non-negative"), which is typical: all non-obvious steps carry a parenthetical justification.

---

## 3. Paragraph-Level Patterns

### 3.1 Boxed Equations Mark the "Deliverable"
The key equations that should be remembered are set in `\boxed{}`. Exactly the following are boxed: the exact absorption law, the geometric absorption law, the generalised Cauchy formula, the multi-source neural-network formula, the point-source solid-angle formula, the exact Cauchy with $\bar{T}$, the exact compliance criterion, and the absorption Stokes vector formula. The boxing identifies the "punchline" of each section.

### 3.2 Numbered Equations Only for Referenced Equations
Equations that are not cited later are unnumbered or placed as inline displays. Only equations that will be referenced by `\cref{eq:…}` elsewhere carry a label. This keeps number density low.

### 3.3 Prose Before Equations
An equation is never given without at least one preceding prose sentence that introduces it. The sentence typically states what the equation says in words (e.g., "The inward power flux through a surface element $dA$ at $\rr$ is"). This makes each equation self-explanatory in context.

### 3.4 "This follows from …" / "This holds because …" / "This is exact" Closing Sentences
After a key equation, the paragraph often closes with a qualifying sentence that explains the status of the result: whether it is exact or approximate, what assumptions it relies on, and what will be relaxed. This is systematically done, e.g., "This holds for each polarisation separately. We now derive the transmission coefficients." The closing sentence simultaneously validates the result and creates a forward pointer.

### 3.5 Explicit Announcement of Simplifications
Whenever an approximation is introduced, the text explicitly says so: "One further simplification reduces it to a constant; this is the subject of the next section." Simplifications are never silently applied; they are always labelled and their justification stated.

### 3.6 Numbered Enumerated Consequences
When a result has several consequences, they are listed with `\begin{enumerate}[nosep]` and bold-face lead words: "\textbf{Integral geometry.}", "\textbf{Computer graphics.}", "\textbf{Machine learning and differentiable ray tracing.}" This structural habit appears at least four times: in the introduction (the three fields), in the conclusion (the three consequences), in the applications section, and in the computation section (the itemised optimisation problems).

### 3.7 Italic Emphasis for Named Concepts
Technical terms defined for the first time in a definition environment (or inline) are set in `\emph{}`. Examples: \emph{exact absorption law}, \emph{geometric absorption law}, \emph{exposure fraction}, \emph{absorption area}, \emph{polarisation splitting}, \emph{unpolarised baseline}, etc. The convention is used consistently: a term is italicised at its first full definition and then used plain thereafter.

---

## 4. Sentence-Level Patterns

### 4.1 Short Declarative Opening Sentences
Sections and subsections almost always begin with a short (one-clause) declarative sentence that states the core finding: "For a lossless dielectric interface, the TM reflection coefficient vanishes at the Brewster angle." "The geometric absorption law treats the surface as locally flat." "A sphere illuminated by a plane wave provides a convenient scalar measure."

### 4.2 Nested Qualification via Semicolons and Parenthetical Clauses
Complex sentences are common but always structured. Parenthetical information (physical intuition, numerical values, range restrictions) is placed in parentheses or subordinate clauses introduced by "since", "where", or "because". Semicolons separate two closely related complete thoughts. Commas before conjunctions are used consistently.

### 4.3 "For [condition], [result]" Sentence Template
Many sentences follow a conditional pattern: "For biological tissue at mmWave frequencies, two independent simplifications collapse the exact absorption law to a formula that depends on geometry alone." "For a convex body, $O\equiv 1$ and the formula reduces to the geometric absorption law." This structure frontloads the scope of validity before the assertion.

### 4.4 Active Voice for Mathematical Derivations
Mathematical derivations use the active "we show", "we define", "we extend", "we prove" — always first-person plural (not passive). Non-derivational statements about existing literature uses passive or third-person formulations ("Azzam showed that…", "Bamba et al. measured…").

### 4.5 Coordinate Verbal Pairs for Contrast
Contrasting behaviour is expressed with exactly parallel verb pairs: "$T_s$ *decreases* monotonically … while $T_p$ *increases* towards the pseudo-Brewster peak." "The framework underestimates by 10% at mmWave, because it misses shadow-region absorption." This verbal parallelism appears wherever a compensation mechanism is being explained.

### 4.6 Precise Numerical Quantification with Units Inline
Physical numbers always carry units written with a non-breaking thin space (`\,`): "5.6\,\%", "28\,GHz", "0.3 to 0.5\,mm". The unit is never separated from the number. Range syntax is consistent: "10 to 60\,GHz" (spelled out) for emphasis, "10--60\,GHz" (en-dash) in more compact contexts such as table cells.

### 4.7 "This is a [adjective] error" / "This error is [adverb] [adjective]"
Errors and approximations are always characterised qualitatively: "This is a conservative error." "This is non-conservative by a small margin, negligible relative to ICNIRP's 50× safety factor." "The error is bounded and smaller than the uncertainty in the tissue data." The distinction between conservative (under-estimating the risk) and non-conservative (over-estimating it) is maintained rigorously throughout.

### 4.8 Explicit Cross-References with \cref{} for All Internal Links
Every claim that builds on a previously derived result references it explicitly: "(derived in \cref{sec:local-law})", "(\\cref{sec:corrections} discusses…)", "as shown in \\cref{app:q-proof}". No fact is assumed without attribution to its locus of derivation, whether internal or external.

---

## 5. Word Choice Patterns

### 5.1 "Exact" vs. "Approximate" Used Precisely and Repeatedly
The word "exact" is reserved for results that hold without approximation under the stated assumptions. It appears in the names of the key equations ("exact absorption law", "exact identity", "exact bounds"), in validation claims ("This is exact and follows from the same Fubini argument"), and explicitly contrasted with simplified forms ("The word 'exact' distinguishes it from the simplified form that follows"). The antonym "approximate" or "simplified" is equally precisely used.

### 5.2 "Collapse" as a Technical Metaphor
The verb "collapse" is the preferred term for the dimensional reduction that makes physics tractable: "causes the material factor to collapse to a single constant", "collapse the exact absorption law to a formula that depends on geometry alone." This is the central metaphor of the document re-stated at least five times.

### 5.3 "Governs" / "Encodes" / "Imports" for Structural Relationships
Mathematical relationships between quantities are described with strong verbs: "the tissue physics enters only through the scalar $T_0$", "encodes exponential decay into the medium", "imports four decades of GPU-optimised algorithms", "absorbs all the geometric complexity … into a single scalar". These verbs suggest that the mathematical structure is doing epistemic work, not just parameterisation.

### 5.4 "Conservative" Used in the Safety-Factor Sense
"Conservative" consistently means *underestimates exposure* (safe-side), following the regulatory convention. "Non-conservative" means overestimates exposure (potentially unsafe). This jargon is used without definition because the intended audience knows it, but it is applied consistently wherever an error sign is discussed.

### 5.5 "Precomputed" vs. "Run-time"
The text consistently distinguishes between quantities that are computed once from the body mesh ("precomputed" in a table with a dedicated subsection) and quantities that are computed at run time from the scene. This computational abstraction is central to the practical contribution.

### 5.6 "Classical" for Established Mathematical Results
Theorems from other fields are introduced as "classical": "Cauchy's formula is a classical result of integral geometry", "the pseudo-Brewster angle is a classical concept". This positions them as well-established starting points, not as results for which a proof is needed.

### 5.7 Latin Terms Used Sparingly and Correctly
"i.e." (that is) and "e.g." (for example) are used, always followed by a comma and always correctly distinguished. "Via" is used instead of "through" when specifying a mathematical route.

### 5.8 Minimal Hedging
The writing almost never uses "it might", "perhaps", "could possibly", "somewhat". When uncertainty exists, it is quantified numerically ("approximately 20\,\%", "roughly 10\,\%") rather than hedged verbally. Qualitative hedges like "in general" or "typically" appear only when a numerical qualification would be impractical.

---

## 6. Notation and Mathematical Style

### 6.1 Notation Declared Early and Reused Without Redeclaration
Key symbols ($\hat{\bm{k}}$, $\hat{\bm{n}}$, $\mu$, $\xi$, $T_0$, $\bar{T}$, $\Aab$, $\eta$) are defined in the first section that uses them and then used throughout without repetition. The preamble defines a rich set of custom `\newcommand` macros to ensure consistent typesetting. No symbol is reused for two different quantities.

### 6.2 Roman Upright for Named Parameters, Italic for Variables
Subscripts that are names or labels use roman type (`\mathrm{ab}`, `\mathrm{inc}`, `\mathrm{eff}`, `\mathrm{avg}`) while subscripts that are indices use italic. This distinguishes "absorbed" from a variable index. The custom commands enforce this automatically.

### 6.3 Physical Dimensions Always Stated at Definition
When a symbol representing a physical quantity is first defined, its SI unit is stated: "Poynting vector … (units: W/m²)", "angular frequency $\omega = 2\pi f$". After the first definition the unit is not restated but remains implicit.

### 6.4 Complex Quantities Marked with Tilde
Complex numbers (as opposed to real approximations) are consistently marked with a tilde: $\tilde{n}$ for the complex refractive index, $\tilde{\varepsilon}_r$ for complex permittivity, $\tilde{A}_\perp$, $\tilde{B}$ for the polarisation-dependent Stokes vector components. This convention is global.

### 6.5 Subscript Conventions Are Systematic
- Material-origin subscripts: $T_0$ (normal incidence), $T_s$, $T_p$ (TE/TM), $\bar{T}$ (flux-averaged)
- Geometric subscripts: $A_\perp$ (projected), $A_\mathrm{ab}$ (absorption)
- Multi-source index: $i$ for path index, $j$ for triangle index
- The two-letter subscripts for physical quantities all use `\mathrm{}`: `\mathrm{abs}`, `\mathrm{inc}`, `\mathrm{ref}`, `\mathrm{eff}`, `\mathrm{avg}`, `\mathrm{wb}`

---

## 7. Table and Figure Patterns

### 7.1 Tables Are Always Referred to Before They Appear
Every table is cited with a `\Cref{tab:…}` in the text before or immediately after its float. Tables are never presented without a preceding sentence naming what the reader should look for.

### 7.2 Table Captions Are Self-Contained Mini-Summaries
Captions do not just label the content; they state the main takeaway: "The ratio $\Tavg/T_0$ stays within 5.6\% of unity up to 75°.", "The framework is most accurate in the 20 to 60 GHz band.", "All levels are fed by the same ray-tracing output." A reader who reads only the caption should understand the table's purpose.

### 7.3 All Tables Use Booktabs (`\toprule`, `\midrule`, `\bottomrule`)
No vertical rules appear anywhere. The spacing and horizontal rules follow the booktabs style throughout.

### 7.4 Figure Captions Describe Each Panel Explicitly
Multi-panel figures have captions that describe each panel: "(a) panel description; (b) panel description; …". The description includes what axis label means and what the reader should observe. The final sentence always makes the interpretive point: "confirming the geometric absorption law", "quantifying the directional sensitivity of whole-body absorption."

### 7.5 All Figures Are `\includegraphics` of PDF Files
Source figures are explicitly pre-compiled `.pdf` files, included from a `figures/` subfolder. No inline TikZ figures appear (suggesting figures are generated externally).

---

## 8. Citation and Attribution Patterns

### 8.1 Prior Work Cited for the Specific Observation, Not the Whole Field
Citations are precise: "Azzam showed that for dielectric substrates with $|\tilde{n}|>2.5$, the unpolarised reflectance is nearly angle-independent." "Diao and Li observed the Brewster-related angular enhancement of TM heating on skin but framed it as a local compliance problem, not as a compensating mechanism." The distinction made in the second example (what prior work *did not* frame) is characteristic of how prior art is positioned relative to the new contribution.

### 8.2 Important Authors Named in the Text, Not Just in Brackets
When a result is specifically attributable to a named researcher, the name appears in the prose: "Andersen et al. introduced room electromagnetics", "Bamba fitted an empirical absorption efficiency", "Zhukov et al. introduced the concept [of ambient occlusion]." This honours intellectual priority while still citing the paper.

### 8.3 Contribution Defined by What Was *Not* Done Before
Where a novel connection is made, the text explicitly states that neither predecessor made it: "Neither has been applied to dosimetry." "no closed-form surface-based framework existed before this work." "a physical mechanism not previously identified in the dosimetry literature." This is a consistent rhetorical strategy for establishing originality without aggrandisement.

### 8.4 Footnotes Used Sparingly for Numerical Precision Remarks
The one footnote in the document clarifies the rounding convention used in a numerical example. This is the only footnote. All other qualifications are in the main text or in remark environments.

---

## 9. Error Budget and Accuracy Reporting

### 9.1 All Approximations Are Quantified
Wherever an approximation is introduced, its error is stated numerically: "5.6\% local", "1\% integrated", "2 to 6\%". The error is always stated as a percentage and always compared against the dominant uncertainty (tissue data: 20\%).

### 9.2 The "Conservative vs. Non-Conservative" Axis Is Always Stated
For regulatory compliance, the sign of an approximation error matters. The text always states which direction an error goes and whether it is safe (conservative) or unsafe (non-conservative). This is done systematically in the error budget table, in the Mie analysis, and in the compliance criterion discussion.

### 9.3 A Dedicated Error Budget Table
Section 6.3 contains an explicit error budget (`tab:error-budget`) that lists every source of error, its magnitude, and a note on its character. This is a deliberate choice that raises the discourse above qualitative accuracy claims.

### 9.4 Worst-Case Geometry Identified and Used
The sphere is explicitly identified as "the worst-case geometry" for the Fresnel and diffraction errors because it maximises the angular spread and curvature. Using the worst case for validation makes the claims conservative in the strongest sense.

---

## 10. Rhetorical and Argumentative Patterns

### 10.1 The Core Argument Is Stated Three Times (Abstract, Introduction, Conclusion)
The pseudo-Brewster compensation mechanism and the resulting geometric simplification are stated in: the abstract (compressed, quantified), the introduction (expanded, with context), and the conclusion (summarised as three numbered consequences). This triple exposure ensures the main idea cannot be missed.

### 10.2 Surprise/Discovery Narrative in the Preface
The preface uses a discovery narrative structure: "To my surprise…", "I did not expect…", "At every turn, the answer was a known result in another field." This narrative positions the framework as genuinely novel while simultaneously crediting other fields for the mathematical tools. It is the emotional and motivational frame for the entire work.

### 10.3 Cross-Field Analogies Used to Import Credibility
Whenever the framework coincidentally matches a known result from another field (ambient occlusion, ReLU network, view factors, Mueller calculus, Luneburg–Kline expansion, GELU activation), the equivalence is explicitly noted and the other field is cited. This serves a double purpose: validation (the result is already known to work in that field) and accessibility (readers from those fields can enter at that point).

### 10.4 "This is [adjective]: [elaboration]" Assertions
Key structural observations are made as confident, short statements: "This is exact, not approximate." "This is a conservative error." "Both are precomputable from the body mesh." These one-sentence conclusions after longer derivations serve as section landmarks.

### 10.5 Enumerated Limitations Section
The limitations section uses exactly five numbered items, each beginning with a bold-face name in the pattern "\textbf{[Limitation name]} ($d < \lambda/(2\pi)$, i.e., 1.7 mm at 28 GHz)." Physical parameters are given inline. The section is disciplined: it only lists *irreducible* limitations, explicitly excluding "relaxable specialisations treated in §X".

### 10.6 Scope Restrictions Are Stated Before, Not After, the Claim
When a result only holds under restrictions, the restriction is stated before the equation: "For a lossy half-space in which the skin depth δ is much smaller than any body dimension … all transmitted power is absorbed within the surface layer." This prevents the reader from being misled before reading the caveat.

---

## 11. Computational Framing

### 11.1 Big-O Cost Analysis for Every Formula
Computational complexity is given as O() for every level of the hierarchy: O(MN) for the full spatial computation, O(N) for the aggregate level, O(1) for the bound. This is explicit and systematic.

### 11.2 Precomputed vs. Run-Time Dichotomy
The paper consistently distinguishes quantities that depend only on the body mesh (precomputed once) from quantities that depend on the electromagnetic scene (computed at run time). A dedicated subsection and table (\cref{tab:precomputed}) enumerate all precomputed quantities with their symbols, sizes, and descriptions.

### 11.3 Physics-to-Neural-Network Analogies Named Explicitly
The text explicitly names when a physical formula is a neural-network architecture (ReLU → single-hidden-layer network, GELU → diffraction-corrected activation, curvature correction → ReLU²). A dedicated table (\cref{tab:activations}) maps asymptotic optics regimes to activation functions. This framing is novel and repeated in the abstract, introduction, computation section, corrections section, and conclusion.

---

## 12. Summary of the Most Distinctive Stylistic Signatures

| Level | Signature |
|---|---|
| Document | Two-part structure; personal preface; mirrored abstract/conclusion |
| Section | Orientation sentence → exact result → simplification → numbers |
| Environment | Definitions/Theorems/Remarks are named environments; proofs use Fubini annotation |
| Paragraph | Prose before equations; qualifying closing sentence; boxed "punchlines" |
| Sentence | Declarative openings; "For X, Y" conditionals; parallel verbal pairs for contrast |
| Word | "exact", "collapse", "conservative/non-conservative", "precomputed"; minimal hedging |
| Mathematics | Tilde for complex; `\mathrm` subscripts; units at definition; `\cref` everywhere |
| Tables | Self-contained captions; booktabs; cited before they appear |
| Error reporting | All errors quantified; conservative/non-conservative direction always noted |
| Citations | Named in prose; contribution framed by what was *not* done before |
| Rhetoric | Triple repetition of core claim; discovery narrative; cross-field analogies |
