#!/usr/bin/env python3
"""SessionStart: show the task and action-item state before any work begins.

The workflow's first rule is that every change is tracked, so a session opens by
reading what is already in flight rather than by taking a new instruction on a
blank slate. Silent in any repository that has not opted into the harness.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_config

FILES = (('task.md', 'task.md — start-of-session review'),
         ('action_items.md', 'action_items.md — manual-only residue'))


def main():
    root = os.environ.get('CLAUDE_PROJECT_DIR') or harness_config.repo_root()
    if not harness_config.installed(root):
        return 0                       # not a harness repo — say nothing
    for name, heading in FILES:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        print(f'=== {heading} ===')
        with open(path, encoding='utf-8', errors='replace') as f:
            print(f.read().rstrip())
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
