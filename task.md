# Task

<!--
FORMAT — three levels, one file.

    MACRO  a task      ## <NN-DDMMYY> — <title>     one branch, one PR, one outcome
    MICRO  a slice     ### S<n> — <outcome>          one commit, own Done-check
    ITEM   an action   - [ ] <action>                atomic; the text is the assertion

Field lines are indented so they never match the `^Task:` regex the pre-push
guard and the commit-message hook key on — do not un-indent them.

  Task:         <NN-DDMMYY>  — REQUIRED, line-anchored, parsed by
                scripts/check_task_tracked.py. The ACTIVE task must be the
                first such line in this file.
  Status:       active · S<n>/<total>  |  pending — parked <date>  |  complete <date>
  Outcome:      merged <ref> | abandoned <date> — <why> | taken-back <date>
                The task is NOT finished until this line is set. Status
                `complete` with no Outcome still occupies the in-flight slot.
  Branch:       feature/<NN-DDMMYY>-<slug>
  Goal:         the one outcome, in a sentence
  Done-check:   END-TO-END proof for the whole task — a runnable command with
                its expected result, or a named manual observation. Never a
                description of intent.
-->

## Active

## 01-061126 — the seeded task.md is in the format the parsers read

Task:         01-061126
Date:         2026-11-06
Status:       complete 2026-11-06 — ship pending
Outcome:
Branch:       feature/01-061126-task-template
Type:         harness improvement
Goal:         A freshly seeded repo gets a task.md that workflow_state and the
              pre-push guard can actually read, and awaiting a merge no longer
              blocks the next task from starting.
Constraints:  The template must still parse to ZERO in-flight tasks when
              untouched, and must never satisfy the pre-push guard's ^Task:
              grep with its own example text. Archive rows keep their
              unindented `Task:` prefix so historical ids still resolve.
              Stacked on feature/01-041126-grok-parity: that branch merges
              first.
Inputs:       templates/root/task.md, templates/root/task_archive.md,
              scripts/workflow_state.py, skills/jarvis/SKILL.md,
              skills/task-breakdown/SKILL.md, docs/WORKFLOW.md
Outputs:      a three-level templates/root/task.md with a copyable scaffold;
              in_flight/awaiting_outcome split; tests/test_template.py
Done-check:   `python3 -m pytest tests -q` green, and in a fresh
              `./install.sh <scratch>` repo
              `python3 scripts/workflow_state.py guard` exits 0 while
              the seeded task.md parses to zero blocks — then filling the
              template's own scaffold yields exactly one in-flight task that
              satisfies `check_task_tracked.py`.
Out-of-scope: The jarvis/task-breakdown skills' own prose (already correct).
              No change to how task_archive.md is structured.
Result:       46 tests green. In a fresh `./install.sh` repo the seeded task.md
              now parses: zero in-flight blocks and zero documented ids on a
              clean slate, three headings in order. Copying its own scaffold
              into ## Active — the way an agent would — yields exactly one
              in-flight task (`01-061126`, `active · S1/1`), and the real
              pre-push guard then passes for that branch while correctly
              BLOCKING `feature/99-311299-undocumented` (exit 1). Before this,
              a seeded file parsed to nothing and both guards were inert.
              S1 also corrected 01-041126: `complete — ship pending` no longer
              holds the one-in-flight slot (that stalled the next task behind a
              human merge gate); it is now reported by a non-blocking nudge
              instead. This task's own Outcome stays blank until its PR merges.

### S1 — awaiting a merge no longer blocks the next task

Files:        scripts/workflow_state.py, tests/test_outcome.py
Done-check:   `python3 -m pytest tests/test_outcome.py -q` green with a
              `complete`-no-Outcome block counted as NOT in flight but still
              listed by `workflow_state.py outcome`.
- [ ] in_flight() means "being worked": parked and complete both release the slot
- [ ] the guard still reports unrecorded outcomes, as a warning that never blocks
- [ ] tests/test_outcome.py pins the distinction rather than the old conflation

### S2 — the seeded template is the three-level format

Files:        templates/root/task.md, tests/test_template.py, docs/WORKFLOW.md
Done-check:   `python3 -m pytest tests/test_template.py -q` green: the untouched
              template parses to zero blocks and satisfies no guard, and its own
              copyable scaffold fills in to exactly one readable task.
- [ ] Active / Parked / Archive index sections, in that order
- [ ] a COPY FROM HERE scaffold carrying macro + slice + item
- [ ] the lifecycle prose matches the archive model, not comment-it-out

## 01-041126 — port the four Grok "own the loop" entities and ship the harness as a plugin

