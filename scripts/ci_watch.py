#!/usr/bin/env python3
"""Watch a pull request's CI and speak only when the verdict changes.

Chasing CI is work an agent should not do by waking on a timer: polling every
interval costs tokens even when everything is green, which is the pattern this
harness rejects. So the polling is a dumb script and the agent hears about it
only on a state TRANSITION — pending -> failing, failing -> passing. Detection
is cheap and deterministic; attention is the expensive part, and it is spent on
events.

    ci_watch.py --once              # read-only status for the current branch
    ci_watch.py --once --branch b   # read-only status for one branch
    ci_watch.py                     # watch loop: print only on a change

Wired as a plugin monitor, what this prints reaches the agent as a notification.

REPORT ONLY. It never commits, pushes, merges, or re-runs a job. A red build is
reported to the owner, who decides what happens next.
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_config

# gh buckets a check into one of these; `state` is the raw forge value. Prefer
# the bucket when present — it is gh's own documented categorisation.
_BUCKET = {'pass': 'pass', 'fail': 'fail', 'pending': 'pending',
           'skipping': 'skip', 'cancel': 'fail'}
_STATE = {'SUCCESS': 'pass', 'NEUTRAL': 'pass', 'SKIPPED': 'skip',
          'FAILURE': 'fail', 'TIMED_OUT': 'fail', 'CANCELLED': 'fail',
          'ACTION_REQUIRED': 'fail', 'STARTUP_FAILURE': 'fail',
          'PENDING': 'pending', 'QUEUED': 'pending', 'IN_PROGRESS': 'pending',
          'EXPECTED': 'pending', 'REQUESTED': 'pending', 'WAITING': 'pending'}

# States that never warrant a notification: there is no PR to chase, or the
# forge could not be reached. Neither is news about the code.
SILENT = ('no-pr', 'unknown')

POLL_SECONDS = 60


def _classify(check):
    bucket = str(check.get('bucket') or '').lower()
    if bucket in _BUCKET:
        return _BUCKET[bucket]
    return _STATE.get(str(check.get('state') or '').upper(), 'pending')


def verdict(checks):
    """One word for a whole check run: failing | pending | passing | no-checks.

    A failure outranks a pending check — a red build is news now, not once the
    queue drains.
    """
    kinds = [_classify(c) for c in checks]
    if not kinds:
        return 'no-checks'
    if 'fail' in kinds:
        return 'failing'
    if 'pending' in kinds:
        return 'pending'
    return 'passing'


def describe(checks):
    """A short human detail line for the current verdict."""
    kinds = [_classify(c) for c in checks]
    failed = [c.get('name') or '?' for c, k in zip(checks, kinds) if k == 'fail']
    if failed:
        return ', '.join(failed[:4]) + (f' +{len(failed) - 4} more' if len(failed) > 4 else '')
    pending = sum(1 for k in kinds if k == 'pending')
    if pending:
        return f'{len(kinds) - pending} of {len(kinds)} done'
    return f'{len(kinds)} checks green'


def current_branch():
    try:
        r = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                           capture_output=True, text=True, timeout=10)
    except Exception:
        return ''
    return r.stdout.strip() if r.returncode == 0 else ''


def poll(branch, gh_repo=None):
    """(state, detail) for one branch, straight from gh. Never raises.

    gh exits 8 while checks are pending and 1 when one failed, so the exit code
    is not an error signal here — the JSON on stdout is what matters.
    """
    cmd = ['gh', 'pr', 'checks', branch]
    if gh_repo:
        cmd += ['--repo', gh_repo]
    cmd += ['--json', 'name,state,bucket,link']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception:
        return 'unknown', 'gh unavailable'
    out = (r.stdout or '').strip()
    if not out:
        err = (r.stderr or '').lower()
        if 'no pull requests found' in err or 'no open pull requests' in err:
            return 'no-pr', ''
        if 'no checks reported' in err:
            return 'no-checks', 'no checks reported yet'
        return 'unknown', (r.stderr or '').strip().splitlines()[0] if r.stderr else 'no output'
    try:
        checks = json.loads(out)
    except ValueError:
        return 'unknown', 'unreadable gh output'
    return verdict(checks), describe(checks)


class Watcher:
    """Remembers the last verdict per branch, so only changes are reported."""

    ICON = {'passing': 'green', 'failing': 'RED', 'pending': 'running',
            'no-checks': 'no checks'}

    def __init__(self):
        self.last = {}

    def transition(self, branch, state, detail):
        """A message when this is news for `branch`, else None.

        Only the verdict is compared, never the detail: '2 of 5 done' becoming
        '3 of 5 done' is progress, not news.
        """
        if state in SILENT:
            return None            # keep the last real verdict: an outage is
                                   # not a change, and forgetting it would make
                                   # the next successful poll look like news
        if self.last.get(branch) == state:
            return None
        previous = self.last.get(branch)
        self.last[branch] = state
        arrow = f'{previous} -> ' if previous else ''
        tail = f' ({detail})' if detail else ''
        return f'[ci] {branch}: {arrow}{state} [{self.ICON.get(state, state)}]{tail}'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--once', action='store_true',
                    help='print the current state and exit; no side effects')
    ap.add_argument('--branch', default=None, help='branch to watch (default: current)')
    ap.add_argument('--interval', type=int, default=POLL_SECONDS,
                    help=f'seconds between polls (default {POLL_SECONDS})')
    args = ap.parse_args(argv)

    gh_repo = harness_config.gh_repo()
    branch = args.branch or current_branch()
    if not branch or branch in ('HEAD', 'master', 'main'):
        if args.once:
            print(f'[ci] {branch or "detached"}: not a feature branch — nothing to chase')
        return 0

    if args.once:
        state, detail = poll(branch, gh_repo)
        print(f'[ci] {branch}: {state}' + (f' ({detail})' if detail else ''))
        return 0

    watcher = Watcher()
    while True:
        state, detail = poll(branch, gh_repo)
        msg = watcher.transition(branch, state, detail)
        if msg:
            print(msg, flush=True)
        try:
            time.sleep(max(args.interval, 15))
        except KeyboardInterrupt:
            return 0


if __name__ == '__main__':
    sys.exit(main())
