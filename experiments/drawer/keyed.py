"""Matched vs mismatched task-space teaching with a rotary-lift teacher."""

import argparse
import json
from math import asin, radians
from pathlib import Path
import ode
from ode_fixture import Drawer


class KeyedDrawer(Drawer):
    def __init__(self, gate_mm, **kwargs):
        super().__init__(**kwargs)
        # The lug runs in a slot on the side, clear of the handle face and pin.
        self.geoms[3].setOffsetPosition((0.034, 0.035, 0.014))
        if gate_mm is None:
            return
        required = gate_mm / 1000
        bottom = 0.005 + required
        top = 0.023 + required + 0.010
        for lo, hi in [(-0.008, bottom), (top, 0.13)]:
            self.box(
                None,
                (self.origin + 0.055, 0.035, (lo + hi) / 2),
                (0.018, 0.020, hi - lo),
            )


class LeverTeacher(KeyedDrawer):
    """The pin sweeps an arc around a pivot on the translating carriage."""

    length = 0.15

    def make_lift(self, carriage):
        self.carriage = carriage
        tool = ode.Body(self.world)
        mass = ode.Mass()
        mass.setParameters(0.25, 0, 0, 0, 0.002, 0.002, 0.002, 0, 0, 0)
        tool.setMass(mass)
        # Initial pin centre is directly at (origin,0,.045), as in the student.
        tool.setPosition((self.origin, 0, 0))
        self.hinge = ode.HingeJoint(self.world)
        self.hinge.attach(tool, carriage)
        self.hinge.setAnchor((self.origin - self.length, 0, 0.045))
        self.hinge.setAxis((0, -1, 0))
        self.hinge.setParam(ode.ParamLoStop, radians(-5))
        self.hinge.setParam(ode.ParamHiStop, radians(34))
        return tool

    def drive_targets(self, x, z):
        angle = asin(z / self.length)
        torque = 12 * (angle - self.hinge.getAngle()) - 0.55 * self.hinge.getAngleRate()
        self.hinge.addTorque(max(-2, min(2, torque)))
        return [x, 0.0, 0.0]

    def read(self):
        obs = super().read()
        x, _, z = self.tool.getRelPointPos((0, 0, 0.045))
        obs.update(
            tool_x_mm=round(1000 * (x - self.origin), 2),
            tool_z_mm=round(1000 * z - 45, 2),
            pivot_x_mm=round(
                1000 * (self.carriage.getPosition()[0] - self.origin - self.length), 2
            ),
        )
        return obs


GATES = (12, 30, 48)
GAPS = (0.003, 0.008, 0.012)


def expert(gate):
    rig = LeverTeacher(gate)
    # The expert knows its own fixture. The student receives object motion only.
    height = gate + 9 if gate is not None else 0
    rig.move(0, height)
    end = rig.move(90, height)
    if end["drawer_x_mm"] < 60:
        raise RuntimeError(f"Teacher failed at {gate}: {end}")
    segment = []
    for f in rig.trace:
        segment.append({k: f[k] for k in ("tick", "handle_z_mm", "drawer_x_mm")})
        if f["drawer_x_mm"] >= 5:
            break
    return {"trace": rig.trace, "segment": segment}


def study():
    teachers = {g: expert(g) for g in GATES}
    results = []
    for i, g in enumerate(GATES):
        for method in ("matched", "shuffled", "fixed", "none"):
            source = None
            if method in ("matched", "shuffled"):
                source = g if method == "matched" else GATES[(i + 1) % len(GATES)]
                # Reconstruct a linear pin-height target from observed object motion.
                lift = max(f["handle_z_mm"] for f in teachers[source]["segment"]) + 3
            else:
                lift = 40 if method == "fixed" else 0
            for gap in GAPS:
                student = KeyedDrawer(g, gap=gap, origin=0.17)
                if lift:
                    student.move(0, lift)
                obs = student.move(90, lift)
                results.append(
                    dict(
                        gate_mm=g,
                        source_gate_mm=source,
                        method=method,
                        gap_mm=round(gap * 1000),
                        student_lift_mm=round(lift, 2),
                        passed=obs["drawer_x_mm"] >= 60,
                        result=obs,
                        trace=student.trace,
                    )
                )
    return {"teachers": teachers, "trials": results}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    if args.output.exists():
        p.error("Choose a new output file")
    record = study()
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    for method in ("matched", "shuffled", "fixed", "none"):
        trials = [t for t in record["trials"] if t["method"] == method]
        print(
            method,
            sum(t["passed"] for t in trials),
            [t["result"]["drawer_x_mm"] for t in trials],
        )
