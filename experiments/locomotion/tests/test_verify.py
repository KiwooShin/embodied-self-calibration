"""Require archived replies for a fully offline locomotion replay."""

from pathlib import Path

import pytest

from experiments.locomotion.agent import decide
from experiments.locomotion.verify import verify


def test_offline_missing_decision_is_an_error() -> None:
    """Fail offline reproducibility without contacting an external model."""
    with pytest.raises(ValueError, match="Missing archived"):
        decide([], ["refine"], "", {}, Path("."))


def test_replay_requires_complete_cohort() -> None:
    """Disallow silently passing an incomplete experiment."""
    with pytest.raises(ValueError, match="twelve"):
        verify({"episodes": []})
