"""Check that film scorecards can be drawn directly from a real episode log."""

import json
from pathlib import Path

from integrated_film import score
from PIL import Image, ImageDraw


def test_draw_all_episodes() -> None:
    """Render the aggregate score separately from the example playback."""
    image = Image.new("RGB", (1440, 900))
    root = Path(__file__).resolve().parents[3]
    data = json.loads((root / "results/integrated-rule.json").read_text())
    score(ImageDraw.Draw(image), [("A", data), ("B", data)])
    assert image.getpixel((250, 360)) != (0, 0, 0)
