---
description: When and how to tag patch/minor releases, and how to prompt the user about it
---

# Release cadence

AEGIS has historically only bumped minor versions (v0.5, v0.6, v0.7) and never shipped a patch release (v0.7.1). This leads to massive releases with 300+ commits. Fix this.

## Patch releases (v0.X.Y where Y > 0)

Tag a patch release after:
- A bug fix that changes behavior users would notice.
- A test fix that was masking a real issue.
- A doc fix that corrects wrong information.
- A dependency bump that fixes a compatibility issue.

Do NOT tag for: pure refactors, CI-only changes, config tweaks, or cosmetic doc edits.

## When to prompt the user

At the end of a session where you committed a bug fix, small feature, or meaningful correction, suggest a patch release. Example:

> "This bug fix is a good candidate for a v0.7.1 patch release. Want me to tag it?"

Do this proactively. The user has asked for it. Do not silently skip tagging because the change feels small. Small, frequent releases are better than giant infrequent ones.

## How to tag

```bash
git tag v0.X.Y
git push origin master --tags
```

The release.yml workflow handles the rest: full matrix test + GitHub release with auto-generated notes.

## Minor releases (v0.X.0)

Tag a minor release after:
- A new feature, kernel, or module.
- A meaningful new capability.

Aim for no more than ~50 commits between minor releases. If you notice the commit count since the last tag is growing large, mention it to the user.
