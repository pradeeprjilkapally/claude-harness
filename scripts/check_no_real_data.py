#!/usr/bin/env python3
"""Deterministic PII guard: keep real user data out of the repo.

Real user data lives in the gitignored data dir named by .harness.json
(data_dir / data_dir_env). This scans a git diff (the staged change by default) for
values that also appear in that data — a large numeric amount, or an
account/client-id-shaped string — and fails if such a value is being committed
into a tracked file (tests, task.md, code, docs).

It is a heuristic, not a secret scanner: it flags only distinctive values so
small shared numbers and plain words don't false-positive —
  * numbers whose magnitude is >= NUM_MIN, matched numerically so 45000,
    45,000 and 45000.00 all compare equal;
  * strings >= STR_MIN chars that mix letters AND digits (id-shaped).
It no-ops where there is no data dir (CI, a fresh clone), so it is safe to wire
into a shared pre-push hook.

Usage:
    check_no_real_data.py                 # scans `git diff --cached`
    check_no_real_data.py --range A..B    # scans that commit range
    git diff | check_no_real_data.py -    # scans a diff on stdin
Exit 0 = clean; 1 = a real value appears in an added line (file + a truncated
value are printed as a systemMessage).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_config
import re
import subprocess
import sys

NUM_RE = re.compile(r'-?\d[\d,]*\.?\d*')
NUM_MIN = 1000.0            # only amounts this large are distinctive enough to guard
STR_MIN = 8                 # account/client-id-shaped strings


def data_dir():
    return harness_config.data_dir()


def _collect(obj, nums, strs):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        if abs(float(obj)) >= NUM_MIN:
            nums.add(round(float(obj), 2))
    elif isinstance(obj, str):
        s = obj.strip()
        if len(s) >= STR_MIN and any(c.isdigit() for c in s) and any(c.isalpha() for c in s):
            strs.add(s.lower())
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect(v, nums, strs)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, nums, strs)


def sensitive_values(directory):
    """(numeric set, lowercased-string set) drawn from every *.json in the data dir."""
    nums, strs = set(), set()
    for path in glob.glob(os.path.join(directory, '*.json')):
        try:
            with open(path, encoding='utf-8') as f:
                _collect(json.load(f), nums, strs)
        except (OSError, ValueError):
            continue
    return nums, strs


def added_lines(diff_text):
    """(file, added-line-text) for every '+' line in a unified diff."""
    out, cur = [], None
    for line in diff_text.splitlines():
        if line.startswith('+++ b/'):
            cur = line[6:]
        elif line.startswith('+') and not line.startswith('+++'):
            out.append((cur, line[1:]))
    return out


def scan(diff_text, nums, strs):
    """List of (file, offending-value) for values from the data dir found in added lines."""
    hits = []
    for fname, text in added_lines(diff_text):
        low = text.lower()
        for s in strs:
            if s in low:
                hits.append((fname, s))
        if nums:
            for tok in NUM_RE.findall(text):
                try:
                    val = round(float(tok.replace(',', '')), 2)
                except ValueError:
                    continue
                if abs(val) >= NUM_MIN and val in nums:
                    hits.append((fname, tok))
    return hits


def _read_diff(args):
    if args and args[0] == '-':
        return sys.stdin.read()
    if len(args) >= 2 and args[0] == '--range':
        cmd = ['git', 'diff', args[1]]
    else:
        cmd = ['git', 'diff', '--cached']
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def main(argv):
    directory = data_dir()
    if not os.path.isdir(directory):
        return 0                       # no local data here — nothing to guard
    nums, strs = sensitive_values(directory)
    if not nums and not strs:
        return 0
    hits = scan(_read_diff(argv[1:]), nums, strs)
    if hits:
        detail = '; '.join(f'{f}: {str(v)[:6]}…' for f, v in hits[:8])
        print(json.dumps({'systemMessage':
                          'PII GUARD: the diff contains value(s) that also appear '
                          'in your local data dir — do not commit real user '
                          f'data. {detail}'}))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
