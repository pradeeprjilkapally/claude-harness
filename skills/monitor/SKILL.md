---
name: monitor
description: >-
  Triggered when {{OWNER}} types "monitor". Runs this repo's health check on
  demand and reports the live status. Read-only — never auto-fixes, never edits
  files, never notifies anyone. The command it runs is whatever the repo declares
  as health_check in .harness.json; without one, the skill says so rather than
  guessing.
---

# Monitor — on-demand health check

When {{OWNER}} types `monitor`, give them an instant, read-only status of whatever
this project depends on being up.

## Run it

The command comes from the repo, not from this skill — every project's stack is
different. Read `.harness.json`:

```json
{ "health_check": "python -m yourapp.healthcheck --report" }
```

```bash
python3 -c "import json;print(json.load(open('.harness.json')).get('health_check',''))"
```

Then run exactly that command. If `health_check` is absent, say so plainly and
offer to help define one — do not invent a command, and do not go poking at
services to improvise a check.

## Ground rules

- **Read-only.** No auto-fix, no file writes, no messages to anyone. If the check
  itself has side effects, that is the repo's problem to fix, not this skill's to
  work around.
- **Report what the command reported.** Do not soften a failure, and do not call
  something healthy because a different signal looked fine.

## Report back

Lead with **all green** or the count of failures, then list each failure with its
detail. For each one, say which it is:

- **Agent-fixable** — you can diagnose and fix it now; offer to.
- **Needs {{OWNER}}** — a credential to enter, a login to complete, a purchase, a
  dashboard setting. State exactly what they have to do, then add it to
  `action_items.md`.

If the check exits non-zero but prints nothing useful, say that rather than
inferring a cause. Never push or deploy from this skill — it is observation only.
