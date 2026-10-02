#!/usr/bin/env bash
#
# Install the harness hooks into ~/.claude/. Run ONCE PER MACHINE, not per repo.
#
# The hooks are global on purpose: both global and repo-level hooks fire, so
# duplicating file-appending logic in each repo would double every log entry.
# They stay inert in repos without a .harness.json marker, which is what makes
# one global install safe across every project on the machine.
#
#   ./install-hooks.sh [--dry-run]
#
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1

CLAUDE_HOME="$HOME/.claude"
HOOKS="$CLAUDE_HOME/hooks"
SETTINGS="$CLAUDE_HOME/settings.json"

say() { printf '  %s\n' "$*"; }

echo "Harness hooks -> $HOOKS"
[ "$DRY" = 1 ] && echo "  (dry run — nothing will be written)"

if [ "$DRY" = 0 ]; then
  mkdir -p "$HOOKS"
  for f in "$HARNESS_DIR"/hooks/*.py; do cp "$f" "$HOOKS/$(basename "$f")"; done
fi
say "copied $(ls "$HARNESS_DIR"/hooks/*.py | wc -l | tr -d ' ') hook files"

# Wire the hooks into settings.json without disturbing anything already there.
# A backup is written first: this edits a file the user owns and may have
# customised well beyond the harness.
if [ "$DRY" = 0 ]; then
  [ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.harness-backup"
  python3 - "$SETTINGS" <<'PY'
import json, os, sys
path = sys.argv[1]
cfg = {}
if os.path.exists(path):
    try:
        with open(path) as f: cfg = json.load(f)
    except Exception:
        print("  settings.json is not valid JSON — not touching it"); sys.exit(1)

WANT = {
    "PostToolUse": [
        "python3 ~/.claude/hooks/log_commit.py 2>/dev/null || true",
        "python3 ~/.claude/hooks/memory_mirror.py 2>/dev/null || true",
        "python3 ~/.claude/hooks/tooling_decision.py snapshot 2>/dev/null || true",
        "python3 ~/.claude/hooks/tooling_decision.py nudge 2>/dev/null || true",
        "python3 ~/.claude/hooks/workflow_hook.py task-updated 2>/dev/null || true",
        "python3 ~/.claude/hooks/workflow_hook.py plan-branch 2>/dev/null || true",
    ],
    "SessionStart": [
        "python3 ~/.claude/hooks/session_handoff.py start 2>/dev/null || true",
        "python3 ~/.claude/hooks/tooling_decision.py snapshot 2>/dev/null || true",
    ],
    "SessionEnd": [
        "python3 ~/.claude/hooks/session_handoff.py end 2>/dev/null || true",
    ],
}

hooks = cfg.setdefault("hooks", {})
added = 0
for event, commands in WANT.items():
    matchers = hooks.setdefault(event, [])
    existing = {h.get("command", "")
                for m in matchers for h in m.get("hooks", [])}
    missing = [c for c in commands if c not in existing]
    if missing:
        matchers.append({"hooks": [{"type": "command", "command": c} for c in missing]})
        added += len(missing)

with open(path, "w") as f:
    json.dump(cfg, f, indent=2); f.write("\n")
print(f"  wired {added} hook command(s); existing entries left untouched")
PY
fi

echo
echo "Done. The hooks no-op in any repo without a .harness.json marker."
echo "Restart your agent session (or open /hooks) so the new settings load."
