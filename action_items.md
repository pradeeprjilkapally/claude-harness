# Action Items

Only work an agent genuinely cannot do belongs here. Everything an agent *can*
do — including config and infra edits — is a `task.md` task.

## Open

| # | Item | Why it is manual | Filed |
|---|---|---|---|
| 1 | Review the `01-041126` branch and merge `feature/01-041126-grok-parity` | The two merge gates are human-gated by design | 2026-11-04 |
| 2 | `git push origin feature/01-041126-grok-parity` | The harness never pushes automatically | 2026-11-04 |
| 3 | Decide whether the CI monitor should run `always` rather than only on `deploy-model` | A cost/benefit call about per-session token spend | 2026-11-04 |

## Parking lot

| # | Item | Note |
|---|---|---|
| 1 | `templates/root/task.md` is the old two-level format, but `workflow_state.active_blocks` parses the three-level one | A freshly seeded `task.md` yields zero parsed blocks, so the one-in-flight guard is inert until an agent rewrites the file in the three-level format. Pre-existing; deliberately out of scope for `01-041126`. |
| 2 | Hosting the marketplace | `dist/` is gitignored, so a clone has no plugin until `build_plugin.py` runs. Hosting needs either a committed build or a CI release step. |

## Done

| # | Item | Closed |
|---|---|---|