Task:         01-041126
Date:         2026-11-04
Status:       complete 2026-11-04 — ship pending
Outcome:
Branch:       feature/01-041126-grok-parity
Type:         harness improvement
Goal:         The harness gains the four load-bearing behaviours Grok's
                  Engineering Lead bot has and it lacks — a terminal merge
                  outcome, an edge-triggered CI chase, a quiet-first reporting
                  contract, and steer-before-respawn — and installs as a Claude
                  Code plugin in one command instead of two shell installers.
Constraints:  Report-only: the CI watcher never commits, pushes, or merges.
                  No always-on agent loop — polling stays a dumb script, agent
                  tokens are spent only on a state change. One source for the
                  skills: the installer's {{TOKEN}} render path must keep
                  working byte-for-byte alongside the new plugin render.
                  Plugin name cannot start with `claude-` (reserved).
Inputs:       skills/ (16), scripts/, hooks/, templates/, docs/WORKFLOW.md,
                  install.sh, README.md
Outputs:      scripts/check_merged.py, scripts/ci_watch.py,
                  scripts/build_plugin.py, skills/report-cadence/SKILL.md,
                  .claude-plugin/marketplace.json, templates/plugin/,
                  amended workflow_state.py + subagent-handshake + task.md
                  template + WORKFLOW.md + README.md
Done-check:   `python3 scripts/build_plugin.py && claude plugin validate
                  ./dist/plugin` prints "Validation passed", and
                  `claude plugin validate ./.` passes for the marketplace;
                  `python3 scripts/ci_watch.py --once` prints a CI state line
                  without writing anything; `python3 -m pytest tests -q` green.
Result:       All four entities landed and the plugin installs. Verified:
              `claude plugin validate ./dist/plugin` and `claude plugin
              validate .` both print "Validation passed"; the plugin installed
              and enabled at user scope with its three userConfig values
              stored in ~/.claude/settings.json; 33 tests green; a
              plugin-delivered workflow_state.py resolved OWNER=Pradeep and
              REMOTE=rebalancer from a scratch repo's own marker at runtime;
              install.sh still renders the installer path with zero tokens
              left. check_merged.py resolved all 12 of pyPMClient's stale
              "ship pending" tasks to real merged PRs (#80-#105). This task's
              own Outcome is deliberately blank — by its own rule it is not
              finished until the PR merges.
Out-of-scope: The stale two-level templates/root/task.md vs the three-level
                  format the parser expects (pre-existing; filed as a follow-up,
                  not fixed here). No auto-fix-PR autonomy. No external
                  notifications. No hosted marketplace.

### S1 — a task is not done until its outcome is recorded

Files:        scripts/check_merged.py, scripts/workflow_state.py,
                  templates/root/task.md, tests/test_outcome.py
Done-check:   `python3 -m pytest tests/test_outcome.py -q` green: a block at
                  `Status: complete` with no `Outcome:` still counts as in
                  flight; the same block with `Outcome: merged #12` does not.
    - [ ] check_merged.py reports a task's real merge state from gh, failing open
    - [ ] in_flight() releases the slot only on a recorded terminal Outcome
    - [ ] the seeded task.md template carries the Outcome field and its rule

### S2 — CI state changes reach the agent without it polling

Files:        scripts/ci_watch.py, tests/test_ci_watch.py
Done-check:   `python3 scripts/ci_watch.py --once` exits 0 and prints one
                  state line; `pytest tests/test_ci_watch.py -q` green on the
                  edge-trigger (same state twice prints once).
    - [ ] poll gh pr checks and print only on a state transition
    - [ ] --once read-only on-demand mode, no side effects
    - [ ] silent when the branch has no PR, so it never spams a session

### S3 — the reporting contract and steer-before-respawn are written down

Files:        skills/report-cadence/SKILL.md,
                  skills/subagent-handshake/SKILL.md, docs/WORKFLOW.md
Done-check:   MANUAL — the new skill states the three speak-now triggers
                  (blocked / ready to merge / done) and WORKFLOW.md's chain
                  names report-cadence; grep confirms both.
    - [ ] report-cadence skill: silent while healthy, batch the rest
    - [ ] subagent-handshake makes SendMessage-to-existing the default spawn
    - [ ] WORKFLOW.md records both in the active chain

### S4 — the harness installs as one plugin

Files:        scripts/build_plugin.py, .claude-plugin/marketplace.json,
                  templates/plugin/plugin.json, templates/plugin/hooks.json,
                  templates/plugin/monitors.json, .gitignore, README.md, VERSION
Done-check:   `python3 scripts/build_plugin.py && claude plugin validate
                  ./dist/plugin` prints "Validation passed"; the built skills
                  contain `${user_config.owner}` and no `{{OWNER}}` remains.
    - [ ] build_plugin.py renders the one skill source into a plugin tree
    - [ ] manifest declares skills, hooks, monitors and the three userConfig keys
    - [ ] README documents the plugin path beside the installer path

## Parked

## Archive index
