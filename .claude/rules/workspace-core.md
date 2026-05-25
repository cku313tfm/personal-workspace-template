# Workspace Rules

## Agent Summon Protocol

When the user types `@<name>`, load the agent's identity from `.claude/agents/<name>.md` and adopt that operating stance fully. Only one agent is active at a time. A new summon replaces the previous one.

If no agent is summoned, operate as a general assistant aware of the workspace context.

## Session Start

**These steps apply to EVERY session — new or resumed.** Prior context may be stale. Always re-read. No exceptions.

Every session, before doing anything else:
1. If an agent is summoned, load its identity from `.claude/agents/<name>.md`
2. Read `plan.md` for current operational context
3. Read recent `memory/YYYY-MM-DD.md` files (today + yesterday) for context
4. In main sessions (direct chat), also read `MEMORY.md`
5. Check your GitHub Issues queue for current tasks
6. Check for dispatched stack from the orchestrator (in memory files or plan.md)

Do not ask permission for these reads. Just do it. Do not skip steps because you think you already have context.

## Approval Gates

- **External actions (emails, messages, public posts, calendar invites with external attendees) require explicit user approval.** Surface the proposed action for ratify BEFORE running.
- Internal actions (reading files, organizing, planning, analysis) are safe to do freely.
- When proposing a plan or action, present it clearly and wait for the user's decision.
- Extra caution with personal data — this workspace contains anything personal you put into it (health, finance, relationships, etc.).

## Memory Conventions

- `plan.md` — active operational context and priorities
- `MEMORY.md` — long-term curated memory (main sessions only)
- `memory/YYYY-MM-DD.md` — daily raw logs. Create today's file if it doesn't exist. Write to it as things happen.
- `agents/flags.md` — cross-agent session-end flags (short-lived, actionable items that need to surface at the top of the next agent session)
- When you want to remember something, write it to a file. Mental notes don't survive session restarts.

## Canonical Sources (advanced — optional pattern)

When you eventually integrate external data sources (Google Calendar, Gmail, Google Tasks, a structured contacts DB, brokerage data, etc.), establish the discipline that **the external source is canonical** for the relevant question — not the workspace text files.

For example: if you connect Google Calendar via a Python helper, the calendar is canonical for any scheduled-event date/time/conflict question. Files like `flags.md`, `plan.md`, memory logs are auxiliary and may be stale or wrong. Query the helper FIRST; reason from the structured source, not from inference over text.

When a flag, plan entry, or memory note diverges from canonical truth, update the workspace artifact to match. **Helper output beats text-file inference whenever a helper exists.**

This rule isn't load-bearing in the MVP (no external integrations yet), but it's the discipline you'll want once you add them. See `docs/build-from-scratch.md` Step 8 for the integration pattern.

## Agent Task Board Rules

All agent tasks are tracked in GitHub Issues (repo: `[GITHUB_REPO]`).

**Title format:** Always prefix issue titles with the owning agent: `[Agent]`.
- Example: `[Finance] Q2 estimated tax deadline prep`

**Labels:** Every issue must have:
- Agent label: `agent:<name>` (e.g., `agent:[ORCHESTRATOR_NAME]`, `agent:[DOMAIN_1]`)
- Priority label: `priority:high`, `priority:medium`, or `priority:low`
- Add `needs:user-decision` if blocked on the user

**Cross-system tasks:** If you manage personal tasks in another system (Notion, Todoist, etc.), GitHub Issues is the agent-driven task board; the other system holds user-driven personal tasks. No sync required. The orchestrator can surface overdue items from the other system at session start (best-effort).

## Agent Dispatch Protocol

The orchestrator (`@[ORCHESTRATOR_NAME]`) is the manager of the domain agents. Domain agents don't self-prioritize.

**The flow:**
1. Orchestrator wakes up → pulls board, plan.md, agent session-end notes from memory/
2. Orchestrator delivers morning brief + **Agent Dispatch** (separate block, max 2 items per agent)
3. User approves or reorders in one message (~60 seconds)
4. Domain agents execute their dispatched stack when they wake up

**Agent execution rules:**
- Work items in dispatched order. Tactical reordering allowed (blocker, dependency). Adding new work is not.
- If blocked on an item, move to next in stack and note the blocker.
- If entire stack is blocked, escalate to the user. Don't freelance.
- If no dispatch exists (orchestrator hasn't run), propose your own stack to the user before executing.

**Session-end notes (all agents, every session):**
Write a 3-line note to today's `memory/YYYY-MM-DD.md` before ending:
- **Done:** issues closed, what shipped
- **80% done:** issues in progress, what's left
- **Blocked:** issues blocked, what's blocking them

The orchestrator reads these before dispatching. No notes = blind dispatch.

**Session-end commit check (all agents, every session):**
Before wrapping, run `git status` and review your uncommitted work. Commit your session's deliverables atomically with a clear message that names what shipped. Don't let the repo accumulate stale modifications or untracked files.

- Commit your own work. Leave other agents' modifications alone.
- If other agents have uncommitted work that's been sitting, write a flag into `agents/flags.md` under their section so they address it on their next session.
- Never auto-push. The user decides when work goes to the remote.
- For commit scope, prefer atomic logical units (one intent per commit) over one bundled commit covering mixed concerns.

## Soft Bridge (optional)

`[SOFT_BRIDGE_BLOCK — only included if recipient opted into soft-bridge pattern at bootstrap. Otherwise this section is removed.]`

If you have a second workspace (e.g., a business workspace separate from this personal one), you can establish a one-way bridge: this workspace's orchestrator reads `[OTHER_WORKSPACE_PATH]/plan.md` at session start to understand cross-context. This is read-only. Never write to the other workspace.

The bridge is one-way to prevent personal data from leaking into business contexts. If the other workspace also benefits from this workspace's context, the user is the bridge — relay directly.

## Checkout

Every agent runs the checkout playbook on session end. Triggered by phrases like "let's check out," "wrap for the day," "evening close," etc. Deterministic checklist, not agent judgment.

**Canonical playbook:** `.claude/rules/checkout-playbook.md`

## Communication Style

- Be direct. No filler. No sycophancy.
- Concise when the answer is simple. Thorough when it matters.
- End with a next move or a choice. Return agency to the user.
