"""Check that the sensitivity film draws both observed estimator results."""

import json
from pathlib import Path

from observation_film import load_record, traces
from PIL import Image, ImageDraw


def test_draw_example_after_teacher_finishes() -> None:
    """Render completed teacher observations with the original trial record."""
    root = Path(__file__).resolve().parents[3]
    record = json.loads((root / "results/teacher-observation-errors.json").read_text())
    image = Image.new("RGB", (1440, 900))
    traces(ImageDraw.Draw(image), record["cases"][0], 150)
    assert image.getpixel((950, 340)) != (0, 0, 0)


def test_daily_film_counts_clean_control_once(tmp_path: Path) -> None:
    """Pool new noisy starts while deduplicating repeated noiseless controls."""
    root = Path(__file__).resolve().parents[3]
    record = json.loads((root / "results/replications/seed-100.json").read_text())
    for seed in (100, 101):
        record["seeds"] = [seed]
        (tmp_path / f"seed-{seed}.json").write_text(json.dumps(record))
    combined = load_record(tmp_path)
    assert combined["paired_summary"]["0"]["starts"] == 27
    assert combined["paired_summary"]["4"]["starts"] == 54
