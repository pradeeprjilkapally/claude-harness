---
name: report-cadence
description: >-
  The reporting contract for a long-running task: stay silent while the work is
  healthy, speak the moment something is blocked on {{OWNER}}, ready to merge,
  or done, and batch everything else into one digest instead of narrating each
  step. Invoke it when a task will run across many tool calls or stages, when a
  CI watch or background job is in flight, or whenever you are about to post a
  progress update that nobody asked for.
---

# Report cadence — quiet while it is working

A long task produces a lot of true sentences that are not worth saying. Every
stage entered, every file read, every check that stayed green: narrating those
costs {{OWNER}} attention and buys nothing, because none of it changes what he
would do next. The contract is the inverse of a status feed — **silence is the
default, and speech is reserved for the three moments that need a human.**

This is a presentation rule for work already being done. It never licenses
skipping a stage, a gate, or a verification, and it never means withholding a
real problem.

## Speak immediately — these three only

1. **Blocked on {{OWNER}}.** The work cannot proceed without a decision, a
   credential, a login, a purchase, or an approval only he can give. Say what is
   blocked, what you need, and what you have already done — in that order, so he
   can unblock in one reply.
2. **Ready to merge.** A PR is green and waiting on his word (the `deploy-model`
   gates). Give the diff and the evidence, not a request to look at something.
3. **Done.** The task reached a terminal outcome — merged, explicitly abandoned,
   or taken back. Report what landed and the `Outcome:` recorded. "The code is
   written" is NOT done — `Status: complete` with no `Outcome:` is still in
   flight.

A fourth case overrides the cadence: **something broke that he would want to
know about now** — a red CI on a branch he thinks is green, a guard that fired,
a failure you cannot fix. Report it when you learn it. Quiet-first is not
quiet-about-bad-news.

## Batch everything else

Progress, stages passed, slices built, checks that stayed green, files touched,
intermediate findings: hold them and deliver one digest at the next moment you
speak anyway. One consolidated report beats six interruptions carrying the same
information.

Per-slice diff review is an explicit exception. {{OWNER}} has asked to see each
slice as it lands, so a finished slice is a speak-now event in its own right —
the digest rule covers the narration *inside* a slice, not the slice gate
itself.

## Never

- Never announce that you are about to start something, or restate the task back
  before doing it.
- Never post "still running", "checking", or "no change yet" — a quiet hold is
  reported by saying nothing. If a loop must tick, let it tick silently.
- Never pad a real report with the steps that produced it. The evidence belongs
  in the report; the travelogue does not.
- Never let the cadence delay bad news to make a digest tidier.

## Why this is in the harness at all

A background watch (`scripts/ci_watch.py`, a plugin monitor) is edge-triggered
for exactly this reason: it prints on a state change and stays silent otherwise,
so what reaches the session is already filtered to the moments that matter. This
skill is the same discipline applied to the agent's own output — the watcher
does not spam the session, and neither should the agent.
