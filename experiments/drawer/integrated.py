"""Eight unseen fixture / motor pairs under the same limited teaching budget."""

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
from keyed import KeyedDrawer, expert
from run import trial
from supervisor import SYSTEM


@contextmanager
def station(**kwargs):
    yield KeyedDrawer(**kwargs)


def demonstrate(_, config):
    return expert(config["gate_mm"])["trace"]


def study(mode, endpoint, model_id):
    cases = {}
    for g in (None, 16, 34, 52):
        for reversed_pull in (False, True):
            key = f"{g or 'open'}-{'reverse' if reversed_pull else 'normal'}"
            cases[key] = trial(
                station,
                {"gate_mm": g, "reversed_pull": reversed_pull},
                mode,
                endpoint,
                demonstrate=demonstrate,
                clearance_mm=3,
                model_id=model_id,
            )
            print(
                key,
                [d["action"] for d in cases[key]["decisions"]],
                sum(t["success"] for t in cases[key]["tests"]),
                flush=True,
            )
    return {
        "backend": "ode",
        "mode": mode,
        "model_id": model_id,
        "prompt": SYSTEM,
        "conditions": cases,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["rule", "qwen-observed"], required=True)
    p.add_argument("--model", default="qwen3-8b")
    p.add_argument("--endpoint", default="http://127.0.0.1:18081/v1")
    p.add_argument("out", type=Path)
    args = p.parse_args()
    if args.out.exists():
        p.error("Choose a new output file")
    args.out.write_text(
        json.dumps(study(args.mode, args.endpoint, args.model), indent=1) + "\n"
    )
