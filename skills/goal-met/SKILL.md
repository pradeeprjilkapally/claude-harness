---
name: goal-met
description: >-
  The gate before human review — first loop each smallest item to its own
  goal, then check that the real outputs and test results actually match the
  task's macro Goal, not just that the slices are ticked. If they do not
  match, append the plan and re-enter the workflow; hand over for review only
  once the goal is met, then doc-sync, review-gate, deploy-model. Invoked by
  the `workflow` skill after the build stage, or on a WORKFLOW [goalmet]
  directive.
---

# Goal met — the gate before handover

Every slice being ticked is not the same as the goal being met. Slices can each
pass and still leave the user-visible outcome missing, half-wired, or wired to
the wrong thing. This is the last gate that catches that.

## 0. Per-item goal loop — before the primary check

Before touching the macro Goal, work the smallest actionable items one at a
time. For each `- [ ]` item: run its own `Goal:` assertion, loop until it is
met, and **capture what was verified** beside it (real output, not "looks
right"). Do not move to the next item until the current one's goal is met.
Only once **every** item's goal is met does the primary check below run — an
unmet item goal is a stop, not a footnote.

## 1. Re-read the goal, not the slices

Read the active task's `Goal:` and macro `Done-check:` **first**, before looking
at what was built. Judging the goal by the diff you just produced is how a
half-done feature gets shipped.

## 2. Run the macro Done-check for real

Run it as written and capture the actual output. Then run the full suite:

```bash
python -m pytest -m "not live" -q
```

Both are evidence. "The slices passed" is not.

## 3. Compare against the goal

For each of Goal, Outputs, and macro Done-check, decide **met** or **not met**,
with the observed evidence beside it. Watch for:

- an output that exists but is not reachable from the user's path
- a check that passes on a fixture but not on the real path
- a slice that satisfied its local check by narrowing its own scope
- something in `Out-of-scope` that got touched anyway
- a previously green test now red (regression the slice checks did not cover)

## 3b. Real-path gate — sandbox evidence is not "verified"

Check each slice's `Verification surface:`. If a Done-check that proves the macro
Goal ran `sandboxed`/`fixture` (a temp dir, a fake keyring, a stub backend), the
goal is **not** proven on the user's path — do NOT write "verified". The `Result:`
must say `NOT VERIFIED ON REAL PATH — <what>`, and the real check (real Keychain,
real install/uninstall, real double-click) is either run now or filed as an
`action_items.md` row for {{OWNER}}. This is the
[[scar-sandbox-passed-real-path-failed]] gate: that exact gap once shipped as "no
code bug" on the strength of a fake-keychain test.

## 4a. If the goal is NOT met

1. Say exactly which part is unmet and what was observed.
2. **Append the plan** in `plans/<slug>_<date>_plan.md` — add the gap and the
   corrective slices; do not silently patch and re-declare victory.
3. Re-enter the workflow at the affected stage. New slices go through the RED
   check too — a corrective check gets the same true-negative scrutiny.
4. Return here. Loop until met.

## 4b. If the goal IS met

1. Fill the task's `Result:` with the evidence — what was verified, real numbers,
   suite count.
2. Set `Status: complete <date> — ship pending`. The block stays under `## Active`
   until its PR merges.
3. Run `second-brain-sync` (Haiku updates the second-brain `.md` files, committed
   into this same PR), then `review-gate` (diff review → goal alignment →
   evaluation pass → no-slop → shipping proof), then `deploy-model`.
4. Add the push item to `action_items.md` — never push automatically.
5. Hand over for human review, stating **verified / not-verified / known-issues**.

## Never

- Never hand over with a red done-check, however small — task-level or per-item.
- Never move a goalpost to make it green — if a check was wrong, say so, fix the
  check, and re-run it.
- Never claim a manual check was performed. Name it and hand it to {{OWNER}}.
