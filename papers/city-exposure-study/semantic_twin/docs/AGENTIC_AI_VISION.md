# Agentic AI vision for the urban RF semantic twin

## Vision and fit to the paper

Build a general-purpose, evidence-seeking vision agent that can reason over an
urban panorama and its RF scene model, while every claim that reaches the
semantic or transport Atlas remains traceable, replayable, and physically
validated, then test in the 15 August OJCOMS paper whether deliberate view and
prompt choice improves semantic evidence that drives exposure without claiming
that an LLM replaces the ray tracer or the physics model.

Production is currently Vistas-first. `gate_prompts` selects prompts from
`config/semantic_concepts.json`. SAM3 creates masks. Multi-view fusion produces
a joint semantic/material Atlas. Atlas binding and transport are the strict
boundary to physics. A provider-neutral material VLM transcript flow exists,
but the current study used Claude and has no Gemini adapter. No new AI
experiment has run.

## The agent loop

The agent has a scientific goal, an observation record, a bounded tool set, an
explicit state, and a log of every action and outcome. The model may revise its
plan or stop. It must not silently fill a missing physical parameter.

**Goal.** Produce the most useful, defensible semantic evidence for the scene
and body-exposure calculation under a declared call, time, and cost budget. The
agent should seek distinctions that can change the RF result, such as
conductor versus dielectric, glazing versus opaque facade, or a transport
relevant surface family. It should also be allowed to conclude that more
evidence is unlikely to matter.

**Observations.** The initial context can include full equirectangular
panoramas, registered rectilinear views, image crops, pose and camera metadata,
Vistas labels and confidence, existing SAM3 masks, multi-view overlap, Atlas
posteriors, depth and visibility support, transport inputs, and uncertainty
summaries. The agent can request a crop or view rather than receive only a
preselected thumbnail. It can inspect disagreement between views and compare
the image evidence with the current Atlas state.

**Available tools.** Tools are read-only unless a named evidence operation is
requested. They include panorama and crop viewers, view selection, image
registration checks, Vistas and Atlas queries, SAM3 prompt execution, mask
overlap and stability checks, material-transcript validation, sensitivity-trace
requests, and paired RF evaluations. A tool returns its input digest, model or
code identity, parameters, output digest, and an error or refusal status. For
the bounded paper experiment, this tool surface is frozen and the agent cannot
alter transport or write a material constant directly into the scene. A
long-term agent may create analysis code or tools in a sandbox, subject to
artifact review before anything can affect production.

**State.** A serializable state records the scene and run identifiers, current
ontology version, unresolved concepts, observations already inspected, prompt
strings, selected views and crops, tool results, Atlas revisions, uncertainty,
budget remaining, and the reason for the next action. Each revision has a
parent state. A replay can therefore reconstruct what the agent saw and why a
mask or binding was accepted.

**Actions.** The model may select another view, request a crop, ask SAM3 for one
or more prompts, ask for a paraphrase or negative prompt, compare two views,
inspect a conflict, ask for an Atlas posterior or uncertainty trace, request an
RF sensitivity trace, propose a concept, map a concept to an existing class, or
stop. It may choose a small set of actions in sequence, but each action must
state the question it is intended to answer. The action record includes the
exact image and prompt digests.

**Feedback.** The environment reports mask quality and support, cross-view
agreement, prompt interference, ontology mapping status, Atlas changes, and RF
sensitivity. Validation can accept evidence, map it to an existing ontology
entry, or retain it as an unknown. A failed or rejected action is still logged.
The agent receives the result and may revise its plan. A low-confidence mask is
not silently promoted by a later answer.

**Stop.** Stop when the requested scene questions are answered with accepted
evidence, when the remaining budget is exhausted, when repeated views and
prompts add no material information, or when the agent cannot resolve a claim
without inventing a parameter. The stop record states which condition held,
what remains unresolved, and whether the resulting Atlas is suitable for RF
validation.

The governing principle is broad freedom in reasoning and tool use, with strict
evidence, provenance, and physics interfaces. Hallucination is handled by
evidence checks and logged outcomes. The model is not reduced to a fixed prompt
selector. The physics boundary remains deterministic and reviewable.

## Long-term agent and bounded submission experiment

