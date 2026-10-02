#!/usr/bin/env python3
"""Decide which slices of the active task can be built in parallel.

Each slice in task.md carries a `Files:` line naming only what it touches. Slices
whose file sets are disjoint can be handed to Sonnet sub-agents concurrently;
slices sharing a file must run one after another or they clobber each other.

Grouping is transitive: A-B overlap and B-C overlap puts A, B and C in one
sequential chain even when A and C are disjoint.

Usage:  slice_overlap.py [task.md]
Output: PARALLEL groups (build concurrently) and SEQUENTIAL chains (one at a
        time, in slice order). Exit 0 always — this informs, it does not gate.
"""
import re
import sys

BRACE_RE = re.compile(r'^(?P<head>.*?)\{(?P<alts>[^}]*)\}(?P<tail>.*)$')


def expand(token):
    """agent/{a,b}.py -> ['agent/a.py', 'agent/b.py']; anything else -> [token]."""
    m = BRACE_RE.match(token)
    if not m:
        return [token]
    head, tail = m.group('head'), m.group('tail')
    return [f'{head}{alt.strip()}{tail}' for alt in m.group('alts').split(',') if alt.strip()]


def active_task_chunk(text):
    """The first '## NN-DDMMYY' block under '## Active'."""
    section = re.split(r'^## (?:Parked|Archive index)', text, flags=re.M)[0]
    blocks = re.split(r'^## (?=\d{2}-\d{6})', section, flags=re.M)[1:]
    return blocks[0] if blocks else ''


def parse_slices(text):
    """[(slice_title, {files}), ...] for the active task, in file order."""
    chunk = active_task_chunk(text)
    out = []
    parts = re.split(r'^### ', chunk, flags=re.M)[1:]
    for part in parts:
        title = part.split('\n', 1)[0].strip()
        title = re.sub(r'\s*\[[ x]\].*$', '', title).strip()
        # Files: may wrap onto continuation lines (indented, no `Field:` prefix).
        m = re.search(r'^Files:\s*(.*(?:\n\s{2,}(?![A-Z][a-z-]+:).*)*)', part, re.M)
        files = set()
        if m:
            for tok in re.split(r'[,\s]+', m.group(1)):
                tok = tok.strip().rstrip(',;')
                if tok and not tok.endswith(':'):
                    files.update(expand(tok))
        out.append((title, files))
    return out


def group(slices):
    """Union-find over shared files -> list of groups, each a list of indices."""
    parent = list(range(len(slices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(len(slices)):
        for j in range(i + 1, len(slices)):
            if slices[i][1] & slices[j][1]:
                union(i, j)

    groups = {}
    for i in range(len(slices)):
        groups.setdefault(find(i), []).append(i)
    return [sorted(v) for _, v in sorted(groups.items())]


def report(slices, groups):
    lines = []
    parallel = [g for g in groups if len(g) == 1]
    chains = [g for g in groups if len(g) > 1]

    if parallel:
        lines.append(f'PARALLEL — {len(parallel)} slice(s), no shared files. '
                     f'Spawn these Sonnet sub-agents concurrently, in ONE message:')
        for g in parallel:
            title, files = slices[g[0]]
            lines.append(f'  · {title}   [{", ".join(sorted(files)) or "no files listed"}]')
    for chain in chains:
        shared = set.intersection(*(slices[i][1] for i in chain))
        lines.append(f'SEQUENTIAL — {len(chain)} slices share files '
                     f'({", ".join(sorted(shared)) or "transitively"}). '
                     f'One Sonnet sub-agent at a time, in this order:')
        for i in chain:
            title, files = slices[i]
            lines.append(f'  {chain.index(i) + 1}. {title}   [{", ".join(sorted(files))}]')
    if not lines:
        lines.append('No slices with a Files: line found in the active task.')
    return '\n'.join(lines)


def main(argv):
    path = argv[1] if len(argv) > 1 else 'task.md'
    try:
        text = open(path).read()
    except OSError as e:
        print(f'slice_overlap: {e}', file=sys.stderr)
        return 2
    slices = parse_slices(text)
    print(report(slices, group(slices)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
