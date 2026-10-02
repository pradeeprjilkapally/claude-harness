---
name: red-check
description: >-
  Verify every done-check FAILS before anything is built — the true-negative
  gate. Spawns a Haiku sub-agent to run each done-check in the active task
  against the unbuilt code; any check that passes is a false positive and gets
  redesigned, then added to the test suite. Runs after task.md is written and
  before planning. Invoked by the `workflow` skill or a WORKFLOW [redcheck]
  directive.
---

# RED check — prove the tests can fail

A done-check that passes before the feature exists proves nothing. It will also
pass after, and it will pass if the implementation is deleted. This stage catches
those **false positives while they are still cheap to fix** — before a plan is
written, before a line is built.

## 1. Two roles: Opus BUILDS the suite, Haiku EXECUTES

Split the models by role — do not have one model both author and run the tests:
- **Opus builds the test suite** (`model: "opus"`) — authors the tests and ensures
  they cover **every aspect** of the change (the judgement part). This is where the
  RED tests are designed/redesigned.
- **Haiku executes** (`model: "haiku"`) — runs the suite against the *unbuilt* code
  to confirm each check fails (red) for the right reason. Running is cheap and
  deterministic — that is Haiku's job, not authoring.

The main agent loops the two until the suite is complete and correctly red. (One
Haiku pass suffices to execute; Opus iterates on coverage.)

Brief them with, verbatim from the active `task.md` block:
- the macro `Done-check`
- every slice's `Done-check` and its `Files:`
- the `Constraints` (so it does not "helpfully" fix anything)

**Its instructions must include:** run each check exactly as written, against the
current unbuilt tree. Implement nothing. Create nothing except a test file the
check itself names. Report, per check: the command, the real output, and
`FAILS-AS-EXPECTED` or `PASSES-UNEXPECTEDLY`.

## 2. Read the result

| Outcome | Meaning | Action |
|---|---|---|
| `FAILS-AS-EXPECTED` | the check genuinely exercises the unbuilt change | keep it |
| `PASSES-UNEXPECTEDLY` | **false positive** | redesign — see below |
| `INCONCLUSIVE` | it broke for a reason unrelated to the change | make it runnable, re-run |

**Not every error is inconclusive.** `ModuleNotFoundError` for the module you are
about to write, or `file or directory not found` for the test file this task
creates, *is* the correct red — the check is pointing at the absent thing. What
makes a result inconclusive is failing for a reason the task will never fix: a
typo in the command, a missing dev dependency, the wrong interpreter, a fixture
error in an unrelated file. The test: **would completing this task turn this
exact failure green?** Yes → red for the right reason. No → inconclusive, fix the
check.

## 3. Redesign every false positive

Typical causes and the fix:

- **Asserts something already true** ("the module imports", "the route exists")
  → assert the new *behavior* and its value, not presence.
- **Tautological** (asserts a literal, or re-computes the thing under test)
  → assert against an independently known expected value.
- **Too loose** (`assert result` , `status != 500`) → assert the exact value,
  status, and side effect.
- **Mocked past the change** → let the code path under test actually run.
- **Manual check with no observable** ("looks right") → name the exact string,
  file, or state to observe, and who observes it.

Rewrite the check in `task.md`, then re-run it through the Haiku agent. Repeat
until every check is red for the right reason.

## 4. Land the tests in the suite

Automated checks must exist as real test files under `tests/`, collected by the
normal run — **not** as ad-hoc commands that vanish with the session. They are
expected to fail right now; that is the point. Do not mark them skipped or
xfail — a skipped test is not a gate.

Confirm collection:

```bash
python -m pytest tests/ -q --collect-only | tail -3
```

## 5. Report and hand back

State per check: `failing-as-expected` or `false-positive-redesigned (<why>)`.
Then the workflow moves to the plan stage. **Do not plan or build from this
skill** — it ends when every check is legitimately red.
