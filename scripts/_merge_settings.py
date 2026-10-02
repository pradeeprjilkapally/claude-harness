#!/usr/bin/env python3
"""Merge the harness's repo-level hook wiring into .claude/settings.json.

Installer-only. The target file belongs to the repo and may carry settings the
harness knows nothing about, so this adds only what is missing and never rewrites
what is already there. A hook command already present — by exact string — is left
alone rather than duplicated, which is what stops a re-run doubling every entry.

    _merge_settings.py <target-settings.json> <harness-settings.json>
"""
import json
import os
import shutil
import sys


def existing_commands(hooks, event):
    return {h.get('command', '')
            for matcher in hooks.get(event, [])
            for h in matcher.get('hooks', [])}


def main():
    target, source = sys.argv[1], sys.argv[2]

    with open(source) as f:
        want = json.load(f)

    cfg = {}
    if os.path.exists(target):
        try:
            with open(target) as f:
                cfg = json.load(f)
        except ValueError:
            print('  .claude/settings.json is not valid JSON — leaving it alone')
            return 1
        shutil.copyfile(target, target + '.harness-backup')

    # Non-hook keys: fill in only what the repo has not set for itself.
    for key, value in want.items():
        if key != 'hooks':
            cfg.setdefault(key, value)

    hooks = cfg.setdefault('hooks', {})
    added = 0
    for event, matchers in want.get('hooks', {}).items():
        present = existing_commands(hooks, event)
        for matcher in matchers:
            missing = [h for h in matcher.get('hooks', [])
                       if h.get('command', '') not in present]
            if missing:
                entry = {k: v for k, v in matcher.items() if k != 'hooks'}
                entry['hooks'] = missing
                hooks.setdefault(event, []).append(entry)
                added += len(missing)

    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w') as f:
        json.dump(cfg, f, indent=2)
        f.write('\n')
    print(f'  repo settings: {added} hook command(s) wired, existing left untouched')
    return 0


if __name__ == '__main__':
    sys.exit(main())
