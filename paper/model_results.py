"""Summarize fully written integrated runs; report missing checkpoints explicitly."""

import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
out = {}
for tag, file in [
    ("rule", "integrated-rule"),
    ("small", "integrated-qwen-observed"),
    ("large", "integrated-qwen32"),
]:
    path = ROOT / "results" / (file + ".json")
    if not path.exists():
        continue
    cases = json.loads(path.read_text())["conditions"]
    choices = [d for c in cases.values() for d in c["decisions"]]
    calls = [d["latency_s"] for d in choices if "latency_s" in d]
    totals = [sum(t["success"] for t in c["tests"]) for c in cases.values()]
    assert len(cases) == 8 and all(len(c["tests"]) == 3 for c in cases.values())
    out[tag] = dict(
        passed=sum(totals),
        episodes=sum(n == 3 for n in totals),
        calls=len(calls),
        queries=sum(d["action"] == "ask_teacher" for d in choices),
        pulses=sum(d["action"] == "probe" for d in choices),
        latency=round(median(calls), 1) if calls else 0,
        splits={key: sum(t["success"] for t in c["tests"]) for key, c in cases.items()},
    )
(ROOT / "paper/model-results.json").write_text(json.dumps(out, indent=2) + "\n")
