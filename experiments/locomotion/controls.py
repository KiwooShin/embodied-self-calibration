"""Test observation encoders directly with the supervisor removed."""

import argparse
import json
from pathlib import Path
from typing import Any

from .learning import HOLDOUT, source
from .rig import STUDENT, calibrate, rollout


def direct_transfer() -> dict[str, Any]:
    """Score both observed stride encoders, shuffled counterparts, and two controls.

    Returns:
        Per-start measurements after directly installing each frozen timing pattern.
    """
    lesson, _ = source()
    wiring = calibrate(410)
    patterns = {
        "standing": None,
        "contact": lesson.phases,
        "height": lesson.height_phases,
        "source_oscillator_reference": (0, 2, 2, 0),
    }
    for method in ("contact", "height"):
        gait = patterns[method]
        patterns[method + "_swapped"] = (gait[0], gait[1], gait[3], gait[2])
    runs = {}
    for label, gait in patterns.items():
        phases = None if gait is None else tuple(p / 4 for p in gait)
        starts = [rollout(STUDENT, phases, start, wiring) for start in HOLDOUT]
        runs[label] = {
            "quarters": gait,
            "starts": starts,
            "passed": sum(test["passed"] for test in starts),
        }
    return runs


def main() -> None:
    """Write the direct execution controls to a new file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output")
    args.output.write_text(json.dumps(direct_transfer(), indent=1) + "\n")


if __name__ == "__main__":
    main()
