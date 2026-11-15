"""Simulate distinct free-base quadrupeds and measure their stride contact timing."""

from dataclasses import asdict, dataclass
from functools import lru_cache
from math import acos, atan2, cos, pi, sin
from typing import Any

import mujoco
import numpy as np
from numpy.typing import NDArray

LEGS = ("front_left", "front_right", "hind_left", "hind_right")
STEP = 0.0025
DT = 0.01
SECONDS = 3.2
Array = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class Body:
    """Specify the local mechanism and its built-in stance controller in metres."""

    name: str
    hip: float
    shin: float
    length: float
    width: float
    mass: float
    abduction: bool
    period: float
    stroke: float


TEACHER = Body("Longstride", 0.16, 0.185, 0.205, 0.107, 3.6, True, 0.56, 0.15)
STUDENT = Body("Pip", 0.121, 0.113, 0.145, 0.082, 2.05, False, 0.46, 0.098)


@dataclass(frozen=True, slots=True)
class Start:
    """Describe friction, floor tilt and initial yaw for one evaluation start."""

    friction: float = 0.9
    tilt: float = 0.0
    yaw: float = 0.0


@lru_cache(maxsize=32)
def model(body: Body, start: Start, mounted: bool = False) -> mujoco.MjModel:
    """Build a MuJoCo robot with physical contacts and torque-limited position drives.

    Args:
        body: Geometry and actuation family.
        start: Floor condition.
        mounted: Bolt the trunk to a raised support to test motor channels.
    Returns:
        Compiled rigid-body model.
    """
    legs, motors = [], []
    for i, leg in enumerate(LEGS):
        x = body.length * (1 if i < 2 else -1)
        y = body.width * (1 if i % 2 == 0 else -1)
        joint = (
            f'<joint name="{leg}_roll" axis="1 0 0" range="-.40 .40"/>' if body.abduction else ""
        )
        legs.append(f"""<body name="{leg}_hip" pos="{x} {y} 0">{joint}
        <joint name="{leg}_thigh" axis="0 1 0" range="-1.7 1.2"/>
        <geom type="capsule" fromto="0 0 0 0 0 {-body.hip}" size=".016" mass=".11" material="upper"/>
        <body name="{leg}_shank" pos="0 0 {-body.hip}"><joint name="{leg}_knee" axis="0 1 0" range=".05 2.55"/>
        <geom type="capsule" fromto="0 0 0 0 0 {-body.shin}" size=".012" mass=".075" material="lower"/>
        <geom name="{leg}" type="sphere" pos="0 0 {-body.shin}" size=".021" mass=".035" material="foot"/>
        </body></body>""")
        for suffix in (("roll", "thigh", "knee") if body.abduction else ("thigh", "knee")):
            motors.append(
                f'<position joint="{leg}_{suffix}" kp="55" kv="2.2" forcerange="-12 12"/>'
            )
    height = 0.6 if mounted else 0.83 * (body.hip + body.shin) + 0.021
    color = ".86 .50 .18" if body.abduction else ".11 .59 .62"
    xml = f"""<mujoco><compiler angle="radian"/><option timestep="{STEP}" integrator="implicitfast"/>
    <visual><global offwidth="1000" offheight="700"/><headlight ambient=".48 .48 .48"/></visual>
    <statistic center="0 0 .18" extent="1.0"/>
    <asset><texture type="skybox" builtin="gradient" rgb1=".21 .33 .39" rgb2=".66 .73 .72" width="192" height="1152"/><texture name="grid" type="2d" builtin="checker" width="128" height="128" rgb1=".27 .34 .37" rgb2=".30 .38 .41"/>
    <material name="floor" texture="grid" texrepeat="4 4" texuniform="true" reflectance=".07"/>
    <material name="upper" rgba="{color} 1"/><material name="lower" rgba=".66 .72 .73 1"/>
    <material name="foot" rgba=".12 .15 .17 1"/></asset>
    <default><joint damping=".08" armature=".005"/><geom friction="{start.friction} .004 .0001" condim="3"
    solref=".008 1" contype="2" conaffinity="1"/></default>
    <worldbody><light pos="0 -2 3" directional="true" dir="0 .5 -1"/>
    <geom name="floor" type="plane" size="0 0 .1" euler="0 {start.tilt} 0" material="floor" contype="1" conaffinity="2"/>
    <body name="trunk" pos="0 0 {height}">{'' if mounted else '<freejoint/>'}
    <geom name="chassis" type="box" size="{body.length} {body.width} .042" mass="{body.mass}" material="upper"/>
    <geom name="nose" type="box" pos="{body.length} 0 .027" size=".013 .047 .014" mass=".02" material="lower"/>
    {''.join(legs)}</body></worldbody><actuator>{''.join(motors)}</actuator></mujoco>"""
    return mujoco.MjModel.from_xml_string(xml)


def targets(body: Body, phases: tuple[float, ...] | None, time: float) -> Array:
    """Convert relative foot phases to the body's own local position targets.

    Args:
        body: Local stance and swing geometry.
        phases: Touchdown offsets in leg order, or None to stand.
        time: Elapsed gait time in seconds.
    Returns:
        Joint position targets in encoder order.
    """
    command = []
    for i in range(4):
        x, lift = 0.0, 0.0
        if phases is not None:
            phase = (time / body.period - phases[i]) % 1
            if phase < 0.62:
                x = body.stroke * (0.5 - phase / 0.62)
            else:
                swing = (phase - 0.62) / 0.38
                x = body.stroke * (-0.5 + (1 - cos(pi * swing)) / 2)
                lift = 0.24 * (body.hip + body.shin) * sin(pi * swing) ** 1.4
        depth = 0.83 * (body.hip + body.shin) - lift
        knee = acos(
            np.clip(
                (x * x + depth * depth - body.hip**2 - body.shin**2) / (2 * body.hip * body.shin),
                -1,
                1,
            )
        )
        thigh = atan2(-x, depth) - atan2(body.shin * sin(knee), body.hip + body.shin * cos(knee))
        if body.abduction:
            command.append(0.0)
        command.extend((thigh, knee))
    return np.array(command)


