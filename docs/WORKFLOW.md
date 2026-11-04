# Workflow — the ACTIVE (lean) model

**This is the workflow the repo actually runs.** The skills in `.claude/skills/`
(mirrored in `.agents/skills/`) implement *this* file. Every change to how work
moves through the repo updates THIS file — it is the single source of truth and it
is tracked (never gitignored).

A full parallel-orchestration variant (persistent monitor agent, parallel
plan+build, autonomous handshake loops) is **parked, inactive** in
[`WORKFLOW_FULL_ORCHESTRATION.md`](WORKFLOW_FULL_ORCHESTRATION.md) — for
token-abundant days. Do not run it unless explicitly switched on.

Two layers do the work:
- **Deterministic layer** — shell/Python hooks in `settings.json`. Hooks *cannot*
  spawn sub-agents, so they only track state, enforce invariants, and emit
  `WORKFLOW [stage]` directives back into the conversation. `scripts/workflow_state.py`
  is the seam.
- **Agent layer** — the skills. They read the directives and do the classifying,
  branching, spawning, planning, building, and gating.

**Lean means the main agent mediates the loops in-line** — it runs the
RED-check↔test-suite loop itself, interleaves planning with test-building rather
than keeping two agents alive in parallel, and walks the review-gate checklist
itself. Same gates, same loops, a fraction of the tokens.

---

## The chain

```
prompt
 -> classify      task type: coding | documentation | harness | manual
 -> branch        cut feature/<id>-<slug> off develop  — FIRST, before task.md
 -> pr-guard      pr-conflicts: hold if an open PR touches the same files
 -> breakdown     task-breakdown -> task.md  (every item gets its OWN goal)
 -> redcheck      Opus BUILDS the test suite (covers every aspect); Haiku EXECUTES
                  it to confirm every done-check fails (red) before the build
 -> plan          Fable (fallback Opus) -> plans/<slug>_<date>_plan.md; {{OWNER}} approves
 -> build         one Sonnet PER SLICE (slice_overlap: parallel if disjoint, sequential
                  if shared) — review each slice with {{OWNER}} as it lands (parallel: stream)
 -> item-goals    per-item goal loop: each smallest item verified to its own goal
 -> goalmet       goal-met: the primary Goal verified on the real path
 -> doc-sync      Haiku updates the second-brain .md files — committed into THIS PR
 -> review-gate   the 5 gate items, each looped to its own goal
 -> deploy        deploy-model: feature->develop PR (await OK) then develop->master (await OK)
 -> outcome       own the loop to the end: record Outcome: merged / abandoned /
                  taken-back in task.md. Until then the task is still in flight
```

Stage state: `.claude/.workflow_state.json` via `scripts/workflow_state.py`.

---

## 1. Classify the task FIRST

Before anything, decide the type — it sets the path:

| Type | What it is | Path |
|---|---|---|
| **coding** | app behaviour changes | the full chain below |
| **documentation** | README/docs/`.md` only | lighter: author the `.md` directly (no RED/plan/Sonnet-build); still branch-first + pr-guard + goal-met + doc-sync + review + deploy |
| **harness improvement** | skills, hooks, loops, the workflow itself | same lighter path as documentation, **and every change updates WORKFLOW.md** |
| **manual** | only {{OWNER}} can do it (an account login, a purchase, a secret, a merge) | it goes to `action_items.md`, not a build |

When the initial context is already given (a detailed spec, an obvious edit),
docs/harness tasks skip the nudging ceremony and go straight to authoring the
respective `.md`/skill files — recorded in `task.md` with `Type:` noted.

## 2. Branch FIRST — before task.md

Cut `feature/<NN-DDMMYY>-<slug>` off develop **before** writing the `task.md`
entry. `scripts/plan_branch.py` supports creating the branch up front; the branch
exists, then breakdown writes `task.md` on it. Rationale: writing `task.md` first
and branching later is what let two branches collide on `task.md`.

## 3. PR-conflict guard — no parallel cuts that will collide

Right after `task.md` is written (and ideally before cutting the branch), run the
**`pr-conflicts`** skill: a sub-agent lists open PRs and checks whether any touches
the same files as this task (every task edits the top of `## Active` in `task.md`
and the `memory.md` mirror, so any two in-flight tasks collide there). If there is
overlap: **HOLD.** Hand the pending PR to {{OWNER}} to review + merge, wait for their
confirmation, verify the merge landed, then resume. Never cut a second colliding
branch while a PR is in flight.

## 4. Breakdown — with a goal per item

`task-breakdown` writes the three-level entry. **Every smallest actionable item
(`- [ ]`) gets its own goal**, just like the primary task — a one-line assertion of
what that item must achieve and how it's verified.

## 5. RED check — Opus BUILDS the test suite, Haiku EXECUTES

Split the two models by role:
- **Opus builds the test suite** — authors the tests and ensures they cover **every
  aspect** of the new feature (the judgement part). It designs the coverage; it does
  not just run things.
- **Haiku only executes** — runs the suite against the *unbuilt* code to confirm it
  is genuinely RED for the right reasons (and later GREEN after the build). Running
  is cheap and deterministic — that is Haiku's job, not authoring.

The main agent loops the two until the suite is complete and correctly red — nothing
taken for granted. (In the full variant this is a two-instance handshake; lean = the
main agent mediates.) For a docs/harness task the checks are file-content assertions
— verify inline, skip the spawn.

## 6. Plan (Fable, then {{OWNER}} approves)

