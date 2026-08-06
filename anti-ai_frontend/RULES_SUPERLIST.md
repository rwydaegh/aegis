# Anti-AI frontend rule list

A reference file for building web UI that does not read as machine-generated. Drop it into a
project (an agent's context, a `CLAUDE.md`, a `.cursorrules`, a design brief) and the work that
comes out should stop looking and sounding like every other one-shotted SaaS site.

It is the frontend sibling of the PaperMaker9000 rule list, which does the same job for IEEE
papers. A handful of rules are lifted from there almost verbatim, because a tell is a tell in any
medium: an em dash, a puffed-up adjective, a decorative gradient, and a "seamlessly" all betray
the same averaged-out origin. Most of the material here is new and specific to the web.

## How to use this file

The document has three layers, in descending order of authority:

1. **The empirical spine** (Parts 1-2): which tells real people actually flag, ranked, from two
   independent quantitative studies. This is data, not taste.
2. **The spec** (Parts 3-5): the concrete "do this instead" rules, with exact values (hex codes,
   font names, durations, ratios). This is where a project should pin its decisions.
3. **The enforcement layer** (Parts 6-7): the craft references and the deterministic gates that
   make the rules stick.

Treat the percentages as an ordering, not gospel. The keyword-matched studies catch sarcasm and
the wrong sense of words, so trust the *rank* more than the decimal. The point is relative
loudness: "it all looks the same" dwarfs every specific feature by more than five to one.

### The prime directive

Every tell below is a **default the tool reaches for when you do not specify otherwise.** The
stack is Next.js + Tailwind + shadcn/ui, and left alone it emits the statistical center of its
training data: the same starter layout, the same palette, every time. The averaging is the
disease. Every rule is a symptom.

Three findings should shape how you act on this, more than any single rule:

- **Feed the model a real reference.** The most-repeated fix across the corpus is to hand the
  model an actual site you admire and have it adapt, instead of letting it guess from the average.
  A concrete reference beats any quantity of negative constraints.
- **Deterministic gates beat prose.** A measured study found that written guidance *alone* made AI
  output worse (slop-rule failures rose), while a mechanical pass/fail build gate drove them near
  zero. Where a rule can be a banned value that fails the build (Part 7), make it one. Prose is the
  fallback, not the mechanism.
- **Escaping a default into another default is still a tell.** Ban indigo and the model reaches for
  emerald green ("the safe-green regression") or a cream/beige "tasteful startup" wash. Swap Inter
  and it picks Geist. Swap "Supercharge" and it writes "Unlock." The fix is brand-derived
  specificity, not the next-most-common option.

---

## Part 1 - Why AI frontends converge (the mechanism)

State this once so the rest makes sense. LLMs and AI builders do not design, they average. They
predict the most probable next token from a corpus saturated with Tailwind + shadcn starter code
scraped 2019-2024, so unconstrained they emit the statistical center of that corpus. The result
lacks a point of view because it is the mean of millions of examples with no unifying intent. It
is self-reinforcing. AI sites ship, get re-scraped, become the next training set, and the
homogeneity compounds.

The load-bearing anecdote, worth citing because it names the exact mechanism: in August 2025,
**Adam Wathan, the creator of Tailwind, publicly apologized** for it. *"I'd like to formally
apologize for making every button in Tailwind UI `bg-indigo-500` five years ago, leading to every
AI generated UI on earth also being indigo."* The default became the documentation became the
training data became the web.

### Two empirical anchors

Cite these for credibility. They are independent and they agree.

- **The Reddit corpus (JCarterJohnson, "vibecoded-design-tells").** 3,214,533 posts across 47
  AI/SaaS subreddits, 2020-2026, narrowed to 46,971 on-topic posts and ranked from 3,033 comments
  in 125 canonical threads. The conversation barely existed before 2024, then jumped from ~2
  mentions per 10,000 posts to 278 (2024) and 336 (2025). The single loudest theme is *not* any
  feature: "they all look the same" and "screams AI / slop" each appear in roughly 13% of on-topic
  posts.
- **The DOM audit (Adrian Krebs).** A headless-Playwright scan of 1,590 Show HN sites checking
  computed styles, no LLM image analysis: **22% "heavy slop" (4+ tells), 32% mild, 46% clean.**
  Submission volume "exploded within a few months of the launch of Claude Code." Per-pattern
  frequencies (a useful sanity check on the prompts): permanent dark mode 20-34%, gradients
  27-28%, uncustomized shadcn 23.5%, centered titles 23.5%, icon-card grids 20-22%, glass panels
  17%, specific font combos 15.8%, colored card stripe 13%, purple CTA buttons 10.7%, badge-above-
  H1 4.7%.

---

## Part 2 - The ranked tells (what real people flag)

Ordered by share of on-topic comments naming the tell (the cleanest signal in the corpus). The two
umbrella complaints sit far above every specific feature. Fixing specifics without fixing the
umbrella is rearranging deck chairs.

### The two umbrella complaints (fix these or nothing else matters)

**U1. "It screams AI / soulless / slop" - 6.4% of comments, the loudest single theme.**
A gestalt verdict, not a feature. A site earns it by stacking three or four specific tells until
the whole reads as machine-averaged. You cannot fix it by removing one gradient. You fix it by
giving the thing a point of view (Part 6).

**U2. "They all look the same / cookie-cutter / template" - 6.1% of comments, 91% negative.**
The highest negative-sentiment tell on the entire list. Sameness is the actual grievance. The
honest counterpoint from the threads: sites converged on shared kits long before AI (Bootstrap,
Shopify, Dreamweaver). AI did not invent convergence, it made it instant and universal. The
defense is differentiation, not novelty for its own sake.

### The two "em-dash-equivalent" lead tells

Two visual signatures are, in the sources' own words, "almost as reliable a sign of AI-generated
design as em-dashes are for text." Lead any audit with these:

1. **The AI-purple gradient.** The indigo-violet band, usually as a `from-violet-500 to-blue-600`
   diagonal, and as gradient *text*. (Detail in T2 and T3.)
2. **The colored card border stripe.** A 3-4px purple or blue accent border on the left or top edge
   of a card. Measured at 13% of sites by Krebs. Almost nothing else screams "generated" as
   cheaply.

### The specific visual tells, ranked

**T1. The default shadcn / Tailwind kit - 2.5% of comments (top concrete cause), 41% negative.**
*"Every Claude/Cursor project defaults to the same shadcn components with identical slate-gray
cards, that specific blue accent, and the same padding rhythm. You can spot it from a screenshot."*
The tell is not shadcn (it is a good kit), it is shadcn *unmodified*. The code fingerprint is the
`lib/utils.ts` `cn()` helper plus a `components/ui/` folder of untouched defaults (see Part 5).
Re-theme before you ship: radius, accent, spacing, shadows, card treatment.

**T2. The "AI purple" - 2.3% of comments, 68% negative (the most-named color tell).**
Traced to Tailwind's default `indigo`/`violet`. The exact offenders: **indigo-500 `#6366f1`,
violet-500 `#8b5cf6`, purple-500 `#a855f7`.** Developers call it "VibeCode Purple." On dark
themes it travels with **cyan `#06b6d4`** and **magenta `#ec4899`** accents. *"This purple is used
way too much everywhere."* Move the brand hue off this band entirely and derive it from something
real.

**T3. Gradients, especially purple-to-blue, and gradient text - 2.0% of comments, 59% negative.**
The highest-scored design comment in the whole corpus (373 upvotes) leads with it: *"the
purple-to-blue gradient is the biggest tell. Also bento grid layouts, rounded corners on
everything, hero section with gradient text that says 'transform your X', and way too much
whitespace."* Purple and gradients co-occur in comments more than any other pair, which is why
people say "purple-to-blue gradient" as one phrase. Kill gradient fills on text first. Gradient
text reduces scannability on top of looking generated.

**T4. Too many hover and scroll animations / Framer fade-ins - 1.1% of comments, 40% negative.**
*"It's always the unnecessary hover animations and gradients that give it away."* The default
`whileInView` fade-in on every section is the giveaway (it even fires on the first pixel, animating
text before it is readable on mobile), as is the identical `scale: 1.02` hover on every card. Treat
it as a soft signal in the data but a real one. Note the dev-side cost flagged in the threads:
stacked shadows, glows, and hover transforms cause real paint-time jank, including multi-second
delays on Chrome mobile from a single bad shadow.

**T5. Rounded corners on everything - 0.8% of comments.**
*"AI LOVES border radius... rounded cards on rounded cards on rounded buttons."* The complaint is
uniform `rounded-lg` (8px) everywhere plus pill buttons, with 24px+ "soft blob" cards at the
extreme. Honest caveat from a senior dev in the thread: border radius is just modern styling, every
framework ships it. The operative rule: vary your radii or commit to a sharper language, and do not
let every element default to the same soft round.

**T6. Dark mode with neon glow, often unprompted - 0.7% of comments, 41% negative.**
Krebs' single most common tell (up to 34%). The full pattern: near-black canvas (`#000000`,
`#030712`, `#0b0f19`), slightly lighter container grays (`#1f2937`, `#111827`), white headings,
muted gray body (`#9ca3af`, `#6b7280`) that routinely fails WCAG AA, a violet or cyan accent, and
glowing colored box-shadows. *"AI loves this glowing shit, for no reason."* If dark mode is not a
deliberate brand choice, do not let it be the default identity, and never bolt neon glow onto it.

