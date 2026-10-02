---
name: pr-conflicts
description: >-
  Invoked right after task.md is written (and ideally before cutting the
  branch) to guard against two in-flight branches colliding. Spawns a
  sub-agent that lists open PRs and checks whether any open PR touches the
  same files as the current task — every task edits the top of `## Active` in
  task.md and the memory.md mirror, so any two in-flight tasks collide there.
  If there is overlap, HOLD: hand the pending PR to {{OWNER}} to review + merge,
  wait for their confirmation, verify the merge landed, then resume. Runs as
  stage `pr-guard` in WORKFLOW.md, right after breakdown.
---

# PR conflicts — no parallel cuts that will collide

Two branches cut from `develop` in parallel always collide on `task.md` and
`memory.md`, because every task adds a block to the top of `## Active` /
appends to the mirror. This is the guard that catches the collision **before**
a second branch is cut, not after — see
[[feedback_branch_strategy_no_parallel_cuts]] (branches #80/#81 collided on
exactly this).

## 1. Spawn the checker

Use the Agent tool with a light model (Haiku is enough — this is a read-and-
list pass, not an investigation). Brief it with:

- the current task's `Files:` (macro + every slice, from the just-written
  `task.md` block)
- the instruction to run:

```bash
gh pr list --repo {{GH_REPO}} --state open --json number,title,headRefName,files
```

- for each open PR, diff its `files` against the current task's `Files:` **plus**
  the two always-touched paths, `task.md` and `memory.md` — those two collide on
  *every* pair of tasks regardless of what the task itself declares.
- report back: PR number, title, branch, and the exact overlapping path(s), or
  `NO-OVERLAP` if none.

## 2. Read the result

| Outcome | Action |
|---|---|
| `NO-OVERLAP` | proceed — branch, then continue the chain |
| overlap found | **HOLD** — do not cut the branch, do not proceed |

## 3. On overlap — hold and hand off

1. Tell {{OWNER}} exactly which open PR overlaps (number, title, files) and that
   the new task is held until it lands.
2. Wait for his explicit confirmation that he reviewed and merged it — do not
   merge it yourself, do not proceed on a guess that it's "probably fine."
3. Verify the merge landed for real:

```bash
git fetch origin develop
git log origin/develop -1 --format='%H %s'
```

   Confirm the merge commit for that PR is present before treating the hold as
   cleared.
4. Only then resume: cut the branch (or continue, if it was already cut) and
   proceed to `breakdown`.

## Never

- Never cut a second branch off `develop` while a colliding PR is still open —
  even "just to start the breakdown" recreates the exact collision this skill
  exists to prevent.
- Never treat "I opened the PR" as merged — confirm the fetch shows the commit
  on `develop`.
