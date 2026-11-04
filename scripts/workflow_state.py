#!/usr/bin/env python3
"""Stage machine for the orchestrated task workflow.

The workflow runs one primary task from prompt to human review. The chain is the
lean model in WORKFLOW.md — branch is cut FIRST, before task.md:

    idle -> classify -> branch -> pr-guard -> breakdown -> redcheck -> plan
         -> build -> item-goals -> goal-met -> doc-sync -> review-gate -> deploy

Hooks are shell commands — they cannot spawn sub-agents. So this script is the
deterministic half: it tracks which stage the active task is in, enforces the
one-in-flight-task rule, and prints the directive a hook feeds back to the agent
(`hookSpecificOutput.additionalContext`). The agent-facing half — spawning Haiku
for the RED check, Fable/Opus for the plan, Sonnet for the build — lives in the
`workflow` skill, which acts on those directives.

Usage:
    workflow_state.py get                 -> current stage
    workflow_state.py set <stage>         -> force a stage
    workflow_state.py advance             -> move to the next stage
    workflow_state.py directive [<stage>] -> hook JSON for that stage
    workflow_state.py guard               -> exit 1 if >1 in-flight task
    workflow_state.py outcome             -> exit 1 if a task awaits an outcome
    workflow_state.py on-task-updated     -> guard + directive for redcheck
"""
import json
import os
import re
import sys

STAGES = ['idle', 'classify', 'branch', 'prguard', 'breakdown', 'redcheck',
          'plan', 'build', 'itemgoals', 'goalmet', 'docsync', 'reviewgate',
          'deploy']

# The three ways work actually ends. Anything else leaves a task in flight.
TERMINAL_OUTCOMES = ('merged', 'abandoned', 'taken-back')

STATE_FILE = '.claude/.workflow_state.json'
TASK_MD = 'task.md'