**T7. Emoji as icons and section bullets - 0.5% of comments (2.7% of posts), 33% negative.**
*"Emojis as icons. If I see them, I instantly doubt the creator's ability to even vibe-code
properly."* The post-vs-comment gap means it looks worse in casual posts than in careful threads,
so weight accordingly. Still a strong amateur signal. Use a coherent icon family (and prefer
Phosphor or Radix over the unprompted lucide-react default), reserve emoji for genuinely informal
surfaces.

**T8. Generic sans fonts, Inter and Geist - 0.4% of comments.**
Anthropic's own frontend-design skill bans this directly: avoid *"overused font families (Inter,
Roboto, Arial, system fonts)"* and *"purple gradients on white background."* The trap is that
escaping Inter into Geist is itself a tell now. The overused set: **Inter, Geist, Space Grotesk,
Instrument Serif.** A related micro-tell: the single serif-italic accent word dropped into an
otherwise-Inter hero for "emphasis." Pick a display face with a point of view.

**T9. The symmetric hero + three feature cards + CTA layout - 0.4% of comments (1.6% of posts),
41% negative.** *"shadcn defaults give you symmetric centered hero + 3 feature cards + CTA, which
is the dead giveaway. Break the grid: asymmetric hero, one oversized screenshot."* The canonical AI
page skeleton. The related "same hero: huge headline + tiny subtext + two CTA buttons" lands
separately at 0.2%. Break the symmetry.

### The micro-tells that travel in packs

Individually minor, collectively the thing that earns U1. When you see one, look for the rest:

- **The "Introducing v2.0" badge.** A narrow pill above the H1 with a soft border glow announcing a
  release. (Krebs: badge-above-H1 at 4.7%.)
- **The eyebrow chrome.** An uppercase label with a dot prefix and a thin trailing line above a
  section heading.
- **Numbered 01 / 02 / 03 steps** in a "how it works" row.
- **The stat banner with fake metrics.** A three-up row of big numbers: "99.9% Uptime," "10M+
  Users," "500% ROI," "Trusted by teams at" with faded monochrome logos, even for a pre-launch
  product.
- **The icon-tile-above-heading feature card.** A `rounded-lg` square holding a vector icon, then a
  bold three-word title, then exactly two lines of generic text. The universal AI feature card.
- **Nested cards** (cards inside cards), **non-functional colored status dots**, lines over 80
  characters, and the **`blur(100px)` ambient glow blob** absolutely-positioned behind the hero.
