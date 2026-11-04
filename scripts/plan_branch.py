#!/usr/bin/env python3
"""Branch-first FALLBACK: create the feature branch if it was not cut first.

The lean workflow cuts feature/<task-id>-<slug> off develop FIRST — before task.md
is written (WORKFLOW.md §2; the branch-first order in scripts/workflow_state.py's
STAGES). This hook is only the safety-net for the case where that was skipped:
wired as a PostToolUse hook on Write/Edit, when a `plans/<slug>_<date>_plan.md`
file is written it ensures a feature branch exists so the build stage never edits
develop. When branch-first already happened it no-ops (we are already on it).

Deliberately conservative — it declines rather than surprises:
  * already on the target branch, or it exists  -> no-op, exit 0
  * staged changes in the index                 -> declines (a checkout would
                                                    carry someone else's work)
  * no develop ref                              -> declines with a message

Usage:  plan_branch.py <plan-file>        (hook passes the written path)
        plan_branch.py --hook             (reads the hook JSON payload on stdin)
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_config

PLAN_RE = re.compile(r'plans/(?P<slug>[^/]+?)_(?P<date>\d{4}-\d{2}-\d{2})_plan\.md$')


def git(*args, cwd=None):
    r = subprocess.run(['git', *args], capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def active_task_id(task_md_text):
    m = re.search(r'^Task:\s+(\d{2}-\d{6})', task_md_text, re.M)
    return m.group(1) if m else None


def branch_name(task_id, slug):
    clean = re.sub(r'[^a-z0-9]+', '-', slug.lower()).strip('-')
    return f'feature/{task_id}-{clean}'


def develop_ref():
    """Prefer a local develop, else the remote-tracking ref.

    The remote comes from the repo's own marker rather than a rendered
    placeholder: a plugin-delivered script is shared by every repo, so it cannot
    carry one repo's remote baked in.
    """
    for ref in ('develop', f'{harness_config.remote()}/develop'):
        if git('rev-parse', '--verify', '--quiet', ref)[0] == 0:
            return ref
    return None


def say(msg):
    print(json.dumps({'systemMessage': msg}))


def run(plan_path):
    m = PLAN_RE.search(plan_path.replace(os.sep, '/'))
    if not m:
        return 0                                  # not a plan file — nothing to do

    try:
        task_id = active_task_id(open('task.md').read())
    except OSError:
        return 0
    if not task_id:
        say('plan_branch: no active `Task: NN-DDMMYY` in task.md — branch not created.')
        return 0

    target = branch_name(task_id, m.group('slug'))
    current = git('rev-parse', '--abbrev-ref', 'HEAD')[1]
    if current == target:
        return 0
    if git('rev-parse', '--verify', '--quiet', target)[0] == 0:
        say(f'plan_branch: branch {target} already exists — checkout skipped, '
            f'still on {current}.')
        return 0

    staged = git('diff', '--cached', '--name-only')[1]
    if staged:
        say(f'plan_branch: staged changes present — not switching branches. '
            f'Create {target} yourself once the index is clean.')
        return 0

    base = develop_ref()
    if not base:
        say(f'plan_branch: no develop ref found — create {target} manually.')
        return 0

    code, _, err = git('checkout', '-b', target, base)
    if code != 0:
        say(f'plan_branch: could not create {target} off {base}: {err}')
        return 0
    say(f'plan_branch (fallback — branch-first was skipped): created and checked '
        f'out {target} off {base} for the plan {os.path.basename(plan_path)}. '
        f'Build the slices on this branch.')
    return 0


def main(argv):
    if len(argv) > 1 and argv[1] == '--hook':
        try:
            data = json.loads(sys.stdin.read() or '{}')
        except ValueError:
            return 0
        path = (data.get('tool_response', {}) or {}).get('filePath') \
            or (data.get('tool_input', {}) or {}).get('file_path') or ''
        return run(path)
    if len(argv) < 2:
        print(__doc__)
        return 2
    return run(argv[1])


if __name__ == '__main__':
    sys.exit(main(sys.argv))
