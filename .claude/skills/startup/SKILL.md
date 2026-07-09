---
name: startup
description: "Agent Startup Routine"
---

# Agent Startup Routine

Run this at the start of every session — new or resumed. Type `/startup` to trigger.

## Steps

Execute ALL of these steps in order. Do not skip any. Report what you find after completing them.

1. **Read your agent identity** from `.claude/agents/<name>.md` (where `<name>` is the active agent)
2. **Read `plan.md`** for current priorities
3. **Read today's memory file** (`memory/YYYY-MM-DD.md` using today's date)
4. **Read yesterday's memory file** if it exists
5. **Check your task board:**
   - If you use GitHub Issues:
     ```bash
     gh issue list --repo <your-repo> --label "agent:<name>" --state open
     ```
   - If you use the file-based board: read `agents/backlog.md`.
6. **Check for dispatched tasks from the orchestrator** — look in today's memory file for an "Agent Dispatch" section

### Orchestrator-specific additions
If you are the `<orchestrator>` agent, also run:
- Read its commitments and decisions logs, if it keeps them
- Pull the full task board across all agents (not just your own section), e.g. `gh issue list --repo <your-repo> --state open`
- Run canonical verification against your source-of-truth tools (calendar / mail / tasks) for anything the workspace text asserts about state

### Domain-agent additions
If you are a `<domain agent>`, also read your own domain state files (the trackers/logs your domain owns).

## After completing all steps

Report a summary:
- **Dashboard** (orchestrator only): status across your domains
- **Your dispatch:** what the orchestrator assigned you (or "no dispatch found")
- **Board:** how many items in your queue, any due today
- **Context:** key items from memory files

Then ask: "Ready to start. Work the dispatch, or different priority?"
