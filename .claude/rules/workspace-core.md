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
5. Check your task board for current tasks (see **Agent Task Board Rules** — GitHub Issues or the file-based board, whichever this workspace uses)
6. Check for dispatched stack from the orchestrator (in memory files or plan.md)

Do not ask permission for these reads. Just do it. Do not skip steps because you think you already have context.

There is a `/startup` skill (`.claude/skills/startup/`) that scripts these steps, and a `session-flags` hook that injects `agents/flags.md` into context at the start of every prompt (see **Flags + the session hook** below). The hook surfaces the flags; the startup routine does the reads.

## Approval Gates

- **External actions (emails, messages, public posts, calendar invites with external attendees) require explicit user approval.** Surface the proposed action for ratify BEFORE running. A calendar invite with an external attendee fires immediately (there is no draft-event state) — treat it as an external send.
- Internal actions (reading files, organizing, planning, analysis) are safe to do freely.
- When proposing a plan or action, present it clearly and wait for the user's decision.
- Extra caution with personal data — this workspace contains anything personal you put into it (health, finance, relationships, etc.). See **Keeping personal data out of git** below.

## Memory Conventions

- `plan.md` — active operational context and priorities
- `MEMORY.md` — long-term curated memory (main sessions only)
- `memory/YYYY-MM-DD.md` — daily raw logs. Create today's file if it doesn't exist. Write to it as things happen.
- `agents/flags.md` — cross-agent session-end flags (short-lived, actionable items that need to surface at the top of the next agent session)
- When you want to remember something, write it to a file. Mental notes don't survive session restarts.

## Canonical Sources (the discipline that makes this trustworthy)

When you integrate an external data source (Google Calendar, Gmail, Google Tasks, a structured contacts DB, brokerage data, etc.), **the external source is canonical** for the question it answers — not the workspace text files.

- Calendar is canonical for any scheduled-event date/time/conflict question.
- Email is canonical for any thread-status / reply-status / received-message question.
- The task list is canonical for what the user still owes.

Files like `flags.md`, `plan.md`, and memory logs are **auxiliary and may be stale or wrong**. When a helper exists, query it FIRST and reason from the structured source, not from inference over text. When a flag, plan entry, or memory note diverges from canonical truth, **update the workspace artifact to match — canonical wins.**

**This applies at BOTH startup and checkout.** Startup is where a stale "still pending" flag misleads the brief; checkout is where a stale flag gets wrongly cleared, or a staged draft gets wrongly reported as sent. Before you clear a flag that asserts a send/reply/received state — or report that state to the user — verify it against the live source. A concrete trap: a bare "to:X" email search matches drafts too and reads as sent; qualify sent vs draft before you close a send-task or clear a send-flag.

If you have no integrations yet, this rule is dormant — but adopt the discipline the moment you add the first helper. See `docs/build-from-scratch.md` for the integration pattern.

## Agent Task Board Rules

Agent tasks (durable, multi-session agent work) are tracked on **one** of two boards. Pick whichever fits — both work; the rest of the system doesn't care which you chose:

**Option A — GitHub Issues** (`<owner>/<repo>`). Good if you already live in GitHub and want a real issue tracker.
- Prefix issue titles with the owning agent: `[Finance] Q2 estimated tax deadline prep`.
- Label each issue: `agent:<name>` + `priority:high|medium|low`; add `needs:user-decision` if blocked on the user.

**Option B — File-based board** (`agents/backlog.md`, in-repo). Good if you want the board to fold into the same startup read as `flags.md`, or if an agent that reaches this repo can't authenticate to GitHub (e.g., a phone/remote client with no token).
- One line per item: `#ref · priority · owner · one-liner · (date added)`, grouped under an `## <Agent>` heading with `**Active**` / `**Backlog**` sub-blocks.
- Done items move to `## Archive` with a one-line outcome; prune Archive at the weekly checkpoint.

**Keep the board distinct from the user's own to-do list.** The board is *agent* work. If the user also tracks their own external actions (sends, clicks, applications) in a task system (Google Tasks, Notion, Todoist), that is a separate surface — don't merge them, or you pollute the one list the user prunes each morning.

