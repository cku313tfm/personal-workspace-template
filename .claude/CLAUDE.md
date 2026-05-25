# CLAUDE.md

## Workspace Bootstrap

This is `[USER_NAME]`'s personal workspace.

Available agents:
- `@[ORCHESTRATOR_NAME]` — Personal orchestrator. Morning briefs, dispatch, cross-domain coordination, life ops.
- `@[DOMAIN_1]` — `[DOMAIN_1_DESCRIPTION]`
- `@[DOMAIN_2]` — `[DOMAIN_2_DESCRIPTION]`
- `@[DOMAIN_3]` — `[DOMAIN_3_DESCRIPTION]`
- `@[DOMAIN_4]` — `[DOMAIN_4_DESCRIPTION]`
- `@[SYNTHESIS_NAME]` — Synthesis agent. Compounding knowledge base, post-meeting capture, externalization to memos and public posts. _(Optional — delete this line and the file if you didn't elect a synthesis agent at bootstrap.)_

Summon an agent by typing `@<name>` in your message.

Installed files:
- `.claude/agents/[ORCHESTRATOR_NAME].md` — Orchestrator identity
- `.claude/agents/[DOMAIN_*].md` — Domain agent identities
- `.claude/agents/[SYNTHESIS_NAME].md` — Synthesis agent identity (optional)
- `.claude/rules/workspace-core.md` — operating rules (summon protocol, approval gates, memory)
- `.claude/rules/checkout-playbook.md` — session checkout discipline

## MANDATORY STARTUP (every session — new or resumed, NO exceptions)

When an agent is summoned (or already active from a prior session), you MUST run these steps before doing anything else. This applies on resume too — prior context is stale.

1. Read your agent identity from `.claude/agents/<name>.md`
2. Read `plan.md`
3. Read today's and yesterday's `memory/YYYY-MM-DD.md` files (create today's if missing)
4. Check your GitHub Issues queue: `gh issue list --repo [GITHUB_REPO] --label "agent:<name>" --state open`
5. Check for dispatched task from `[ORCHESTRATOR_NAME]` in the memory files
6. **Report what you found before starting work**

If you are the orchestrator (`[ORCHESTRATOR_NAME]`), also: read `agents/[ORCHESTRATOR_NAME]/commitments.md`, read `agents/[ORCHESTRATOR_NAME]/decisions.md`, [SOFT_BRIDGE_LINE — only included if recipient opts into soft-bridge pattern at bootstrap], and pull ALL open issues (not just yours).

**Do not skip these steps. Do not summarize from memory. Re-read the files.**

Default behavior:
- If no agent is summoned on the first message, offer the choice: "Summon an agent (`@[ORCHESTRATOR_NAME]` for coordination, `@[DOMAIN_1]` for `[DOMAIN_1_AREA]`, etc.) or I can help as a general assistant."
- When an agent is summoned, adopt its identity and operating stance fully.
- Do not answer with a generic Claude greeting. Acknowledge the workspace context.

Key workspace files:
- `plan.md` — active priorities and goals
- `MEMORY.md` — long-term curated memory
- `memory/` — daily raw logs
- `agents/flags.md` — cross-agent session-end flags (short-lived, actionable)

## What this workspace is

A multi-agent personal operations system that:

- Remembers across sessions via memory files
- Coordinates work across `[N]` domains via the orchestrator + dispatch pattern
- Tracks decisions, commitments, and learnings explicitly (not in agent memory)
- Compounds capability over time via the synthesis agent's knowledge base _(if elected)_

Architecture WHY: see `docs/build-from-scratch.md`.
