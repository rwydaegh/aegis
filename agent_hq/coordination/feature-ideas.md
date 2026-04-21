# Feature ideas

Durable seed list for the feature-agent. These are concrete anchors for the
kind of work that sits at the right altitude: obvious what "better" looks
like, autonomously iterable, not super-tier.

Not a prescription. The feature-agent is free to pick something here, pick
something from `spinoff/` or `docs/internal/`, or notice something on its
own. Seeds are suggestions, not assignments.

Cross items out (`~~text~~`) when they're shipped, or delete them if they
stop being relevant. Add new ones freely.

---

## Compliance footprint is a circle, should be a shape

The viewer shows a little circle for the compliance zone. It's quite buggy,
and more importantly the shape is wrong: real compliance is almost never a
circle. It depends on phantom pose, channel model, and how much compute the
user is willing to spend on it.

Things that are clearly better than the current circle:
- Pose-aware footprint (the human isn't a point)
- Channel-model-aware shape (FSPL ≠ urban LoS ≠ NLoS cluster)
- Compute-budget-aware: maybe always-on in a cheap approximation, with a
  higher-fidelity module that the user opts into
- Honest about uncertainty when the model is coarse

This is a classic "iterate autonomously with AI" problem: the definition of
better is clear, the work is bounded, and Robin would say "yes obviously"
on first look.
