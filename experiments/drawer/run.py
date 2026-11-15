"""Run inside Isaac Sim's Python. See README for runtime and model commands."""

import argparse
import json
from pathlib import Path
from types import MappingProxyType

from supervisor import SYSTEM, decision

# Coordinates in metres. Held-out tests also change the initial pin-to-face gap.
TEST_POSES = ((0.16, 0.003), (-0.09, 0.008), (0.28, 0.012))
GOAL_MM = 60


def attempt(station, config, skill, origin=0, gap=0):
    with station(**config, origin=origin, gap=gap) as rig:
        if skill["lift_mm"]:
            rig.move(0, skill["lift_mm"])
        command = skill["polarity"] * 90
        result = rig.move(command, skill["lift_mm"])
        return {
            "kind": "practice",
            "pull_command_mm": command,
            "result": result,
        }, rig.trace


def standard_demo(station, config):
    with station(latched=config["latched"], teacher=True) as rig:
        rig.move(0, 45)
        result = rig.move(90, 45)
        if result["drawer_x_mm"] < GOAL_MM:
            raise RuntimeError("Teacher failed the demonstration")
        return rig.trace


def trial(
    station,
    config,
    mode,
    endpoint,
    training_gap=0,
    demonstrate=standard_demo,
    clearance_mm=6,
    model_id="qwen3-8b",
):
    skill = {"polarity": 1, "lift_mm": 0.0}
    initial, trace = attempt(station, config, skill, gap=training_gap)
    history, traces, choices = [initial], [trace], []
    for _ in range(5):
        selected = decision(mode, history, skill, endpoint, model_id=model_id)
        choices.append(selected)
        action = selected["action"]
        if action == "assess":
            break
        if action == "practice":
            episode, trace = attempt(station, config, skill, gap=training_gap)
        elif action == "probe":
            with station(**config, free=True) as rig:
                result = rig.move(12, 0)
                if abs(result["tool_x_mm"]) >= 4:
                    skill["polarity"] = 1 if result["tool_x_mm"] > 0 else -1
                episode = {"kind": action, "pull_command_mm": 12, "result": result}
                trace = rig.trace
        elif action == "ask_teacher":
            trace = demonstrate(station, config)
            segment = []
            for frame in trace:
                segment.append(
                    {k: frame[k] for k in ("tick", "handle_z_mm", "drawer_x_mm")}
                )
                if frame["drawer_x_mm"] >= 5:
                    break
            lift = max(frame["handle_z_mm"] for frame in segment)
            skill["lift_mm"] = min(80, lift + clearance_mm)
            episode = {"kind": action, "segment": segment}
        history.append(episode)
        traces.append(trace)
    frozen = MappingProxyType(skill.copy())
    tests = []
    for origin, gap in TEST_POSES:
        result, trace = attempt(station, config, frozen, origin, gap)
        tests.append(
            {
                "origin_m": origin,
                "gap_m": gap,
                "result": result["result"],
                "success": result["result"]["drawer_x_mm"] >= GOAL_MM,
                "trace": trace,
            }
        )
    return {
        "training_gap_m": training_gap,
        "clearance_mm": clearance_mm,
        "decisions": choices,
        "history": history,
        "traces": traces,
        "frozen_skill": dict(frozen),
        "tests": tests,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--shifted", action="store_true", help="ODE gain 0.92, 6 mm training gap"
    )
    parser.add_argument(
        "--mode",
        choices=["rule", "qwen", "qwen-observed", "qwen-scheduled"],
        required=True,
    )
    parser.add_argument("--backend", choices=["isaac", "ode"], default="isaac")
    parser.add_argument("--suite", choices=["paired", "transfer"], default="paired")
    parser.add_argument("--endpoint", default="http://127.0.0.1:18081/v1")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Choose a new output file")
    if args.shifted and args.backend != "ode":
        parser.error("--shifted is defined on ODE")
    app = None
    if args.backend == "isaac":
        from isaacsim import SimulationApp

        app = SimulationApp({"headless": True})
        from fixture import station
    else:
        from ode_fixture import station
    try:
        results = {}
        suites = {
            "paired": (
                ("channel_reversed", True, False),
                ("latch_engaged", False, True),
            ),
            "transfer": (("both_faults", True, True), ("nominal", False, False)),
        }
        for name, polarity, latch in suites[args.suite]:
            config = dict(reversed_pull=polarity, latched=latch)
            if args.shifted:
                config["gain"] = 0.92
            results[name] = trial(
                station, config, args.mode, args.endpoint, 0.006 if args.shifted else 0
            )
            print(
                name,
                [d["action"] for d in results[name]["decisions"]],
                [t["success"] for t in results[name]["tests"]],
                flush=True,
            )
        args.out.parent.mkdir(exist_ok=True, parents=True)
        args.out.write_text(
            json.dumps(
                {
                    "mode": args.mode,
                    "suite": args.suite,
                    "backend": args.backend,
                    "shifted": args.shifted,
                    "prompt": SYSTEM,
                    "conditions": results,
                },
                indent=2,
            )
            + "\n"
        )
    except Exception:
        import traceback

        traceback.print_exc()
        raise
    else:
        if app is not None:
            app.close()
