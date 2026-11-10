#!/usr/bin/env bash
#
# Install the agent harness into a repository.
#
#   ./install.sh /path/to/repo [--gh-repo owner/name] [--owner "Your Name"]
#                              [--remote origin] [--data-dir mydata]
#                              [--data-dir-env APP_DATA_DIR]
#                              [--dry-run]
#
# Idempotent: re-run it to upgrade a repo to this harness version. Files the repo
# owns (task.md, action_items.md, and the other management docs) are seeded once
# and never overwritten, so re-running cannot destroy your task history.
#
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(cat "$HARNESS_DIR/VERSION")"
RENDER="$HARNESS_DIR/scripts/_render.py"

TARGET=""; GH_REPO=""; DATA_DIR="mydata"; DATA_DIR_ENV=""; OWNER="the owner"; REMOTE="origin"; DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --gh-repo)      GH_REPO="$2"; shift 2 ;;
    --owner)        OWNER="$2"; shift 2 ;;
    --remote)       REMOTE="$2"; shift 2 ;;
    --data-dir)     DATA_DIR="$2"; shift 2 ;;
    --data-dir-env) DATA_DIR_ENV="$2"; shift 2 ;;
    --dry-run)      DRY=1; shift ;;
    -h|--help)      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)              TARGET="$1"; shift ;;
  esac
done

[ -n "$TARGET" ] || { echo "usage: ./install.sh /path/to/repo [options]" >&2; exit 2; }
[ -d "$TARGET" ] || { echo "not a directory: $TARGET" >&2; exit 2; }
TARGET="$(cd "$TARGET" && pwd)"

git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1 \
  || { echo "not a git repository: $TARGET" >&2; exit 2; }

# The repo's own git root, so installing from a subdirectory still lands correctly.
TARGET="$(git -C "$TARGET" rev-parse --show-toplevel)"

say() { printf '  %s\n' "$*"; }
run() { if [ "$DRY" = 1 ]; then say "would: $*"; else "$@"; fi; }

# Render the {{TOKEN}} placeholders in one file. The harness keeps a single
# source for everything and substitutes at install time, so the Claude and Codex
# skill sets cannot drift apart the way two hand-synced copies did.
render() {
  [ "$DRY" = 1 ] && return 0
  python3 "$RENDER" "$1" "${2:-CLAUDE.md}" "${3:-Claude}" "$OWNER" "$TARGET" "${GH_REPO:-owner/name}" "$REMOTE"
}

echo "Harness $VERSION -> $TARGET"
[ "$DRY" = 1 ] && echo "  (dry run — nothing will be written)"

# --- skills: one source, rendered per agent ---------------------------------
render_skills() {
  local dest="$1" agent_doc="$2" agent_name="$3"
  if [ "$DRY" = 1 ]; then say "would render skills -> $dest"; return 0; fi
  rm -rf "${TARGET:?}/$dest"
  mkdir -p "$(dirname "$TARGET/$dest")"
  cp -R "$HARNESS_DIR/skills" "$TARGET/$dest"
  find "$TARGET/$dest" -name '*.md' -print0 | while IFS= read -r -d '' f; do
    python3 "$RENDER" "$f" "$agent_doc" "$agent_name" "$OWNER" "$TARGET" "${GH_REPO:-owner/name}" "$REMOTE"
  done
  say "skills -> $dest ($(find "$TARGET/$dest" -name SKILL.md | wc -l | tr -d ' ') skills)"
}

render_skills ".claude/skills" "CLAUDE.md" "Claude"
render_skills ".agents/skills" "AGENTS.md" "Codex"

