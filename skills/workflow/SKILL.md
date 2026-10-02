---
name: workflow
description: >-
  The primary orchestration skill — invoke it whenever {{OWNER}} gives a primary
  task (a feature, a fix, an infra change, anything that will touch this repo)
  rather than a question or a one-off command. Drives the lean chain: classify
  task type -> branch first (before task.md) -> pr-guard -> breakdown (every
  item gets its own goal) -> RED check looped with the test-suite (Haiku) ->
  plan (Fable, {{OWNER}} approves) -> build (Sonnet) -> per-item goal loop ->
  goal-met -> doc-sync (Haiku, same PR) -> review-gate -> deploy-model. Also
  invoke it when the user says "workflow", or when a WORKFLOW [stage]
  directive appears from a hook.
---

# Workflow — one task, prompt to human review

This sits **on top of** the existing conventions; it does not replace them.
`jarvis` still executes a filed task, `ledger` still owns `action_items.md`.
This skill is the sequencing layer that makes every other skill fire in the
right order.

**`WORKFLOW.md` at the repo root is the source of truth for this chain** — this
skill mirrors it; if the two drift, `WORKFLOW.md` wins and this file gets
corrected. The full parallel-orchestration variant (persistent monitor agent,
parallel plan+build, concurrent handshake loops) is parked, inactive, in
`WORKFLOW_FULL_ORCHESTRATION.md` — for token-abundant days only, never run
without {{OWNER}} explicitly switching it on.

**Lean means the main agent mediates every loop in-line** — the RED-check ↔
test-suite loop, the per-item goal loop, and the review-gate loop all run
without a persistent parallel or monitor agent. Same gates, same loops, a
fraction of the tokens.

## The chain

```
prompt
  -> classify     task type: coding | documentation | harness | manual
  -> branch       cut feature/<id>-<slug> off develop — FIRST, before task.md
  -> pr-guard     pr-conflicts skill        -> hold if an open PR touches the same files
  -> breakdown    task-breakdown skill      -> task.md (every item gets its own goal)
  -> redcheck     Haiku sub-agent           -> every done-check FAILS, looped with
                                                the test-suite until it covers every
                                                aspect of the feature
  -> plan         Fable (fallback Opus)     -> plans/<slug>_<date>_plan.md; {{OWNER}} approves
  -> build        Sonnet sub-agents         -> parallel or sequential per overlap
  -> item-goals   per-item goal loop        -> each smallest item verified to its own goal
  -> goalmet      goal-met skill            -> primary Goal verified on the real path
  -> doc-sync     second-brain-sync skill (Haiku) -> committed into THIS PR
  -> review-gate  the 5 gates              -> each its own looped goal
  -> deploy       deploy-model skill        -> feature->develop PR, then develop->master PR
```

Stage state lives in `.claude/.workflow_state.json` via
`scripts/workflow_state.py`. Hooks read it and inject a `WORKFLOW [stage]`
directive after the relevant tool call — **hooks cannot spawn sub-agents, so
they tell you to, and you do it here.**

## 1. Classify — task type first

Decide the type before anything else:

- **coding** — app behaviour changes → the full chain below.
- **documentation** / **harness** (skills, hooks, loops, the workflow itself) —
  lighter path: author the `.md`/skill file directly, skip RED/plan/Sonnet-build;
  still branch-first + pr-guard + goal-met + doc-sync + review-gate + deploy. A
  harness change also updates `WORKFLOW.md` itself.
- **manual** — only {{OWNER}} can do it (an account login, a purchase, a secret, a
  merge) → `action_items.md`, not a build.

When context already gives a detailed spec or an obvious edit, docs/harness
tasks skip the nudging ceremony and go straight to authoring the target files.

## 2. Branch — FIRST, before task.md

Cut `feature/<NN-DDMMYY>-<slug>` off develop **before** running `task-breakdown`.
`task.md` is written on the already-created branch, not before it exists —
writing `task.md` first and branching later is what let two branches collide
on `task.md`.

## 3. PR-guard

Run the `pr-conflicts` skill right after `task.md` is written: it lists open
PRs and checks whether any touches the same files as this task (every task
edits the top of `## Active` in `task.md` and the `memory.md` mirror, so any
two in-flight tasks collide there). If there is overlap: **HOLD** — hand the
pending PR to {{OWNER}}, wait for their confirmation the merge landed, then resume.

## 4. Breakdown — every item gets its own goal

Run the `task-breakdown` skill. It writes the three-level entry to `task.md`,
classifying `Type:` and, on the already-cut branch. **Every smallest actionable
item (`- [ ]`) gets its own one-line goal** — what it must achieve and how it's
verified — not just the macro task.

