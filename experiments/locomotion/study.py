"""Run paired cross-body locomotion teaching and separately score frozen checkpoints."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .agent import decide
from .learning import HOLDOUT, Gait, Lesson, candidates, choose_candidate, rank, source
from .rig import STUDENT, calibrate, rollout

ARMS = ("qwen_no_demo", "qwen_demo", "qwen_shuffled", "fixed_search", "fixed_demo")
SECONDARY = ("qwen_no_demo", "qwen_demo", "qwen_height", "qwen_height_shuffled", "fixed_height")
GATED = ("qwen_no_demo", "qwen_gate_height", "qwen_gate_height_shuffled", "fixed_height")
SEEDS = tuple(range(410, 422))
BUDGET = 6


def train(
    seed: int,
    arm: str,
    lesson: Lesson,
    wiring: dict[str, Any],
    inference: tuple[str, dict[str, Any], Path],
) -> list[dict[str, Any]]:
    """Teach one student without exposing any held-out outcome to the supervisor.

    Args:
        seed: Paired curriculum seed.
        arm: Registered intervention condition.
        lesson: Observed teacher stride.
        wiring: Supported calibration and hidden actuator adapter.
        inference: Local endpoint, request archive and resumable journal path.
    Returns:
        Practice history with persistent frozen student checkpoints.
    """
    queue = candidates(seed)
    pattern = lesson.height_phases if "height" in arm else lesson.phases
    if arm.endswith("shuffled"):
        pattern = (pattern[0], pattern[1], pattern[3], pattern[2])
    used = False
    history = []
    for slot in range(BUDGET):
        key = None
        cached = False
        gate_key = None
        action = "explore"
        if slot:
            if arm.startswith("qwen"):
                available = ["explore", "refine"]
                if "gate" in arm and not used:
                    gate_action, gate_key, cached = decide(
                        history, ["continue_search", "ask_teacher"], *inference
                    )
                    if gate_action == "ask_teacher":
                        action, key, gate_key = gate_action, gate_key, None
                elif arm != "qwen_no_demo" and not used:
                    available.append("ask_teacher")
                if key is None:
                    action, key, cached = decide(history, available, *inference)
            elif arm in ("fixed_demo", "fixed_height") and not used:
                action = "ask_teacher"
        used |= action == "ask_teacher"
        gait = choose_candidate(action, history, queue, pattern) if slot else queue[0]
        trial = rollout(STUDENT, tuple(k / 4 for k in gait), mapping=wiring)
        history.append(
            {
                "action": action,
                "candidate": list(gait),
                "trial": trial,
                "request": key,
                "reused": cached,
                "gate_request": gate_key,
            }
        )
        best = max(history, key=lambda entry: rank(entry["trial"]))
        history[-1]["retained"] = best["candidate"]
        if trial["passed"]:
            break
    return history


def evaluate(history: list[dict[str, Any]], wiring: dict[str, Any]) -> dict[str, Any]:
    """Execute retained snapshots on three hidden starts after teaching has ended.

    Args:
        history: Completed training with saved phase patterns.
        wiring: Student's previously learned command map.
    Returns:
        Independent outcomes, first crossing, censoring and final mastery.
    """
    tested: dict[Gait, list[dict[str, Any]]] = {}
    curve = []
    first = None
    for slot, item in enumerate(history, 1):
        retained = tuple(item["retained"])
        if retained not in tested:
            tested[retained] = [
                rollout(STUDENT, tuple(k / 4 for k in retained), start, wiring) for start in HOLDOUT
            ]
        scores = tested[retained]
        passed = all(s["passed"] for s in scores)
        curve.append(passed)
        if passed and first is None:
            first = slot
    return {
        "first_mastery": first,
        "capped_practices": first if first is not None else BUDGET,
        "final_mastery": curve[-1],
        "curve": curve,
        "tests": [{"retained": list(gait), "starts": scores} for gait, scores in tested.items()],
    }


def main() -> None:
    """Run the registered grid, logging paired outcomes and provenance."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--journal", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--secondary", action="store_true")
    group.add_argument("--gated", action="store_true")
    parser.add_argument("--endpoint", default="http://127.0.0.1:18085/v1")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new result path")
    archive = json.loads(args.journal.read_text()) if args.journal.exists() else {}
    lesson, teacher = source()
    print("source", lesson.phases, lesson.duration, flush=True)
    records = []
    seeds, arms, label = (
        (range(610, 622), GATED, "gated")
        if args.gated
        else (
            (range(510, 522), SECONDARY, "height") if args.secondary else (SEEDS, ARMS, "contacts")
        )
    )
    for seed in seeds:
        wiring = calibrate(seed)
        episodes = {}
        for arm in arms:
            history = train(seed, arm, lesson, wiring, (args.endpoint, archive, args.journal))
            episodes[arm] = {"training": history, **evaluate(history, wiring)}
        records.append({"seed": seed, "mapping": wiring, "arms": episodes})
        print(
            seed,
            [(a, ep["first_mastery"], len(ep["training"])) for a, ep in episodes.items()],
            flush=True,
        )
    output = {
        "model": "Qwen3-8B-Q4_K_M",
        "budget": BUDGET,
        "lesson": asdict(lesson),
        "source_metrics": {
            k: v for k, v in teacher.items() if k not in ("qpos", "contacts", "foot_height")
        },
        "observation_study": label,
        "episodes": records,
        "inference": archive,
    }
    args.output.write_text(json.dumps(output, indent=1) + "\n")


if __name__ == "__main__":
    main()
