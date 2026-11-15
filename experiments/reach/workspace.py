"""Evaluate retained and locally refitted motor maps on a paired grid."""

import argparse
import json
from pathlib import Path
import numpy as np
from run import BODIES, probe, reach


def sweep(record):
    result = {}
    for name, params in BODIES.items():
        lengths = params[0]
        frozen = np.array(record["bodies"][name]["frozen_matrix"])
        cases = []
        for shift_deg in range(-90, 91, 15):
            shift = np.deg2rad(shift_deg)
            local = np.column_stack(
                [probe(name, ch, shift)[0] for ch in range(len(lengths))]
            )
            for angle in range(0, 360, 45):
                a = np.deg2rad(angle)
                displacement = 0.1 * np.array([np.cos(a), np.sin(a)])
                entry = {"posture_deg": shift_deg, "direction_deg": angle}
                for method, matrix in (("frozen", frozen), ("refitted", local)):
                    r = reach(name, matrix, shift, displacement)
                    # This test permits the 10 mm scoring ball to touch the
                    # geometric workspace. Joint limits can shrink that area.
                    radius = np.linalg.norm(r["goal"])
                    lo = max(0, 2 * max(lengths) - sum(lengths))
                    entry["within_radial_bound"] = bool(
                        lo - 0.01 <= radius <= sum(lengths) + 0.01
                    )
                    entry[method] = {
                        "passed": r["passed"],
                        "error_mm": r["error_mm"],
                        "commands": (len(r["trace"]) - 1) // 12,
                    }
                cases.append(entry)
        result[name] = cases
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("calibration", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    if args.output.exists():
        p.error("Choose a new output file")
    rows = sweep(json.loads(args.calibration.read_text()))
    args.output.write_text(json.dumps(rows, indent=1) + "\n")
    for name, cases in rows.items():
        print(
            name,
            [(k, sum(c[k]["passed"] for c in cases)) for k in ("frozen", "refitted")],
        )