**One primary task in flight at a time.** `scripts/workflow_state.py guard`
blocks a second non-`complete` block under `## Active`. If it fires, park or
finish the current task first.

## 5. RED check, looped with the test-suite

The moment `task.md` is written the hook emits `WORKFLOW [redcheck]`. Run the
`red-check` skill: a **Haiku** sub-agent runs every done-check against the
*unbuilt* code — all must fail. It also builds/extends the suite so it covers
**every aspect** of the feature; loop Haiku until the suite is genuinely red
for the right reasons and complete. Nothing is taken for granted. Docs/harness
tasks verify inline (file-content assertions) and skip the spawn.

## 6. Plan

Spawn a planning sub-agent — `model: "fable"`, falling back to `"opus"` if
Fable is unavailable. Interleave planning with test-building rather than
blocking the plan on a finished suite — feed any RED-suite coverage findings
back into the plan. Show the plan to {{OWNER}} and **wait for approval** before
building. On approval, save it as:

```
plans/<one-to-three-words-of-goal>_<YYYY-MM-DD>_plan.md
```

## 7. Build — fan out

```bash
python scripts/slice_overlap.py
```

One Sonnet sub-agent **per slice** — never one agent covering multiple slices:
- **PARALLEL group** (disjoint `Files:`) — spawn those Sonnet sub-agents
  **concurrently, in a single message**, one per single actionable item.
- **SEQUENTIAL chain** (shared files) — one Sonnet sub-agent at a time, in the
  printed order, so they cannot clobber each other.

Brief each agent with: the slice outcome, its `Files:`, its `Done-check:`, and
the task's `Constraints`/`Out-of-scope`. Gate every slice on its own done-check.

**Human review PER SLICE — the review gate happens here, not at the end:**
- **Sequential:** build a slice → gate on its done-check → **show {{OWNER}} that
  slice's diff, get their sign-off** → commit → next slice.
- **Parallel:** the moment ANY slice's Sonnet agent reports back, immediately
  **throw that slice's diff to {{OWNER}} for review — do NOT wait for the sibling
  slices still building.** Stream each for review as it lands.

Never batch multiple slices and ping only once the whole task is built (see
[[feedback_per_slice_approval]]). Keep each sub-agent alive until its handshake is
verified ([[subagent-handshake]]).

## 8. Per-item goal loop, then primary goal-met

For each smallest item, loop until its own goal is met — **capture what was
verified** beside it. Only once every item's goal is met, run the `goal-met`
skill for the **primary** Goal (real path, real output, full suite). If
outputs and test results do not match the macro `Goal`, append the plan and
re-enter the flow at the affected stage.

## 9. Doc-sync — part of THIS PR

Once the goal is met, run the `second-brain-sync` skill: a **Haiku** sub-agent
updates every second-brain `.md` file the change touches — `{{AGENT_DOC}}`,
`{{AGENT_DOC}}`, `WORKFLOW.md`, `README.md`, `BUILD.md`, `decisions/`,
`.env.example`, the `memory.md` mirror. **These edits are committed into the
same task PR**, not a separate one.

## 10. Review-gate — each gate its own looped goal

Walk the five gates from the `review-gate` skill in order; each is its own
check with its own goal, looped until green — the main agent runs them in-line,
no persistent monitor agent in the lean model.

## 11. Deploy — human-gated

Run the `deploy-model` skill after the goal is met: re-check every
review-gate item is green (reuse that item's loop if not); build only on
merge to master (`package.yml` is release-tag-only); open the **feature →
develop** PR, ping {{OWNER}} the diff, merge on their "all good"; then open the
**develop → master** PR, hand it to him, merge on their "good".

## Sub-agent handshakes — don't kill until the handshake is good

Use the `subagent-handshake` skill: never spawn-and-forget. Keep a sub-agent
alive (via SendMessage) until it confirms it did exactly what was asked and
you have verified its report — this matters most inside the RED↔suite loop and
the per-item goal loop, where a dropped agent mid-loop breaks the guarantee the
loop exists to provide.

## Conventions

- Agent work goes in `task.md`; anything only {{OWNER}} can do goes in
  `action_items.md`.
- Never push automatically — add the push item to `action_items.md`.
- Never auto-merge without {{OWNER}}'s "good", at either PR step.
- `.claude/skills/` and `.agents/skills/` hold the identical skill set — a new
  or changed skill lands in both in the same change.
- If a hook directive arrives for a stage you have already completed, re-read
  `python scripts/workflow_state.py get` before repeating work.
