"""Check the raw source of the plotted workspace grid."""

from figures import load


def test_all_workspace_outcomes_available() -> None:
    """Require both arms and all 208 measured posture and direction combinations."""
    assert sorted(map(len, load("workspace-sweep.json").values())) == [104, 104]
