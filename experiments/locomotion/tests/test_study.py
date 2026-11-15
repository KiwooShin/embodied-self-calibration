"""Exercise intervention isolation and teacher-disconnected evaluation."""

from pathlib import Path

from experiments.locomotion.learning import source
from experiments.locomotion.rig import calibrate
from experiments.locomotion.study import evaluate, train


def test_fixed_control_shares_initial_practice(tmp_path: Path) -> None:
    """Train both fixed schedules from identical states without a model endpoint."""
    lesson, _ = source()
    mapping = calibrate(19)
    records = [
        train(19, arm, lesson, mapping, ("", {}, tmp_path / "unused"))
        for arm in ("fixed_search", "fixed_demo")
    ]
    assert records[0][0]["trial"] == records[1][0]["trial"]
    evaluated = evaluate(records[0], mapping)
    assert len(evaluated["curve"]) == len(records[0])
    assert all(len(g["starts"]) == 3 for g in evaluated["tests"])