The long-term system could operate over many panoramas, cities, weather and
lighting conditions, and several RF frequencies. It could maintain a site
memory, learn which observations resolve recurring conflicts, and ask for a new
view or a new measurement. It could propose concepts that the fixed ontology
does not contain, such as a ventilated metal screen, a photovoltaic facade, a
double-glazed curtain wall, or a wet surface. Those concepts would enter an
unresolved, audited state until a validator maps them to a known RF family or a
future transport model accepts them. The agent would never create a dielectric
constant, conductivity, roughness, or thickness by implication.

The submission experiment must be smaller. Freeze one city, one panorama set,
one mesh and transport configuration, a predeclared seed set, one model
version, and a hard call, time, and cost budget. Run the agent on matched scenes where
the current Vistas-first result is already available. Preserve all transcripts,
tool arguments, image digests, masks, Atlas revisions, and RF outputs. The
paper can then report a controlled comparison without implying generality that
has not been tested.

## Gemini and ontology freedom

Gemini may propose a label outside the fixed ontology. The proposal is useful
even when it is not yet actionable. Store the original wording, evidence, view
set, confidence, and reason for proposal. A validator may accept it as an
existing concept, map it to an RF material family with an explicit rule, or keep
it unresolved and exclude it from transport. The unresolved record remains in
the audit trail and in the replay package.

This preserves the value of a broad model without letting an open vocabulary
become an unreviewed transport input. The Gemini API is available. The live
model and version, key handling, retention policy, and budget must be frozen
before any experiment. No result should be described as Gemini evidence until
those choices and the run manifest are recorded.

## Compact experiment design

Use paired runs on the same seeds, viewpoints, geometry, and RF inputs. The
candidate methods are:

| Method | Semantic decision rule |
| --- | --- |
| Current Vistas gate | Existing `gate_prompts` selection from the fixed catalogue, followed by current fusion and binding. |
| Full fixed SAM3 | Run the fixed catalogue without agent selection, using the same views and fusion rules. |
| Gemini agent | Let Gemini select views, crops, prompts, comparisons, and sensitivity requests under the frozen budget. |
| Agent without RF feedback | Same agent and budget, but hide RF sensitivity and transport feedback from its planning loop. |

For each method, report calls, input and output tokens where available, wall
time, cost, rejected calls, and the fraction of the budget used. Report the
evidence ledger: views and crops inspected, prompts issued, mask support and
quality, cross-view agreement, unresolved concepts, and Atlas revisions. Run
the same downstream RF validation for every accepted Atlas. Report changes in
whole-body SAR and maximum absorbed power density (`wbSAR` and `Sab,max`), the
number and size of semantic misses, and convergence under additional calls.
Use paired per-seed differences and uncertainty intervals. Do not pool methods
with different geometry or ray seeds.

The primary question is whether the agent finds evidence that changes the RF
answer in a traceable way. Secondary questions are whether it reaches the same
answer with fewer calls, whether RF feedback improves stopping, and whether
unknown concepts expose a real ontology gap or only a naming preference. A
small or null RF change is a valid result, especially where existing material
evidence indicates that ordinary dielectric distinctions have little exposure
impact. Conductor versus dielectric and other material-family changes can still
matter substantially.

## SAM3 prompt-capability study

