# Task

<!--
FORMAT — three levels, one file.

    MACRO  a task      ## <NN-DDMMYY> — <title>     one branch, one PR, one outcome
    MICRO  a slice     ### S<n> — <outcome>          one commit, own Done-check
    ITEM   an action   - [ ] <action>                atomic; the text is the assertion

The field lines in THIS comment are indented on purpose. The pre-push guard and
workflow_state.py both anchor on `^Task:`, so an unindented example here would
register as a real task and the guards would read the template as live work. In
a real block the fields are NOT indented.

  Task:         <NN-DDMMYY>  — REQUIRED, line-anchored, parsed by
                scripts/check_task_tracked.py. NN restarts at 01 each day.
  Date:         when the task was filed
  Type:         coding | documentation | harness | manual
  Status:       active · S<n>/<total>  |  pending — parked <date>  |  complete <date>
                Short and machine-readable. Evidence goes in Result:, not here.
  Outcome:      merged <ref> | abandoned <date> — <why> | taken-back <date>
                Left EMPTY while the work is in flight. `Status: complete` means
                the build is done; it does NOT mean the work landed. Until this
                line is set the task is still chased — the guard reports it on
                every stop, and `python3 scripts/check_merged.py` asks the forge
                what actually merged and prints the line to record.
                Completing a task frees the one-in-flight slot, so the next task
                can start while this one waits on review.
  Branch:       feature/<NN-DDMMYY>-<slug>
  Goal:         the one outcome, in a sentence
  Constraints:  what it must and must not do
  Inputs:       the file surface for the whole task
  Outputs:      what exists when it is finished
  Done-check:   END-TO-END proof for the whole task. NOT the sum of the slice
                checks — it is the user-visible assertion that only holds once
                the slices compose. A task whose Done-check merely restates its
                slices has no gate.
  Out-of-scope: what not to touch
  Result:       written at completion — the evidence, one paragraph

  Per slice (### S<n>):
  Files:        only the files this slice touches — makes a slice resumable
                alone, and is what scripts/slice_overlap.py reads to decide
                parallel vs sequential. Real paths, no prose.
  Done-check:   a runnable command with its expected result, or
                MANUAL — <observation> plus who performs it and when.

Lifecycle:
  ACTIVE    one task being worked at a time (scripts/workflow_state.py guard).
  PARKED    Status becomes "pending — parked <date>"; the block moves to
            ## Parked and stops holding the slot.
  COMPLETE  Status becomes "complete <date>"; Result: carries the evidence. The
            slot is free, but the task is not finished — it is still chased
            until Outcome: is recorded.
  ARCHIVED  once the PR has merged and Outcome: is set, the whole block moves to
            task_archive.md and ONE index row stays below under
            ## Archive index. Blocks are never commented out.

Copy the scaffold between the markers below into ## Active to start a task.

COPY FROM HERE
## <NN-DDMMYY> — <title>

Task:         <NN-DDMMYY>
Date:
Type:
Status:       active · S1/1
Outcome:
Branch:       feature/<NN-DDMMYY>-<slug>
Goal:
Constraints:
Inputs:
Outputs:
Done-check:
Out-of-scope:
Result:

### S1 — <the outcome this slice delivers>

Files:
Done-check:
- [ ] <the first atomic action>
TO HERE
-->

## Active

## Parked

## Archive index

<!--
One row per archived task, newest first. The `Task:` prefix is required — the
pre-push guard resolves historical ids from these rows, and ## Archive index
ends the Active section so a row here never counts as work in flight.

Task: <NN-DDMMYY> | <date> | <goal snippet> | complete | → task_archive.md#<NN-DDMMYY>
-->
