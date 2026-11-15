"""Check the recurring audit against original and corrupted paired evidence."""

import json
from pathlib import Path

import pytest
from review import validate

RECORD = Path(__file__).resolve().parents[2] / "results/teacher-observation-errors.json"


def test_clean_archive() -> None:
    """Reconstruct the registered outcomes without rerunning the simulator."""
    validate(json.loads(RECORD.read_text()))


def test_changed_score_rejected() -> None:
    """Catch an inconsistent success flag even if the overall table stays untouched."""
    record = json.loads(RECORD.read_text())
    trial = record["cases"][0]["methods"]["peak"]["starts"][0]
    trial["passed"] = not trial["passed"]
    with pytest.raises(AssertionError):
        validate(record)
