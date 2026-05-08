# Style Guide for Academic Paper Writing (with AI)

This guide has three parts. Part A lists AI writing habits to avoid. Part B collects sentence-level craft rules from Strunk's *Elements of Style* and Cargill & O'Connor's *Writing Scientific Research Articles*. Part C states the overriding voice and tone preferences for this project.

Read the whole thing before writing. Refer back often.

---

## PART A: AI Writing Pitfalls to Eliminate

Even modern, capable LLMs produce recognizable patterns. Below is a complete catalog. Every item here is **banned** from our writing unless a specific exception is noted.

### A1. Em Dash and Dash Overuse

LLMs scatter em dashes (—) everywhere. They use them where commas, parentheses, colons, or semicolons belong. They use them to create punchy parallelisms that mimic sales copy.

**Rule:** Never use em dashes (—) in standard prose. Never. Use commas for light interruptions. Use parentheses for true asides. Use colons to introduce explanations. Use semicolons to connect independent clauses.

**Exception:** En dashes (–) or double hyphens (--) are acceptable for ranges and technical notation: "1–2 mm," "the 2020–2023 period," "a 300--500 nm bandwidth." Hyphens (-) in compound words remain standard: "near-infrared," "wide-angle," "substrate-dependent."

### A2. Excessive Boldface

LLMs bold key terms, names, and phrases in a "key takeaways" style inherited from slide decks and listicles. This is not how academic prose works.

**Rule:** Never bold words for emphasis in running text. Bold is for headings and defined terms at first use only. For emphasis, restructure the sentence so the important word lands at the end (see B12).

### A3. Bullet-Point and List Addiction

LLMs love vertical lists with inline bold headers followed by colons. Academic papers are built from paragraphs, not lists.

**Rule:** Use prose. Convert lists into sentences or short paragraphs. Reserve numbered or bulleted lists for truly enumerative content (e.g., experimental steps) where the journal style permits them.

### A4. Rule of Three

LLMs reflexively produce "adjective, adjective, and adjective" or "short phrase, short phrase, and short phrase" triplets. This creates a shallow, cadenced feel.

**Rule:** Use the number of modifiers the content demands. One is fine. Two is fine. Four is fine. Do not default to three.

### A5. Puffery and Loaded Language

LLMs inflate importance. Watch for:
- "rich/vibrant/diverse tapestry"
- "cultural/literary/media landscape"
- "continues to captivate"
- "groundbreaking," "intricate," "stunning"
- "enduring/lasting legacy"
- "nestled," "in the heart of"
- "boasts a"

**Rule:** State facts. Let the reader judge importance. If something is significant, show why with evidence, not adjectives.

### A6. Superficial Significance Phrases

LLMs attach present-participle ("-ing") clauses that editorialize:
- "...ensuring broader adoption"
- "...highlighting its importance"
- "...underscoring the significance"
- "...reflecting broader trends"
- "...showcasing the potential"
- "...contributing to the field"
- "...aligning with recent developments"

These are empty. A fact or event does not "highlight" or "underscore" anything by itself.

**Rule:** Delete every trailing "-ing" clause that tells the reader what to think. If the point matters, give it its own sentence with evidence.

### A7. Importance and Symbolism Inflation

LLMs insert claims that things "stand as a testament," "play a vital/crucial/significant role," "represent a key turning point," or leave "an indelible mark."

**Rule:** Ban these phrases outright. Say what happened. Say what it caused. Stop there.

### A8. Didactic Disclaimers

LLMs say "It is important to note," "It is crucial to remember," "It should be noted that."

**Rule:** If something is important, just say it. The reader can judge importance. Delete the frame.

### A9. Formulaic Hedging with "Not only ... but also"

LLMs overuse negative parallelisms: "not only X but Y," "it is not just about X, it is about Y."

**Rule:** Prefer direct positive statements. State what something is, not what it is not-but-also-is.

### A10. Elegant Variation (Synonym Cycling)

LLMs avoid repeating the same word by cycling through synonyms: a person becomes "the researcher," then "the scholar," then "the investigator," then "the key figure." This confuses more than it clarifies.

**Rule:** Repeat the same term for the same thing. Consistency is clarity. In technical writing, one term per concept.

### A11. False Ranges

LLMs write "from X to Y" where X and Y do not form a meaningful scale: "from computational modeling to experimental validation" is not a range.

**Rule:** Use "from X to Y" only for real scales (numerical, temporal, categorical with a clear ordering). Otherwise, just list the items.

### A12. Section Summaries and Conclusions Within Sections

