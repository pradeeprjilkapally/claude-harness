#!/usr/bin/env python3
"""Session continuity for <repo>/sessions_handoff.md.

  start (SessionStart): print the last session block to stdout so Claude reads it
                        as context, and stash the session start time + head commit.
  end   (SessionEnd):   append a new session block (time range, branch, commits and
                        files changed during the session) and drop the stash.
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hooklib import append, ensure_header, git, read_payload, repo_root, state_path

HEADER = """# Sessions Handoff

Continuity log between Claude Code sessions. The last block is surfaced at the start
of each session; a new block is appended when the session ends. Maintained by the
`session_handoff.py` hook.
"""


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _last_block(path):
    """Return the text of the last '## Session' block, or ''."""
    try:
        text = open(path).read()
    except FileNotFoundError:
        return ""
    idx = text.rfind("\n## Session")
    if idx == -1:
        idx = text.find("## Session")
        if idx == -1:
            return ""
    return text[idx:].strip()


def do_start(data, root):
    handoff = os.path.join(root, "sessions_handoff.md")
    block = _last_block(handoff)
    if block:
        print("=== sessions_handoff.md — last session ===")
        print(block)
    sp = state_path(data.get("session_id"))
    with open(sp, "w") as f:
        json.dump({
            "start": _now(),
            "head": git(root, "rev-parse", "HEAD"),
            "root": root,
        }, f)


def do_end(data, root):
    sp = state_path(data.get("session_id"))
    start, head = "?", ""
    if os.path.exists(sp):
        try:
            st = json.load(open(sp))
            start = st.get("start", "?")
            head = st.get("head", "")
        except Exception:
            pass
    end = _now()
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    handoff = os.path.join(root, "sessions_handoff.md")
    ensure_header(handoff, HEADER)

    lines = [f"\n## Session {start} – {end}", f"- Branch: {branch}"]
    if head:
        commits = git(root, "log", "--pretty=%h %s", f"{head}..HEAD")
        files = git(root, "diff", "--name-only", f"{head}..HEAD")
        commit_lines = [c for c in commits.splitlines() if c.strip()]
        file_lines = [f for f in files.splitlines() if f.strip()]
        if commit_lines:
            lines.append(f"- Commits ({len(commit_lines)}):")
            lines.extend(f"    - {c}" for c in commit_lines)
        else:
            lines.append("- Commits: none")
        if file_lines:
            lines.append(f"- Files changed ({len(file_lines)}): " + ", ".join(file_lines))
    append(handoff, "\n".join(lines))

    if os.path.exists(sp):
        try:
            os.remove(sp)
        except OSError:
            pass


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    data = read_payload()
    root = repo_root(data)
    if not root:
        return
    if mode == "start":
        do_start(data, root)
    elif mode == "end":
        do_end(data, root)


if __name__ == "__main__":
    main()