Spawn Fable (fallback Opus) → `plans/<slug>_<date>_plan.md`. **Planning and
test-building are conceptually parallel; lean = interleave them** — don't block the
plan on a finished suite, and once the RED suite is green, feed any coverage
findings back into the plan. Show the plan to {{OWNER}} and **wait for approval
before building.**

## 7. Build (Sonnet) — one agent PER SLICE, review each

Run `python scripts/slice_overlap.py` FIRST, then spawn **one Sonnet sub-agent per
slice** — **never one agent covering multiple slices**:
- **PARALLEL group** (disjoint `Files:`) — spawn those Sonnet agents concurrently, in
  a single message.
- **SEQUENTIAL chain** (shared files) — one Sonnet agent at a time, in the printed
  order, so they can't clobber each other.

Brief each with the slice outcome, `Files:`, `Done-check:`, and
`Constraints`/`Out-of-scope`.

**Review each slice with {{OWNER}} as it lands — this is the human-review gate, not
something deferred to the end:**
- **Sequential:** build a slice → gate on its done-check → **show {{OWNER}} that
  slice's diff and get their sign-off** → commit → next slice.
- **Parallel:** the moment ANY slice's agent reports back, immediately **throw that
  slice's diff to {{OWNER}} for review — do NOT wait for the sibling slices still
  building.** Stream each for review as it completes.

Never batch multiple slices and ping only once the whole task is built.

## 8. Per-item goal loop, then primary goal-met

For each smallest item, loop until its own goal is met — **capture what was
verified** beside it. Only once every item's goal is met, run `goal-met` for the
**primary** Goal (real path, real output, full suite) — again capturing what was
verified.

## 9. Doc-sync (Haiku) — part of THIS PR

Once the goal is met, spawn a **Haiku** sub-agent to update **all** the second-brain
`.md` files the change touches — `CLAUDE.md`, `AGENTS.md`, `WORKFLOW.md`, `README.md`,
`BUILD.md`, `decisions/`, `.env.example`, and the `memory.md` mirror — so the living
reference matches reality. **These edits are committed into the same task PR**, not
a separate one.

## 10. Review-gate — each item its own looping goal

Walk the five gates; each is its own check with its own goal, looped until green
(the main agent runs them in-line — no persistent monitor agent in the lean model):

1. **Diff small enough** — smallest actionable items, **reviewed by {{OWNER}} PER SLICE
   during the build (§7), not batched to the end**; parallel slices are streamed to
   him for review as each agent returns.
2. **Goal matches the change** — the goal-met result.
3. **Test passed** — the RED check + full suite after the build.
4. **No-slop** — the end-to-end no-slop checklist after goal-met.
5. **Shipping proof** — the local build/test result (future: lower-environment
   deployment + proper test evidence).

## 11. Deploy-model (human-gated)

Run the **`deploy-model`** skill after the goal is met:
- Re-check every review-gate item is green; if not, reuse that item's loop until it is.
- **Build only on merge to master** — never per PR (`package.yml` is release-tag-only).
- Open the **feature → develop** PR, ping {{OWNER}} the git diff, and on their "all good" merge it.
- Then open the **develop → master** PR, hand it to {{OWNER}}, and on their "good" merge it.

## Sub-agent handshakes — don't kill until the handshake is good

The **`subagent-handshake`** skill: never spawn-and-forget, and **steer before
you spawn** — an agent that already holds the task's context gets a follow-up
via SendMessage; a fresh spawn is for genuinely disjoint work or a different
model role, never an escape from an unresolved report. Keep a sub-agent alive
until it confirms it did exactly what was asked and you have verified its
report; only then let it end and proceed. A dropped agent mid-loop
(e.g. the RED↔suite loop) breaks the guarantee the loop exists to provide.

---

## Own the loop — a task ends at an outcome, not at a commit

The chain does not stop when the code is written. A task is finished when **the
PR is merged, the work is explicitly abandoned, or {{OWNER}} takes it back** —
and the `Outcome:` line in `task.md` records which one. Nothing else settles it.

`Status: complete` says only that the build is done. A block at `complete` with
no `Outcome:` **still occupies the one-in-flight slot**, so the next task cannot
start until the last one actually landed (`scripts/workflow_state.py guard`
enforces it; `scripts/workflow_state.py outcome` lists what is awaiting one).
`python3 scripts/check_merged.py` asks the forge what really merged and prints
the line to record — it reports only, it never edits `task.md`.

Between the PR opening and that outcome, CI is chased by a script, not by an
agent on a timer: `scripts/ci_watch.py` polls `gh pr checks` and prints **only
on a verdict change**, so the session hears `pending -> failing` and never
hears "still running". `--once` is the read-only on-demand status. It reports;
it never commits, pushes, merges, or re-runs a job.

## Report cadence — quiet while it is working

The **`report-cadence`** skill is the output contract for everything above:
stay silent while the work is healthy, speak on the three moments that need a
human — **blocked on {{OWNER}}, ready to merge, done** — and batch the rest into
one digest rather than narrating each stage. Bad news overrides the cadence and
is reported when learned. Per-slice diff review stays a speak-now event: the
digest rule covers narration *inside* a slice, never the slice gate itself.

## Conventions carried over

- Agent-doable work → `task.md`; only-{{OWNER}} work → `action_items.md`.
- Never push automatically; never auto-merge without {{OWNER}}'s "good".
- `.claude/skills/` and `.agents/skills/` hold the identical skill set — a new or
  changed skill lands in both in the same change.
- If a hook directive arrives for a stage already done, re-read
  `python scripts/workflow_state.py get` before repeating work.
