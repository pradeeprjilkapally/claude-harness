#!/usr/bin/env python3
"""Report the real merge outcome of a task's branch, for the Outcome: field.

A task is finished when its PR is merged, the work is explicitly abandoned, or
the owner takes it back. `Status: complete` records only that the build is done,
so a repo that stops there drifts: the task sits at "complete — ship pending"
and nobody knows whether it ever landed. This script answers that one question
from the only authority that has it — the forge.

    check_merged.py                 # every active task awaiting an outcome
    check_merged.py <NN-DDMMYY>     # one task
    check_merged.py --branch <name> # one branch

It REPORTS; it never edits task.md. Writing the Outcome line is a decision, and
the `deploy-model` skill makes it with the owner. Fails open: when `gh` is
missing, unauthed, or offline, every answer is `unknown` and the exit code stays
0, so a tooling outage can never look like an abandoned task.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_config
import workflow_state

_GH_REPO = harness_config.gh_repo()


def _gh(*args, timeout=15):
    """Run gh with the configured --repo, returning stdout or None on any failure.

    The explicit slug matters where `origin` is a read-only upstream fork:
    without it `gh` queries the wrong repository and reports no PRs at all.
    """
    cmd = ['gh', *args[:2]] + (['--repo', _GH_REPO] if _GH_REPO else []) + list(args[2:])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return None
    return r.stdout if r.returncode == 0 else None


def branches_for(task_id):
    """Local and remote branch names carrying this task id."""
    try:
        r = subprocess.run(['git', 'branch', '--all', '--format=%(refname:short)'],
                           capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    if r.returncode != 0:
        return []
    names = [n.strip() for n in r.stdout.splitlines() if task_id in n]
    seen, out = set(), []
    for n in names:                        # origin/feature/x and feature/x are one branch
        bare = n.split('/', 1)[1] if n.startswith(('origin/', 'remotes/')) else n
        if bare not in seen:
            seen.add(bare)
            out.append(bare)
    return out


def outcome_for_branch(branch):
    """(outcome, detail) for one branch — outcome is merged/open/none/unknown."""
    out = _gh('pr', 'list', '--head', branch, '--state', 'all',
              '--json', 'number,state,mergedAt,title')
    if out is None:
        return 'unknown', 'gh unavailable'
    try:
        prs = json.loads(out or '[]')
    except ValueError:
        return 'unknown', 'unreadable gh output'
    if not prs:
        return 'none', 'no PR for this branch'
    merged = [p for p in prs if p.get('mergedAt')]
    if merged:
        p = merged[0]
        return 'merged', f"#{p['number']} at {p['mergedAt']}"
    p = prs[0]
    return 'open', f"#{p['number']} is {str(p.get('state', '')).lower()}"


def outcome_from_pr_history(task_id):
    """(outcome, detail) by matching the task id against the forge's own PRs.

    The branch-name lookup misses the common case: a merged PR whose branch was
    deleted, which is precisely when the outcome is worth recording. Task ids
    survive in the branch ref and in the PR title, so search those instead.
    """
    out = _gh('pr', 'list', '--state', 'all', '--limit', '200',
              '--json', 'number,state,mergedAt,title,headRefName', timeout=30)
    if out is None:
        return 'unknown', 'gh unavailable'
    try:
        prs = json.loads(out or '[]')
    except ValueError:
        return 'unknown', 'unreadable gh output'
    hits = [p for p in prs
            if task_id in (p.get('headRefName') or '') or task_id in (p.get('title') or '')]
    if not hits:
        return 'none', 'no PR carries this task id'
    merged = [p for p in hits if p.get('mergedAt')]
    if merged:
        p = merged[0]
        return 'merged', f"#{p['number']} at {p['mergedAt']} ({p.get('headRefName', '')})"
    p = hits[0]
    return 'open', f"#{p['number']} is {str(p.get('state', '')).lower()}"


def report(task_id):
    """(task_id, outcome, detail) for a task, by branch then by PR history."""
    for branch in branches_for(task_id):
        oc, detail = outcome_for_branch(branch)
        if oc in ('merged', 'open'):
            return task_id, oc, f'{branch}: {detail}'
    oc, detail = outcome_from_pr_history(task_id)   # branch deleted after merge
    return task_id, oc, detail


SUGGESTION = {
    'merged': 'record  Outcome: merged {detail}',
    'open':   'still open — chase it, do not mark the task finished',
    'none':   'no PR found — open one, or record an explicit abandoned/taken-back',
    'unknown': 'could not reach gh — leave the Outcome field alone',
}


def main(argv):
    if len(argv) > 2 and argv[1] == '--branch':
        oc, detail = outcome_for_branch(argv[2])
        print(f'{argv[2]:<40} {oc:<8} {detail}')
        return 0

    if len(argv) > 1:
        ids = [argv[1]]
    else:
        repo = harness_config.repo_root()
        try:
            text = open(os.path.join(repo, workflow_state.TASK_MD), encoding='utf-8').read()
        except OSError:
            print('[merged] task.md not found at the repo root.')
            return 0
        ids = [t for t, _ in workflow_state.awaiting_outcome(text)]
        if not ids:
            print('[merged] no active task is awaiting an outcome.')
            return 0

    for tid in ids:
        _, oc, detail = report(tid)
        print(f'{tid:<12} {oc:<8} {detail}')
        print(f'{"":<12} -> ' + SUGGESTION[oc].format(detail=detail.split(": ", 1)[-1]))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
