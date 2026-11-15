"""Replay paired teacher height observations under known bias and per-frame noise."""

import argparse
from collections import Counter
import json
from pathlib import Path
from random import Random
from statistics import median

from keyed import GAPS, GATES, KeyedDrawer, expert

BIASES = (-6, 0, 6)
SIGMAS = (0, 2, 4)


def estimate(samples):
    filtered = [median(samples[i - 2 : i + 1]) for i in range(2, len(samples))]
    return {"peak": max(samples) + 3, "median3_peak": max(filtered) + 3}


def evaluate(gate, lift):
    starts = []
    for gap in GAPS:
        student = KeyedDrawer(gate, gap=gap, origin=0.17)
        student.move(0, lift)
        result = student.move(90, lift)
        starts.append(
            {
                "gap_mm": round(gap * 1000),
                "drawer_mm": result["drawer_x_mm"],
                "passed": result["drawer_x_mm"] >= 60,
            }
        )
    return starts


def run(seeds):
    cases = []
    for gate in GATES:
        heights = [f["handle_z_mm"] for f in expert(gate)["segment"]]
        for seed in seeds:
            rng = Random(1009 * seed + gate)
            draws = [rng.gauss(0, 1) for _ in heights]
            for sigma in SIGMAS:
                if sigma == 0 and seed != seeds[0]:
                    continue
                for bias in BIASES:
                    obs = [h + bias + sigma * z for h, z in zip(heights, draws)]
                    trials = {
                        name: {"lift_mm": lift, "starts": evaluate(gate, lift)}
                        for name, lift in estimate(obs).items()
                    }
                    cases.append(
                        dict(
                            gate_mm=gate,
                            bias_mm=bias,
                            sigma_mm=sigma,
                            seed=seed if sigma else None,
                            teacher_heights_mm=heights,
                            observed_heights_mm=obs,
                            methods=trials,
                        )
                    )
    return {"seeds": seeds, "cases": cases}


def summarize(cases):
    by_sigma = {}
    for sigma in SIGMAS:
        counts = Counter()
        for c in cases:
            if c["sigma_mm"] != sigma:
                continue
            a, b = (c["methods"][m]["starts"] for m in ("peak", "median3_peak"))
            for x, y in zip(a, b):
                counts.update(
                    dict(
                        starts=1,
                        peak=int(x["passed"]),
                        median3_peak=int(y["passed"]),
                        gain=int(y["passed"] and not x["passed"]),
                        loss=int(x["passed"] and not y["passed"]),
                    )
                )
        by_sigma[str(sigma)] = dict(counts)
    return by_sigma


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    if len(set(args.seeds)) != len(args.seeds) or args.out.exists():
        p.error("Use distinct seeds and a new output path")
    result = run(args.seeds)
    result["paired_summary"] = summarize(result["cases"])
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["paired_summary"], indent=2))