LLMs end paragraphs and sections by restating the main idea: "In summary," "Overall," "In conclusion." This is redundant in a paper where the reader can re-read.

**Rule:** End sections with the last substantive point. Do not summarize what you just said. The abstract and conclusion serve that purpose for the paper as a whole.

### A13. "Despite ... Challenges" Formula

LLMs write "Despite its [positive words], [subject] faces challenges including..." then end with vague optimism. This is a rigid template, not analysis.

**Rule:** If limitations exist, state them plainly. Do not frame them as a dramatic contrast with preceding praise.

### A14. Vague Attribution of Opinion

LLMs write "observers have noted," "some critics argue," "industry reports suggest" without naming specific sources.

**Rule:** Attribute to named sources with citations. If you cannot name a source, reconsider whether the claim belongs.

### A15. Curly Quotes and Typographic Artifacts

LLMs sometimes produce curly quotes (" ") or mix curly and straight quotes inconsistently.

**Rule:** Use straight quotes consistently, or follow the journal's typographic conventions. Be consistent throughout.

### A16. Title Case in Headings

LLMs capitalize all main words in headings: "Early Life and Education."

**Rule:** Follow the journal's heading convention. For this project, use sentence case unless the style guide requires otherwise.

### A17. Emoji, Decorative Symbols, and Markdown Artifacts

No emoji. No decorative bullets (•, ★). No hash-symbol headings in final text. No Markdown artifacts.

**Rule:** Plain text with the formatting conventions of the target document class.

### A18. Filler Adverbs and Intensifiers

LLMs overuse: "very," "highly," "extremely," "particularly," "especially," "significantly" (outside statistical use), "notably," "remarkably," "incredibly."

**Rule:** Delete them. Use words strong in themselves (Strunk, Rule 12). "Very important" becomes "essential" or just state why it matters. "Significantly" is reserved for statistical significance.

### A19. Throat-Clearing Openings — REMOVED

(Previously banned phrases like "It is worth noting that..." This rule generated too many false positives in practice and is no longer enforced. Use judgment.)

### A20. Overuse of "Furthermore," "Moreover," "Additionally"

LLMs chain these transition words mechanically. They become invisible filler.

**Rule:** If two sentences follow logically, you often need no connective at all. When you do need one, vary your approach: sometimes the connection is best shown by placing old information at the start of the new sentence (see B10).

---

## PART B: Sentence Craft Rules

These rules come from Strunk's *Elements of Style* and Cargill & O'Connor's *Writing Scientific Research Articles*. They are the core toolkit for writing clear, forceful academic prose.

### Sentence Structure

#### B1. Use the Active Voice (Strunk 11)

Active voice is more direct and more concise.

- Weak: "The samples were analyzed by the authors."
- Strong: "We analyzed the samples."

Use passive voice only when (a) the agent is unknown or unimportant, (b) you need the object as the topic for information flow, or (c) convention in your field demands it (e.g., parts of Methods).

#### B2. Get Subject and Verb Within the First 7-9 Words (Cargill, Strategy 5)

Long subjects before the verb create "top-heavy" sentences. Readers lose the thread.

- Weak: "The quality and quantity of flour protein, dough mixing requirements and tolerance, dough handling properties and loaf volume potential are quality parameters."
- Strong: "Quality parameters of wheat seed include the quality and quantity of flour protein, dough mixing requirements..."

Put the subject-verb core up front. Move long lists to the end.

#### B3. Keep Sentences Short

Start by writing sentences with two clauses at most. Join them later only if the connection is tight and the result reads easily. Aim for an average sentence length of 15-25 words. Vary length for rhythm, but never let a sentence run past 40 words without a very good reason.

#### B4. One Paragraph, One Topic (Strunk 9)

Every paragraph earns its existence by treating one topic. Start it with a topic sentence. End it in line with the beginning. Do not drift into a new subject.

#### B5. Begin Each Paragraph with a Topic Sentence (Strunk 10)

The topic sentence tells the reader what the paragraph will do. It also links the paragraph to the previous one. This is your single most powerful tool for reader orientation.

#### B6. Omit Needless Words (Strunk 13)

Every word must earn its place. Common offenders:

| Wordy | Concise |
|-------|---------|
| the question as to whether | whether |
| owing to the fact that | because |
| in spite of the fact that | although |
| it is a subject that | this subject |
| he is a man who | he |
| in a hasty manner | hastily |
| the fact that he failed | his failure |

#### B7. Put Statements in Positive Form (Strunk 12)

Say what is, not what is not.

- Weak: "He was not very often on time."
- Strong: "He usually came late."

Use "not" for denial or antithesis, never for evasion.

