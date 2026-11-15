"""Derive the manuscript tables from completed integrated teaching episodes."""

import json
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "rule": "integrated-rule",
    "small": "integrated-qwen-observed",
    "large": "integrated-qwen32",
}


def summarize_conditions(cases: dict[str, Any]) -> dict[str, Any]:
    """Count frozen-student outcomes and supervisor costs.

    Args:
        cases: Integrated trial histories indexed by the gate and motor polarity.
    Returns:
        Counts, matched per-condition splits, and median model latency in seconds.
    Raises:
        ValueError: If any expected fixture or independent evaluation start is missing.
    """
    expected = {
        f"{gate}-{pol}" for gate in ("open", "16", "34", "52") for pol in ("normal", "reverse")
    }
    if set(cases) != expected or any(len(c["tests"]) != 3 for c in cases.values()):
        raise ValueError(
            "Expected all eight gate/polarity conditions and three frozen starts in each"
        )
    choices = [decision for case in cases.values() for decision in case["decisions"]]
    calls = [d["latency_s"] for d in choices if "latency_s" in d]
    splits = {key: sum(t["success"] for t in c["tests"]) for key, c in cases.items()}
    return {
        "passed": sum(splits.values()),
        "episodes": sum(n == 3 for n in splits.values()),
        "calls": len(calls),
        "queries": sum(d["action"] == "ask_teacher" for d in choices),
        "pulses": sum(d["action"] == "probe" for d in choices),
        "latency": round(median(calls), 1) if calls else 0,
        "splits": splits,
    }


def main() -> None:
    """Build the paper table from each available complete checkpoint."""
    table = {}
    for label, file in FILES.items():
        path = ROOT / "results" / (file + ".json")
        if path.is_file():
            table[label] = summarize_conditions(json.loads(path.read_text())["conditions"])
    (ROOT / "paper/model-results.json").write_text(json.dumps(table, indent=2) + "\n")


if __name__ == "__main__":
    main()
