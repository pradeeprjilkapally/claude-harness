#!/usr/bin/env python3
"""PostToolUse(Write|Edit): when task.md changed, demand the RED check.

Reads the hook payload on stdin and acts only when the edited file was the
repo's own task.md — every other edit is none of its business. The decision
about whether this is a new task or a mid-flight progress edit belongs to
workflow_state, which this only delegates to.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness_config


def edited_path(payload):
    resp = payload.get('tool_response') or {}
    inp = payload.get('tool_input') or {}
    return resp.get('filePath') or inp.get('file_path') or ''


def main():
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except (ValueError, OSError):
        return 0
    if os.path.basename(edited_path(payload)) != 'task.md':
        return 0
    root = os.environ.get('CLAUDE_PROJECT_DIR') or payload.get('cwd') or os.getcwd()
    if not harness_config.installed(root):
        return 0
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        r = subprocess.run([sys.executable, os.path.join(here, 'workflow_state.py'),
                            'on-task-updated'], cwd=root, capture_output=True,
                           text=True, timeout=20)
    except Exception:
        return 0
    if r.stdout.strip():
        print(r.stdout.strip())
    return 0


if __name__ == '__main__':
    sys.exit(main())
