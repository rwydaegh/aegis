---
name: qa
description: Open the AEGIS viewer and investigate it for bugs
user-invocable: true
---

# /qa - QA the AEGIS viewer

The full instructions -- how to pick a focus area, drive the viewer
with Playwright, interact with the 3D canvas, judgment calls on what
counts as a bug, issue filing conventions, and coverage logging --
live in one canonical place so cron agents, GitHub Actions swarm
testers, and interactive `/qa` sessions never drift apart.

**Read `agent_hq/prompts/qa-tester.md` and follow it.**

If invoked with a specific focus ("test the MIMO panel"), skip the
"Pick your focus area" step and test that area directly. Otherwise
pick a focus using the three signals described there
(`features.md`, `qa-coverage.md`, recent commits).
