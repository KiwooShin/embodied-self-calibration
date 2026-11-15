"""Exercise chapter generation and exact subtitle time formatting."""

from walkthrough import chapters, stamp


def test_score_is_read_from_completed_run() -> None:
    """Use the supplied episode score in the visible chapter caption."""
    reels = chapters(
        {
            "small": {"episodes": 5},
            "large": {"episodes": 7, "queries": 10},
            "rule": {"episodes": 8, "queries": 6},
        }
    )
    assert len(reels) == 6
    assert "32B  7/8" in reels[3][3]


def test_subtitle_minute_rollover() -> None:
    """Carry a rounded millisecond through a minute boundary."""
    assert stamp(59.9997) == "00:01:00,000"