#### B8. Express Coordinate Ideas in Parallel Form (Strunk 15)

Similar ideas deserve similar grammar. This helps the reader see the similarity.

- Weak: "Formerly, science was taught by the textbook method, while now the laboratory method is employed."
- Strong: "Formerly, science was taught by the textbook method; now it is taught by the laboratory method."

#### B9. Keep Related Words Together (Strunk 16)

The subject and verb should not be split by a long clause. Modifiers go next to what they modify. Relative pronouns follow their antecedents immediately.

- Weak: "Wordsworth, in the fifth book of The Excursion, gives a minute description."
- Strong: "In the fifth book of The Excursion, Wordsworth gives a minute description."

#### B10. Put Old Information Before New (Cargill, Strategy 3)

When the reader starts a new sentence, the first thing they should see is something they already know. New information comes at the end.

- Weak: "The interactions of these clay surfaces with water control the ability of soils to shrink." (if "clay surfaces" is old info but appears late)
- Strong: Start sentence 2 with the known concept from sentence 1, then add the new.

This is the single most important rule for paragraph flow. It sometimes requires switching from active to passive voice, and that is fine.

#### B11. Link Sentences Within the First 7-9 Words (Cargill, Strategy 4)

The reader should find a connection to the previous sentence within the first seven to nine words. If they have to read fifteen words before recognizing a link, the paragraph feels disjointed.

#### B12. Place Emphatic Words at the End (Strunk 18)

The end of a sentence is its position of power. Put your most important word or idea there.

- Weak: "Humanity has hardly advanced in fortitude since that time, though it has advanced in many other ways."
- Strong: "Humanity, since that time, has advanced in many other ways, but it has hardly advanced in fortitude."

This rule applies at every level: words in a sentence, sentences in a paragraph, paragraphs in a section.

#### B13. Move from General to Specific (Cargill, Strategy 2)

Within a paragraph, state the general principle or context first, then give details and examples. Readers expect this order.

#### B14. Avoid Loose Sentence Chains (Strunk 14)

A series of sentences all built as "X, and Y" or "X, which Y" becomes monotonous. Vary your sentence types: simple sentences, semicolons, periodic sentences, three-clause sentences.

#### B15. A Participial Phrase Must Refer to the Grammatical Subject (Strunk 7)

- Wrong: "Walking slowly down the road, a woman was seen."
- Right: "Walking slowly down the road, he saw a woman."

Dangling modifiers are errors, not style choices.

### Word Choice

#### B16. Prefer Simple, Common Words

- "use" over "utilize" or "employ"
- "show" over "demonstrate" or "elucidate"
- "because" over "due to the fact that"
- "about" over "approximately" (when precision is not the point)
- "many" over "a plethora of"
- "help" over "facilitate"
- "change" over "modification" (when the verb form works)
- "begin" over "commence" or "initiate"
- "end" over "terminate" or "finalize"
- "enough" over "sufficient" (context-dependent)
- "need" over "necessitate"
- "try" over "endeavor" or "attempt"

Do not oversimplify. Technical terms are fine when they carry precise meaning that simpler words cannot. "Refractive index" is exact; do not replace it with "how much light bends." But "utilize" is never more precise than "use."

#### B17. Use "Very" Sparingly (Strunk)

Where emphasis is needed, choose words strong in themselves. "Very important" is weaker than "essential." "Very large" is weaker than "vast" or a specific number.

#### B18. Avoid Hackneyed Words

"Factor," "feature," "nature," "character," "system," "aspect" are often filler. Replace them with something concrete.

- Weak: "Heavy artillery is becoming an increasingly important factor in deciding battles."
- Strong: "Heavy artillery is playing a larger part in deciding battles."

#### B19. Less vs. Fewer

"Less" for quantity, "fewer" for number. "Fewer samples," not "less samples."

#### B20. "Which" vs. "That"

- Defining (restrictive) clauses: "that" (no commas). "The samples that were heated..."
- Non-defining (non-restrictive) clauses: "which" (commas). "The samples, which were heated in a furnace, ..."

Test: if you can insert "by the way" after "which" and the sentence still makes sense, use "which" with commas.

#### B21. "However" Placement

"However" meaning "nevertheless" should not start a sentence. Place it after the first phrase or clause.

- Weak: "However, we at last succeeded."
- Strong: "At last, however, we succeeded."

When "however" means "in whatever way," it can start a sentence: "However you advise him, he will do as he thinks best."

### Claim Strength in Scientific Writing

#### B22. Match Verb Strength to Evidence Strength (Cargill, Ch. 9)