# What the agent must do on entering each stage. Emitted verbatim to the model.
# Keys are stage ids (STAGES); the human-readable tag in the text may differ
# (e.g. 'prguard' -> "WORKFLOW [pr-guard]").
DIRECTIVES = {
    'classify': (
        "WORKFLOW [classify]: classify the task type FIRST — coding | "
        "documentation | harness | manual. Coding runs the full chain; "
        "documentation/harness (skills, hooks, docs) take the lighter path "
        "(author the target file directly, skip the Haiku RED spawn) but still "
        "branch-first + pr-guard + goal-met + doc-sync + review-gate + deploy; "
        "manual (only {{OWNER}} can do it — an account login, a purchase, a secret) "
        "goes to action_items.md, not a build."
    ),
    'breakdown': (
        "WORKFLOW [breakdown]: break this primary task into macro -> micro "
        "(slices) -> single actionable items and write it to task.md in the "
        "three-level format. Anything only {{OWNER}} can do (an account login, a "
        "purchase, a secret, a dashboard setting) goes to action_items.md, not "
        "task.md. Do not start implementing."
    ),
    'redcheck': (
        "WORKFLOW [redcheck]: task.md was updated. BEFORE planning or building, "
        "spawn a Haiku sub-agent (Agent tool, model 'haiku') to run every "
        "done-check in the active task WITHOUT implementing anything. Every "
        "done-check MUST fail. Any check that passes against unbuilt code is a "
        "FALSE POSITIVE — redesign it so it genuinely exercises the change, and "
        "add it to the test suite so it is created fresh when required. Report "
        "each check as failing-as-expected or false-positive-redesigned. "
        "EXCEPTION: for a non-behavioral task — every slice's Files: is a "
        "doc/config/version file (*.md, setup.py, .gitignore) — the done-checks "
        "are trivially red (an absent file/tag); verify that inline and SKIP the "
        "Haiku spawn."
    ),
    'plan': (
        "WORKFLOW [plan]: done-checks verified red. Spawn a planning sub-agent "
        "(Agent tool, model 'fable'; fall back to 'opus' if fable is "
        "unavailable) to produce the implementation plan, then show it to "
        "{{OWNER}} for review. On his approval save it as "
        "plans/<one-three-words-of-goal>_<YYYY-MM-DD>_plan.md. Only ONE primary "
        "task may be in flight."
    ),
    'branch': (
        "WORKFLOW [branch]: cut feature/<NN-DDMMYY>-<slug> off develop NOW — "
        "BEFORE writing task.md. Branch-first is what stops two tasks colliding "
        "on task.md; task.md is written on the already-created branch, never "
        "before it exists. (scripts/plan_branch.py is only a fallback safety-net "
        "for the case where this was skipped.)"
    ),
    'prguard': (
        "WORKFLOW [pr-guard]: run the `pr-conflicts` skill — list open PRs and "
        "check whether any touches the same files as this task (every task edits "
        "the top of ## Active in task.md and the memory.md mirror, so two "
        "in-flight tasks collide there). If there is overlap, HOLD: hand the "
        "pending PR to {{OWNER}}, wait for it to merge, then resume. No parallel "
        "cuts from develop while a PR touching the same files is open."
    ),
    'build': (
        "WORKFLOW [build]: run `python scripts/slice_overlap.py` to group the "
        "slices. Slices with disjoint Files: -> spawn Sonnet sub-agents in "
        "PARALLEL, one per single actionable item, in a single message. Slices "
        "that share files -> spawn Sonnet sub-agents SEQUENTIALLY, one slice at "
        "a time. Gate each slice on its own done-check before committing it. "
        "Show {{OWNER}} each slice's diff PER SLICE (stream a parallel slice the "
        "moment its agent returns — do not batch to the end)."
    ),
    'itemgoals': (
        "WORKFLOW [item-goals]: for each smallest actionable item, loop until "
        "its OWN one-line goal is met and capture what was verified beside it. "
        "Only once every item's goal is met, proceed to the primary goal-met "
        "check."
    ),
    'goalmet': (
        "WORKFLOW [goalmet]: slices are built and the suite has run. Invoke the "
        "`goal-met` skill: compare the real outputs and test results against the "
        "macro Goal. If they do not match, append the plan and re-enter the "
        "flow. Proceed to doc-sync ONLY once the goal is met on the real path."
    ),
    'docsync': (
        "WORKFLOW [doc-sync]: run the `second-brain-sync` skill — spawn a Haiku "
        "sub-agent to update every second-brain .md the change touches "
        "(CLAUDE.md, AGENTS.md, WORKFLOW.md, README.md, BUILD.md, decisions/, "
        ".env.example, the memory.md mirror). Keep CLAUDE.md and AGENTS.md "
        "byte-identical. These edits are committed into THIS task's PR, not a "
        "separate one. VERIFY the sub-agent's edits against the real code — it "
        "has invented function names before."
    ),
    'reviewgate': (
        "WORKFLOW [review-gate]: walk the five gates in order, each its own "
        "looped check — 1 diff small enough (reviewed per slice during build), "
        "2 goal matches the change, 3 tests passed (RED pre-build + full suite "
        "green after), 4 no-slop over the changed files, 5 shipping proof "
        "(same-session evidence). Nothing ships that skips a line."
    ),
    'deploy': (
        "WORKFLOW [deploy]: run the `deploy-model` skill — HUMAN-GATED. OWN THE "
        "LOOP: this task is not finished when the code is written, it is finished "
        "when the PR is MERGED, the work is explicitly ABANDONED, or {{OWNER}} takes "
        "it back — and the `Outcome:` line in task.md records which. Open the "
        "feature->develop PR, ping {{OWNER}} the diff, merge on their 'good'; then "
        "open the develop->master PR, hand it to him, merge on his 'good'. Then "
        "write the Outcome line (`python3 scripts/check_merged.py` reports it). "
        "Never auto-merge. Packages build only on the master release tag "
        "(package.yml is release-tag-only). Add the push item to "
        "action_items.md — never push automatically (git push {{REMOTE}}, never "
        "origin)."
    ),
}


def _repo_file(name):
    return os.path.join(os.getcwd(), name)


def read_state():
    try:
        with open(_repo_file(STATE_FILE), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'stage': 'idle', 'task': None}


def write_state(state):
    path = _repo_file(STATE_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
        f.write('\n')


def active_blocks(task_md_text):
    """(task_id, status, outcome) for every block under '## Active'.

    Blocks are '## <NN-DDMMYY> — title' headings; the section ends at the next
    top-level heading (## Parked / ## Archive index). Field lines in a live
    block are unindented — the FORMAT comment keeps its example fields indented
    so the template text is not parsed as a real entry.
    """
    section = re.split(r'^## (?:Parked|Archive index)', task_md_text, flags=re.M)[0]
    out = []
    for chunk in re.split(r'^## (?=\d{2}-\d{6})', section, flags=re.M)[1:]:
        tid = re.search(r'^Task:\s+(\d{2}-\d{6})', chunk, re.M)
        status = re.search(r'^Status:\s*(.*)', chunk, re.M)
        outcome = re.search(r'^Outcome:\s*(.*)', chunk, re.M)
        if tid:
            out.append((tid.group(1),
                        (status.group(1) if status else '').strip(),
                        (outcome.group(1) if outcome else '').strip()))
    return out


def terminal_outcome(outcome):
    """The recorded outcome if it is one of the three that finish a task.

    Work is done when the PR is merged, the work is explicitly abandoned, or the
    owner takes it back — nothing else. Free text in the field is not an
    outcome: an unrecognised value leaves the task in flight rather than
    silently settling it.
    """
    first = outcome.strip().split()[0].rstrip(':').lower() if outcome.strip() else ''
    return first if first in TERMINAL_OUTCOMES else None


def in_flight(task_md_text):
    """Active blocks still being worked, as (task_id, status).

    A block leaves the in-flight set only when it is parked or carries a
    terminal Outcome. `Status: complete` alone does NOT release the slot: the
    PR may still be open, and a repo that treats `complete — ship pending` as
    finished loses track of whether the work ever landed.
    """
    live = []
    for tid, status, outcome in active_blocks(task_md_text):
        low = status.lower()
        if low.startswith('pending') or 'parked' in low:
            continue                       # deliberately set aside, not in flight
        if terminal_outcome(outcome):
            continue                       # merged / abandoned / taken back
        live.append((tid, status))
    return live


def settled(task_md_text):
    """(task_id, outcome) for every active block that reached a real end."""
    return [(tid, outcome) for tid, _, outcome in active_blocks(task_md_text)
            if terminal_outcome(outcome)]


def awaiting_outcome(task_md_text):
    """(task_id, status) for blocks marked complete with no outcome recorded.

    These are the ones to chase: the build is finished, so the only question
    left is whether the PR actually merged.
    """
    return [(tid, status) for tid, status, outcome in active_blocks(task_md_text)
            if status.lower().startswith('complete') and not terminal_outcome(outcome)]


def directive_json(stage):
    text = DIRECTIVES.get(stage)
    if not text:
        return None
    return json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': text,
        }
    })