- **Shimmer / rotating-gradient borders** on the primary button, and a faint **background grid
  overlay** applied to look "engineered" regardless of domain.

### Two corrections the data forces (do not over-index on memes)

- **Bento grids came in last (0.1%)** despite being the running joke, and they are contested even
  among complainers (*"leave Bento grids alone, I love Bento grids"*). A bento grid is not a tell.
  A bento grid used as decoration with no content hierarchy is.
- **Mesh / aurora / blob backgrounds did not hold up (0.3%)** once false keyword matches were
  removed, and one was rejected outright as a keyword artifact. Glassmorphism (17% by DOM count but only
  0.2% of named complaints) and "centered everything" (0.2%) are likewise weaker than the memes
  suggest.

The lesson: the loud bloggers' clichés (bento, glass, aurora) are *weaker* signals than the boring
fundamentals (the default kit, the purple, the gradient, the card stripe, dark-mode-by-default).
Spend your effort on the fundamentals.

---

## Part 3 - Visual rules (the spec to enforce)

The "do this instead" layer, with values concrete enough to pin in a config. Many map onto the
figure-craft rules from the PaperMaker list, where the same instincts (minimalism, no chartjunk,
every element earns its place, one consistent design language) already had to be enforced against
the same averaging pressure.

### Color

- **Ban the AI-violet band as a primary.** `#6366f1`, `#8b5cf6`, `#a855f7` and their `bg-indigo-*`
  / `bg-violet-*` classes. The cleanest enforcement is to delete the default Tailwind palette so
  those classes fail the build (Part 7).
- **Avoid the regression defaults too.** Emerald green and the cream/beige warm wash are where the
  model goes when purple is blocked. Derive the accent from something real (a product photo, a
  logo, a physical material), do not pick the next safe hue.
- **Tint your neutrals, do not use pure gray or pure black.** Pure `#000` and untinted slate are
  themselves defaults. Hue your neutrals a few points toward the brand. In OKLCH: backgrounds
  around `oklch(98% 0.005 hue)`, borders `oklch(90% 0.012 hue)`, body ink `oklch(10% 0.01 hue)`,
  using a chroma of 0.005-0.015. Work in OKLCH or HSL, not hex, so lightness is perceptually even.
- **One accent, used selectively.** A single saturated brand color signalling *action* reads as
  more confident than a multi-hue gradient. Keep accent saturation under ~80%. Define semantic
  tokens (`--color-action-primary`) that name function, not decoration.
- **No grey text on colored backgrounds.** Use a lighter or transparent version of the *background*
  hue instead. Washed-out gray-on-color is a tell and usually fails contrast.
- **Hit contrast.** Body text must clear WCAG AA 4.5:1, secondary 3:1. The muted-gray-on-dark
  default fails this constantly, so do not inherit it.
- **Prefer solid tokens over stacked transparency.** Layered RGBA/HSLA produces unpredictable
  combinations and paint cost. Define explicit solid tokens per layer.

### Typography

- **Do not ship the overused set as your identity:** Inter, Geist, Space Grotesk, Instrument Serif,
  plus Roboto, Arial, raw system stacks. They are not bad faces, they are *the* faces, so they read
  as default.
- **Pair across a contrast axis.** An expressive display face against a clearly different body face:
  for example Fraunces / Playfair / Bricolage Grotesque / Cabinet Grotesk for display, against IBM
  Plex / Söhne / Untitled Sans / a humanist or mono for body. Never pair two similar sans.
- **Set a real scale.** A modular ratio around 1.25 (Major Third) is the versatile default. Keep at
  least a 1.25 step between levels so hierarchy is felt, and avoid a flat scale where sizes sit too
  close.
- **Constrain display type.** Cap headline size with `clamp()` so it tops out near 6rem (~96px) on
  large screens, set a letter-spacing floor around `-0.04em`, and use `text-wrap: balance` to kill
  awkward breaks.
- **Constrain body type.** Body text at least 16px, line length 65-75ch (`max-w-[70ch]`), and
  `text-wrap: pretty` to remove orphans. No all-caps body, no monospace body unless it is the
  brand.

### Shape, depth, and surface

- **Cap and vary radius.** Ban `rounded-2xl`/`rounded-3xl` on cards, keep a small scale (2/4/6px)
  and differentiate (sharp containers with softer controls, or commit to crisp throughout). Uniform
  `rounded-lg` on everything is the tell. No reflexive pill buttons.
- **Shadows: layered, color-matched, and subtle, or absent.** Never pure-black shadows. Match the
  shadow to the background hue at lower lightness. Use a layered shadow (3 layers for medium
  elevation, up to 5 for high) with one consistent light source, vertical offset roughly twice the
  horizontal, blur roughly twice the distance. As an element rises, grow the offset and blur and
  drop the opacity. Often the right answer on a card is no shadow at all: a 1px hued border plus
  background contrast does the work. (PaperMaker figure rule, ported: drop shadows, gradients, and
  chartjunk are absent from good figures, and the same holds here.)
- **No `shadow-lg`/`shadow-xl` paired with heavy rounding.** That combination is both a tell and a
  paint cost.
- **Glassmorphism is a deliberate effect, not a default.** `backdrop-blur` plus `border-white/10`
  with no structural reason is trend-chasing. Use it for a real purpose or not at all. Same for
  `blur(100px)` ambient glow blobs.

### Motion

- **Motion budget near zero by default.** No fade-in-on-scroll on every section. Animate state
  changes the user caused, not the arrival of static content. Skip animation entirely on
  high-frequency or repeated actions (a command menu feels faster with none).
- **`ease-out`, almost always, with a custom curve.** Built-in curves are too weak, so use a custom
  cubic-bezier (an `ease-out-quart` / `ease-out-expo` shape). Never `ease-in` for entering UI, and
  no bounce or elastic easing (it reads dated).
- **Fast.** Interaction transitions under ~200ms (Rauno) to 300ms (Emil). A 180ms select feels more
  responsive than a 400ms one.