The verbs you choose in the Discussion carry your claim strength:

| Strength | Main verb | That-clause verb |
|----------|-----------|-----------------|
| Strong | demonstrate, show, confirm | present tense: "is," "controls" |
| Moderate | indicate, reveal | present tense or future: "will be" |
| Weak | suggest, appear | modal: "may," "could," "might" |

Match the strength of your verb to the strength of your data. Overclaiming invites rejection. Underclaiming buries your contribution. Both are errors.

### Verb Tense Conventions

#### B23. Tense in Scientific Papers

- **Present tense:** established knowledge, general truths, what figures show. "Figure 3 shows..."
- **Past tense:** what you did and found in this study. "We measured..." "The reflectance decreased..."
- **Present perfect:** extended past to present; for literature context. "Several studies have examined..."

---

## PART C: Voice and Tone Preferences for This Project

These override everything above when in conflict.

### C1. Clarity Above All

If a sentence can be misread, rewrite it. There is no prize for elegance that sacrifices understanding.

### C2. Short Sentences as Default

Write short. A sentence should do one thing. If it does two things, consider splitting it. Long sentences are allowed when the parts are tightly linked and the structure is parallel. But the default is short.

### C3. Simple Words Almost Always

Prefer the Anglo-Saxon word over the Latinate one. "Get" over "obtain." "Show" over "demonstrate." "Change" over "modification." Except when the technical term is more precise or the simple word is genuinely too informal for a journal.

### C4. Subject-Verb-Rest

Build sentences in this order: subject, then verb, then the rest. Avoid long introductory clauses before the subject appears. Avoid burying the verb at the end.

- Weak: "The compensation of pseudo-Brewster effects in the near-infrared regime by means of multilayer dielectric coatings was investigated."
- Strong: "We investigated how multilayer dielectric coatings compensate pseudo-Brewster effects in the near-infrared."

### C5. Active Voice by Default

Write "we measured," not "measurements were performed." Switch to passive only for information flow or when the agent truly does not matter.

### C6. No Throat-Clearing

Never start a paragraph with meta-commentary about what you are about to say. Start with the content.

- Weak: "In this section, we discuss the theoretical framework underlying our approach."
- Strong: "The compensation mechanism relies on destructive interference between successive reflections."

### C7. No Filler Transitions

Do not chain paragraphs with "Furthermore," "Moreover," "Additionally," "It is also worth noting." If the logic is clear, the connection speaks for itself. If it is not clear, restructure.

### C8. Concrete Over Abstract

Prefer specific, measurable claims over vague ones.

- Weak: "The coating significantly improved performance."
- Strong: "The coating reduced reflectance from 12% to 0.3% at 1064 nm."

### C9. No Decoration

Do not use em dashes (—) in prose, ever. Do not bold for emphasis. Do not use exclamation marks. Do not use rhetorical questions in the body text. Do not use scare quotes around common terms. Let the content carry the weight.

### C10. One Term, One Meaning

Pick a term for each concept and stick with it. Do not alternate between "coating," "film," "layer," and "stack" if they mean the same thing, unless you have defined them as distinct. Consistency is more important than variety.

### C11. No "The" at the Start of Headings

Section titles, subsection titles, and paragraph headings should not begin with "The." Headings are labels, not sentences.

- Weak: "The Compensation Mechanism"
- Strong: "Compensation Mechanism"
- Weak: "The Role of Layer Thickness"
- Strong: "Role of Layer Thickness" or better: "Layer Thickness Effects"

**Exception:** When "The" is part of a proper name or established term that requires it for clarity.

---

## Quick Checklist Before Submitting Any Drafted Text

1. Read every sentence aloud. If you stumble, rewrite it.
2. Check: does every paragraph start with a topic sentence?
3. Check: is the subject-verb core in the first 7-9 words of each sentence?
4. Check: does old information precede new information in each sentence pair?
5. Search for em dashes (—). Delete every single one and replace with comma, parentheses, colon, or semicolon.
6. Search for "very," "significantly" (non-statistical), "importantly," "notably." Delete or replace.
7. Search for "-ing" clauses at the ends of sentences. Delete any that editorialize.
8. Search for "It is," "There is," "There are" at sentence starts. Rewrite with a real subject.
9. Search for "not only ... but also," "It is important to note," "It is worth mentioning." Rewrite.
10. Check that every claim in the Discussion has a verb whose strength matches the evidence.
11. Verify that no paragraph ends with a summary of itself.
12. Verify that no section ends with "In conclusion" or "Overall."
13. Check all section, subsection, and paragraph headings: none should start with "The."