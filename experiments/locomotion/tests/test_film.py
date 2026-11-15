"""Test that gait narration follows measured teaching outcomes."""

from experiments.locomotion.film import narration


def test_narration_uses_recorded_query_count() -> None:
    """Carry the observed gate count into the narrated results."""
    sample = {"demos": 2, "final_mastery": 3}
    studies = [
        {"qwen_demo": sample, "qwen_no_demo": sample},
        {"fixed_height": sample},
        {"qwen_gate_height": sample, "qwen_no_demo": sample, "fixed_height": sample},
    ]
    words = narration(studies, {"requester": "qwen_gate_height", "slot": 2})
    assert len(words) == 5
    assert "requested 2 strides" in words[-1][1]
