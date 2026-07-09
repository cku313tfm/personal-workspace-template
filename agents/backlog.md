# Agent Task Board

The file-based task board (one of the two board options — see `.claude/rules/workspace-core.md` → Agent Task Board Rules). Durable, multi-session **agent** work. Keep it distinct from the user's own external-action to-do list.

**Format:** one line per item — `#ref · priority · owner · one-liner · (date added)`. Priority = high / medium / low. Each agent owns its own section; don't edit another agent's lines.

**Lifecycle:** done items move to `## Archive` with a one-line outcome. Prune Archive at the weekly checkpoint.

> If you chose GitHub Issues as your board at bootstrap instead, you can delete this file.

---

## [ORCHESTRATOR_NAME]

**Active**

**Backlog**

<!-- The bootstrap agent adds one `## <Agent>` section per elected agent. Replace this comment. -->

## Archive
