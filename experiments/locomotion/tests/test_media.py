"""Exercise the gait film's measurement chart without a rendering device."""

from dataclasses import asdict

from experiments.locomotion.learning import source
from experiments.locomotion.media import H, W, canvas, contact_chart


def test_draw_source_stride() -> None:
    """Draw the measured stride at its final frame on a full-size canvas."""
    lesson, _ = source()
    frame = canvas("Stride", "Audit")
    contact_chart(frame, asdict(lesson), 1)
    assert frame.size == (W, H)