- **Animate only `transform` and `opacity`.** Animating width/height/padding/position triggers
  layout and janks. Never animate from `scale(0)`, start at 0.9+. Press buttons to `scale: 0.97`
  on `:active`.
- **Interruptible and accessible.** Animations must be interruptible. Ship a
  `@media (prefers-reduced-motion: reduce)` branch for every animation. Font weight must not change
  on hover (it shifts layout).

### Layout

- **Break the symmetric-hero skeleton.** Centered hero plus three equal cards plus CTA is the AI
  page. Use an asymmetric CSS grid: content offset to a center-left column, one oversized real
  screenshot bleeding off the right edge, an unexpected section order. (A ready hero-grid is in
  Part 7.)
- **Pick a register: Brand or Product.** A marketing surface optimizes for uniqueness (asymmetric,
  editorial, display serif, organic). A product surface optimizes for density and familiarity
  (standard nav, predictable patterns, information-dense). Do not apply marketing flourish to a
  dashboard or sterile uniformity to a landing page. Record which register a surface is in.
- **Content-first ordering.** The default flow (hero, features, testimonials, pricing, CTA) is
  recognizable because it is content-agnostic. Order sections by what *this* product needs the
  visitor to understand, in order.
- **Density through selective de-emphasis, not whitespace as filler.** "Way too much whitespace" is
  in the top design comment. Linear's calm-but-dense playbook: dim the chrome (softer borders,
  smaller icons, warmer grays, nav into small pills) so structure is felt not seen, and preserve
  density by suppressing the secondary rather than deleting content.

### Imagery and icons

- **Real imagery beats stock** (stock illustration carries 40% negative sentiment). The recognizable
  offenders: undraw, Humaaans, faceless 3D-blob people, the "diverse team around a laptop in an
  impossibly lit office." Use real product screenshots, real photography (even a mobile-shot photo
  reads as more authentic than polished stock), or commissioned illustration.
- **A coherent icon family, never emoji.** Consistent stroke weight and metaphor.
- **No placeholder content.** Lorem ipsum, invented logos, AI-generated testimonial quotes, and
  "Powered by AI" badges all read as generated. Real copy and real proof, even sparse, beat
  polished fakes.

---

## Part 4 - Copywriting and microcopy

UI copy is where the *language* tells from the paper-writing rule list transfer, but they need a
register shift. The PaperMaker rules target formal IEEE prose, whereas a landing page is informal,
second-person, and punchy. The *tell-detection* carries over unchanged (an em dash is an em dash, a
puffed adjective is a puffed adjective), while the *formality prescriptions* sometimes flip. The
inversions are flagged below so you do not paste academic stiffness onto web copy.

**The one diagnostic that subsumes the rest (Julian Shapiro):** *if the visitor reads only this
text, will they know exactly what you sell?* AI copy almost always fails it. Most fixes below
reduce to replacing an abstract verb or adverb with a concrete number, a named customer, or a
literal action.

### The web voice (what inverts from the paper rules)

The paper list and a landing page disagree on four points. On the web, take the web side:

- **Use contractions** ("you're," "we'll," "it's," "doesn't"). The paper rule bans them. On the web
  their absence is the stiffness that reads as either a robot or a legal disclaimer. Contractions
  are how humans write to other humans.
- **Write in second person, to "you."** Papers avoid it, web copy lives in it. ("You ship in a day"
  beats "Users can ship in a day.")
- **Short, punchy lines are good here.** The paper rule against "mic-drop stinger sentences" is a
  formality rule. The actual AI tell is the *formula*: the same long-sentence-then-three-word-
  punchline rhythm repeated on every section. One deliberate punch line is fine. A reflexive cadence
  is the tell.
- **One deliberate triad is a real copy device.** Rule-of-three is a classic for a reason. The tell
  is the *reflexive* triplet padded onto every heading ("Fast, simple, and powerful"), not the
  occasional earned one.

### The language tells (these transfer intact from anti-ai-language)

- **No em dashes.** Where a comma, parenthesis, or colon fits, use that. The most notorious text
  tell, called out by name in the threads as a bot filter.
- **Drop didactic disclaimers.** "It's important to note," "Keep in mind," "Remember that." If it
  matters, just say it.
- **Cut throat-clearing and referential filler.** "It's worth noting that," "Note that," "When it
  comes to X," "As mentioned above." Start with the subject. The opener whose deletion changes
  nothing should be deleted.
- **Drop the "In summary / In conclusion / Overall" recap.** A closing block that restates what was
  just said adds nothing. End on a forward-pointing line or stop.
- **Avoid the "X, not Y" contrastive reflex** ("Not just a tool, a platform"). State X. The "not Y"
  half usually rebuts an objection no one raised.
- **No "not only X but also Y"** negative parallelism. Say what it is, directly.
- **Cut editorial "-ing" tails.** "...empowering teams to scale," "...ensuring you never miss a
  beat," "...helping you do more." These dangling participles editorialize without adding
  information. Stop the sentence at the fact.
- **No false ranges.** "From idea to launch," "from design to deployment" when the two are not real
  scale endpoints. Name the actual things.
- **No vague attribution.** "Studies show," "experts agree," "it's widely known that" with no named
  source. Cite a real one or make the claim directly.
- **Drop "may indeed" hedging** and its kin ("can indeed," "does in fact"). Either hedge with a real
  caveat or assert plainly.
- **Cut filler intensifiers, starting with "very."** "Incredibly," "extremely," "highly," "truly,"
  "blazingly fast." Pick a word strong on its own or a number ("very fast" -> "200ms").
- **No puffery / importance inflation.** "Game-changing," "next-generation," "world-class,"
  "cutting-edge," "best-in-class," "boasts," "stands as a testament to," "plays a vital role." Also
  the metaphor nouns: "tapestry," "landscape," "realm," "ecosystem" used to inflate scope.
- **No "In today's fast-paced world" openers** or any scene-setting wind-up. Open on the point.
- **One term per concept.** Do not cycle "platform / solution / tool / system" for the same thing.
  Consistency reads as clarity, and synonym-cycling reads as filler.
