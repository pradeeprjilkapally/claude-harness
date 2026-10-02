---
name: second-brain-sync
description: >-
  Invoked once the goal is met, BEFORE review-gate. Spawns a Haiku sub-agent
  to update every second-brain .md file the change touches — {{AGENT_DOC}},
  {{AGENT_DOC}}, WORKFLOW.md, README.md, BUILD.md, decisions/, .env.example, and
  the memory.md mirror — so the living reference matches reality. These edits
  are committed into the SAME task PR, never a separate one. The Haiku agent
  touches docs only, never code, and reports exactly which files it changed.
  Runs as stage `doc-sync` in WORKFLOW.md, right after goal-met.
---

# Second-brain sync — keep the living reference honest

The docs in this repo (`{{AGENT_DOC}}`, `{{AGENT_DOC}}`, `WORKFLOW.md`, `README.md`,
`BUILD.md`, `decisions/`, `.env.example`, `memory.md`) are read by the next
agent session as ground truth. A change that lands without updating them
leaves the reference lying — the next session inherits a stale picture and
re-derives what this session already learned.

## 1. Scope: which files actually changed

Before spawning, work out which of these the just-shipped change touches:

- **`{{AGENT_DOC}}` / `{{AGENT_DOC}}`** — module map, env vars, run commands, module
  responsibilities, conventions — if the change adds/removes a module, env
  var, command, or changes a described behavior.
- **`WORKFLOW.md`** — only for harness/skill/hook changes (the workflow itself).
- **`README.md` / `BUILD.md`** — user-facing run/build instructions, if changed.
- **`decisions/`** — a new dated ADR (`YYYY-MM-DD-HHMM-<slug>.md`) if this
  change is an infra/tooling/external-service decision that needs a Why /
  Impact / Alternatives record and doesn't already have one.
- **`.env.example`** — a new/removed env var.
- **`memory.md`** — only if the mirror is stale relative to what actually got
  written to project memory this session (rare — the memory-mirror hook
  usually keeps this current on its own).

Not every task touches every file — brief the agent with the actual set, not
the full list by default.

## 2. Spawn the sync agent

Use the Agent tool with `model: "haiku"`. Brief it with:

- the task's `Goal`, `Outputs`, and the diff/summary of what was built
- the scoped file list from step 1
- **hard constraint: docs only.** It must not touch any `.py`, test file,
  `task.md`, or anything under `agent/`/`pmClient/`/`scripts/` except the
  named doc paths.
- instruction to report back, per file it touched: the path and a one-line
  summary of what changed (not a full diff dump).

## 3. Verify the report

Per [[subagent-handshake]] — don't take the file list on faith. Read each
file it claims to have changed and confirm the edit is real, accurate, and
does not invent facts (no fabricated numbers, no describing behavior that
wasn't actually built). If it touched something outside the doc scope, that
is a constraint violation — send it back to revert the out-of-scope edit.

## 4. Commit into the SAME PR

These doc edits are not a follow-up PR. Stage and commit them on the same
feature branch, before the review-gate / deploy-model stages, so the PR that
ships the change also ships the doc that describes it.

```bash
git status                 # confirm only doc paths are staged
git add <the changed doc paths>
git commit -m "<task>-<slug>-docs"
```

## Never

- Never let the sync agent touch code, tests, or `task.md` — docs only.
- Never split doc updates into a separate PR "to keep this one small" — a
  code change and its doc update ship together or the reference goes stale
  the moment this PR merges.
- Never accept "updated the docs" without reading the actual diff of each
  claimed file.
