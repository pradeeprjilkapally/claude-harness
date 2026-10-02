---
name: review-gate
description: >-
  Run before shipping, deploying, merging, or claiming a change is done. Five
  gates — diff size, goal alignment, test passed, no-slop, shipping proof —
  each its own check with its own goal, looped until green, run by the main
  agent in-line (lean model; no persistent monitor). Enforces the rule "never
  claim done without proof": "deployed" or "done" must be backed by
  same-session evidence (curl against a live URL, a production screenshot, or
  a fresh log line). Runs after goal-met and doc-sync, before deploy-model.
---

# Review Gate & Shipping

When work moves faster, the volume of lower-quality output rises with it. This
gate is the quality filter that runs before anything reaches a user, after
`goal-met` and `second-brain-sync` and before `deploy-model`. **Nothing ships
that skips a line.**

**Lean model:** each gate below is its own check with its own goal, looped
until it passes, mediated by the main agent in-line — no persistent monitor
agent. (The parked full-orchestration variant in
`WORKFLOW_FULL_ORCHESTRATION.md` runs these same five as a persistent Opus
monitor that marks each item live instead.)

## The gates (in order, each looped to its own goal)

Run these sequentially; a failure at any gate loops that gate, not the whole
chain — fix, re-check, move on only when it's green.

1. **Diff small enough** — Goal: the change is reviewable as a set of smallest
   actionable items, and {{OWNER}} reviews each **PER SLICE during the build**
   (the `workflow` skill's build stage), not batched at the end — for a parallel
   build, each slice is streamed to him the moment its agent returns, without
   waiting for the siblings. If a slice is sprawling, split it before going further.
2. **Goal matches the change** — Goal: the `goal-met` result — the stated
   objective matches what the diff actually changes. No silent drift, no
   smuggled scope.
3. **Test passed** — Goal: the RED check (every done-check failed pre-build)
   plus the full suite green after the build. Report real output; a failure
   here is a stop, not a footnote.
4. **No-slop** — Goal: the [[no-slop]] checklist run end-to-end after
   `goal-met`; it finds no unexplained issues over the changed files.
5. **Shipping proof** — Goal: human-verifiable evidence that the change works
   on the local build/test result — today that means the local suite output
   and, where relevant, a real-path run (future: lower-environment deployment
   plus proper test evidence once a deploy target exists).

## Never claim done without proof

"Deployed" requires verification produced in the **same session**, by one of:

- `curl` against the live URL,
- a screenshot of the running/production surface, or
- a fresh log line from the live system.

If you cannot point to proof, you ran a command and hoped. That is not done.

## Proof template

Define the proof criteria *before* shipping, then capture the evidence:

```bash
# 1. Inspect what is shipping
git status
git diff --stat

# 2. Prove it passes
<test command>          # e.g. pytest / npm test / make test

# 3. Ship
<deploy/push command>

# 4. Prove it is live (capture this output — it is the evidence)
curl -s -o /dev/null -w '%{http_code}\n' <live-url>
# or: grep the fresh log line / attach the production screenshot
```

## Done means

All five gates green with their captured evidence, then handed to
`deploy-model` — never to a merge — for the human-gated feature→develop and
develop→master steps.
