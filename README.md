# Personal Workspace Template

A multi-agent personal operations system that lives in Claude Code. Remembers across sessions, coordinates work across multiple personal domains via dispatched agents, holds canonical sources of truth, and compounds capability over time instead of restarting every conversation.

Modeled on a working system that has been running and compounding for months across career, finance, networking, health, and synthesis domains.

## Who this is for

Build this if you:
- Already feel the pain of "I told you that last week" with whatever AI tool you use
- Have at least one domain where slippage between sessions costs you real money or relationships
- Want one persistent system to coordinate multiple personal domains rather than five separate AI threads that never talk to each other
- Will invest ~30 min to bootstrap + roughly 30 min/week on maintenance for the first 4 weeks until the system pays itself back

Don't build this if you:
- Just want a chat assistant for occasional questions
- Are looking for a project-management tool (Linear, Notion, Asana solve a different problem better)
- Want to outsource judgment rather than augment it

## Quick start (30 minutes)

### Prerequisites

- A GitHub account
- Claude Code installed ([install instructions](https://docs.claude.com/en/docs/claude-code/quickstart))
- `gh` CLI installed and authenticated (`gh auth login`)
- `git` installed
- Ability to open files in an editor (any will do — VS Code, Cursor, vim, etc.)

### Step 1 — Clone

```bash
git clone https://github.com/<your-username>/personal-workspace-template.git my-workspace
cd my-workspace
```

Or use the GitHub "Use this template" button if available.

### Step 2 — Create your private repo (for agent tasks)

```bash
gh repo create <your-username>/my-workspace --private
git remote set-url origin https://github.com/<your-username>/my-workspace.git
```

Note your repo path (`<your-username>/my-workspace`) — you'll need it during bootstrap.

### Step 3 — Run the bootstrap agent

Open this directory in Claude Code, then type:

```
@bootstrap
```

The bootstrap agent will ask you 5-7 questions (your name, what to call your orchestrator, which domains you want, optional synthesis agent, GitHub repo path, etc.), then customize all the template files for you. Takes ~5-10 min of conversation.

After bootstrap completes, the `@bootstrap` agent self-deletes. You're left with a working personalized workspace.

### Step 4 — Start your first real session

Open a new Claude Code conversation and summon your orchestrator (whatever you named it):

```
@<orchestrator-name>
```

The orchestrator will run its mandatory startup (read plan, memory, your decisions, etc.), then ask what you're working on.

Tell it your top current priority. It writes to `plan.md`. From here, you're operating.

## What you get out of the box (MVP)

- **Orchestrator agent** — coordinates domains, runs morning briefs, dispatches work
- **1-4 domain operator agents** — each owns a domain end-to-end (Finance / Networking / Health / Career / Study / Side-business / Creative / Family — you pick)
- **Optional synthesis agent** — compounding knowledge base layer for capturing meeting substrate, building theses, externalizing thinking
- **Workspace rules** — operating discipline (summon protocol, approval gates, memory conventions, dispatch protocol)
- **Checkout playbook** — deterministic session-end discipline (memory write, lesson promotion, flag janitor, routing pass, commit check)
- **GitHub Issues task board** — agent tasks tracked as labeled issues
- **Memory persistence** — daily logs, long-term curated memory, cross-agent flags

## What you don't get yet (upgrade paths)

The MVP is intentionally lean — get value within 30 min, add complexity only when you feel the pain.

Upgrade paths (refer to `docs/build-from-scratch.md` for the patterns):

- **Google integrations** (Calendar / Gmail / Tasks via Python helpers) — when you want your orchestrator to surface calendar conflicts, watch email thread state, manage external tasks
- **Intake pipeline** (newsletters → daily must-reads) — when you have a domain mastery program and want signal-routed reading instead of inbox scan
- **Synthesis skill** (`/synthesize-intake`) — when intake has accumulated and you need on-demand "what does this week mean for X" capability
- **Networking SQLite layer** — when you have 1000+ LinkedIn connections and want bulk "who do I know at X" queries
- **Council skill** — when you face decisions that benefit from multiple expert voices
- **Soft bridge** — when you have a second workspace (business / family) that benefits from one-way context sharing

Each upgrade is documented and optional. The MVP works without any of them.

## Architecture reference

Want to understand WHY each piece exists? Read `docs/build-from-scratch.md`. It's the long-form architecture guide covering:

- The pattern in one paragraph
- 10-step manual build (the bootstrap automates this; the guide explains why)
- Three reusable agent blueprints
- Best practices learned the hard way
- Anti-patterns to avoid

The guide is 1000+ lines of depth. Read it after you have a working bootstrap, not before — easier to learn from a running system than from text.

## Maintenance discipline (after bootstrap)

Read `.claude/rules/checkout-playbook.md`. Every session ends with the playbook firing. Daily floor (~5 min). Weekly checkpoint (~15-20 min on whatever day you pick).

The playbook is what produces the compounding. Without it, daily memory is sediment, not capability.

## Support / questions / feedback

This template is provided as-is. The reference workspace it's modeled on is private; this template is the share-out artifact.

If you build something on this and want to share what worked / didn't / what you'd change, open an issue or PR — improvements that make the template more useful to others are welcomed.

## License

MIT (or your preferred OSS license — update before publishing).
