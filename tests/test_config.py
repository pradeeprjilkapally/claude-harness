"""Per-repo settings come from the marker, not from a baked-in placeholder.

A plugin-delivered script is shared by every repository, so it cannot carry one
repo's remote or GitHub slug rendered into it. Those have to be read at runtime,
and a repo with no marker has to be invisible to the harness entirely.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import harness_config
import workflow_state


def _marker(tmp_path, **cfg):
    (tmp_path / '.harness.json').write_text(json.dumps(cfg))
    return str(tmp_path)


def test_no_marker_means_not_installed(tmp_path):
    assert harness_config.installed(str(tmp_path)) is False


def test_marker_opts_the_repo_in(tmp_path):
    assert harness_config.installed(_marker(tmp_path, version='1.1.0')) is True


def test_enabled_false_switches_the_harness_off(tmp_path):
    """Installed but deliberately disabled must read as not installed."""
    assert harness_config.installed(_marker(tmp_path, enabled=False)) is False


def test_remote_defaults_to_origin(tmp_path):
    assert harness_config.remote(_marker(tmp_path)) == 'origin'


def test_remote_comes_from_the_marker(tmp_path):
    assert harness_config.remote(_marker(tmp_path, remote='rebalancer')) == 'rebalancer'


def test_directive_carries_no_unrendered_placeholder():
    """The deploy directive is emitted verbatim to the model."""
    out = workflow_state.directive_json('deploy')
    assert '{{REMOTE}}' not in out
    assert 'git push' in json.loads(out)['hookSpecificOutput']['additionalContext']


def test_deploy_directive_states_the_merge_rule():
    """Own-the-loop has to reach the model, not just the docs."""
    text = json.loads(workflow_state.directive_json('deploy'))[
        'hookSpecificOutput']['additionalContext']
    assert 'MERGED' in text and 'Outcome:' in text


def test_owner_defaults_to_generic(tmp_path):
    assert harness_config.owner(_marker(tmp_path)) == 'the owner'


def test_owner_comes_from_the_marker(tmp_path):
    assert harness_config.owner(_marker(tmp_path, owner='Dana')) == 'Dana'


def test_directive_resolves_the_owner_placeholder():
    out = workflow_state.directive_json('plan')
    assert '{{OWNER}}' not in out
