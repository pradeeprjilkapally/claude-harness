---
name: subagent-handshake
description: >-
  A discipline skill for every sub-agent spawn in this repo's workflow — never
  spawn-and-forget. Keep the sub-agent alive (via SendMessage) until it
  confirms it did exactly what was asked AND you have verified its report;
  only then let it end and proceed. Especially load-bearing for the RED-check
  <-> test-suite loop, where a dropped agent mid-loop breaks the true-negative
  guarantee the loop exists to provide. Also governs the choice itself: steer an
  agent that already has the context before spawning a fresh one. Apply this on
  every spawn: red-check, plan, build, goal-met, doc-sync.
---

# Sub-agent handshake — never spawn-and-forget

A sub-agent that returns a report is not the same as a sub-agent whose report
is *true*. Ending the turn the moment a message arrives — without checking it
against what was actually asked — is how a false `FAILS-AS-EXPECTED` or a
half-applied doc edit slips through unnoticed.

## Steer before you spawn

A fresh agent starts cold. It re-reads the files, re-derives the constraints,
and re-discovers what the previous agent already knew — and it does all of that
without the correction history that made the previous agent's current answer
better than its first one. So the default is to **continue an existing agent**,
and spawning a new one is the exception that needs a reason.

Before any spawn, ask in this order:

1. **Is an agent from this task still available?** If it has the context and the
   work is a continuation, `SendMessage` to it. A follow-up instruction to an
   agent mid-task is almost always better than a new agent with a longer brief.
2. **Is this genuinely a different piece of work?** A disjoint slice, a
   different model role (Opus authors the suite, Haiku executes it), or an
   isolated context you deliberately want clean — those earn a fresh spawn.
3. **Am I spawning to escape a problem?** An agent whose report was wrong,
   incomplete, or unverified gets sent back, not replaced. Replacing it discards
   the context AND hides the fact that the first report was never resolved.

Reasons that do NOT justify a fresh spawn: the existing agent's reply was
unsatisfying; it is easier to re-brief from scratch than to explain the
correction; the thread feels long. Each of those is the context being thrown
away precisely when it is most valuable.

## The rule

For every sub-agent spawned in this workflow (Haiku red-check, Fable/Opus
plan, Sonnet build, Haiku doc-sync):

1. **Brief it precisely** — exact task, exact files, exact done-check, and
   what it must *not* do (constraints/out-of-scope). Vague briefs produce
   reports that are vague in the same way.
2. **Keep the thread open.** Do not let the agent end after its first reply.
   Read the report.
3. **Verify, don't trust.** Cross-check the report against something you can
   independently observe:
   - red-check: re-run one of the reported commands yourself, or at minimum
     read the test file it names and confirm it exists and asserts what it
     claims.
   - build: read the diff it produced, don't just read its summary of the diff.
   - doc-sync: read the files it says it changed — confirm the content, not
     just the file list.
4. **If the report is incomplete, wrong, or the verification fails** — send it
   back (`SendMessage` to the same agent) with exactly what's missing or
   wrong. Do not spawn a fresh agent to paper over an unfinished one; that
   loses the context it already built.
5. **Only end the agent once**: (a) it confirms it did exactly what was
   asked, and (b) you have independently verified that confirmation. Then, and
   only then, let it terminate and move to the next stage.

## Why this is load-bearing for the RED-check loop specifically

The RED-check <-> test-suite loop's entire value is that a check *provably*
fails before the feature exists. If the Haiku agent is dropped mid-loop —
before its `PASSES-UNEXPECTEDLY` redesign is confirmed re-run and genuinely
red — the loop's guarantee is gone: a check that was never actually verified
red gets treated as red anyway. The same failure mode applies to any
loop-shaped stage (item-goal loop, review-gate loop): dropping the agent
before the loop closes is indistinguishable, later, from the loop having
never run.

## Never

- Never treat a sub-agent's first message as final if it hasn't been checked
  against the brief.
- Never spawn a replacement agent as a shortcut around verifying — verify
  first, redirect second.
- Never spawn a fresh agent for work an existing one is already holding the
  context for. Steering costs one message; respawning costs the whole re-derive,
  and the new agent cannot know what the old one was told to stop doing.
- Never let a loop-shaped stage (red-check, review-gate) end with an agent
  still mid-cycle; either close the loop or explicitly hand off the unfinished
  state before ending the thread.
