"""Check the registered transfer estimator and noise-grid pairing."""

import pytest
from observations import estimate, run


def test_short_spike_changes_only_raw_peak() -> None:
    """Filter an isolated height spike with the same clearance for both estimates."""
    assert estimate([0, 8, 20, 8]) == {"peak": 23, "median3_peak": 11}


def test_short_segment_rejected() -> None:
    """Reject a teacher segment too short for the median window."""
    with pytest.raises(ValueError, match="at least three"):
        estimate([1, 2])


def test_duplicate_seeds_rejected_before_physics() -> None:
    """Exclude duplicated seed identifiers from a paired replication."""
    with pytest.raises(ValueError, match="distinct"):
        run([1, 1])
