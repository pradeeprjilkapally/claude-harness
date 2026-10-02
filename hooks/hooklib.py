"""Shared helpers for the harness maintenance hooks.

All hooks read a JSON payload on stdin (session_id, cwd, hook_event_name, and for
PostToolUse: tool_name, tool_input, tool_result). They act only on repositories
that have opted in, and no-op everywhere else.

Opt-in is a MARKER FILE at the repo root: .harness.json, written by install.sh.
This replaced a hardcoded parent-directory path, which meant the harness could
only ever run inside one directory tree on one machine.
"""

import json
import os
import subprocess
import sys

MARKER = ".harness.json"
STATE_DIR = os.path.expanduser("~/.claude/hooks/state")


def _marker_path(root):
    return os.path.join(root, MARKER)


def harness_config(root):
    """The repo's .harness.json as a dict, or None if it is not installed there."""
    try:
        with open(_marker_path(root)) as f:
            return json.load(f)
    except Exception:
        return None


def read_payload():
    """Parse the hook JSON payload from stdin. Returns {} on any failure."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def git(cwd, *args):
    """Run git in cwd, returning stripped stdout or '' on failure."""
    try:
        r = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_root(data):
    """Resolve the target repo root for this hook, or None if out of scope.

    Uses the git top-level of the payload cwd (falls back to cwd itself), then
    requires a .harness.json marker at that root. Any repo, any machine — the
    marker is what opts a repo in, not where it happens to live on disk.
    """
    cwd = os.path.realpath(data.get("cwd") or os.getcwd())
    top = git(cwd, "rev-parse", "--show-toplevel")
    root = os.path.realpath(top) if top else cwd
    cfg = harness_config(root)
    if cfg is None:
        return None                      # harness not installed here — no-op
    if cfg.get("enabled") is False:
        return None                      # installed but deliberately switched off
    return root


def ensure_header(path, header):
    """Create path with header if it does not exist yet."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(header if header.endswith("\n") else header + "\n")


def append(path, text):
    """Append text to path (adding a trailing newline if absent)."""
    with open(path, "a") as f:
        f.write(text if text.endswith("\n") else text + "\n")


def emit_system(msg):
    """Emit a systemMessage back to Claude Code."""
    print(json.dumps({"systemMessage": msg}))


def state_path(session_id, suffix=".json"):
    os.makedirs(STATE_DIR, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (session_id or "nosession"))
    return os.path.join(STATE_DIR, safe + suffix)
