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
- "Pre-loaded substrate at three altitudes flips polite-completion conversations into advancing ones."

Write to memory file as:
```markdown
**Promotion candidate:** [memory type — feedback / project / user / reference] — [one-line rule]
- **Why:** [reason / incident behind the rule]
- **How to apply:** [when this kicks in]
```

If today produced no promotable lesson, write `**Promotion candidate:** none today.` Don't fabricate lessons to satisfy the step.

### Step 3 — Flag janitor
- Clear addressed flags from your section in `agents/flags.md` (delete the line, OR replace with `<!-- cleared YYYY-MM-DD reason -->` if context valuable for audit)
- Do NOT touch other agents' sections
- Surface stale flags (>7 days unaddressed) in next-day setup (Step 5)

### Step 4 — Routing pass
Every loose-end item from session goes to ONE bucket:

| Item type | Goes to |
|---|---|
| User external action (send / click / submit / call / apply) | **External task list** (your preferred task system) |
| Agent work, durable, >1 session of work | **GH Issue** (with agent + priority label) |
| Cross-session context for next agent session | **Flag** (correct agent section in `agents/flags.md`) |
| Decision / learning / conversation capture | **Memory** (today's daily log; promotable ones flagged in Step 2) |

### Step 5 — Commit check
Run `git status`. For each modified or untracked file YOU OWN, stage + commit atomically:

- **Commit message format:** `[Agent] [Day] YYYY-MM-DD: [what shipped]`
- **One intent per commit.** Split if mixed concerns.
- **Only commit your own lane.** Skip files in other agents' lanes (let them commit their own work).
- **Never auto-push.** Push happens on explicit user call.

### Step 6 — Tomorrow setup
Pull next 24-hour calendar (if you have a calendar integration; otherwise skip). Surface:
- Specific moves queued
- External dependencies (waiting on what from whom)
- Time-sensitive items in the next 7 days

---

## Weekly checkpoint — runs once weekly (~15-20 min)

Pick a fixed day (e.g., Sunday evening or end-of-week).

### Step 7 — External-source reconciliation pass
- Pull calendar next 14 days, compare against `plan.md` "Upcoming Conversations" + `flags.md` scheduled events. Catch divergence.
- Pull email for active-thread states (each Tier-1 thread). Catch silent-vs-replied divergence.
- Pull task list. Reconcile against flag tripwires.
- Update workspace artifacts to match external truth. **External source wins** when a helper exists for it.

### Step 8 — GH issue triage
- Close anything done that wasn't formally closed
- Downgrade priorities that aren't current focus
- Surface stale items (>7 days no progress) — kill, reassign, or do today

### Step 9 — Synthesis agent file health audit (if you have a synthesis agent)
- Every external conversation this week → one synthesis-agent file update (person, company, position log, market intel)
- List any conversation that didn't produce knowledge-base delta. Backfill or note why not promotable.

### Step 10 — Contact hygiene (if Networking is one of your domains)
- Verify last-touch timestamps against email
- Update next-action fields against current state
- Every active contact has either: upcoming calendar event, "next touchpoint" task with due date, or tripwire flag

### Step 11 — Week shape preview for next week
- Calendar pull next 7 days
- Pipeline state preview (active threads + expected moves)
- Surface anything time-sensitive

### Step 12 — Push to origin
- Pre-push hygiene: scan the week's diff for accidentally-committed sensitive content (secrets, gitignore gaps)
- Verify no agents flagged a do-not-push item this week
- Confirm `git status` is clean (no untracked-or-modified items that should have been caught at daily Step 5)
- Push: `git push origin main`

**Failure modes:**
- Sensitive content detected → STOP. Do NOT push. Resolve first.
- Push rejected (origin moved ahead) → fetch + rebase locally first, then push. Never `--force` to main without explicit user ratification.

---

## Failure modes

1. **Low-energy user.** Daily floor Steps 1-3 mandatory (memory write + lesson promotion + flag janitor). Steps 4-6 can defer to next-AM catch-up.
2. **Mid-session interrupt.** Complete in-flight task first, then run checkout. No half-shipped state.
3. **User forgets to trigger.** If user ends without trigger phrase, agent runs abbreviated checkout (Steps 1 + 3 only) anyway — captures memory + flag state.
4. **Weekly checkpoint missed.** Defer to next day, not skipped. Surface explicit `[CHECKPOINT DEFERRED]` flag.

---

## Compounding mechanisms

The playbook builds capability across sessions through four explicit gates:

1. **Lesson promotion (Step 2)** → `MEMORY.md` curated memory grows weekly. Without this, daily memory is sediment, not capability.
2. **Synthesis agent file health audit (Step 9)** → knowledge graph compounds. Without this, conversation insights leak.
3. **Routing pass (Step 4)** → no loose ends in agent memory. Every item lands somewhere it can be acted on.
4. **External-source reconciliation (Step 7)** → workspace artifacts stay aligned with external truth. Without this, drift accumulates and you reason from stale text.