**Optional — task ↔ flag pairing.** If the user's external actions live in a task system, an advanced pattern is to pair every such task with a one-line flag in `agents/flags.md`, so the action surfaces at the next session start (via the hook) and gets reconciled against canonical truth. Clear the flag when the task completes. Useful once the volume of "things the user owes" grows; skip it early.

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
- **Done:** closed, what shipped
- **80% done:** in progress, what's left
- **Blocked:** blocked, what's blocking them

The orchestrator reads these before dispatching. No notes = blind dispatch.

## Flags + the session hook

`agents/flags.md` is a short-lived, cross-agent hand-off surface. A flag is a **one-line pointer + a "clear when" condition** — not a memo. Durable content (debriefs, decisions, multi-step context) lives in memory / plan / a prep doc; the flag carries a one-line pointer to it.

- **The hook.** `.claude/hooks/session-flags.sh` (wired as a `UserPromptSubmit` hook in `.claude/settings.json`) injects the whole file into context at the start of every prompt. That is what makes a flag surface without anyone running a command — and it's why the file must stay lean.
- **Delete-on-clear.** When a flag is addressed, delete the line. Git history is the audit trail; don't leave `<!-- cleared -->` comments — the file is injected whole every session, so dead lines are a standing token tax.
- **One flag per agent section.** Each agent owns its own section; don't edit another agent's lines (except to hand them a one-line flag).
- **Size tripwire.** If `flags.md` grows large (say past ~50KB), the next agent to checkout prunes its own section.

## Keeping personal data out of git

This system accumulates real personal data. Decide up front what may be committed and what may not, and enforce it with `.gitignore`:

- **Wall off raw data dumps** — brokerage exports, health records, contact exports with emails/phones, anything with account numbers or secrets. The shipped `.gitignore` has commented example blocks for finance / health / networking data directories; uncomment the ones you use.
- **Commit only derived facts.** The workspace `.md` files should carry the *derived* figure or trend (e.g., "runway ~8 months"), never the raw statement. The raw file stays gitignored.
- **Secrets never touch git.** OAuth tokens, API keys, and service-account files live under `secrets/` (gitignored). Load them from there or from env vars.
- **If you ever make this repo public or share it, remember git *history* carries deleted files too.** Gitignoring a file later does not remove it from earlier commits. Start any shared/public repo with a clean history rather than scrubbing a private one.

## Soft Bridge (optional)

`[SOFT_BRIDGE_BLOCK — only included if recipient opted into soft-bridge pattern at bootstrap. Otherwise this section is removed.]`

If you have a second workspace (e.g., a business workspace separate from this personal one), you can establish a one-way bridge: this workspace's orchestrator reads `[OTHER_WORKSPACE_PATH]/plan.md` at session start to understand cross-context. This is read-only. Never write to the other workspace.

The bridge is one-way to prevent personal data from leaking into the other context. If the other workspace also benefits from this one's context, the user is the bridge — relay directly.

## Quality gates (optional, scale to stakes)

Two patterns worth adopting once you're using this for real decisions and real external sends. Both are optional and scale with stakes — skip them on a two-line scheduling reply.

- **Council review before external sends.** For a load-bearing external message, prep doc, or decision, convene a short panel of advisory perspectives (the `council` skill, `.claude/skills/council/`) to pressure-test the frame before it ships. Capture convergence + dissents, apply the changes, then surface to the user to ratify. Depth scales with stakes.
- **Unknowns pass before building in unfamiliar territory.** Before a substantive build in a domain you or the user don't already command, surface what you don't know first — either a "blindspot pass" (an explicit unknown-unknowns sweep given the user's actual starting point) or an "interview-me" pass (ask one shape-changing question at a time until the deliverable's shape is determined). Naming the gaps before you build beats discovering them downstream when they're expensive.

## Checkout

Every agent runs the checkout playbook on session end. Triggered by phrases like "let's check out," "wrap for the day," "evening close," etc. Deterministic checklist, not agent judgment.

**Canonical playbook:** `.claude/rules/checkout-playbook.md`

## Communication Style

- Be direct. No filler. No sycophancy.
- Concise when the answer is simple. Thorough when it matters.
- End with a next move or a choice. Return agency to the user.
