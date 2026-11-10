"""A task is not finished until its terminal outcome is recorded.

Grok's Engineering Lead draws the line at "the PR is merged, the work is
explicitly abandoned, or the user takes it back". The harness used to release
the one-in-flight slot as soon as Status read `complete`, which is why a repo
could accumulate eight tasks at `complete — ship pending` with nothing tracking
whether any of them ever landed.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import workflow_state


def block(status, outcome=''):
    return (
        '# Task\n\n## Active\n\n'
        '## 01-041126 — a task\n\n'
        'Task:         01-041126\n'
        f'Status:       {status}\n'
        f'Outcome:      {outcome}\n'
        '\n## Parked\n'
    )


def test_active_task_is_in_flight():
    assert workflow_state.in_flight(block('active · S1/4')) == [('01-041126', 'active · S1/4')]


def test_complete_without_outcome_does_not_hold_the_slot():
    """A built task waiting on a human merge gate must not block the next one.

    The slot is about attention; whether the work LANDED is tracked separately,
    by awaiting_outcome. Conflating them made the workflow hostage to review
    latency.
    """
    assert workflow_state.in_flight(block('complete 2026-11-04 — ship pending')) == []


def test_complete_without_outcome_is_still_chased():
    """Releasing the slot must not mean forgetting the task."""
    assert workflow_state.awaiting_outcome(block('complete 2026-11-04 — ship pending')) == \
        [('01-041126', 'complete 2026-11-04 — ship pending')]


def test_a_recorded_outcome_ends_the_chase():
    assert workflow_state.awaiting_outcome(block('complete 2026-11-04', 'merged #12')) == []


def test_merged_outcome_releases_the_slot():
    assert workflow_state.in_flight(block('complete 2026-11-04', 'merged #12')) == []


def test_abandoned_outcome_releases_the_slot():
    assert workflow_state.in_flight(
        block('complete 2026-11-04', 'abandoned 2026-11-04 — superseded')) == []


def test_taken_back_outcome_releases_the_slot():
    assert workflow_state.in_flight(block('complete 2026-11-04', 'taken-back 2026-11-04')) == []


def test_parked_task_is_not_in_flight():
    assert workflow_state.in_flight(block('pending — parked 2026-11-04')) == []


def test_unrecognised_outcome_does_not_settle_a_task():
    """Only the three terminal words settle a task — not any text at all."""
    assert workflow_state.settled(block('complete 2026-11-04', 'probably fine')) == []
    assert len(workflow_state.awaiting_outcome(block('complete 2026-11-04',
                                                     'probably fine'))) == 1


def test_settled_reports_the_recorded_outcome():
    assert workflow_state.settled(block('complete 2026-11-04', 'merged #12')) == \
        [('01-041126', 'merged #12')]