- **No emoji or sparkles in headlines.** The sparkle and rocket are the most over-represented in AI
  copy.

### Write in positive voice (ported from positive-voice, transfers well)

- **Put the action in the verb, not a nominalization.** "Decide," not "make a decision." "Review,"
  not "perform a review." "We analyze," not "an analysis is performed." This single habit removes
  most of the limp, agentless feel of generated copy.
- **Say what is, not what is not.** "not very fast" -> a number, "not complicated" -> "simple."
  Negative phrasing is vaguer and weaker. Reserve "not" for genuine denial.
- **Prefer the simpler word** unless the technical term is more precise: use over utilize, show over
  demonstrate, help over facilitate, get over obtain, start over commence, end over terminate.
- **Front-load subject and verb.** Do not bury the verb behind a long introductory clause. "By
  combining real-time sync with offline support, the app keeps your data current" reads slower than
  "The app keeps your data current, online or off."
- **Match verb strength to the evidence.** Do not "revolutionize" what you "improve," or "guarantee"
  what you "aim for." Overclaiming and underclaiming both cost trust.
- **Omit needless words.** "in order to" -> "to," "the fact that" -> "that," "has the ability to" ->
  "can," "make use of" -> "use." Every word earns its place.

### Make every line concrete (ported from prose-structure)

- **Concrete beats abstract, always.** A number, a named customer, a literal action beats any
  abstraction. "Cuts invoice prep from 3 days to 20 minutes" beats "streamlines your workflow."
- **Put the strongest word at the end of the line.** The end is the most memorable position. Build
  toward it rather than trailing off into qualifiers.
- **One idea per unit.** One heading, one line, one card carries one idea. A card trying to say
  three things says none.
- **Use parallel form.** Nav items, feature titles, and list items should share a grammatical shape
  (all verbs, or all nouns, not a mix). Broken parallelism reads as careless.
- **Lead with the point.** Open a section with what it is about, not a wind-up. The reader should not
  have to reach paragraph two to learn the subject.
- **Vary sentence length.** The flat, medium-length, evenly-cadenced rhythm is itself an AI
  signature. Mix a short line against a longer one.
- **Avoid the inline-boldface-list reflex** for prose content. A wall of **bold-header:** colon
  items in place of real writing is an AI tell. (A reference doc like this one uses them by design.
  Marketing and editorial copy should not lean on them as a substitute for prose.)

### Banned hero phrases (exact)

- **"Supercharge your X"** (the canonical bad header), **"Unlock / Unleash the power of X,"
  "Transform / Revolutionize the way you X," "The future of X," "X, reimagined," "Build X in
  seconds," "10x your productivity," "AI-powered productivity tool."** A headline carrying two or
  more of these buzzwords has, in one source's words, a near-zero chance of being human-written.
- **Adverb openers:** "Effortlessly, Seamlessly, Instantly, Simply, Easily." Delete the adverb and
  let a concrete verb plus a number carry the claim.
- **Vague value props:** "For modern teams," "Built for teams who...," "Everything you need to X,"
  "Automation that works." They exclude no one and say nothing.

### CTAs

- **The weak defaults:** "Get Started," "Get Started Free," "Start Free Trial," "Try it now," "Book
  a Demo," "Join the waitlist." "Get Started" is the most common fallback. "Book a Demo" tells
  prospects what they will do, not what they will get.
- **Tie the label to the outcome.** Reported wins worth citing: "See a Live Demo" outperforming
  generic CTAs, and "Book a demo" to "Talk to a Human" lifting conversion ~110%. Specific beats
  generic.

### Fake proof and urgency (these now reduce trust)

The recognizable fakes:

- "Trusted by 10,000+ teams" over one logo or a domain registered last week.
- First-name-only testimonials ("Sarah K.") with stock avatars that fail reverse image search.
- Fake purchase popups ("Samantha from Boston just purchased"), now recognized as fake within ~3
  seconds.
- "SOC 2 Type II pending" badges, and waitlist-as-product with only an email field.

Use real, specific, verifiable numbers only.

### Two more surface tells

- **Title-case headers** ("Powerful Features For Modern Teams") mimic markdown and read as
  generated. Use sentence case.
- **Text overload.** A named complaint in the threads: AI over-explains, info-dumps, and repeats
  itself. Cut the second sentence that restates the first. UI copy should be shorter than your
  instinct.

### How to humanize copy

Replace abstract claims with specific proof, and add the sections AI never writes unprompted:

- **A "not a good fit" section** naming who the product is not for. Filters leads and builds trust.
- **A real process timeline** ("Day 1: intro call. Day 2: estimate.") instead of an icon-block
  "how it works."
- **Concrete case studies** ("how we cut a local invoice workflow from 3 days to 20 minutes") over
  generic feature tiles.
- **Direct service claims** over jargon: "AC repair, technician at your door within 48 hours," not
  "comprehensive residential climate solutions with intelligent integration."

---

## Part 5 - Code and craft tells (under the hood)

Not in the visual ranking, but raised across the dev threads and worth enforcing because they
correlate with the surface look.

- **The shadcn fingerprint.** The dead giveaway is the unmodified `lib/utils.ts`:
  ```ts
  import { clsx, type ClassValue } from "clsx"
  import { twMerge } from "tailwind-merge"
  export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)) }
  ```
  plus an `app/` + `components/ui/` + `lib/utils.ts` tree of untouched default `Button`/`Card`/
  `Dialog`. shadcn is explicitly designed to be copy-pasted by agents, so the tell is *zero*
  customization. Override the tokens (radius, color, font) and component variants. A visual editor
  like TweakCN can generate the overridden Tailwind v4 variables for you.
