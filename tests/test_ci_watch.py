"""The CI watcher is edge-triggered: it speaks on a change, not on a schedule.

Grok's Engineering Lead "chases CI" on a weekday cadence. Doing that with an
agent loop would burn tokens every interval even when everything is green, which
is the pattern the harness deliberately rejects. So the polling is a dumb script
and only a STATE TRANSITION is worth the agent's attention.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import ci_watch


def test_first_observation_is_always_reported():
    w = ci_watch.Watcher()
    assert w.transition('feature/x', 'pending', '2 queued') is not None


def test_same_state_twice_is_silent():
    w = ci_watch.Watcher()
    w.transition('feature/x', 'pending', '2 queued')
    assert w.transition('feature/x', 'pending', '2 queued') is None


def test_a_real_change_speaks():
    w = ci_watch.Watcher()
    w.transition('feature/x', 'pending', '2 queued')
    msg = w.transition('feature/x', 'failing', 'test-conda failed')
    assert msg is not None and 'failing' in msg


def test_detail_churn_alone_is_silent():
    """2 of 5 -> 3 of 5 passing is progress, not news. Only the verdict matters."""
    w = ci_watch.Watcher()
    w.transition('feature/x', 'pending', '2 of 5 done')
    assert w.transition('feature/x', 'pending', '3 of 5 done') is None


def test_branches_are_tracked_independently():
    w = ci_watch.Watcher()
    w.transition('feature/a', 'passing', 'all green')
    assert w.transition('feature/b', 'passing', 'all green') is not None


def test_no_pr_is_silent_even_on_first_sight():
    """A branch with no PR must never produce a notification."""
    w = ci_watch.Watcher()
    assert w.transition('feature/x', 'no-pr', '') is None


def test_recovery_from_failing_is_reported():
    w = ci_watch.Watcher()
    w.transition('feature/x', 'failing', 'test-conda failed')
    assert w.transition('feature/x', 'passing', 'all green') is not None


def test_verdict_maps_check_rollup_to_a_state():
    assert ci_watch.verdict([{'state': 'SUCCESS'}, {'state': 'SUCCESS'}]) == 'passing'
    assert ci_watch.verdict([{'state': 'SUCCESS'}, {'state': 'FAILURE'}]) == 'failing'
    assert ci_watch.verdict([{'state': 'SUCCESS'}, {'state': 'PENDING'}]) == 'pending'
    assert ci_watch.verdict([]) == 'no-checks'


def test_failure_outranks_pending():
    """A red check is news now, not after the queue drains."""
    assert ci_watch.verdict([{'state': 'FAILURE'}, {'state': 'PENDING'}]) == 'failing'


def test_bucket_is_preferred_over_raw_state():
    """gh emits both; `bucket` is its own documented categorisation."""
    assert ci_watch.verdict([{'bucket': 'pass', 'state': 'WHATEVER'}]) == 'passing'
    assert ci_watch.verdict([{'bucket': 'fail', 'state': 'SUCCESS'}]) == 'failing'


def test_cancelled_counts_as_a_failure():
    assert ci_watch.verdict([{'bucket': 'cancel'}]) == 'failing'


def test_skipped_checks_do_not_block_a_pass():
    assert ci_watch.verdict([{'bucket': 'pass'}, {'bucket': 'skipping'}]) == 'passing'


def test_unknown_state_is_silent():
    """A gh outage is not news about the code."""
    w = ci_watch.Watcher()
    assert w.transition('feature/x', 'unknown', 'gh unavailable') is None


def test_an_outage_does_not_fake_a_change_on_recovery():
    """green -> outage -> green must stay silent, not report 'green' twice."""
    w = ci_watch.Watcher()
    w.transition('feature/x', 'passing', 'all green')
    w.transition('feature/x', 'unknown', 'gh unavailable')
    assert w.transition('feature/x', 'passing', 'all green') is None


def test_a_change_during_an_outage_is_still_caught():
    """green -> outage -> RED is real news; the outage must not swallow it."""
    w = ci_watch.Watcher()
    w.transition('feature/x', 'passing', 'all green')
    w.transition('feature/x', 'unknown', 'gh unavailable')
    assert w.transition('feature/x', 'failing', 'test-conda failed') is not None
