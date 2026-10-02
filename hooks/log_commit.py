#!/usr/bin/env python3
"""PostToolUse(Bash): append a compact commit/PR ledger entry to <repo>/log.md.

On `git commit` it records date, short hash, branch, subject and files changed
(deduped by hash). On `gh pr create`/`gh pr merge` it records the PR URL parsed
from the command output, tied to the current branch.
"""

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hooklib import append, ensure_header, git, read_payload, repo_root

HEADER = """# Commit & PR Log

Auto-maintained ledger of commits and PRs, grouped by date. Newest date on top of
each day's list. Maintained by the `log_commit.py` hook — do not edit by hand.

Format: `` - `<short-hash>` (branch) subject — N files: a, b, c — PR #<n> ``
"""

PR_URL = re.compile(r"https://github\.com/[^\s]+/pull/(\d+)")


def _tool_field(data, key):
    ti = data.get("tool_input") or {}
    return ti.get(key, "") if isinstance(ti, dict) else ""


def _tool_result_text(data):
    tr = data.get("tool_result", data.get("tool_response", ""))
    if isinstance(tr, dict):
        return " ".join(str(v) for v in tr.values())
    return str(tr or "")


def _ensure_day_heading(path, day):
    heading = f"## {day}"
    try:
        existing = open(path).read()
    except FileNotFoundError:
        existing = ""
    if heading not in existing:
        append(path, f"\n{heading}\n")


def _log_commit(root, logf):
    h = git(root, "log", "-1", "--pretty=%H")
    if not h:
        return
    short = h[:9]
    if os.path.exists(logf) and short in open(logf).read():
        return  # already recorded
    subject = git(root, "log", "-1", "--pretty=%s")
    day = git(root, "log", "-1", "--date=format:%Y-%m-%d", "--pretty=%ad") or \
        datetime.date.today().isoformat()
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    raw_files = git(root, "show", "--name-only", "--pretty=format:", h)
    files = [f for f in raw_files.splitlines() if f.strip()]
    ensure_header(logf, HEADER)
    _ensure_day_heading(logf, day)
    file_list = ", ".join(files) if files else "no files"
    append(logf, f"- `{short}` ({branch}) {subject} — {len(files)} files: {file_list}")


def _log_pr(root, logf, data):
    m = PR_URL.search(_tool_result_text(data))
    if not m:
        return
    url = m.group(0)
    num = m.group(1)
    if os.path.exists(logf) and url in open(logf).read():
        return
    day = datetime.date.today().isoformat()
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    ensure_header(logf, HEADER)
    _ensure_day_heading(logf, day)
    append(logf, f"- PR #{num} ({branch}) — {url}")


def main():
    data = read_payload()
    cmd = _tool_field(data, "command")
    if not cmd or ("git commit" not in cmd and "gh pr" not in cmd):
        return
    root = repo_root(data)
    if not root:
        return
    logf = os.path.join(root, "log.md")
    if "git commit" in cmd:
        _log_commit(root, logf)
    if "gh pr create" in cmd or "gh pr merge" in cmd:
        _log_pr(root, logf, data)


if __name__ == "__main__":
    main()
