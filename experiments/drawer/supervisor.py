"""Supervisors receive only the public observation history and student skill."""

import json
import time
from urllib.request import Request, urlopen

ACTIONS = ("probe", "ask_teacher", "practice", "assess")
SYSTEM = """You teach a student Cartesian robot to pull a drawer at least 60 mm.
Choose one action for the next trial. probe: run one free-space diagnostic of
the horizontal motor channel; the student estimates its sign from the response.
ask_teacher: request the handle trajectory before first drawer translation
from a robot with a different mechanism. The student learns an object-space
subgoal. practice: try the student's current skill in the training setup.
assess: finish teaching and freeze the student's current skill for new starts.
An attempt report gives positive commanded and measured distances in mm;
negative observations mean the tool moved the other way. The plain pull skill
assumes positive horizontal polarity and zero lift. Use evidence to distinguish
a motor problem from a missing interaction sequence. Spend a teacher query
only when it helps. Prefer a successful practice before assessment. Return
JSON with action and one short evidence sentence. /no_think"""


def decision(mode, history, skill, endpoint, model_id="qwen3-8b"):
    last = history[-1]
    if mode == "rule":
        if last["kind"] == "practice" and last["result"]["drawer_x_mm"] >= 60:
            action = "assess"
        elif last["kind"] != "practice":
            action = "practice"
        elif last["result"]["tool_x_mm"] < -5:
            action = "probe"
        else:
            action = "ask_teacher"
        return {"action": action, "evidence": "Fixed telemetry rule"}
    if mode == "qwen-scheduled":
        if last["kind"] in ("ask_teacher", "probe"):
            return {
                "action": "practice",
                "evidence": "Exercise the updated skill.",
                "source": "scheduler",
            }
        if last["result"]["drawer_x_mm"] >= 60:
            return {
                "action": "assess",
                "evidence": "Practice reached 60 mm.",
                "source": "scheduler",
            }
    report = {"history": history, "skill": skill}
    if mode in ("qwen-observed", "qwen-scheduled"):
        # Derived only from the same measurements available in the raw condition.
        practices = [event for event in history if event["kind"] == "practice"]
        measured = practices[-1]["result"]
        dx = measured["tool_x_mm"]
        report["last_practice_score"] = {
            "tool_motion_relative_to_desired_pull": "backward" if dx < 0 else "forward",
            "drawer_opened_mm": measured["drawer_x_mm"],
            "required_mm": 60,
            "task_goal_met": measured["drawer_x_mm"] >= 60,
        }
    payload = {
        "model": model_id,
        "temperature": 0,
        "seed": 13,
        "max_tokens": 160,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(report)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "decision",
                "schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": list(ACTIONS)},
                        "evidence": {"type": "string"},
                    },
                    "required": ["action", "evidence"],
                    "additionalProperties": False,
                },
            },
        },
    }
    request = Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.monotonic()
    with urlopen(request, timeout=180) as response:
        answer = json.load(response)
    choice = json.loads(answer["choices"][0]["message"]["content"])
    if choice["action"] not in ACTIONS or not isinstance(choice["evidence"], str):
        raise ValueError(f"Invalid supervisor decision: {choice}")
    return dict(
        **choice,
        report=report.copy() | {"history": list(history), "skill": dict(skill)},
        latency_s=round(time.monotonic() - start, 3),
        usage=answer.get("usage"),
    )