- **Div soup and missing semantics.** AI defaults to nested `<div>`/`<span>` with click handlers
  and no `<main>`/`<nav>`/`<section>`/`<button>`/`<a>`/headings. A Frontend Masters teardown of one
  29-line AI sidebar found 10 distinct failures (a `role="generic"` where `<nav>` belonged, a
  heading rendered as a styled `<div>`, clickable `<div>`s for links). Three mechanistic causes:
  training data is mostly `<div>`-heavy React, RLHF rewards visual fidelity and never penalizes
  semantic failure, and `<div onClick>` is fewer tokens than `<button aria-expanded>`. Fix with
  semantic landmarks plus headless primitives (Radix, Headless UI, React Aria) so ARIA and keyboard
  support come for free.
- **Accessibility as a de-slop pass.** One commenter reports an a11y cleanup killed "70% of the
  vibe feel by making it readable." Gate it: `eslint-plugin-jsx-a11y` at error, `jest-axe` with
  Testing Library (`getByRole`, `userEvent.tab()`), `@axe-core/playwright` in CI. Roughly 3-8
  minutes per component up front versus 45-90 minutes remediating later.
- **Tailwind class soup.** Very long `className` strings, arbitrary bracket values (`w-[327px]`,
  `bg-[#316ff6]`), and the same utility cluster copy-pasted instead of extracted. Use scale values
  and extract to components or `tailwind-variants`/CVA.