def calibrate(seed: int) -> dict[str, Any]:
    """Identify a signed permutation using a separate supported motor pulse per channel.

    Args:
        seed: Hidden hardware wiring seed.
    Returns:
        Wiring, inferred inverse, measured joint changes, and interaction duration.
    """
    rng = np.random.default_rng(seed)
    rig = model(STUDENT, Start(), mounted=True)
    wiring = rng.permutation(rig.nu)
    signs = rng.choice([-1, 1], size=rig.nu)
    neutral = targets(STUDENT, None, 0)
    measured = []
    for index, joint in enumerate(wiring):
        state = mujoco.MjData(rig)
        state.qpos[:] = neutral
        state.ctrl[:] = neutral
        mujoco.mj_step(rig, state, nstep=80)
        before = state.qpos.copy()
        state.ctrl[joint] += 0.13 * signs[index]
        mujoco.mj_step(rig, state, nstep=80)
        measured.append((state.qpos - before).tolist())
    response = np.array(measured)
    mapped = np.argmax(np.abs(response), axis=1)
    if len(set(mapped)) != rig.nu or min(abs(response[np.arange(rig.nu), mapped])) < 0.045:
        raise RuntimeError("Supported pulses did not identify eight distinct actuator responses")
    return {
        "wiring": wiring.tolist(),
        "signs": signs.tolist(),
        "inferred": mapped.tolist(),
        "inferred_sign": np.sign(response[np.arange(rig.nu), mapped]).astype(int).tolist(),
        "measured_rad": measured,
        "pulse_seconds": 1.6,
        "settling_seconds": 1.6,
    }


def rollout(
    body: Body,
    phases: tuple[float, ...] | None,
    start: Start = Start(),
    mapping: dict[str, Any] | None = None,
    tape: bool = False,
) -> dict[str, Any]:
    """Execute a free-base gait and score measured motion on a fresh physics state.

    Args:
        body: Source or student body.
        phases: Frozen relative touchdown offsets, or None for standing.
        start: Surface and initial yaw.
        mapping: Identified command adapter and hidden wiring.
        tape: Save full pose and contact observations at 100 Hz for replay.
    Returns:
        Trial measurements, its walking score, and optional replay data.
    """
    rig = model(body, start)
    data = mujoco.MjData(rig)
    neutral = targets(body, None, 0)
    data.qpos[3:7] = [cos(start.yaw / 2), 0, 0, sin(start.yaw / 2)]
    data.qpos[7:] = neutral
    data.ctrl[:] = neutral
    mujoco.mj_step(rig, data, nstep=160)
    initial = data.qpos[:3].copy()
    minimum = 1.0
    drift = energy = 0.0
    air = 0
    counts = np.zeros(4, dtype=int)
    prev = np.ones(4, dtype=bool)
    off = np.zeros(4, dtype=int)
    poses, feet, heights = [], [], []
    low = rig.geom("chassis").id
    foot_ids = [rig.geom(name).id for name in LEGS]
    grounded = False
    if mapping is not None:
        wiring, signs, inferred, polarity = (
            np.array(mapping[k]) for k in ("wiring", "signs", "inferred", "inferred_sign")
        )
    for tick in range(round(SECONDS / DT)):
        desired = targets(body, phases, tick * DT)
        blend = min(1.0, tick * DT / 0.15)
        residual = blend * (desired - neutral)
        if mapping is None:
            data.ctrl[:] = neutral + residual
        else:
            data.ctrl[wiring] = neutral[wiring] + signs * polarity * residual[inferred]
        mujoco.mj_step(rig, data, nstep=4)
        touching = {int(v) for contact in data.contact for v in (contact.geom1, contact.geom2)}
        on = np.array([fid in touching for fid in foot_ids])
        counts += on & ~prev & (off >= 3)
        off = np.where(on, 0, off + 1)
        prev = on
        air += int(not on.any())
        grounded |= low in touching
        minimum = min(minimum, float(data.xmat[1, 8]))
        drift = max(drift, abs(data.qpos[1] - initial[1]))
        energy += float(np.abs(data.actuator_force * data.qvel[6:]).sum()) * DT
        if tape:
            poses.append(np.round(data.qpos, 6).tolist())
            feet.append(on.astype(int).tolist())
            heights.append(np.round(data.geom_xpos[foot_ids, 2] - data.xpos[1, 2], 6).tolist())
    distance = float(data.qpos[0] - initial[0])
    return dict(
        distance=round(distance, 5),
        lateral=round(drift, 5),
        min_upright=round(minimum, 5),
        body_contact=grounded,
        airborne_fraction=air / round(SECONDS / DT),
        touchdowns=counts.tolist(),
        work_j=round(energy, 3),
        start=asdict(start),
        passed=bool(
            distance >= 0.50
            and drift <= 0.18
            and minimum >= 0.8
            and not grounded
            and min(counts) >= 2
            and air / round(SECONDS / DT) <= 0.15
        ),
        **({"qpos": poses, "contacts": feet, "foot_height": heights} if tape else {}),
    )
