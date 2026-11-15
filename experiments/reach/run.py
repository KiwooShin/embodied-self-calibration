"""Discovery of anonymous motor channels on two simulated hinge-chain robots."""

import argparse
import json
from math import cos, sin
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import ode

# Evaluator-only body descriptions: lengths, initial relative angles, channel
# permutation and sign. The supervisor and the student never read this table.
BODIES = {
    "two_link": ([0.23, 0.20], [0.35, 1.2], [1, 0], [-1, 1]),
    "three_link": ([0.16, 0.16, 0.13], [0.3, 0.72, 0.72], [2, 0, 1], [1, -1, 1]),
}
DT = 1 / 960
PULSE = 0.07


class Arm:
    def __init__(self, name, shift=0.0):
        lengths, angles, self.order, self.signs = BODIES[name]
        self.world = ode.World()
        self.world.setGravity((0, 0, 0))
        self.world.setCFM(1e-7)
        self.joints = []
        self.links = []
        parent = None
        point = np.zeros(2)
        heading = 0.0
        for i, (length, angle) in enumerate(zip(lengths, angles)):
            heading += angle + shift * (1 if i % 2 == 0 else -0.5)
            direction = np.array([cos(heading), sin(heading)])
            body = ode.Body(self.world)
            mass = ode.Mass()
            mass.setBoxTotal(0.18, length, 0.025, 0.025)
            body.setMass(mass)
            middle = point + length * direction / 2
            body.setPosition((*middle, 0))
            body.setQuaternion((cos(heading / 2), 0, 0, sin(heading / 2)))
            joint = ode.HingeJoint(self.world)
            joint.attach(body, parent)
            joint.setAnchor((*point, 0))
            joint.setAxis((0, 0, 1))
            joint.setParam(ode.ParamLoStop, -1.5)
            joint.setParam(ode.ParamHiStop, 1.5)
            self.joints.append(joint)
            self.links.append((body, length))
            point += length * direction
            parent = body
        self.targets = np.zeros(len(angles))
        self.trace = [self.points()]

    def points(self):
        return [[0.0, 0.0]] + [
            list(b.getRelPointPos((length / 2, 0, 0))[:2]) for b, length in self.links
        ]

    def endpoint(self):
        return np.array(self.points()[-1])

    def step(self, increments):
        if np.max(np.abs(increments)) > 0.201:
            raise ValueError("relative motor target exceeds bound")
        for channel, delta in enumerate(increments):
            self.targets[self.order[channel]] += self.signs[channel] * delta
        self.targets = np.clip(self.targets, -1.5, 1.5)
        for i in range(576):
            for j, target in zip(self.joints, self.targets):
                torque = np.clip(
                    2.8 * (target - j.getAngle()) - 0.20 * j.getAngleRate(), -0.8, 0.8
                )
                j.addTorque(float(torque))
            self.world.step(DT)
            if (i + 1) % 48 == 0:
                self.trace.append(self.points())


def probe(name, channel, shift=0.0):
    rig = Arm(name, shift)
    start = rig.endpoint()
    cmd = np.zeros(len(rig.joints))
    cmd[channel] = PULSE
    rig.step(cmd)
    return (rig.endpoint() - start) / PULSE, rig.trace


def reach(name, model, shift, displacement=(-0.10, 0.0)):
    arm = Arm(name, shift)
    goal = arm.endpoint() + displacement
    # The matrix is frozen. Only endpoint measurement and goal error change.
    for _ in range(12):
        error = goal - arm.endpoint()
        if np.linalg.norm(error) <= 0.01:
            break
        delta = model.T @ np.linalg.solve(model @ model.T + 0.0004 * np.eye(2), error)
        arm.step(np.clip(delta, -0.2, 0.2))
    mm = float(np.linalg.norm(goal - arm.endpoint()) * 1000)
    return {
        "goal": goal.tolist(),
        "error_mm": round(mm, 3),
        "passed": mm <= 10,
        "start_shift": shift,
        "trace": arm.trace,
    }


def teacher_segment(student):
    name = next(k for k in BODIES if k != student)
    model = np.column_stack([probe(name, i)[0] for i in range(len(BODIES[name][0]))])
    ref = reach(name, model, 0)
    if not ref["passed"]:
        raise RuntimeError("teacher failed")
    traj = np.array([f[-1] for f in ref["trace"]])
    return np.round((traj - traj[0]) * 1000, 1)[::4].tolist()


PROMPT = """Teach an unfamiliar planar arm to move its tool 100 mm left along -X.
Each anonymous signed channel changes different joints. You can probe a channel
to observe its endpoint movement, request another body's demonstration of the
endpoint path, or freeze the student's matrix and assess it. A probe on a fresh
arm records the result of a +0.07 rad pulse. Unmeasured columns remain zero.
The student will use the measured matrix for feedback control on new starts.
The teacher's trace shows the shared goal motion, but cannot identify the
student's motor channels. Aim for <=10 mm error on new starts with few probes
and teacher queries. Return JSON action and brief evidence. /no_think"""


def choose(report, actions, url):
    schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": actions},
            "evidence": {"type": "string"},
        },
        "required": ["action", "evidence"],
        "additionalProperties": False,
    }
    body = {
        "model": "qwen3-8b",
        "temperature": 0,
        "seed": 13,
        "max_tokens": 150,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": json.dumps(report)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "choice", "schema": schema},
        },
    }
    req = Request(
        url + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=180) as reply:
        answer = json.load(reply)
    result = json.loads(answer["choices"][0]["message"]["content"])
    if result["action"] not in actions:
        raise ValueError(result)
    return result


def study(name, mode, url):
    n = len(BODIES[name][0])
    matrix = np.zeros((2, n))
    seen = set()
    history = []
    traces = []
    for _ in range(n + 2):
        choices = [f"probe_{i}" for i in range(n)] + ["ask_teacher", "assess"]
        if mode == "qwen":
            choice = choose(
                {"channels": list(range(n)), "history": history}, choices, url
            )
        elif mode == "all_channels" and len(seen) < n:
            choice = {"action": f"probe_{min(set(range(n)) - seen)}"}
        else:
            choice = {"action": "assess"}
        action = choice["action"]
        if action == "assess":
            history.append(choice)
            break
        if action == "ask_teacher":
            choice["teacher_endpoint_delta_mm"] = teacher_segment(name)
        else:
            channel = int(action.split("_")[1])
            column, trace = probe(name, channel)
            seen.add(channel)
            matrix[:, channel] = column
            choice["observed_delta_mm"] = (column * PULSE * 1000).round(2).tolist()
            traces.append({"channel": channel, "poses": trace})
        history.append(choice)
    return {
        "history": history,
        "probes": traces,
        "frozen_matrix": matrix.tolist(),
        "tests": [reach(name, matrix, shift) for shift in (-0.18, 0.08, 0.22)],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    p.add_argument(
        "--mode", required=True, choices=["qwen", "all_channels", "untrained"]
    )
    p.add_argument("--endpoint", default="http://127.0.0.1:18081/v1")
    args = p.parse_args()
    if args.out.exists():
        p.error("Choose a new output file")
    runs = {name: study(name, args.mode, args.endpoint) for name in BODIES}
    args.out.parent.mkdir(exist_ok=True, parents=True)
    args.out.write_text(
        json.dumps({"mode": args.mode, "prompt": PROMPT, "bodies": runs}, indent=1)
        + "\n"
    )
    for name, v in runs.items():
        print(
            name,
            [d["action"] for d in v["history"]],
            [t["error_mm"] for t in v["tests"]],
        )