- **React anti-patterns that flag generation:** `useEffect` for data fetching ("the biggest
  anti-pattern in modern React," use TanStack Query / Suspense), `key={index}`, inline mock-data
  arrays, God components with five scattered `useState` calls and `{ task: any }` props, generic
  names (`HeroSection`, `Component1`), and line-by-line comments restating the code. AI code arrives
  "fully formed with error handling, logging, documentation" where humans grow it from the happy
  path. Comments should explain *why*, not narrate *what*.
- **Tool-by-tool nuance (not all equal).** v0 is the cleanest (typed prop interfaces, Radix-backed
  accessible primitives, design tokens) and is the one tool Frontend Masters exempts. Lovable looks
  clean but ships `any` types and inline Supabase calls with `console.error`-only handling.
  Bolt.new is the most inconsistent across sessions. The chat models (ChatGPT, Claude, Copilot,
  Cursor) produce the classic div soup. Calibrate review depth to the tool.

---

## Part 6 - Positive craft signals (what intentional frontends do)

The inverse of the list. None of these is achievable by removing a tell. Each requires a decision.
The cure for "screams AI" is not sterility, it is opinion.

- **A point of view.** A distinctive type pairing, an unexpected color, a layout move no template
  ships. Pick something to be deliberate about and be unmistakably deliberate about it.
- **Content-first design.** The layout serves what this product needs to say, in the order it needs
  saying. Sections are not interchangeable.
- **Restraint as a signal.** One accent, one motion idea, one display face, used with discipline,
  reads as more crafted than a stack of trends. (The PaperMaker figure ethos exactly: minimum
  information, every element earns its place, one consistent design language across every screen.)
- **Real proof over polished fakes.** Real screenshots, real numbers, real attributed testimonials.
  The absence of stock filler is itself a craft signal.

### Who to read (and the one idea each is the source of)

The specific rules these voices supply are already folded into Part 3 and the number table below.
This is the reading list and the single signature idea to remember each one by, so you know whose
work to open when you need depth on a topic.

- **Refactoring UI (Wathan & Schoger):** hierarchy comes from weight and color, not size. The whole
  book follows from de-emphasizing everything around the thing you want to emphasize.
- **Anthony Hobday, "Visual design rules you can safely follow every time":** the deterministic
  geometry. Nested radius, padding ratios, brightness deltas, saturated neutrals. Open this for
  exact numbers when a layout feels off and you cannot say why.
- **Rauno Freiberg (`interfaces.rauno.me`):** the robustness thesis. If the UI works only 80% of the
  time the perception of quality breaks, so the craft is in the interaction details (interruptible
  motion, form semantics, optimistic updates).
- **Emil Kowalski (animation):** `ease-out`, short, transform-and-opacity only. The reference for
  *why* an animation feels cheap or expensive.
- **Josh Comeau (depth and color):** layered, color-matched shadows and gradients interpolated in
  OKLCH so two saturated colors do not average to grey mud.
- **Stripe / Linear (production proof):** Stripe runs gradients on the GPU so they do not jank and
  colors only the focused element. Linear holds density by de-emphasizing chrome rather than
  removing content. Two of the best worked examples of restraint at scale.

### Quick-reference numbers (pin these in a project)

| Rule | Number | Source |
|---|---|---|
| Interaction animation duration | <=200ms (Rauno) / <300ms (Emil) | Rauno, Emil Kowalski |
| Active-press button scale | `scale: 0.97` | Emil Kowalski |
| Min input font-size (no iOS zoom) | 16px | Rauno |
| Min body text | 16px | Hobday |
| Min font weight | >=400 | Rauno, Refactoring UI |
| Line length | 65-75ch (~70) | Hobday, Gemini brief |
| Display headline ceiling | ~6rem via `clamp()` | Gemini brief |
| Display letter-spacing | floor ~-0.04em | Gemini brief |
| Shadow vertical:horizontal offset | 2:1 | Josh Comeau |
| Shadow blur:distance | 2:1 | Hobday |
| Layered shadow count | 3 medium / 5 high | Josh Comeau |
| Type scale ratio | 1.25 (Major Third) | Mortensen / Material |
| Max typefaces | 2 | Hobday |
| Hierarchy palette | 2-3 text colors, 2 weights | Refactoring UI |
| Greys to define | 8-10 | Refactoring UI |
| Spacing base | 4px grid | Refactoring UI |
| Neutral tint chroma (OKLCH) | 0.005-0.015 toward brand | Gemini brief |
| Accent saturation | under ~80% | impeccable.style |
| Body contrast (WCAG AA) | >=4.5:1, secondary >=3:1 | WCAG |
| Container vs bg brightness delta | <=12% dark / <=7% light | Hobday |
| Card radius cap | 6px (ban 2xl/3xl) | Gemini brief |

---

## Part 7 - Enforce it deterministically

The research is blunt: prose guidance alone made AI output *worse* (one measured study saw slop-rule
failures rise to ~11.7 per component under written guidance), while a mechanical pass/fail gate drove
them near zero. Where a rule can be a banned value that fails the build, make it one. The workflow:

1. **Start from a real reference, not a prompt.** Hand the model an actual site whose direction you
   want and have it adapt. The corpus's single most-repeated fix. Stop asking it to "make the
   design better." Vague input is what produces the average. A starter set of references worth
   stealing structure and restraint from, none of which reads as generated:
   - **Product / SaaS:** Linear, Stripe, Vercel, Raycast, Resend, Mintlify, Arc.
   - **Editorial / brand:** Anthropic, Basecamp / 37signals, Pitch, Family, Teenage Engineering.
   - **Reference-grade craft:** the sites behind the voices above (`rauno.me`, `interfaces.rauno.me`,
     `emilkowal.ski`, `joshwcomeau.com`, `anthonyhobday.com`).
   Do not copy any one of them wholesale (that just trades one monoculture for another). Pick one as
   a structural anchor, name what specifically you are taking from it (its grid, its type contrast,
   its restraint), and derive the rest from your own brand.
2. **Write a spec first.** Record the decisions in a `DESIGN.md` / `PRODUCT.md` the agent reads on
   init: palette (hexes/OKLCH off the violet axis), the two named typefaces and the scale, spacing
   rhythm, radius cap, motion budget, the register (Brand or Product), and an explicit
   anti-reference list ("standard SaaS templates, Inter, absolute-black canvases").
3. **Ban the defaults at build time.** Two gates do most of the work:
   - **Delete the default Tailwind palette** so `bg-indigo-600` and friends fail to compile and the
     model is forced onto your tokens:
     ```js
     // tailwind.config.js (excerpt) - replace, do not extend, the color block
     colors: {
       transparent: 'transparent',
       current: 'currentColor',
       ink:    { 50:'#fbfaf7', 100:'#f4f1eb', 200:'#e7e2d5', 500:'#4a473f', 900:'#141310' },
       accent: { 50:'#fffbf2', 400:'#e8775a', 600:'#c45530', 800:'#8e3419' },
     },
     fontFamily: { display:['"Fraunces"','serif'], sans:['"IBM Plex Sans"','sans-serif'] },
     borderRadius: { none:'0px', sm:'2px', md:'4px', lg:'6px' }, // 2xl/3xl removed
     ```
   - **A lint rule that flags the class-level tells** in CI or a pre-write hook:
     ```js
     const BANNED = [
       /from-(purple|violet|indigo)-\d+\s+to-(blue|pink|cyan)-\d+/, // the AI gradient
       /bg-(slate|indigo|violet|purple)-[56]00/,                    // default accents/neutrals
       /rounded-(2xl|3xl)/,                                          // blob radii
       /shadow-(lg|xl)/,                                             // heavy untinted shadows
     ]
     ```
     Run it as `eslint-plugin-jsx-a11y` (for the semantic/a11y tells) alongside a small local rule
     that tests `className` literals against `BANNED`.
4. **Break the centered hero with a structural default.** An asymmetric grid that offsets content
   left and lets the visual bleed off the right edge defeats the symmetric-hero skeleton without
   per-page effort:
   ```css
   .hero {
     display: grid;
     grid-template-columns: minmax(2rem, 1fr) minmax(0, 42rem) minmax(0, 1fr);
     align-items: center;
     min-height: 85vh;
   }
   .hero-content { grid-column: 2; }              /* text in the center-left column */
   .hero-media   { grid-column: 2 / -1; }          /* art bleeds into the right edge */
   .hero-title {
     font-size: clamp(2.5rem, 6vw, 5rem);          /* ceiling, not a fixed 64px */
     letter-spacing: -0.03em;
     text-wrap: balance;
   }
   ```
5. **Screenshot-and-critique loop (ported from the PaperMaker PNG loop).** After every change,
   render the actual page, look at the rendered screenshot, critique against this list, edit,
   re-render. Tells are invisible in source and only show in pixels. Resolve the high-level
   questions first (does this page have a point of view? does each section earn its space?) before
   touching typography. Several iterations on a real page is normal.
6. **Turn the model's verbosity down.** The over-explaining, text-overload tell is partly a setting.
   Lower it in custom instructions rather than fighting every generated paragraph.

### Existing toolkits worth knowing

You do not have to build the gate from scratch:

- **Impeccable design skill** (`pbakaus/impeccable`): 44 deterministic local visual rules run as a
  pre/post-write hook (no API call), plus `/impeccable` commands for critique, audit, typeset,
  colorize, layout. The most complete enforcement framework.
- **Anthropic frontend-design skill** (`anthropics/skills`): forces the model to document a custom
  design system before generating, bans the overused fonts and purple-on-white, and works without
  few-shot examples so it does not anchor to one look. "Intentionality, not intensity."
- **TweakCN** (`tweakcn.com`): visual editor that overrides shadcn/Tailwind v4 tokens and exports
  clean variables.
- **Strip AI, Glyfo, Clavix, VibeDoctor:** smaller utilities for stripping typographic tells,
  exporting design tokens as LLM instructions, mapping sections to components, and visual linting.
- **Figma-to-code + Playwright visual diff:** for enterprise, restrict the model to implementation
  and assert rendered output against an approved Figma canvas with visual regression.

---

## Sources

**Empirical spine**
- JCarterJohnson, "I scanned ~3,200,000 posts across 47 AI and SaaS subreddits" (r/ClaudeCode).
  Data: `https://github.com/JCarterJohnson/vibecoded-design-tells`. All ranked percentages,
  sentiment, co-occurrence, and growth figures.
- Adrian Krebs, "Design slop" DOM audit of 1,590 Show HN sites:
  `https://www.adriankrebs.ch/blog/design-slop/`. The per-pattern frequencies.

**The mechanism**
- Adam Wathan, indigo-500 apology (X, Aug 2025): `https://x.com/adamwathan/status/1953510802159219096`.
- Alan West, "Why every AI-built website looks the same":
  `https://dev.to/alanwest/why-every-ai-built-website-looks-the-same-blame-tailwinds-indigo-500-3h2p`
  and the fix: `https://dev.to/alanwest/how-to-fix-the-ai-generated-look-in-your-frontend-1ahh`.
- Jeff Humble, Fountain Institute, "signs of vibe-coded UI":
  `https://www.thefountaininstitute.com/blog/signs-vibe-coded-ui`.
- solodesign.cc, "AI design slop: the tells" (the safe-green regression, deterministic>prose):
  `https://solodesign.cc/blog/ai-design-slop-the-tells/`.

**Visual tell catalogs**
- Developers Digest, 16 patterns: `https://www.developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it`.
- impeccable.style/slop (exact-value checklist): `https://impeccable.style/slop/`.
- 925studios: `https://www.925studios.co/blog/ai-slop-web-design-guide`.

**Copy**
- Wikipedia, "Signs of AI writing": `https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing`.
- conorbronsdon/avoid-ai-writing (banned-word table):
  `https://github.com/conorbronsdon/avoid-ai-writing/blob/main/SKILL.md`.
- Julian Shapiro, landing-page guide: `https://www.julian.com/guide/startup/landing-pages`.
- mouseflow/howdygo/naoma on CTA conversion data.

**Code**
- Frontend Masters, "AI-Generated UI Is Inaccessible by Default":
  `https://frontendmasters.com/blog/ai-generated-ui-is-inaccessible-by-default/`.
- freeCodeCamp React refactoring case study, and the shadcn manual install docs.

**Positive craft**
- Refactoring UI: `https://refactoringui.com/`. Anthony Hobday safe rules:
  `https://anthonyhobday.com/sideprojects/saferules/`. Rauno Freiberg:
  `https://interfaces.rauno.me/`. Emil Kowalski: `https://emilkowal.ski/ui/great-animations`.
  Josh Comeau shadows/gradients. Erik Kennedy, Learn UI Design. Linear design refresh. Stripe
  gradient teardown (kevinhufnagl).

**Ported from**
- PaperMaker9000 rule list (`~/PaperMaker9000/RULES_SUPERLIST.md`): the portable parts of its Style
  family (anti-ai-language tells, positive-voice rules, prose-structure rules) register-shifted to
  web copy, plus the figure-craft ethos mapped to visual design. Left out as non-portable: all of
  Structural (paper anatomy: abstract/intro/methods/results arcs), all of LaTeX, the Wout
  pet-peeves, and the academic-register half of misused-words (comprise/constitute, Latin plurals,
  yields/gives).

---

## Five through-lines (the short version)

1. **Two visual tells are the em-dash equivalents:** the AI-purple gradient and the colored card
   border stripe. Lead every audit with them.
2. **Escaping a default into another default is still a tell.** Inter to Geist, indigo to emerald,
   "Supercharge" to "Unlock." The fix is brand-derived specificity, never the next-most-common
   option.
3. **Deterministic gates beat prose.** Prose alone made output worse, and banned-value build gates
   fixed it. Encode rules as failing builds where you can.
4. **Specificity is the antidote.** Every fix reduces to replacing an averaged default (color, font,
   phrase, layout, component, metric) with an intentional, brand or content-derived specific.
5. **Down-weight the bloggers' clichés.** Bento, glassmorphism, and aurora backgrounds are loudly
   listed but rank near the bottom of what real users flag. Spend effort on the kit, the purple, the
   gradient, the card stripe, and dark-mode-by-default.

---

## Appendix A - Working color-role table (OKLCH)

A drop-in starting point for a non-default palette. Replace `H` with one brand hue (a single number,
e.g. 260 for blue, 145 for green, 25 for orange) and keep it constant down the column so every
neutral is faintly tinted toward the brand rather than dead gray. Values are starting points, not
gospel: tune lightness to hit the contrast targets in the last column. The whole point is that none
of these are `#000`, `#fff`, or `slate-*`.

| Role | Light mode | Dark mode | Contrast target |
|---|---|---|---|
| Canvas background | `oklch(98% 0.005 H)` | `oklch(15% 0.01 H)` | base surface for the ratios below |
| Raised surface / card | `oklch(96% 0.008 H)` | `oklch(19% 0.012 H)` | within ~7% (light) / ~12% (dark) of canvas |
| Border / hairline | `oklch(90% 0.012 H)` | `oklch(28% 0.015 H)` | visible in *both* themes |
| Body text (ink) | `oklch(20% 0.02 H)` | `oklch(92% 0.01 H)`, weight ~350 | >=4.5:1 on canvas |
| Secondary text | `oklch(40% 0.015 H)` | `oklch(70% 0.012 H)` | >=3:1, use only at >=16px |
| Caption / metadata | `oklch(55% 0.01 H)` | `oklch(58% 0.01 H)` | non-essential, no strict ratio |
| Accent (primary action) | `oklch(62% 0.18 Ha)` | `oklch(68% 0.14 Ha)` desaturated | high contrast on its surface |
| Accent hover | `oklch(55% 0.20 Ha)` | `oklch(72% 0.15 Ha)` | distinct from rest state |

Notes that keep this from sliding back into the default look:
- **`H` is the neutral tint hue, `Ha` is the accent hue, and they should differ.** A neutral tinted
  toward the same hue as the accent is what produces the "everything is faintly purple" wash.
- **Keep neutral chroma in the 0.005-0.015 band.** Above that the tint stops reading as a neutral.
- **Desaturate accents in dark mode** so they do not vibrate on the dark canvas.
- **Prefer solid tokens over stacked transparency.** Define each layer explicitly rather than
  layering `rgba()`, which produces unpredictable combinations and paint cost.
- **The accent hue must be off the `#6366f1`-`#a855f7` indigo-violet band** (roughly H 265-295 in
  OKLCH). That band is the single most-named color tell.
