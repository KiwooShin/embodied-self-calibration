"""Check physical walking, a standing control, and calibrated motor permutations."""

import numpy as np

from experiments.locomotion.rig import (
    STUDENT,
    TEACHER,
    Start,
    calibrate,
    model,
    rollout,
)


def test_supported_pulses_recover_wiring() -> None:
    """Recover every hidden channel and its sign from measured response."""
    mapping = calibrate(13)
    assert mapping["inferred"] == mapping["wiring"]
    assert mapping["inferred_sign"] == mapping["signs"]
    assert np.asarray(mapping["measured_rad"]).shape == (8, 8)


def test_standing_fails_forward_task() -> None:
    """Reject stationary standing even when the trunk remains upright."""
    result = rollout(STUDENT, None)
    assert abs(result["distance"]) < 0.01 and not result["passed"]


def test_source_and_student_are_different_and_free() -> None:
    """Use different action sizes with floating bases and gravity."""
    source, target = (model(b, Start()) for b in (TEACHER, STUDENT))
    assert (source.nu, target.nu) == (12, 8)
    assert target.nv == target.nu + 6 and target.opt.gravity[2] < 0
