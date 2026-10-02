> **NOT ACTIVE for this repo.** This is the token-hungry, fully-parallel variant of
> the workflow — kept for token-abundant days. The repo runs the lean model in
> [`WORKFLOW.md`](WORKFLOW.md); do not follow this file unless it is explicitly
> switched on. It documents the same gates and loops, but as persistent, concurrent
> sub-agents instead of loops the main agent mediates in-line.

# Workflow — FULL parallel orchestration (parked)

The lean model (`WORKFLOW.md`) keeps all the guarantees but has the main agent run
the loops one at a time. This variant spends tokens to run them concurrently. Turn
it on only when a task is large enough that wall-clock time matters more than cost.

## What changes vs the lean model

Everything in `WORKFLOW.md` §1–4 and §7–11 is identical (classify → branch-first →
pr-guard → breakdown → build → item-goals → goalmet → doc-sync → review → deploy).
The difference is stages §5–6 and §10, which become live concurrent agents.

## Parallel planning ∥ test-suite build

Spawn **two agents at once** the moment the breakdown is written:
- **Planner** — Fable (first priority; fallback Opus) drafting `plans/<slug>_<date>_plan.md`.
- **Test-suite builder** — Opus building the RED test suite for the feature.

Do **not** wait for planning to finish before building tests — they run together.

## RED-check handshake loop (spawned from the test-builder)

The Opus test-builder spawns a **Haiku** RED-check sub-agent and the two run a
handshake loop (over SendMessage):
1. Haiku runs every done-check against the unbuilt code and reports coverage gaps.
2. The Opus builder extends the suite to cover every aspect of the new feature.
3. Repeat until the suite is fully RED for the right reasons AND complete — nothing
   taken for granted.
4. When the RED suite is green (complete + correctly failing), the builder sends a
   signal to the **Planner** so the plan can absorb any coverage findings before
   {{OWNER}} approves it.

## Persistent review-gate monitor (Opus)

Kick off an **Opus monitor** agent at the very first stage; it lives for the whole
task and marks each review-gate item the moment it is satisfied, rather than the
main agent checking them all at the end. Each gate item is its own sub-skill with
its own goal and its own loop:

1. **diff-size** — the diff stays reviewably small (smallest actionable items + human review after the change).
2. **goal-match** — the goal-met check.
3. **test-passed** — RED check + full suite after build.
4. **no-slop** — the end-to-end no-slop review after goal-met.
5. **shipping-proof** — local build/test evidence (future: lower-env deploy + test evidence).

The monitor loops each item until it meets its own goal and reports the live
checklist state back to the main agent continuously.

## Per-item goal loops as concurrent agents

Each smallest actionable item can run its own verify-loop agent concurrently, each
looping until its item goal is met, before the primary goal-met check runs.

## Handshake discipline

As in the lean model's `subagent-handshake` skill — but more load-bearing here:
none of these concurrent agents is killed until its handshake is confirmed, because
the loops depend on the channels staying open.

## Cost note

This variant keeps 3–4 agents live for most of a task (planner, test-builder,
Haiku RED, Opus monitor, plus per-item loops). That is the reason it is parked:
the lean model in `WORKFLOW.md` achieves the same gates for a fraction of the cost.
