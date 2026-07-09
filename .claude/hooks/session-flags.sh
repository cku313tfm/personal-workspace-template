#!/bin/bash
# UserPromptSubmit hook.
# Injects any pending flags from agents/flags.md into the hook's additionalContext,
# alongside the standard startup reminder.
#
# Wire this in .claude/settings.json as a UserPromptSubmit hook so it fires on
# every prompt, e.g.:
#   {
#     "hooks": {
#       "UserPromptSubmit": [
#         { "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-flags.sh" } ] }
#       ]
#     }
#   }
#
# Convention: flags are lines starting with "- YYYY-" in agents/flags.md.

set -euo pipefail

# Derive the repo root; never hardcode a home dir.
WORKSPACE="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
FLAGS_FILE="$WORKSPACE/agents/flags.md"

STARTUP_REMINDER="STARTUP REMINDER: If you have not already run your mandatory startup routine this session, you MUST do it NOW before responding. Read your agent identity from .claude/agents/<name>.md, read plan.md, read today and yesterday memory files, check your task board (GitHub Issues OR agents/backlog.md, whichever this workspace uses), and check for dispatched tasks from the orchestrator agent. Report what you found. Do not skip this on resume sessions."

# Check for any dated flag lines anywhere in the file.
HAS_FLAGS=""
FLAGS_CONTENT=""
if [ -f "$FLAGS_FILE" ]; then
  HAS_FLAGS=$(grep -E "^- [0-9]{4}-" "$FLAGS_FILE" 2>/dev/null | head -n 1 || true)
  if [ -n "$HAS_FLAGS" ]; then
    FLAGS_CONTENT=$(cat "$FLAGS_FILE")
  fi
fi

if [ -n "$HAS_FLAGS" ]; then
  CONTEXT="PENDING FLAGS (from agents/flags.md) — address items under your agent's section BEFORE other work. After completing each, remove the line from agents/flags.md.

$FLAGS_CONTENT

---

$STARTUP_REMINDER"
else
  CONTEXT="$STARTUP_REMINDER"
fi

# Use python3 for safe JSON encoding (avoids shell-escaping issues with quotes/newlines).
python3 -c "
import json, sys
ctx = sys.argv[1]
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': ctx}}))
" "$CONTEXT"
