#!/usr/bin/env python3
"""Build the harness into a Claude Code plugin at dist/plugin.

The harness has two delivery paths and they are complementary, not rival:

  install.sh  puts the REPO-SIDE layer in place — the pre-push gate, task.md and
              the other management files, the branch-flow CI guard. None of that
              can come from a plugin: a plugin cannot write .git/hooks/pre-push
              and cannot seed a file the repo then owns.

  the plugin  carries the AGENT-SIDE layer — the skills, the lifecycle hooks, and
              the CI monitor. It installs with one command, updates from a
              marketplace, and needs no shell script run against each repo.

Both read the same `.harness.json` marker, so a repo that has not opted in sees
nothing from either.

The skills are kept in ONE source with {{TOKEN}} placeholders. install.sh renders
them to literal values per repo; this renders them to the plugin's own
`${user_config.*}` references, which Claude Code substitutes when it loads the
skill. One source, two renderings — the thing that stopped the Claude and Codex
skill sets drifting apart does the same job here.

    build_plugin.py [--out dist/plugin]
"""
import argparse
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Where each install-time placeholder lands in the plugin rendering.
#
# A plugin is Claude Code only, so the agent-document tokens resolve statically.
# The three the owner must supply become ${user_config.*} — substituted by Claude
# Code in skill, command, and agent content when the skill loads.
SKILL_TOKENS = {
    '{{AGENT_DOC}}': 'CLAUDE.md',
    '{{AGENT_NAME}}': 'Claude',
    '{{OWNER}}': '${user_config.owner}',
    '{{GH_REPO}}': '${user_config.gh_repo}',
    '{{REMOTE}}': '${user_config.remote}',
    '{{REPO_PATH}}': '${CLAUDE_PROJECT_DIR}',
}

# `${user_config.*}` is substituted ONLY in skill/agent/command markdown, hook
# commands and MCP config — never inside a .py file. Scripts therefore keep
# reading the per-repo marker at runtime (scripts/harness_config.py), and the
# placeholders left in them render to the same defaults install.sh uses.
SCRIPT_TOKENS = {
    '{{AGENT_DOC}}': 'CLAUDE.md',
    '{{AGENT_NAME}}': 'Claude',
    '{{OWNER}}': 'the owner',
    '{{GH_REPO}}': 'owner/name',
    '{{REMOTE}}': 'origin',
    '{{REPO_PATH}}': '.',
}

# Installer-only: these exist to render and stamp a target repo, and have no
# meaning inside the built plugin.
NOT_BUNDLED = {'_render.py', '_marker.py', '_merge_settings.py', 'build_plugin.py'}


def render(text, tokens):
    for token, value in tokens.items():
        text = text.replace(token, value)
    return text


def copy_rendered(src_dir, dst_dir, tokens, suffixes):
    """Copy a tree, substituting tokens in files whose suffix is listed."""
    count = 0
    for src in sorted(src_dir.rglob('*')):
        if src.is_dir() or '__pycache__' in src.parts:
            continue
        if src.parent == src_dir and src.name in NOT_BUNDLED:
            continue
        dst = dst_dir / src.relative_to(src_dir)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in suffixes:
            dst.write_text(render(src.read_text(encoding='utf-8'), tokens),
                           encoding='utf-8')
        else:
            shutil.copy2(src, dst)
        count += 1
    return count


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default='dist/plugin', help='output directory')
    ap.add_argument('--owner', default='Pradeep',
                    help='author name recorded in the manifest')
    args = ap.parse_args(argv)

    version = (ROOT / 'VERSION').read_text().strip()
    out = (ROOT / args.out) if not pathlib.Path(args.out).is_absolute() \
        else pathlib.Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    n_skills = copy_rendered(ROOT / 'skills', out / 'skills', SKILL_TOKENS, {'.md'})
    n_scripts = copy_rendered(ROOT / 'scripts', out / 'scripts', SCRIPT_TOKENS, {'.py'})
    n_hooks = copy_rendered(ROOT / 'hooks', out / 'hooks', SCRIPT_TOKENS, {'.py'})

    # The skills tell the agent to seed management files and read WORKFLOW.md, so
    # the plugin has to carry them — otherwise those instructions point nowhere.
    copy_rendered(ROOT / 'templates' / 'root', out / 'templates' / 'root',
                  SCRIPT_TOKENS, {'.md'})
    for name in ('githooks/pre-push', 'workflows/pr-flow.yml', 'gitignore-fragment'):
        src = ROOT / 'templates' / name
        if src.exists():
            dst = out / 'templates' / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    copy_rendered(ROOT / 'docs', out / 'docs', SKILL_TOKENS, {'.md'})

    (out / 'hooks' / 'hooks.json').write_text(
        (ROOT / 'templates' / 'plugin' / 'hooks.json').read_text(), encoding='utf-8')
    (out / 'monitors').mkdir()
    (out / 'monitors' / 'monitors.json').write_text(
        (ROOT / 'templates' / 'plugin' / 'monitors.json').read_text(), encoding='utf-8')

    manifest = json.loads(
        (ROOT / 'templates' / 'plugin' / 'plugin.json').read_text()
        .replace('__VERSION__', version).replace('__OWNER__', args.owner))
    (out / '.claude-plugin').mkdir()
    (out / '.claude-plugin' / 'plugin.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    # Match the harness's own token names, not any '{{': the bundled
    # pr-flow.yml legitimately carries GitHub Actions '${{ github.head_ref }}'.
    leftover = []
    for f in sorted(out.rglob('*')):
        if not f.is_file():
            continue
        body = f.read_text(encoding='utf-8', errors='replace')
        if any(tok in body for tok in SKILL_TOKENS):
            leftover.append(str(f.relative_to(out)))
    if leftover:
        print('unrendered {{TOKEN}} left in: ' + ', '.join(leftover), file=sys.stderr)
        return 1

    print(f'{manifest["name"]} {version} -> {out}')
    print(f'  {n_skills} skill files, {n_scripts} scripts, {n_hooks} hooks, '
          f'1 monitor, {len(manifest["userConfig"])} userConfig keys')
    print(f'  validate:  claude plugin validate {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
