---
name: jarvis
description: >-
  Triggered when the user types "jarvis". Reads task.md, parses the active task
  and its slices, and immediately starts executing the first open slice without
  further prompting. Also fires at the start of each session to show the current
  task state for review. Covers the full task lifecycle: intake, three-level
  breakdown, slice-by-slice execution, completion (archive + index row), and
  parking.
---

# Jarvis — task execution skill

{{AGENT_DOC}} mandates: when the user types `jarvis`, read `task.md` and start the
task without further prompting.

## 1. Read task.md

```bash
cat task.md
```

The file has three sections: **Active**, **Parked**, **Archive index**.
Completed tasks live in `task_archive.md`; `task.md` keeps only a one-line
`Task: <id> | … | → task_archive.md#<id>` row for each.

## 2. Identify the active task and its open slice

Work is tracked at three levels:

| Level | Marker | Scope |
|---|---|---|
| **macro** — task | `## <NN-DDMMYY>` + a `Task:` field line | one branch, one PR, one outcome |
| **micro** — slice | `### S<n> — <outcome>` | one commit, its own `Done-check` |
| **item** — action | `- [ ]` | atomic; the text is the assertion |

The **active task** is the first block under `## Active` with a non-empty
`Goal:`. Within it, the **active slice** is the first `### S<n>` whose box is
`[ ]`. Start there — not at the top of the task.

If there is no such block, respond:

> No active task found in task.md. File a task (Goal, Constraints, Inputs,
> Outputs, Done-check, Out-of-scope + its slices) and type `jarvis` again.

## 3. Execute the open slice without prompting

Read the task's Goal / Constraints / Out-of-scope, then the slice's `Files:` and
`Done-check:`. Act immediately. Do not ask clarifying questions unless the task
is genuinely ambiguous in a way that blocks starting.

Work **one slice at a time**. Adhere strictly to Out-of-scope.

## 4. Gate every slice on its own Done-check

A `Done-check` — at either level — is a runnable command with its expected
result, or a named manual observation with an owner. Never a description of
intent.

1. Finish the slice's items.
2. **Run** its `Done-check` and capture the real output.
3. Only then tick it, recording the evidence inline:

```
### S1 — purge core                  [x] 2026-07-22 · 8 passed
```

4. Commit that slice: `<task-id> (slice <n>): <short goal>`.

A failed check leaves the box `[ ]` with the failure recorded. Never a partial
tick, never an unrun check.

## 5. Close the task

When every slice is ticked, run the **macro `Done-check`** — the end-to-end,
user-visible assertion. It is a separate gate, not the sum of the slice checks;
if it fails, the task is not done however many slices are green.

Then, per the review-gate: tests green → PR. On completion:

1. Fill `Result:` with the evidence (what was verified, suite count).
2. Set `Status: complete <date> — ship pending`. The block **stays under Active**
   until the PR merges — moving it now would leave the commit-format hook
   resolving a parked id for the still-in-flight branch.

Once the PR has merged:

3. **Move the whole block to `task_archive.md`** (newest first, under a
   `## <NN-DDMMYY>` heading).
4. Leave one index row in `task.md` under **Archive index**:

```
Task: <NN-DDMMYY> | <date> | <goal snippet> | complete | → task_archive.md#<NN-DDMMYY>
```

The `Task:` prefix is required — the pre-push guard resolves historical ids from
these rows.

5. Open a fresh block under **Active** for the next task.

## 6. Park a task

If {{OWNER}} says to park mid-execution, set `Status: pending — parked <date>`,
move the block under **Parked** with its slice state intact, and leave the
completed slices ticked so it can be resumed exactly where it stopped.

## 7. Append follow-ups to action_items.md

After completing or parking any task, append leftover items — a pending push, a
config step, a manual verification — to `action_items.md` under the **Open**
table. One row per item, newest on top, with today's date.

## 8. Session start

At the start of each session, briefly summarise:
- The active task (Goal + `Status: active · S<n>/<total>`) and which slice is open
- Whether any tasks are parked

Then wait for `jarvis` to start execution.

## Conventions

- **Never** touch files listed in Out-of-scope.
- **Never** tick a box whose `Done-check` was not run this session.
- **Always** end delivery with: `verified / not-verified / known-issues` plus the
  Done-check result.
- The **active task must be the first `Task:` line in `task.md`** — the global
  commit-format hook takes the first match to build the commit message.
- If the task requires a push, do not push automatically — add a push item to
  `action_items.md` and remind {{OWNER}} to run `git push {{REMOTE}} master`.
- Task numbering: `<NN>-<DDMMYY>` — `NN` resets to `01` for the first task each day.
