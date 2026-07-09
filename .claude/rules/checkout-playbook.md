# Checkout Playbook

Workspace-wide rule, applies to every agent. Mandatory at session end. Deterministic checklist that fires on trigger phrases, not agent judgment.

## Trigger phrases (any of)

When the user uses any of these, the active agent immediately starts checkout (no confirmation needed):

- "let's check out"
- "wrap for the day"
- "evening close"
- "shut down"
- "let's call it"
- "done for today"
- "good night"
- "session end"
- "wrap it up"
- "log off"

---

## Daily floor — every session, mandatory (~3-5 min)

### Step 1 — Memory write
Append session block to today's `memory/YYYY-MM-DD.md` (create if missing):
```markdown
## [Agent] [AM/PM] — [topic]
- Done: [shipped artifacts, decisions, actions taken]
- 80% done: [in-progress items, what's left]
- Blocked: [items + blocker + who/what unblocks]
- User time this session: [estimate to nearest 5-10 min]
```

### Step 2 — Lesson promotion
Single question: **"One promotable lesson from today?"**

A promotable lesson is a transferable rule, not a what-happened note. Examples:
- "When the user prescribes an agent label, pressure-test it against domain ownership before executing."
- "Verify send-state against the live source before reporting it; a staged draft reads as sent if you trust the flag text."

Write to memory file as:
```markdown
**Promotion candidate:** [memory type — feedback / project / user / reference] — [one-line rule]
- **Why:** [reason / incident behind the rule]
- **How to apply:** [when this kicks in]
```

If today produced no promotable lesson, write `**Promotion candidate:** none today.` Don't fabricate lessons to satisfy the step.

### Step 3 — Flag janitor

**Canonical-verification gate (do this first).** Before you clear any flag that asserts a send / reply / draft / received state — OR report that state in the checkout summary — verify it against the live source (email, calendar, task list) if a helper exists, and let canonical override the flag text. Checkout is exactly where a stale "still pending" flag gets wrongly cleared, or a still-staged draft gets wrongly reported as "sent." A send-flag clears ONLY on a confirmed sent hit; still a draft, or no hit → the flag stays and the summary says "staged, not sent." (No integrations yet? This gate is dormant — adopt it the moment you add an email/calendar/task helper.)

Then:
- **Clear addressed flags by deleting the line.** Git history is the audit trail; don't leave `<!-- cleared -->` comments — `flags.md` is injected whole at every session start (via the `session-flags` hook), so dead lines are a standing token tax.
- One-line flags only. If a flag has grown into a multi-paragraph memo, move the body to memory / plan / a prep doc and leave a one-line pointer.
- Do NOT touch other agents' sections (except to hand them a one-line flag).
- Surface stale flags (>7 days unaddressed) in next-day setup (Step 6).
- **Size tripwire:** if `flags.md` is large (say past ~50KB), prune your own section as part of checkout.

### Step 4 — Routing pass
Every loose-end item from session goes to ONE bucket:

