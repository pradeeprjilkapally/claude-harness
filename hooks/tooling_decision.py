#!/usr/bin/env python3
"""Architecture-decision automation for <repo>/decisions/.

  snapshot : compare the current MCP server set (global + this project's, from
             ~/.claude.json) against <repo>/.claude/.mcp_snapshot.json. First run
             baselines silently; a later change writes a dated decision file listing
             what was added/removed and nudges Claude to fill in the rationale.
  nudge    : on a Write/Edit to an external-tool/infra file (CI, containers, IaC,
             launchd, deps, cloud config, MCP config) tell Claude to record a
             decision in decisions/ — the agent authors it since only it knows the why.
"""

import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hooklib import emit_system, read_payload, repo_root

CLAUDE_JSON = os.path.expanduser("~/.claude.json")

# Filenames / path fragments that signal an external tool or infra connection.
INFRA_PATTERNS = [
    r"/launchd/.*\.plist$", r"\.plist$",
    r"/\.github/workflows/", r"Dockerfile", r"docker-compose", r"/compose\.ya?ml$",
    r"\.tf$", r"/terraform/", r"wrangler\.toml$", r"fly\.toml$", r"vercel\.json$",
    r"serverless\.ya?ml$", r"\.mcp\.json$",
    r"requirements(-\w+)?\.txt$", r"pyproject\.toml$", r"setup\.cfg$",
]
INFRA_RE = re.compile("|".join(INFRA_PATTERNS))


def _current_servers(root):
    """Set of MCP server names: global mcpServers ∪ this project's mcpServers."""
    try:
        cfg = json.load(open(CLAUDE_JSON))
    except Exception:
        return set()
    servers = set((cfg.get("mcpServers") or {}).keys())
    for key, proj in (cfg.get("projects") or {}).items():
        if os.path.realpath(key) == os.path.realpath(root):
            servers |= set((proj.get("mcpServers") or {}).keys())
    return servers


def do_snapshot(data, root):
    snap_path = os.path.join(root, ".claude", ".mcp_snapshot.json")
    os.makedirs(os.path.dirname(snap_path), exist_ok=True)
    current = _current_servers(root)

    if not os.path.exists(snap_path):
        json.dump({"servers": sorted(current)}, open(snap_path, "w"))
        return

    try:
        prev = set(json.load(open(snap_path)).get("servers", []))
    except Exception:
        prev = set()
    if prev == current:
        return

    added = sorted(current - prev)
    removed = sorted(prev - current)
    json.dump({"servers": sorted(current)}, open(snap_path, "w"))

    now = datetime.datetime.now()
    fname = now.strftime("%Y-%m-%d-%H%M") + "-tooling-change.md"
    decisions_dir = os.path.join(root, "decisions")
    os.makedirs(decisions_dir, exist_ok=True)
    fpath = os.path.join(decisions_dir, fname)

    body = [
        f"# Tooling change — {now.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## What changed",
        f"- MCP servers added: {', '.join(added) if added else 'none'}",
        f"- MCP servers removed: {', '.join(removed) if removed else 'none'}",
        f"- Current connected set: {', '.join(sorted(current)) if current else 'none'}",
        "",
        "## Why",
        "_To be completed: what prompted connecting/removing this tool._",
        "",
        "## Impact",
        "_To be completed: what capabilities this adds/removes and any config touched._",
        "",
        "## Alternatives considered",
        "_To be completed._",
        "",
    ]
    with open(fpath, "w") as f:
        f.write("\n".join(body))

    change = []
    if added:
        change.append("added " + ", ".join(added))
    if removed:
        change.append("removed " + ", ".join(removed))
    emit_system(
        "Tooling change detected (" + "; ".join(change) + "). A decision record was "
        f"started at decisions/{fname} — fill in the Why / Impact / Alternatives "
        "sections now with the real rationale for this change."
    )


def do_nudge(data, root):
    ti = data.get("tool_input") or {}
    path = ti.get("file_path", "") if isinstance(ti, dict) else ""
    if not path or not INFRA_RE.search(path):
        return
    emit_system(
        f"External-tool/infra file changed ({os.path.basename(path)}). Record a dated "
        "architecture decision in decisions/ (YYYY-MM-DD-HHMM-<slug>.md) capturing what "
        "external tool or infra connection changed and why."
    )


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    data = read_payload()

    if mode == "snapshot":
        # Fast exit for the PostToolUse(Bash) registration unless MCP is involved.
        ti = data.get("tool_input") or {}
        cmd = ti.get("command", "") if isinstance(ti, dict) else ""
        if data.get("hook_event_name") == "PostToolUse" and "mcp" not in cmd.lower():
            return
        root = repo_root(data)
        if root:
            do_snapshot(data, root)
    elif mode == "nudge":
        root = repo_root(data)
        if root:
            do_nudge(data, root)


if __name__ == "__main__":
    main()
