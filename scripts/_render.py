#!/usr/bin/env python3
"""Substitute the harness's install-time placeholders in one file.

Installer-only; not copied into consuming repos. Keeping one source and
rendering here is what stops the Claude and Codex skill sets drifting apart.

    _render.py <file> <agent_doc> <agent_name> <owner> <repo_path> <gh_repo> <remote>
"""
import pathlib
import sys

TOKENS = ('{{AGENT_DOC}}', '{{AGENT_NAME}}', '{{OWNER}}', '{{REPO_PATH}}',
          '{{GH_REPO}}', '{{REMOTE}}')


def main():
    if len(sys.argv) < 5:
        print('usage: _render.py <file> <agent_doc> <agent_name> <owner> [repo_path]',
              file=sys.stderr)
        return 2
    path = pathlib.Path(sys.argv[1])
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return 0                                   # binary or unreadable: leave it
    rendered = text
    defaults = ['CLAUDE.md', 'Claude', 'the owner', '/path/to/your/repo',
                'owner/name', 'origin']
    values = sys.argv[2:2 + len(TOKENS)]
    values += defaults[len(values):]               # fill any trailing omissions
    for token, value in zip(TOKENS, values):
        rendered = rendered.replace(token, value)
    if rendered != text:
        path.write_text(rendered, encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
