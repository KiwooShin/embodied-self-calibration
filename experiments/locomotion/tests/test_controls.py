"""Verify equal-start comparisons for the direct transfer diagnostic."""

from experiments.locomotion.controls import direct_transfer


def test_direct_controls_share_starts() -> None:
    """Score standing and both encoders against identical hidden conditions."""
    runs = direct_transfer()
    assert runs["standing"]["passed"] == 0
    expected = [s["start"] for s in runs["standing"]["starts"]]
    assert all([s["start"] for s in item["starts"]] == expected for item in runs.values())
