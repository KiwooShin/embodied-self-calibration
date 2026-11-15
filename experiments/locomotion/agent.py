"""Call a local schema-constrained Qwen supervisor and retain its exact evidence."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

SYSTEM = """Teach a student quadruped to walk forward independently. Its anonymous motors were already calibrated.
The student owns its stance controller and learns relative foot timing in quarter cycles. You choose the next practice.
explore: try the next untested pattern from a varied gait repertoire. refine: try the nearest untested pattern to the best measured one.
ask_teacher, when available: observe one stride of a differently sized, differently actuated quadruped; the student derives contact timing and practices it.
A teacher playback costs time and may be used once. Minimize student practices to a stable forward gait. A previously successful practice ends instruction.
The learner can see previous training distance, lateral drift, balance, airborne fraction and touchdowns per foot. Select one available action and give a short reason. /no_think"""

GATE = """You allocate practice time for a student quadruped that has just failed a walking test in training.
Choose between continuing the student's own gait search and asking a different quadruped to show one stride.
A student practice costs 3.6 seconds. Watching the teacher costs 0.55 additional seconds and uses the one available demonstration.
If you ask, the student will try phase offsets inferred from the teacher's measured foot heights. Different bodies can respond differently.
If you continue, the student will try a new gait from its own repertoire. Motor channel directions have already been identified.
Aim to reach stable, independent forward walking in as little combined robot interaction time as possible. Pick one option and a short reason. /no_think"""


def decide(
    history: list[dict[str, Any]],
    available: list[str],
    endpoint: str,
    archive: dict[str, Any],
    checkpoint: Path,
) -> tuple[str, str, bool]:
    """Select an intervention with Qwen, reusing only byte-identical requests.

    Args:
        history: Public student trials.
        available: Legal actions.
        endpoint: Loopback-compatible chat-completion endpoint.
        archive: Exact requests, responses, inference usage and wall times.
        checkpoint: Working request journal for resuming an interrupted evaluation.
    Returns:
        Action, request key and whether the inference was reused.
    """
    report = {
        "goal": {
            "distance_m": 0.5,
            "horizon_s": 3.2,
            "max_lateral_m": 0.18,
            "min_upright_cos": 0.8,
            "max_air_fraction": 0.15,
            "min_touchdowns_each": 2,
            "chassis_must_stay_clear": True,
        },
        "practices_left": 6 - len(history),
        "available": available,
        "training": [
            {
                "phase_quarters": h["candidate"],
                "action": h["action"],
                "measurements": {
                    key: h["trial"][key]
                    for key in (
                        "distance",
                        "lateral",
                        "min_upright",
                        "body_contact",
                        "airborne_fraction",
                        "touchdowns",
                    )
                },
            }
            for h in history
        ],
    }
    payload = {
        "model": "qwen3-8b",
        "temperature": 0,
        "seed": 13,
        "max_tokens": 192,
        "messages": [
            {"role": "system", "content": GATE if "continue_search" in available else SYSTEM},
            {"role": "user", "content": json.dumps(report)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "gait_intervention",
                "schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": available},
                        "reason": {"type": "string", "maxLength": 120},
                    },
                    "required": ["action", "reason"],
                    "additionalProperties": False,
                },
            },
        },
    }
    raw = json.dumps(payload).encode()
    key = hashlib.sha256(raw).hexdigest()
    cached = key in archive
    if not cached:
        request = Request(
            endpoint.rstrip("/") + "/chat/completions",
            data=raw,
            headers={"Content-Type": "application/json"},
        )
        before = time.monotonic()
        with urlopen(request, timeout=180) as response:
            answer = json.load(response)
        reply = json.loads(answer["choices"][0]["message"]["content"])
        if reply["action"] not in available or not isinstance(reply["reason"], str):
            raise ValueError(f"Invalid supervisory reply {reply}")
        archive[key] = {
            "request": payload,
            "reply": reply,
            "latency_s": round(time.monotonic() - before, 3),
            "usage": answer.get("usage"),
        }
        partial = checkpoint.with_suffix(".tmp")
        partial.write_text(json.dumps(archive))
        partial.replace(checkpoint)
    return archive[key]["reply"]["action"], key, cached
