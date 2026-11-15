"""Check mastery threshold boundaries and the finite study size."""

import pytest

from experiments.locomotion.metrics import scores, verify_trial


def test_threshold_boundary() -> None:
    """Credit a grounded walk at the limits and reject one without alternating landings."""
    trial = {
        "distance": 0.5,
        "lateral": 0.18,
        "min_upright": 0.8,
        "body_contact": False,
        "touchdowns": [2] * 4,
        "airborne_fraction": 0.15,
    }
    assert verify_trial(trial)
    assert not verify_trial(trial | {"touchdowns": [1, 2, 2, 2]})


def test_incomplete_study_rejected() -> None:
    """Reject partial scores before any comparison is published."""
    with pytest.raises(ValueError, match="twelve"):
        scores({"episodes": []})
