"""Calibrate the numeric switching rule on one body and evaluate on another."""

import argparse
import json
from pathlib import Path
import time
import numpy as np
from run import Arm, BODIES, choose, motor_command, probe, reach

PROMPT = """After the first movement of a planar reaching skill, decide whether to keep
the current local motor map or reset and reprobe every channel. You see an endpoint
goal and the displacement predicted and actually measured during the first move.
The target is within 10 mm of the goal. A refit costs three extra bounded pulses
and a reset. Seek high success while avoiding needless probes. A residual ratio
of zero means perfect predicted first-step motion. Recalibration cannot make an
unreachable goal reachable. Return one action and a brief evidence sentence. /no_think"""


def first_move(name, shift, goal, matrix):
    student = Arm(name, shift)
    before = student.endpoint()
    command = motor_command(matrix, goal)
    predicted = matrix @ command
    student.step(command)
    actual = student.endpoint() - before
    return {
        "goal_mm": (1000 * goal).round(2).tolist(),
        "predicted_mm": (1000 * predicted).round(2).tolist(),
        "actual_mm": (1000 * actual).round(2).tolist(),
        "remaining_mm": round(1000 * np.linalg.norm(goal - actual), 2),
        "residual_ratio": round(
            np.linalg.norm(predicted - actual) / max(1e-9, np.linalg.norm(predicted)), 4
        ),
        "reprobe_count": matrix.shape[1],
    }


def displacement(angle):
    return 0.1 * np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])


def select_threshold(matrix, training):
    rows = []
    for r in training:
        report = first_move(
            "two_link",
            np.deg2rad(r["posture_deg"]),
            displacement(r["direction_deg"]),
            matrix,
        )
        rows.append(
            (report["residual_ratio"], r["frozen"]["passed"], r["refitted"]["passed"])
        )
    scored = []
    for threshold in [0] + sorted(set(r[0] for r in rows)):
        changed = sum(r[0] > threshold for r in rows)
        passed = sum(
            (new if residual > threshold else old) for residual, old, new in rows
        )
        scored.append((passed - 0.05 * 2 * changed, -changed, threshold))
    return max(scored)[2]


def run(args):
    calibration = json.loads(args.calibration.read_text())["bodies"]
    training = json.loads(args.training.read_text())["two_link"]
    threshold = select_threshold(
        np.array(calibration["two_link"]["frozen_matrix"]), training
    )
    name = "three_link"
    frozen = np.array(calibration[name]["frozen_matrix"])
    rows = []
    for degrees in (-72, -36, -12, 12, 36, 72):
        shift = np.deg2rad(degrees)
        local = np.column_stack(
            [probe(name, c, shift)[0] for c in range(len(BODIES[name][0]))]
        )
        for angle in np.arange(22.5, 360, 45):
            goal = displacement(angle)
            obs = first_move(name, shift, goal, frozen)
            t = time.monotonic()
            qwen = choose(obs, ["keep", "reprobe"], args.endpoint, PROMPT)
            latency = time.monotonic() - t
            outcomes = {}
            for action, matrix in (("keep", frozen), ("reprobe", local)):
                # keep replays the exact first move as part of the rollout.
                # reprobe begins at the original posture after the diagnostic.
                trial = reach(name, matrix, shift, goal)
                outcomes[action] = {k: trial[k] for k in ["error_mm", "passed"]}
                outcomes[action]["student_commands"] = (
                    len(trial["trace"]) - 1
                ) // 12 + (1 + len(local.T) if action == "reprobe" else 0)
            rows.append(
                {
                    "posture_deg": degrees,
                    "direction_deg": float(angle),
                    "observation": obs,
                    "qwen": qwen,
                    "qwen_latency_s": round(latency, 3),
                    "rule": "reprobe" if obs["residual_ratio"] > threshold else "keep",
                    "outcomes": outcomes,
                }
            )
        print(f"{len(rows)}/48 held-out decisions measured", flush=True)
    return {"threshold": threshold, "prompt": PROMPT, "rows": rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("calibration", type=Path)
    p.add_argument("training", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--endpoint", default="http://127.0.0.1:18081/v1")
    args = p.parse_args()
    if args.output.exists():
        p.error("Choose a new output file")
    args.output.write_text(json.dumps(run(args), indent=1) + "\n")