| Item type | Goes to |
|---|---|
| User external action (send / click / submit / call / apply) | **The user's task list** (your preferred task system) |
| Agent work, durable, >1 session of work | **Task board** (GitHub Issue or `agents/backlog.md`, with agent + priority) |
| Cross-session context for next agent session | **Flag** (correct agent section in `agents/flags.md`) |
| Decision / learning / conversation capture | **Memory** (today's daily log; promotable ones flagged in Step 2) |

**Optional — task ↔ flag pairing.** If you adopted the pairing pattern (workspace-core → Task Board), every user-action task also gets a one-line paired flag here, cleared in Step 3 when the task completes.

### Step 5 — Commit check
Run `git status`. For each modified or untracked file YOU OWN, stage + commit atomically:

- **Commit message format:** `[Agent] [Day] YYYY-MM-DD: [what shipped]`
- **One intent per commit.** Split if mixed concerns.
- **Only commit your own lane.** Skip files in other agents' lanes (let them commit their own work). Skip do-not-commit files (secrets, gitignored data exports).
- **Push policy — pick one for your setup:**
  - **Solo / single machine (default):** never auto-push; push on the user's explicit call, or at the weekly checkpoint (Step 12).
  - **Shared branch (multiple machines / clients / bots write the same branch):** push every checkout so divergence stays near zero. A safe helper (rebase-onto-origin → push, retry on a moving origin, **fail loud on conflict, never force**) is the right tool; refuse to push on a dirty tree that isn't yours, and reconcile conflicts by hand. Never `git push --force` to the main branch without explicit user ratification.

### Step 6 — Tomorrow setup
Pull next 24-hour calendar (if you have a calendar integration; otherwise skip). Surface:
- Specific moves queued
- External dependencies (waiting on what from whom)
- Time-sensitive items in the next 7 days

---

## Active-pipeline trigger — adds one step (when you have several live external threads)

### Step 6.5 — Response-needed sweep (optional)
If you have an email integration and several live external threads, run a stateful sweep for NEW inbound emails needing a response (past a stored watermark, excluding automation/newsletters, skipping threads whose last message is from you). Surface a short "Needs response" block — sender · subject · one-line ask · age — at the end of the brief. Decision-ready pointers, not summaries; don't auto-draft. Under-surface over over-surface: a noisy sweep dies of distrust.

---

## Weekly checkpoint — runs once weekly (~15-20 min)

Pick a fixed day (e.g., Sunday evening or end-of-week).

### Step 7 — External-source reconciliation pass
- Pull calendar next 14 days, compare against `plan.md` + `flags.md` scheduled events. Catch divergence.
- Pull email for active-thread states. Catch silent-vs-replied divergence.
- Pull task list. Reconcile against flag tripwires.
- Update workspace artifacts to match external truth. **External source wins** when a helper exists for it.

### Step 8 — Task board triage
- Close anything done that wasn't formally closed
- Downgrade priorities that aren't current focus
- Surface stale items (>7 days no progress) — kill, reassign, or do today
- (File-based board: prune the `## Archive` section.)

### Step 9 — Synthesis agent file health audit (if you have a synthesis agent)
- Every external conversation this week → one synthesis-agent file update (person, company, position log, market intel)
- List any conversation that didn't produce a knowledge-base delta. Backfill or note why not promotable.

### Step 10 — Contact hygiene (if Networking is one of your domains)
- Verify last-touch timestamps against email
- Update next-action fields against current state
- Every active contact has either: an upcoming calendar event, a "next touchpoint" task with a due date, or a tripwire flag

### Step 11 — Week shape preview for next week
- Calendar pull next 7 days
- Pipeline state preview (active threads + expected moves)
- Surface anything time-sensitive

### Step 12 — Push to origin
- Pre-push hygiene: scan the week's diff (`git log origin/main..HEAD --stat`) for accidentally-committed sensitive content (secrets, gitignore gaps, data exports)
- Verify no agents flagged a do-not-push item this week
- Confirm `git status` is clean
- Push: `git push origin main`  (skip if you already push every checkout on a shared branch — this step is then just the hygiene scan)

**Failure modes:**
- Sensitive content detected → STOP. Do NOT push. Resolve first (and if it's already in history, that history needs scrubbing before any share/public step).
- Push rejected (origin moved ahead) → fetch + rebase locally first, then push. Never `--force` to the main branch without explicit user ratification.

---

## Failure modes

1. **Low-energy user.** Daily floor Steps 1-3 mandatory (memory write + lesson promotion + flag janitor). Steps 4-6 can defer to next-AM catch-up.
2. **Mid-session interrupt.** Complete in-flight task first, then run checkout. No half-shipped state.
3. **User forgets to trigger.** If the user ends without a trigger phrase, the agent runs an abbreviated checkout (Steps 1 + 3 only) anyway — captures memory + flag state.
4. **Weekly checkpoint missed.** Defer to next day, not skipped. Surface an explicit `[CHECKPOINT DEFERRED]` flag.

---

## Compounding mechanisms

The playbook builds capability across sessions through explicit gates:

1. **Lesson promotion (Step 2)** → `MEMORY.md` curated memory grows weekly. Without this, daily memory is sediment, not capability.
2. **Canonical-verification gate (Step 3)** → the workspace never drifts from external truth at the exact moment a flag would otherwise be wrongly cleared.
3. **Routing pass (Step 4)** → no loose ends in agent memory. Every item lands somewhere it can be acted on.
4. **Synthesis agent file health audit (Step 9)** → knowledge graph compounds. Without this, conversation insights leak.
5. **External-source reconciliation (Step 7)** → workspace artifacts stay aligned with external truth. Without this, drift accumulates and you reason from stale text.
