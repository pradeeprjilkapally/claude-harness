# claude-harness

An agent workflow harness packaged so any repository can run it. 17 skills, 6 hooks, 12 guard/workflow scripts, and the management-file
templates they assume.

It installs two ways, and they are complementary rather than rival:

| | Delivers | Why it has to be this one |
|---|---|---|
| **Plugin** (`dist/plugin`) | the 17 skills, the lifecycle hooks, the CI monitor | one command, updates from a marketplace, no shell script run against each repo |
| **Installer** (`install.sh`) | the pre-push gate, `task.md` + the management files, the branch-flow CI guard | a plugin cannot write `.git/hooks/pre-push`, and cannot seed a file the repo then owns |

The guards are what give the workflow teeth and they live in the repo; the
skills are what the agent reads and they travel better as a plugin. Use the
plugin for the agent layer, the installer for the repo layer, and
**don't also run `install-hooks.sh` when the plugin is enabled** — both layers
fire, so the file-appending hooks would double every log entry.

## Install as a plugin

```bash
python3 scripts/build_plugin.py                       # -> dist/plugin
claude plugin validate ./dist/plugin                  # -> Validation passed
claude plugin marketplace add ./                      # this repo is the marketplace
claude plugin install agent-workflow-harness@pradeep-harness \
  --config owner="Your Name" \
  --config gh_repo=owner/name \
  --config remote=origin
```

`dist/` is a build output and is gitignored — rebuild it after changing a skill,
then `/reload-plugins` in a session (a local-path marketplace is read in place,
so no version bump is needed).

