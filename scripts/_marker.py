#!/usr/bin/env python3
"""Write or upgrade a repo's .harness.json marker.

Installer-only; not copied into consuming repos. Existing keys are preserved so
an upgrade never discards settings the repo added by hand.

    _marker.py <path> <version> <gh_repo> <data_dir> <data_dir_env> [remote] [owner]
"""
import json
import os
import sys


def main():
    path, version, gh_repo, data_dir, data_dir_env = sys.argv[1:6]
    remote = sys.argv[6] if len(sys.argv) > 6 else ''
    owner = sys.argv[7] if len(sys.argv) > 7 else ''
    cfg = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                cfg = loaded
        except (OSError, ValueError):
            cfg = {}                               # unreadable: rewrite from scratch
    cfg['version'] = version
    cfg.setdefault('enabled', True)
    if gh_repo:
        cfg['gh_repo'] = gh_repo
    if data_dir:
        cfg.setdefault('data_dir', data_dir)
    if data_dir_env:
        cfg['data_dir_env'] = data_dir_env
    if owner:
        cfg['owner'] = owner
    if remote:
        # Persisted, not only rendered into the skills: the guards resolve the
        # remote at runtime (a plugin-delivered script is shared by every repo),
        # so a remote the installer knew but never wrote down would be lost.
        cfg['remote'] = remote
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=2)
        f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
