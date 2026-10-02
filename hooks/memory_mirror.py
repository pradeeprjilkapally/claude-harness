#!/usr/bin/env python3
"""PostToolUse(Write|Edit): mirror agent-memory writes into <repo>/memory.md.

When Claude writes to a file under ~/.claude/projects/<proj>/memory/ (individual
memory files or the MEMORY.md index), the same content is appended — timestamped and
attributed to its source file — to the active repo's memory.md.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hooklib import append, ensure_header, read_payload, repo_root

HEADER = """# Memory Mirror

Everything written to the agent's project memory is mirrored here automatically,
newest at the bottom, timestamped and attributed to its source file. Maintained by
the `memory_mirror.py` hook.
"""

MEMORY_MARKER = os.sep + "memory" + os.sep


def _is_memory_path(path):
    real = os.path.realpath(path)
    return ".claude" in real and "projects" in real and MEMORY_MARKER in real


def main():
    data = read_payload()
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        return
    path = ti.get("file_path", "")
    if not path or not _is_memory_path(path):
        return
    root = repo_root(data)
    if not root:
        return
    # Write carries full content; Edit carries the replacement text.
    body = ti.get("content")
    if body is None:
        body = ti.get("new_string", "")
    body = (body or "").strip()
    if not body:
        return
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    src = os.path.basename(path)
    memf = os.path.join(root, "memory.md")
    ensure_header(memf, HEADER)
    append(memf, f"\n## {ts} — {src}\n\n{body}\n")


if __name__ == "__main__":
    main()