The three `--config` values are the harness's install-time tokens, carried into
the plugin as [`userConfig`](https://code.claude.com/docs/en/plugins/manifest-reference#user-configuration):
`{{OWNER}}` becomes `${user_config.owner}` in the skill text and Claude Code
substitutes it at load. On Claude Code older than v2.1.271 the in-session
`/plugin configure` flow sets the same values.

**The plugin costs about 2.8k tokens of context in every session** — 17 skill
descriptions have to be loaded for Claude to know they exist, in every project,
whether or not the harness runs there. The installer has no such floor: its
skills exist only in the repos it was run against. If you work mostly in one
repo, the installer is cheaper; if you work across many, the plugin is less
to maintain. `claude plugin details agent-workflow-harness` prints the current
figure, and `/plugin` can disable it without uninstalling.

The plugin's scripts read the same `.harness.json` marker as everything else, so
an enabled plugin stays silent in every repository that has not opted in.

## Install with the shell installer

```bash
./install-hooks.sh                       # once per machine
./install.sh /path/to/repo --gh-repo owner/name --owner "Your Name" --remote origin
```

`install-hooks.sh` copies the hooks into `~/.claude/hooks` and wires them into
`~/.claude/settings.json` (backing it up first, leaving existing entries alone).
Run it once per machine.

`install.sh` sets up one repo:

| Installs | Where |
|---|---|
| 17 skills, rendered per agent | `.claude/skills/`, `.agents/skills/` |
| guard + workflow scripts | `scripts/` |
| management files, seeded once | repo root |
| repo-level hook wiring | `.claude/settings.json` (merged, never clobbered) |
| the pre-push gate | `.git/hooks/pre-push` |
| branch-flow CI guard | `.github/workflows/pr-flow.yml` |
| opt-in marker | `.harness.json` |

**The pre-push gate is what gives the workflow teeth.** It blocks a push whose
branch has no `task.md` entry, whose PR is already merged, or whose tests fail —
verified by installing into a clean repo and confirming an undocumented push is
rejected while a documented one goes through. `git push --no-verify` overrides it
for genuine emergencies.

Declare your test command in `.harness.json` to arm the test gate:

```json
{ "test_command": "python -m pytest -q" }
```

Without one, that gate is skipped rather than guessing how to run your suite.

Re-run `install.sh` to upgrade a repo. It is idempotent: management files the repo
owns — `task.md`, `action_items.md`, `log.md`, `memory.md`, `config.md`,
`sessions_handoff.md` — are seeded once and never overwritten, so your task
history survives an upgrade.

## How a repo opts in

A `.harness.json` marker at the repo root:

```json
{
  "version": "1.0.0",
  "enabled": true,
  "gh_repo": "owner/name",
  "data_dir": "mydata",
  "data_dir_env": "APP_DATA_DIR"
}
```

The hooks are installed globally but read this file before doing anything, so they
stay silent in every repo that has not opted in. `"enabled": false` switches the
harness off in a repo without uninstalling it.

| Key | Used by | Meaning |
|---|---|---|
| `gh_repo` | PR guards | `gh --repo` target. Set it where `origin` is a read-only upstream fork — otherwise the guards query the wrong repository and silently pass. |
| `data_dir` / `data_dir_env` | `check_no_real_data.py` | The gitignored directory holding real user data, so the PII guard knows what must never reach a diff. |

## What this fixes from the original

**Hooks were pinned to one directory.** `hooklib.py` hardcoded a single absolute
parent directory and no-op'd everywhere else, so the harness could only run inside
one tree on one machine. Opt-in is now the marker file.

**The two skill directories had to be hand-synced, and had already drifted.**
`.claude/skills/` and `.agents/skills/` differed in `add-scheduled-job` and
`ledger`. There is now one source; `install.sh` renders both variants.

**It was written for one person.** The skills named a specific owner and assumed
that person's pronouns. The owner is now a `{{OWNER}}` token rendered at install
time (`--owner`, defaulting to "the owner"), and owner pronouns are they/them.

| Token | Rendered to | Flag |
|---|---|---|
| `{{AGENT_DOC}}` | `CLAUDE.md` / `AGENTS.md` | — (per variant) |
| `{{AGENT_NAME}}` | `Claude` / `Codex` | — (per variant) |
| `{{OWNER}}` | the repo owner's name | `--owner` |
| `{{GH_REPO}}` | the `gh --repo` slug | `--gh-repo` |
| `{{REMOTE}}` | the git remote to push to | `--remote` |
| `{{REPO_PATH}}` | the install target's absolute path | — (derived) |

Nothing project-specific is baked into a skill: the GitHub slug, the push remote,
the owner and the repo path are all substituted at install time.

**Guards carried one project's constants.** The GitHub slug and data directory
were baked into the scripts; they now come from the marker via
`scripts/harness_config.py`.

## Layout

```
skills/          17 skills, single source with install-time tokens
hooks/           6 hooks — marker-gated, installed to ~/.claude/hooks
scripts/         guards, workflow state machine, slice overlap, config reader
                 (_render.py, _marker.py, _merge_settings.py and
                 build_plugin.py are installer-only, never copied)
templates/       management files seeded per repo, plus plugin/ — the manifest,
                 hooks and monitor the plugin build assembles
.claude-plugin/  marketplace.json: this repo is its own plugin marketplace
docs/            WORKFLOW.md and the parked full-orchestration variant
tests/           the suite for the workflow state machine and the CI watcher
dist/            build output (gitignored) — python3 scripts/build_plugin.py
```

## The workflow it installs

`docs/WORKFLOW.md` is the source of truth. In short: classify → branch first →
pr-guard → breakdown → RED check → plan → build per slice → goal-met → doc-sync →
review-gate → deploy. Hooks track stage state and emit `WORKFLOW [stage]`
directives; the skills do the work.

## Verifying an install

```bash
cd /path/to/repo
python3 scripts/workflow_state.py get      # prints a stage, not an error
python3 scripts/check_task_tracked.py      # the pre-push task guard
python3 scripts/workflow_state.py outcome  # tasks still awaiting an outcome
python3 scripts/check_merged.py            # what actually merged, per task
python3 scripts/ci_watch.py --once         # this branch's CI verdict
```

Then open the repo in your agent and type `jarvis` — it should read `task.md` and
report the current task state.

## Caveats

- Installed files are copies. Editing a skill inside a consuming repo means the
  next `install.sh` overwrites it — change it here and reinstall. The files your
  repo owns (`task.md` and the other management docs, `.claude/settings.json`,
  `.gitignore`, an existing `pr-flow.yml`) are never overwritten.
- An existing `.git/hooks/pre-push` is backed up to `pre-push.before-harness`
  before being replaced.
- `install-hooks.sh` edits `~/.claude/settings.json`. It backs up to
  `settings.json.harness-backup` first and only appends commands that are not
  already present, but it is your file: check the diff if you have customised it.
- The skills assume the management files exist. Installing the scripts without the
  templates will leave `jarvis` and `ledger` with nothing to read.

## License

Apache-2.0. See [LICENSE](LICENSE).
