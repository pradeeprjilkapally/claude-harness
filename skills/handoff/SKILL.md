---
name: handoff
description: >-
  Triggered when {{OWNER}} types "handoff" (or relays a Claude Code "approaching
  limit" warning). Writes the HANDOFF.md baton — current branch, active task,
  what's done, what's left, next step — sets the owner to the other agent, and
  tells {{OWNER}} which terminal to switch to. This is the manual trigger.
---

# Handoff — pass the baton to the other agent

Claude and Codex share this repo (see the cross-agent section in {{AGENT_DOC}} /
{{AGENT_DOC}}). When the current agent is near its token limit — or {{OWNER}} wants to
switch deliberately — hand the active work over cleanly so the other agent resumes
without losing context.

## Do this

1. Capture the live state into `HANDOFF.md` (repo root). Run the monitor's writer
   so the format matches what the automatic job produces:

   ```bash
   # if the repo declares a token/usage command in .harness.json, run it here
   ```

   Then write `HANDOFF.md` with: target agent, branch (`git rev-parse --abbrev-ref HEAD`),
   the active task ID from `task.md`, a 1-line "what's done", a 1-line "what's left /
   next step", and the deploy step (review-gate → PR).
2. Flip the owner: write `codex` (or `claude`) to `.token_monitor_state`.
3. Tell {{OWNER}} which terminal to open and that they should type `resume` there.
   Note: Codex is a **free-tier** account — if handing TO Codex, keep its scope to
   exactly what's blocked, and the monitor will hand back the moment Claude refreshes.

## Don't

- Don't hand off mid-commit — finish or stash to a clean point first.
- Don't hand off work that's safe to leave for when tokens refresh; prefer waiting if
  the task isn't time-sensitive (saves Codex's free quota).
