"""Verify that table generation preserves the teaching episode as the unit."""

import json
from pathlib import Path

import pytest
from model_results import summarize_conditions


def test_valid_rule_record() -> None:
    """Count a fully successful fixed rule as eight teaching episodes."""
    path = Path(__file__).resolve().parents[2] / "results/integrated-rule.json"
    table = summarize_conditions(json.loads(path.read_text())["conditions"])
    assert (table["episodes"], table["passed"], table["queries"]) == (8, 24, 6)


def test_partial_run_rejected() -> None:
    """Prevent a partial model run from entering the manuscript tables."""
    with pytest.raises(ValueError, match="eight"):
        summarize_conditions({})
