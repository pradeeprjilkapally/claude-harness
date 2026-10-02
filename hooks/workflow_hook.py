#!/usr/bin/env python3
"""Global entry point for the orchestrated task workflow.

Installed in ~/.claude/settings.json so the workflow fires in every harnessed
project, not only the one that happens to have repo-level settings. Self-scopes
via hooklib.repo_root(), which requires a .harness.json marker at the repo root,
and no-ops in every repo that has not opted in.

The real logic lives in each repo's own scripts/ so a repo can evolve it
independently; this only routes to it. A repo without those scripts is silently
skipped, so seeding a new repo is never a prerequisite.

Modes (PostToolUse on Write|Edit):
    task-updated  -> scripts/workflow_state.py on-task-updated   (task.md written)
    plan-branch   -> scripts/plan_branch.py --hook               (plans/*.md written)
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib  # noqa: E402

ROUTES = {
    'task-updated': ('scripts/workflow_state.py', ['on-task-updated']),
    'plan-branch': ('scripts/plan_branch.py', ['--hook']),
}


def repo_owns_hook(root, script_name):
    """True if the repo's own .claude/settings.json already runs this script.

    Both levels are installed on purpose (repo settings are the per-project
    source of truth, global covers repos that have none). Without this check
    both fire and the agent gets every directive twice.
    """
    try:
        with open(os.path.join(root, '.claude', 'settings.json')) as f:
            return script_name in f.read()
    except OSError:
        return False


def written_path(data):
    resp = data.get('tool_response') or {}
    inp = data.get('tool_input') or {}
    return resp.get('filePath') or inp.get('file_path') or ''


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    route = ROUTES.get(mode)
    if not route:
        return 0

    data = hooklib.read_payload()
    root = hooklib.repo_root(data)
    if not root:
        return 0                                   # harness not installed here — no-op

    path = written_path(data)
    if mode == 'task-updated' and os.path.basename(path) != 'task.md':
        return 0
    if mode == 'plan-branch' and '/plans/' not in path.replace(os.sep, '/'):
        return 0

    script, args = route
    target = os.path.join(root, script)
    if not os.path.exists(target):
        return 0                                   # repo hasn't adopted it yet
    if repo_owns_hook(root, os.path.basename(script)):
        return 0                                   # repo fires it — don't double up

    stdin = '' if mode == 'task-updated' else __import__('json').dumps(data)
    try:
        r = subprocess.run([sys.executable, target, *args], cwd=root, input=stdin,
                           capture_output=True, text=True, timeout=20)
    except Exception:
        return 0
    if r.stdout.strip():
        print(r.stdout.strip())
    return 0


if __name__ == '__main__':
    sys.exit(main())
