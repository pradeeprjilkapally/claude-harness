#!/usr/bin/env python3
"""Write or upgrade a repo's .harness.json marker.

Installer-only; not copied into consuming repos. Existing keys are preserved so
an upgrade never discards settings the repo added by hand.

    _marker.py <path> <version> <gh_repo> <data_dir> <data_dir_env>
"""
import json
import os
import sys


def main():
    path, version, gh_repo, data_dir, data_dir_env = sys.argv[1:6]
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
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=2)
        f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