This study is planned, not run. It must test prompt forms rather than assume
that a sentence is always better. SAM3's documented base text interface uses
short noun phrases with a noun and optional modifiers, such as “red apple” or
“striped cat”. The SAM3 paper says it is not designed for long referring
expressions or queries that require reasoning, and recommends combining it with
an MLLM for complex language. Gemini should therefore decompose an RF question
into short, auditable noun phrases and selected views or crops. A full sentence
is a planned stress test, not the preferred interface. See the [SAM3
paper](https://arxiv.org/abs/2511.16719) and the [official SAM3
repository](https://github.com/facebookresearch/sam3).

For each common and niche RF-relevant label, compare:

1. a noun, such as “glass”
2. a noun phrase, such as “glass facade”
3. material plus object, such as “metal railing”
4. an attribute, such as “reflective glazing”
5. a relation, such as “glass within a facade”
6. a negative or disambiguating phrase, such as “metal screen, not tree”
7. a full sentence describing the target

Test common labels and niche labels that may affect RF transport, including
glass, metal, concrete, brick, foliage, wire or mesh, and photovoltaic panels
when the scene supports them. Keep views, image scale, seeds, and thresholds
fixed. Assess mask quality against reviewed regions, stability under paraphrase,
score calibration, prompt interference when labels are run together, and
failure or rejection rates. Record whether a prompt returns no mask, a diffuse
mask, a duplicate of another concept, or a plausible but unsupported region.
The current `prompted.py` wrapper accepts only fixed-catalog text prompts and
rejects prompts outside that catalogue. Novel noun phrases, positive or
negative image exemplars, and interactive visual refinement are future adapter
work, not current behavior. The official repository includes a `sam3_agent`
notebook that can inform that future design, but it does not make those paths
available in this study automatically. Official SAM3 training and
prompt-handling details still require citation review. Do not invent them. The
paper should cite only details verified from the official source or the run
manifest.

The current catalogue contains exactly 60 prompt strings and 61 raster IDs,
including the unlabelled ID. Its prompts are noun phrases, with a maximum
length of 27 characters. The wrapper pre-encodes this fixed catalogue, and
novel text raises `ValueError`. No local SAM3 package or source is present now,
so a live wording study needs the pinned remote or GPU environment restored.

## Failure modes and honest claims

The agent can select an unhelpful view, over-segment a texture, miss a thin
conductor, mistake a reflection for a material, or repeat a confident error
across views. Registration, depth, and occlusion can make two agreeing masks
wrong for the same reason. A prompt can suppress another prompt, and scores may
not be calibrated probabilities. An open-vocabulary proposal can be visually
reasonable yet have no traceable RF transport row. RF feedback can also create
a loop that chases numerical noise rather than evidence.

Mitigations are explicit checks, not hidden restrictions: view and prompt
digests, overlap and support tests, paraphrase checks, conflict flags, posterior
calibration, sensitivity thresholds, a fixed budget, and a hard physics
interface. Keep rejected calls and unknowns in the record. State clearly that a
successful replay shows procedural reproducibility, not universal model
reliability. A result on one city does not establish performance in other
cities. No exposure improvement should be claimed before paired RF validation.

## Paper-space budget

Reserve 0.75 to 1.0 IEEE two-column page in the main paper and one two-column
figure. Allocate about 80 to 110 words to the method and 180 to 220 words to
results, plus one conclusion sentence. Replace detailed VLM and texture
paragraphs with the agent loop, the evidence gate, and the paired RF result.
Compress repeated discussion. Remove or rerun the stale illumination
subsection before submission. Put the audit schema, prompts, transcripts,
per-view masks, calibration plots, cost table, and unresolved-concept examples
in a 1.5 to 2.5 page supplement. If the experiment is not complete by the
paper freeze, describe the design as future work and retain the current tested
pipeline as the result.

## Decision gates

Include the agent in the main paper only if the model and budget are frozen,
all four methods have paired runs, evidence and provenance are replayable, the
physics validator accepts every transport input, and the result has a clear
effect or a clear, informative null. A small effect can qualify if the cost,
miss rate, or stopping behavior is materially better and the uncertainty is
reported.

Move the agent to future work if any run lacks a complete manifest, if the
Gemini version or key policy changes mid-study, if unknown concepts reach
transport without an explicit map, if RF feedback is not paired, or if the
result cannot be separated from seed, view, or geometry changes. Do not include
an unrun SAM3 prompt study as evidence.

## No-code-yet sequence and open questions

1. Freeze the scene set, RF configuration, model version, key policy, budgets,
   seeds, and retention rules.
2. Define the action and transcript schemas, validator outcomes, unknown state,
   and replay manifest.
3. Implement read-only adapters for panorama, crop, Vistas, SAM3, Atlas, and RF
   sensitivity tools.
4. Run the SAM3 prompt-capability study on reviewed common and niche labels.
5. Run the four paired baselines, then inspect misses and convergence.
6. Review the audit package, compute paired RF statistics, and decide main paper
   or supplement only after the gates above pass.

Open questions include the exact Gemini model and API version, how image data
and transcripts will be retained, the threshold for an Atlas revision, the
minimum RF sensitivity that justifies another call, how to calibrate SAM3
scores across views, and which unresolved concepts can be mapped safely to an
existing material family. These are experiment decisions, not assumptions to
hide in code.
