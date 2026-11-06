"""The seeded task.md must be in the format the parsers actually read.

The template shipped the old two-level layout — a comment block and a bare field
list — while `workflow_state.active_blocks` and the `task-breakdown` skill both
expect the three-level one under `## Active`. A freshly seeded file therefore
parsed to zero blocks, so the one-in-flight guard was inert in a new repo, and an
agent filling the fields in place produced a file no guard could read.

These tests pin the template to the format, not to prose about the format.
"""
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import check_task_tracked
import workflow_state

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / 'templates' / 'root' / 'task.md'
SCAFFOLD_START = 'COPY FROM HERE'
SCAFFOLD_END = 'TO HERE'


def template():
    return TEMPLATE.read_text(encoding='utf-8')


def scaffold():
    """The ready-to-copy task block the template carries, uncommented."""
    body = template()
    start = body.index(SCAFFOLD_START) + len(SCAFFOLD_START)
    return body[start:body.index(SCAFFOLD_END, start)].strip('\n')


def filled():
    """The template with one real task filled into its Active section."""
    block = (scaffold()
             .replace('<NN-DDMMYY>', '01-061126')
             .replace('<title>', 'a worked example')
             .replace('<slug>', 'worked-example'))
    body = template()
    return body.replace('## Parked', block + '\n\n## Parked', 1)


def test_the_three_sections_exist_in_order():
    body = template()
    positions = [body.index(h) for h in ('## Active', '## Parked', '## Archive index')]
    assert positions == sorted(positions)


def test_a_freshly_seeded_file_has_nothing_in_flight():
    """A new repo starts with a clean slate, not with a phantom task."""
    assert workflow_state.in_flight(template()) == []


def test_the_example_fields_cannot_be_mistaken_for_a_real_task():
    """The pre-push guard greps ^Task: — the template must not satisfy it."""
    assert check_task_tracked.documented_task_ids(template()) == set()


def test_no_unindented_field_line_outside_a_task_block():
    """An unindented `Task:` in the prose is what fools both parsers."""
    live = re.split(r'^## Active', template(), flags=re.M)[0]
    assert not re.search(r'^Task:', live, re.M)


def test_the_template_carries_a_copyable_scaffold():
    assert SCAFFOLD_START in template() and SCAFFOLD_END in template()


def test_the_scaffold_parses_as_exactly_one_in_flight_task():
    """The real assertion: filling the template in place produces a readable file."""
    assert workflow_state.in_flight(filled()) == [('01-061126', 'active · S1/1')]


def test_the_filled_scaffold_satisfies_the_pre_push_guard():
    ok, msg = check_task_tracked.check('feature/01-061126-worked-example', filled())
    assert ok, msg


def test_the_scaffold_carries_all_three_levels():
    body = scaffold()
    assert re.search(r'^## \S+ —', body, re.M)        # macro
    assert re.search(r'^### S1 —', body, re.M)        # micro
    assert re.search(r'^- \[ \]', body, re.M)         # item


def test_the_scaffold_has_the_outcome_field_empty():
    """A new task must start in flight: an outcome is recorded, never seeded."""
    assert re.search(r'^Outcome:\s*$', scaffold(), re.M)


def test_an_archive_row_does_not_count_as_in_flight():
    """Archive rows carry `Task:` for the guard, but the task is long done."""
    body = template().replace(
        '## Archive index',
        '## Archive index\n\nTask: 02-010126 | 2026-01-01 | an old task | complete')
    assert workflow_state.in_flight(body) == []
    assert '02-010126' in check_task_tracked.documented_task_ids(body)
