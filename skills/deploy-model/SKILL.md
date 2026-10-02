---
name: deploy-model
description: >-
  The final stage, invoked after the goal is met and review-gate is green.
  Re-checks every review-gate item, confirms packaging only ever builds on a
  merge to master (never per PR — package.yml is release-tag-only), then walks
  two human-gated merges in order: feature -> develop (ping {{OWNER}} the diff,
  merge only on his "all good") and develop -> master (hand it to him, merge
  only on their "good"). Never auto-merge without their word at either step.
---

# Deploy model — human-gated, two merges, build only at master

This is the last stage of the chain. It does not replace `review-gate`; it
runs after it and re-verifies before touching a merge button.

## 1. Re-check review-gate is actually green

Do not trust that it was green a few messages ago. Re-read the five items —
diff review, goal alignment, evaluation pass, no-slop, shipping proof. Any
item not currently green: **reuse that item's own loop** (re-run the
evaluation pass, re-run no-slop, etc.) until it is. Do not paper over a red
item to reach the merge step faster.

## 2. Packaging only builds on merge to master

`package.yml` triggers on a `v*` tag on `master` and manual
`workflow_dispatch` — it does **not** run per PR, per feature branch, or per
merge to `develop`. Do not add packaging steps here and do not expect an
installer artifact until the change is on `master` and tagged. If a task
seems to need a build earlier than that, that is a sign the task belongs in
`action_items.md` (only {{OWNER}} can cut a release tag) — not a reason to
change `package.yml`'s trigger.

## 3. feature -> develop (first human gate)

1. Open the PR: `gh pr create --repo {{GH_REPO}} --base develop --head feature/<id>-<slug> ...`
2. Ping {{OWNER}} with the PR link **and** the `git diff` (or a summary of it if
   the diff is long) — he reviews the actual change, not a description of it.
3. **Wait.** Do not merge on your own judgment that it "looks fine."
4. Merge only after his explicit "all good" (or equivalent). Then:

```bash
git fetch origin develop
git log origin/develop -1 --format='%H %s'
```

   confirm the merge commit landed before treating this gate as cleared.

## 4. develop -> master (second human gate)

1. Open the PR: `gh pr create --repo {{GH_REPO}} --base master --head develop ...`
2. Hand it to {{OWNER}} the same way — link plus diff.
3. **Wait** for their "good" (or equivalent) — a separate, explicit signal from
   the first gate. His approval of feature->develop is not standing approval
   for develop->master.
4. Merge only then. Confirm with `git fetch origin master && git log origin/master -1`.

## Never

- Never merge either PR without {{OWNER}}'s explicit word for **that specific**
  merge — his "all good" on feature->develop does not carry over to
  develop->master.
- Never trigger or wait on a packaging build as part of a feature or develop
  PR — it isn't going to run until `master` is tagged.
- Never re-declare review-gate green from memory; re-check it in this stage.
