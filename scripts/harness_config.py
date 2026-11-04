#!/usr/bin/env python3
"""Per-repo harness settings, read from .harness.json at the repo root.

The guards below used to hardcode one project's GitHub slug and data directory,
which is exactly what stopped the harness being reusable. Everything
project-specific now lives in the marker file the installer writes, so the
scripts themselves are identical in every repo.

    {
      "version": "1.0.0",
      "gh_repo": "owner/name",        # gh --repo target for the PR guards
      "data_dir_env": "APP_DATA_DIR", # env var naming the gitignored data dir
      "data_dir": "mydata",           # fallback when that env var is unset
      "remote": "origin",             # the git remote the workflow pushes to
      "enabled": true
    }

Every value is optional; each accessor falls back to a safe default, so a repo
with an empty marker still works.
"""
import json
import os
import subprocess

MARKER = '.harness.json'


def repo_root(start=None):
    """The git top-level for `start` (default cwd), or cwd if not in a repo."""
    cwd = start or os.getcwd()
    try:
        r = subprocess.run(['git', '-C', cwd, 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return os.path.realpath(cwd)


def load(start=None):
    """The repo's harness config as a dict — {} when absent or unreadable."""
    try:
        with open(os.path.join(repo_root(start), MARKER)) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def installed(start=None):
    """True when this repo has opted in — a marker that is not switched off.

    Every agent-facing hook keys off this, which is what lets one globally
    installed harness (or one enabled plugin) stay completely silent in every
    repository that has not asked for it.
    """
    cfg = load(start)
    return bool(cfg) and cfg.get('enabled') is not False


def remote(start=None):
    """The git remote the workflow pushes to. `origin` unless the repo says otherwise."""
    return load(start).get('remote') or 'origin'


def gh_repo(start=None):
    """The `gh --repo` slug, or None to let gh fall back to its own default.

    An explicit slug matters where `origin` is a read-only upstream fork: without
    it `gh` queries the wrong repository and the PR guards silently pass.
    """
    return os.getenv('GH_REPO') or load(start).get('gh_repo') or None


def data_dir(start=None):
    """The gitignored directory holding real user data, for the PII guard."""
    cfg = load(start)
    env_name = cfg.get('data_dir_env')
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    return cfg.get('data_dir') or 'mydata'
