#!/usr/bin/env python3
"""
Pre-push merge-guard: refuse to push to a branch whose PR is already MERGED.

Pushing a follow-up commit to a branch after its PR merged orphans that commit —
it never reaches develop/master (the recurring "fix lost after a fast merge" bug).
The fix is to branch fresh off develop for follow-up work.

Fails open if `gh` is unavailable/unauthed (never blocks a legitimate push just
because tooling is down); blocks only when a merged PR is positively found.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_config
import subprocess
import sys

# Query the configured slug explicitly — without --repo, `gh` defaults to `origin`
# which may be a read-only upstream fork carrying none of these PRs,
# so the guard would silently never fire.
_GH_REPO = harness_config.gh_repo()


def merged_pr_number(gh_json: str) -> int | None:
    """Parse `gh pr list --head <b> --state merged --json number` → PR number, or None."""
    try:
        prs = json.loads(gh_json or '[]')
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(prs, list) and prs:
        return prs[0].get('number')
    return None


def current_branch() -> str:
    return subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                          capture_output=True, text=True).stdout.strip()


def main() -> int:
    branch = current_branch()
    if branch in ('master', 'main', 'develop', 'HEAD'):
        return 0
    try:
        out = subprocess.run(
            ['gh', 'pr', 'list'] + (['--repo', _GH_REPO] if _GH_REPO else []) + [
             '--head', branch, '--state', 'merged', '--json', 'number'],
            capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return 0                          # gh missing/unauthed → fail open
    except Exception:
        return 0                              # fail open
    n = merged_pr_number(out.stdout)
    if n:
        print(f"[merge-guard] ❌ branch '{branch}' already has MERGED PR #{n} — "
              "pushing here orphans the commit (it won't reach develop/master).")
        print("[merge-guard]    Branch fresh off develop for follow-up work: "
              "git checkout -b feature/<NN-DDMMYY>-<slug> {{REMOTE}}/develop")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
