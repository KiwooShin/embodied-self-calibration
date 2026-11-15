"""Audit independent locomotion outcomes and summarize paired learning speed."""

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any


def verify_trial(trial: dict[str, Any]) -> bool:
    """Recompute registered success from measurements.

    Args:
        trial: Recorded simulator outcome.
    Returns:
        Whether the trial met all registered walking requirements.
    """
    return (
        trial["distance"] >= 0.5
        and trial["lateral"] <= 0.18
        and trial["min_upright"] >= 0.8
        and not trial["body_contact"]
        and min(trial["touchdowns"]) >= 2
        and trial["airborne_fraction"] <= 0.15
    )


def scores(record: dict[str, Any]) -> dict[str, Any]:
    """Check the raw logs and aggregate censored first mastery and teaching costs.

    Args:
        record: Complete scored study.
    Returns:
        Per-arm learning curves, matched comparisons and costs.
    Raises:
        ValueError: If held-out traces, thresholds or budgets disagree.
    """
    results = {}
    episodes = record["episodes"]
    if len(episodes) != 12 or len({r["seed"] for r in episodes}) != 12:
        raise ValueError("Expected twelve distinct teaching seeds")
    for arm in episodes[0]["arms"]:
        times, reference, firsts, queries, logical = [], [], [], 0, []
        practice_counts, falls, late_stops = [], 0, 0
        for row in episodes:
            run = row["arms"][arm]
            tests = {tuple(t["retained"]): t["starts"] for t in run["tests"]}
            curve = []
            for item in run["training"]:
                starts = tests[tuple(item["retained"])]
                if len(starts) != 3 or any(
                    verify_trial(t) != t["passed"] for t in [item["trial"], *starts]
                ):
                    raise ValueError(f"Inconsistent score in seed {row['seed']}, arm {arm}")
                curve.append(all(t["passed"] for t in starts))
                queries += int(item["action"] == "ask_teacher")
                falls += int(item["trial"]["body_contact"] or item["trial"]["min_upright"] < 0.8)
                if item.get("gate_request"):
                    gate = record["inference"][item["gate_request"]]
                    if gate["reply"]["action"] != "continue_search":
                        raise ValueError(
                            "Unexpected second-stage decision following a gait request"
                        )
                    logical.append(gate["latency_s"])
                if item["request"]:
                    reply = record["inference"][item["request"]]
                    if reply["reply"]["action"] != item["action"]:
                        raise ValueError(
                            "Practice intervention differs from the recorded Qwen reply"
                        )
                    logical.append(reply["latency_s"])
            first = next((i for i, passed in enumerate(curve, 1) if passed), None)
            if (
                curve != run["curve"]
                or run["first_mastery"] != first
                or len(curve) > record["budget"]
            ):
                raise ValueError("Independent mastery does not match the recorded checkpoint")
            if (
                run["training"][0]["candidate"]
                != row["arms"]["qwen_no_demo"]["training"][0]["candidate"]
            ):
                raise ValueError("First practices differ in a paired run")
            firsts.append(first)
            times.append(first if first is not None else record["budget"])
            reference.append(row["arms"]["qwen_no_demo"]["capped_practices"])
            practice_counts.append(len(curve))
            late_stops += int(first is None and run["training"][-1]["trial"]["passed"])
        results[arm] = {
            "mastery_by_practice": [
                sum(t is not None and t <= i for t in firsts) for i in range(1, 7)
            ],
            "final_mastery": sum(r["arms"][arm]["final_mastery"] for r in episodes),
            "capped_mean": round(mean(times), 3),
            "capped_sum": sum(times),
            "first_mastery": firsts,
            "faster": sum(t < r for t, r in zip(times, reference, strict=True)),
            "tied": sum(t == r for t, r in zip(times, reference, strict=True)),
            "slower": sum(t > r for t, r in zip(times, reference, strict=True)),
            "demos": queries,
            "teacher_playback_s": round(queries * record["lesson"]["duration"], 2),
            "calls": len(logical),
            "attributed_call_s": round(sum(logical), 2),
            "median_call_s": round(median(logical), 2) if logical else None,
            "actual_practices": sum(practice_counts),
            "actual_practice_s": round(sum(practice_counts) * 3.6, 2),
            "training_balance_failures": falls,
            "training_pass_but_no_mastery": late_stops,
        }
    return results


def main() -> None:
    """Print a machine-readable summary of the named study files."""
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps({p.stem: scores(json.loads(p.read_text())) for p in args.records}, indent=1))


if __name__ == "__main__":
    main()
