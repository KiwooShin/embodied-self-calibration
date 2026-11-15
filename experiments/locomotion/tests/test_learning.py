"""Check circular phase inference, the real source stride, and student search."""

import pytest

from experiments.locomotion.learning import (
    candidates,
    choose_candidate,
    source,
    stride_phases,
)


def test_circular_contact_inference() -> None:
    """Recover diagonal timing even when the stance straddles the trace boundary."""
    contacts = [[int((t - offset) % 16 < 9) for offset in (3, 11, 11, 3)] for t in range(16)]
    assert stride_phases(contacts) == (0, 2, 2, 0)


def test_missing_swing_rejected() -> None:
    """Reject a source continuously planted on all four feet."""
    with pytest.raises(ValueError, match="touchdown"):
        stride_phases([[1] * 4 for _ in range(20)])


def test_source_measurements_and_candidate_coverage() -> None:
    """Use measured motion and allow search to discover either resulting phase pattern."""
    lesson, trace = source()
    assert trace["passed"] and 0.4 < lesson.duration < 0.7
    choices = candidates(9)
    assert len(set(choices)) == 64 and lesson.phases in choices and lesson.height_phases in choices
    assert choose_candidate("ask_teacher", [], choices, lesson.phases) == lesson.phases