def cmd_guard():
    try:
        text = open(_repo_file(TASK_MD), encoding='utf-8').read()
    except OSError:
        return 0                      # no task.md here — nothing to enforce
    live = in_flight(text)
    if len(live) > 1:
        ids = ', '.join(t for t, _ in live)
        print(json.dumps({'systemMessage':
                          f'WORKFLOW: {len(live)} in-flight tasks under ## Active '
                          f'({ids}). One primary task at a time — park the others, '
                          f'or finish them: a task is done only once its Outcome is '
                          f'recorded (merged / abandoned / taken-back). Run '
                          f'`python3 scripts/check_merged.py` to see which already '
                          f'merged.'}))
        return 1
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'get'
    state = read_state()

    if cmd == 'get':
        print(state.get('stage', 'idle'))
    elif cmd == 'set':
        stage = argv[2]
        if stage not in STAGES:
            print(f'unknown stage: {stage}', file=sys.stderr)
            return 2
        state['stage'] = stage
        write_state(state)
        print(stage)
    elif cmd == 'advance':
        cur = state.get('stage', 'idle')
        i = STAGES.index(cur) if cur in STAGES else 0   # a retired stage -> restart
        nxt = STAGES[min(i + 1, len(STAGES) - 1)]
        state['stage'] = nxt
        write_state(state)
        print(nxt)
    elif cmd == 'directive':
        stage = argv[2] if len(argv) > 2 else state.get('stage', 'idle')
        out = directive_json(stage)
        if out:
            print(out)
    elif cmd == 'guard':
        return cmd_guard()
    elif cmd == 'outcome':
        try:
            text = open(_repo_file(TASK_MD), encoding='utf-8').read()
        except OSError:
            print('task.md not found at the repo root.')
            return 0
        waiting = awaiting_outcome(text)
        for tid, status in waiting:
            print(f'{tid:<12} AWAITING OUTCOME  ({status})')
        for tid, outcome in settled(text):
            print(f'{tid:<12} {terminal_outcome(outcome).upper():<17} {outcome}')
        if not waiting and not settled(text):
            print('no active task has reached completion yet.')
        return 1 if waiting else 0
    elif cmd == 'on-task-updated':
        # task.md was written: enforce one-in-flight, then demand the RED check —
        # but ONLY for a genuinely new task. A progress edit (tick a box, fill
        # Result, mark complete) on the task already in flight must not re-fire
        # the directive, or the RED check nags on every edit of a task's lifetime.
        if cmd_guard() != 0:
            return 0                  # guard already spoke; don't stack messages
        try:
            text = open(_repo_file(TASK_MD), encoding='utf-8').read()
        except OSError:
            return 0
        live = in_flight(text)
        current = live[0][0] if live else None
        prev_task = state.get('task')
        prev_stage = state.get('stage', 'idle')

        if current is None:
            # No task in flight (all complete / parked) — a completion or
            # housekeeping edit. Nothing to red-check; forget the tracked task.
            state['task'] = None
            write_state(state)
            return 0
        intake = ('idle', 'classify', 'branch', 'prguard', 'breakdown')
        if current == prev_task and prev_stage not in intake:
            # Same task, already past intake — a mid-flight progress edit. No-op.
            return 0

        # A genuinely new task (id changed, or first write from idle/breakdown).
        state['task'] = current
        state['stage'] = 'redcheck'
        write_state(state)
        print(directive_json('redcheck'))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
