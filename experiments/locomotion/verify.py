"""Reproduce each published gait episode using archived Qwen replies and fresh physics."""

import argparse
import json
from pathlib import Path
from typing import Any

from .learning import source
from .metrics import scores
from .rig import calibrate
from .study import evaluate, train


def verify(record: dict[str, Any]) -> int:
    """Run the saved choices again without a model endpoint or a writable journal.

    Args:
        record: Published study with its exact model request archive.
    Returns:
        Number of reproduced complete teaching episodes.
    Raises:
        ValueError: If a decision, simulator outcome, checkpoint or hidden score differs.
    """
    scores(record)
    lesson, _ = source()
    if list(lesson.phases) != record["lesson"]["phases"]:
        raise ValueError("Measured source stride differs from archive")
    count = 0
    for row in record["episodes"]:
        seed = row["seed"]
        mapping = calibrate(seed)
        if mapping != row["mapping"]:
            raise ValueError(f"Motor response replay diverged at seed {seed}")
        for arm, stored in row["arms"].items():
            history = train(seed, arm, lesson, mapping, ("", record["inference"], Path(".")))
            if len(history) != len(stored["training"]):
                raise ValueError(f"Different practice count at {seed}/{arm}")
            for current, old in zip(history, stored["training"], strict=True):
                for key in ("action", "candidate", "trial", "request", "retained", "gate_request"):
                    if current.get(key) != old.get(key):
                        raise ValueError(f"Replay mismatch at {seed}/{arm}/{key}")
            for key, value in evaluate(history, mapping).items():
                if value != stored[key]:
                    raise ValueError(f"Independent test mismatch at {seed}/{arm}/{key}")
            count += 1
    return count


def main() -> None:
    """Audit one or more source JSON files and report replayed episode counts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="+", type=Path)
    for path in parser.parse_args().records:
        print(path.name, verify(json.loads(path.read_text())), flush=True)


if __name__ == "__main__":
    main()
