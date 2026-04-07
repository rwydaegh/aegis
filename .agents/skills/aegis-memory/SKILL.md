---
name: aegis-memory
description: Use when a task depends on long-lived AEGIS context not obvious from the repo, such as commercialization, patent sensitivity, deployment history, local agents, DiffeRT collaboration, base station pipeline status, or Robin-specific working preferences
---

# AEGIS memory bridge

This skill bridges Codex to the historical Claude memory bank for AEGIS without copying that memory into the repo.

## When to use

Use this when the task depends on project history or user preferences that are not fully captured in `AGENTS.md`, code comments, or docs.

Common triggers:
- commercialization, funding, co-founders, or spin-out planning
- patent, disclosure, or IP sensitivity
- production deployment, Hetzner, Modal RT, Umami, or CloudRF
- local agent runners, QA automation, or overnight workflows
- DiffeRT collaboration or BVH acceleration history
- base station pipeline status or recently shipped viewer features
- Robin-specific preferences that were previously stored as Claude memory

## Primary source

Start with the memory index:

- `~/.claude/projects/-home-user-aegis/memory/MEMORY.md`

Then read only the specific files relevant to the task. Do not bulk-load the whole memory directory unless the task truly requires it.

## Memory map

- User preferences: `user_robin.md`, `feedback_*.md`
- Business and IP: `project_commercialization.md`, `project_idf_patent.md`
- Infra and deployment: `reference_domain.md`, `reference_hetzner_deploy.md`, `reference_modal_rt.md`, `reference_umami_analytics.md`
- External tools and research services: `reference_cloudrf.md`, `reference_perplexity.md`, `reference_tensordock.md`
- AEGIS roadmap and shipped state: `project_recent_features.md`, `project_basestations.md`, `project_cesium_globe.md`
- Agent history: `project_agent_hq.md`, `project_local_agents.md`, `project_overnight_agents.md`, `reference_qa_automation.md`
- DiffeRT context: `project_differt_collaboration.md`, `project_differt_bvh.md`

## Guardrails

- Treat memory as historical context, not gospel. Check dates.
- Prefer targeted reads over loading every memory file.
- If memory conflicts with the current repo state, trust the repo and mention the conflict.
- Be especially careful with files that include credentials, production hosts, or private business information.