# --- scripts ----------------------------------------------------------------
run mkdir -p "$TARGET/scripts"
for f in "$HARNESS_DIR"/scripts/*.py; do
  base="$(basename "$f")"
  case "$base" in _render.py|_marker.py|_merge_settings.py) continue ;; esac  # installer-only
  run cp "$f" "$TARGET/scripts/$base"
  render "$TARGET/scripts/$base"
done
say "scripts -> scripts/"

# --- management docs: seed once, never clobber ------------------------------
seeded=0; kept=0
for f in "$HARNESS_DIR"/templates/root/*; do
  base="$(basename "$f")"
  if [ -e "$TARGET/$base" ]; then
    kept=$((kept+1))
  else
    run cp "$f" "$TARGET/$base"; render "$TARGET/$base"; seeded=$((seeded+1))
  fi
done
run mkdir -p "$TARGET/decisions" "$TARGET/plans"
say "management docs: $seeded seeded, $kept left untouched (yours)"

# --- workflow reference -----------------------------------------------------
for f in WORKFLOW.md WORKFLOW_FULL_ORCHESTRATION.md; do
  if [ ! -e "$TARGET/$f" ]; then run cp "$HARNESS_DIR/docs/$f" "$TARGET/$f"; render "$TARGET/$f"; fi
done
say "workflow reference in place"

# --- repo-level hook wiring -------------------------------------------------
# These fire per-repo (the session-start task review, the Stop workflow guard,
# the anti-slop reminder, the task.md -> RED-check trigger). Distinct from the
# machine-wide hooks install-hooks.sh wires; both layers are needed.
if [ "$DRY" = 0 ]; then
  python3 "$HARNESS_DIR/scripts/_merge_settings.py" \
    "$TARGET/.claude/settings.json" "$HARNESS_DIR/templates/claude-settings.json"
else
  say "would wire repo-level hooks into .claude/settings.json"
fi

# --- the pre-push gate ------------------------------------------------------
# Without this the guard scripts are inert files: nothing blocks a push that has
# no task entry or a red suite.
HOOK_DIR="$(git -C "$TARGET" rev-parse --git-path hooks)"
if [ "$DRY" = 0 ]; then
  mkdir -p "$HOOK_DIR"
  if [ -e "$HOOK_DIR/pre-push" ] && ! grep -q "harness" "$HOOK_DIR/pre-push" 2>/dev/null; then
    cp "$HOOK_DIR/pre-push" "$HOOK_DIR/pre-push.before-harness"
    say "existing pre-push backed up to pre-push.before-harness"
  fi
  cp "$HARNESS_DIR/templates/githooks/pre-push" "$HOOK_DIR/pre-push"
  chmod +x "$HOOK_DIR/pre-push"
fi
say "pre-push gate installed"

# --- branch-flow CI guard ---------------------------------------------------
if [ ! -e "$TARGET/.github/workflows/pr-flow.yml" ]; then
  run mkdir -p "$TARGET/.github/workflows"
  run cp "$HARNESS_DIR/templates/workflows/pr-flow.yml" "$TARGET/.github/workflows/pr-flow.yml"
  say "branch-flow CI guard -> .github/workflows/pr-flow.yml"
else
  say "pr-flow.yml already present — left untouched"
fi

# --- gitignore --------------------------------------------------------------
# HANDOFF.md and the state files are session scratch; committing them is noise.
if [ "$DRY" = 0 ] && ! grep -q "agent harness" "$TARGET/.gitignore" 2>/dev/null; then
  printf '\n' >> "$TARGET/.gitignore"
  cat "$HARNESS_DIR/templates/gitignore-fragment" >> "$TARGET/.gitignore"
  say "gitignore entries appended"
fi

# --- the marker that opts this repo in --------------------------------------
# hooks/hooklib.py keys off this file. No marker, no harness — which is what lets
# one set of globally-installed hooks stay silent in every other repo.
if [ "$DRY" = 0 ]; then
  python3 "$HARNESS_DIR/scripts/_marker.py" \
    "$TARGET/.harness.json" "$VERSION" "$GH_REPO" "$DATA_DIR" "$DATA_DIR_ENV" "$REMOTE" "$OWNER"
fi
say "marker -> .harness.json (version $VERSION${GH_REPO:+, gh_repo $GH_REPO})"

echo
echo "Installed. Next:"
echo "  1. ./install-hooks.sh          # once per machine, not per repo"
[ -n "$GH_REPO" ] || echo "  2. set \"gh_repo\" in $TARGET/.harness.json so the PR guards query the right repo"
echo "  3. open the repo in your agent and type 'jarvis' to confirm the skills load"
