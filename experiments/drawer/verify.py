"""Audit saved reports against the physics traces without Isaac, ODE, or a model."""

import argparse
import json
from pathlib import Path


def audit(path):
    run = json.loads(path.read_text())
    totals = dict(passed=0, starts=0, calls=0, queries=0, student_s=0.0, teacher_s=0.0)
    for name, case in run["conditions"].items():
        events, traces, choices = case["history"], case["traces"], case["decisions"]
        assert len(events) == len(traces), name
        assert events[0]["kind"] == "practice" and len(choices) <= 5, name
        assert [e["kind"] for e in events[1:]] == [
            d["action"] for d in choices if d["action"] != "assess"
        ], name
        skill = dict(polarity=1, lift_mm=0.0)
        for event, trace in zip(events, traces):
            assert [f["tick"] for f in trace] == list(
                range(12, trace[-1]["tick"] + 1, 12)
            ), name
            duration = trace[-1]["tick"] / 240
            kind = event["kind"]
            if kind == "ask_teacher":
                segment = event["segment"]
                assert segment[-1]["drawer_x_mm"] >= 5, name
                assert all(f["drawer_x_mm"] < 5 for f in segment[:-1]), name
                assert all(
                    all(t[k] == f[k] for k in f) for t, f in zip(trace, segment)
                ), name
                skill["lift_mm"] = min(80, max(f["handle_z_mm"] for f in segment) + 6)
                totals["queries"] += 1
                totals["teacher_s"] += duration
            else:
                assert all(trace[-1][k] == v for k, v in event["result"].items()), name
                if kind == "probe" and abs(trace[-1]["tool_x_mm"]) >= 4:
                    skill["polarity"] = 1 if trace[-1]["tool_x_mm"] > 0 else -1
                totals["student_s"] += duration
        assert skill == case["frozen_skill"], name
        assert len({(t["origin_m"], t["gap_m"]) for t in case["tests"]}) == 3, name
        for t in case["tests"]:
            assert t["result"]["drawer_x_mm"] == t["trace"][-1]["drawer_x_mm"], name
            assert t["success"] == (t["result"]["drawer_x_mm"] >= 60), name
            totals["starts"] += 1
            totals["passed"] += t["success"]
        totals["calls"] += sum("latency_s" in d for d in choices)
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path, nargs="+")
    for record in parser.parse_args().records:
        print(record.name, json.dumps(audit(record)))
