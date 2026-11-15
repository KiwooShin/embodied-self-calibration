"""Check that the sensitivity film draws both observed estimator results."""

import json
from pathlib import Path

from observation_film import traces
from PIL import Image, ImageDraw


def test_draw_example_after_teacher_finishes() -> None:
    """Render completed teacher observations with the original trial record."""
    root = Path(__file__).resolve().parents[3]
    record = json.loads((root / "results/teacher-observation-errors.json").read_text())
    image = Image.new("RGB", (1440, 900))
    traces(ImageDraw.Draw(image), record["cases"][0], 150)
    assert image.getpixel((950, 340)) != (0, 0, 0)
