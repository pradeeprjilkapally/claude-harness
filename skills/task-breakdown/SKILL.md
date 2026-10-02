---
name: task-breakdown
description: >-
  Break a primary task into macro (task) -> micro (slice) -> single actionable
  item and write it to task.md in the three-level format, so the change is
  readable when handed over for human review. Classifies the task type first
  (coding | documentation | harness | manual) and gives every item its own
  goal. Splits out anything only {{OWNER}} can do into action_items.md. Runs on
  the branch already cut for the task, as the `workflow` skill's stage after
  branch, or directly when a task needs filing before work starts.
---

# Task breakdown — macro → micro → item

Every change to this repo gets a `task.md` entry **before the work starts**,
written on the branch that was already cut for it (branch-first — see below).
This skill produces that entry at the three levels the file tracks.

## 0. Classify the task type first

Before filling in any field, decide the type and record it on the macro entry
as a `Type:` field:

| Type | What it is | Path |
|---|---|---|
| **coding** | app behaviour changes | the full chain: RED check, plan, Sonnet build |
| **documentation** | README/docs/`.md` only | lighter: author the `.md` directly — skip RED/plan/Sonnet-build |
| **harness** | skills, hooks, loops, the workflow itself | same lighter path as documentation, and the change also updates `WORKFLOW.md` |
| **manual** | only {{OWNER}} can do it | goes to `action_items.md`, not a `task.md` entry |

When the initial context already gives a detailed spec or an obvious edit,
docs/harness tasks skip the nudging ceremony and go straight to authoring the
target `.md`/skill files, with `Type:` still noted in the entry.

## 1. Branch-first — this runs on an already-cut branch

`feature/<NN-DDMMYY>-<slug>` is cut off develop **before** this skill runs
(the `workflow` skill's branch stage, before breakdown). Confirm you are on
that branch before writing anything — this entry is written on it, never on
develop.

## The three levels

| Level | Marker | Rule of thumb |
|---|---|---|
| **macro** — task | `## <NN-DDMMYY> — <title>` | one branch, one PR, one outcome. If it needs two branches, it is two tasks. |
| **micro** — slice | `### S<n> — <outcome>` | one commit, its own `Done-check`, its own `Files:`. A slice a reviewer can read in one sitting. |
| **item** — action | `- [ ]` | atomic. Names a real file, function or test, and carries its own one-line `Goal:`. If it needs its own verification step, it is a slice, not an item. |

## Where work goes

- **`task.md`** — everything an agent can do, including config and infra edits.
- **`action_items.md`** — only what an agent *genuinely cannot* do in any case:
  an account login {{OWNER}} must complete, a domain they must buy, a secret they must enter,
  a dashboard setting only he can change, a push. One row per item, newest on
  top, with today's date.

Getting this split wrong is the common failure: "I'll let {{OWNER}} do it" for
something an agent can do is not an action item.

## Producing the entry

1. **Check the guard first** — `python scripts/workflow_state.py guard`. One
   primary task in flight at a time; a `complete … ship pending` block does not
   count (it is awaiting a PR).
2. **Number it** `<NN>-<DDMMYY>`, `NN` restarting at `01` each day. Read the
   existing Active + Archive index rows for today's highest number.
3. **Fill the macro fields** — Task, Type, Date, Status (`active · S1/<n>`),
   Branch, Goal, Constraints, Inputs, Outputs, Done-check, Out-of-scope, Result.
4. **Write the macro `Done-check` as the end-to-end assertion.** It is NOT the
   sum of the slice checks — it is what a user can observe once the slices
   compose. If it only restates the slices, the task has no gate.
5. **Cut the slices.** Each gets:
   - `Files:` — only what that slice touches. This is what
     `scripts/slice_overlap.py` reads to decide parallel vs sequential, so list
     real paths, no prose.
   - `Done-check:` — a runnable command with its expected result, or
     `MANUAL — <observation>` plus who performs it.
   - `Verification surface:` — `real | sandboxed(<why>) | fixture(<why>)`. Where
     the Done-check actually runs. Required whenever the task touches secrets, the
     Keychain, install/uninstall, or where data lives — the scar
     [[scar-sandbox-passed-real-path-failed]] is what happens when a fixture pass
     is reported as real-world "verified". `sandboxed`/`fixture` is allowed, but
     then `goal-met` forces the Result to say `NOT VERIFIED ON REAL PATH` and the
     real check becomes a follow-up or an `action_items.md` row for {{OWNER}}.
6. **Write the items** as `- [ ]` under each slice. **Every smallest actionable
   item gets its own `Goal:`** — a one-line assertion of what that specific item
   must achieve and how it's verified, the same discipline as the macro Goal,
   scaled down. This is what the `goal-met` per-item loop checks off one at a
   time before the primary macro check runs.
7. **Facts only.** Real file names, real values traced to source, the actual
   check. No invented numbers, no vague goals, no placeholder slices.

## Do not

- Do not start implementing. Breakdown ends when `task.md` is written — the
  RED done-check stage runs next (skipped for docs/harness types).
- Do not tick any box. Nothing is ticked until its `Done-check` (or per-item
  `Goal:`) has been run.
- Do not file a second in-flight task to "get ahead".
