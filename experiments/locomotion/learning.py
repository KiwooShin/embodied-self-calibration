"""Learn gait timing from paired student rollouts and a measured cross-body stride."""

from dataclasses import dataclass
from itertools import product
from typing import Any

import numpy as np

from .rig import DT, LEGS, TEACHER, Start, rollout

Gait = tuple[int, ...]
HOLDOUT = (Start(0.70, 0.025, 0.06), Start(1.05, -0.025, -0.06), Start(0.83, 0, 0.10))
COMMON = (
    (0, 2, 2, 0),
    (0, 2, 0, 2),
    (0, 0, 2, 2),
    (0, 0, 0, 0),
    (0, 2, 1, 3),
    (0, 2, 3, 1),
    (0, 1, 3, 2),
    (0, 3, 1, 2),
    (0, 1, 2, 3),
    (0, 3, 2, 1),
    (0, 1, 1, 3),
    (0, 3, 3, 1),
)


@dataclass(frozen=True, slots=True)
class Lesson:
    """Retain the measured public source stride and the policy it suggests."""

    contacts: list[list[int]]
    trunk_xyz: list[list[float]]
    duration: float
    phases: Gait
    slice_start: int
    foot_height: list[list[float]]
    height_phases: Gait


def stride_phases(contacts: list[list[int]]) -> Gait:
    """Estimate quarter-cycle phase offsets from the longest observed swing per leg.

    Args:
        contacts: One stride of measured binary foot contacts in shared foot order.
    Returns:
        Quantized touchdown timing relative to the front-left contact.
    Raises:
        ValueError: If a foot lacks a complete swing or stance.
    """
    data = np.asarray(contacts)
    if data.ndim != 2 or data.shape[1] != len(LEGS) or len(data) < 4:
        raise ValueError("Expected a stride of four-foot contact samples")
    onsets = []
    for foot in data.T:
        landings = np.flatnonzero((foot == 1) & (np.roll(foot, 1) == 0))
        if not len(landings):
            raise ValueError("Expected a measured touchdown on every foot")

        lengths = [
            next(i for i in range(1, len(foot) + 1) if foot[(landing - i) % len(foot)])
            for landing in landings
        ]
        onsets.append(landings[int(np.argmax(lengths))])
    return tuple(int(np.floor(4 * (start - onsets[0]) / len(data) + 0.5)) % 4 for start in onsets)


def source() -> tuple[Lesson, dict[str, Any]]:
    """Run the source policy and extract its first steady measured stride after 1.2 s.

    Returns:
        Public lesson and the evaluator-only teacher replay.
    """
    tape = rollout(TEACHER, (0, 0.5, 0.5, 0), tape=True)
    front = np.array(tape["contacts"])[:, 0]
    starts = [
        i
        for i in range(120, len(front))
        if front[i] and not front[i - 1] and not front[i - 3 : i].any()
    ]
    if len(starts) < 2 or not tape["passed"]:
        raise RuntimeError("Expected a walking teacher with two steady touchdowns")
    a, b = starts[:2]
    feet = tape["contacts"][a:b]
    trunk = np.array(tape["qpos"])[a:b, :3]
    heights = tape["foot_height"][a:b]
    peaks = np.argmax(heights, axis=0)
    height_phases = tuple(
        int(np.floor(4 * (peak - peaks[0]) / (b - a) + 0.5)) % 4 for peak in peaks
    )
    return (
        Lesson(
            feet,
            (trunk - trunk[0]).round(6).tolist(),
            (b - a) * DT,
            stride_phases(feet),
            a,
            heights,
            height_phases,
        ),
        tape,
    )


def candidates(seed: int) -> list[Gait]:
    """Order familiar gait topologies first, then the remaining quarter-cycle grid.

    Args:
        seed: Paired curriculum seed.
    Returns:
        All 64 possible patterns, each occurring once.
    """
    rng = np.random.default_rng(seed)
    common = list(COMMON)
    extra = [(0, *tail) for tail in product(range(4), repeat=3) if (0, *tail) not in common]
    rng.shuffle(common)
    rng.shuffle(extra)
    return common + extra


def rank(trial: dict[str, Any]) -> tuple[bool, bool, float]:
    """Rank measured skills by training pass, upright execution and motion quality.

    Args:
        trial: One training trial's measured telemetry.
    Returns:
        Lexicographic ranking using training observations.
    """
    return (
        trial["passed"],
        trial["min_upright"] >= 0.8 and not trial["body_contact"],
        trial["distance"] - 1.4 * trial["lateral"] - trial["airborne_fraction"],
    )


def choose_candidate(
    action: str, history: list[dict[str, Any]], queue: list[Gait], lesson: Gait
) -> Gait:
    """Choose the student's next gait from its history and the optional measured lesson.

    Args:
        action: One of explore, refine, and ask_teacher.
        history: Student training trials only.
        queue: Paired search order.
        lesson: Public phase estimates, consumed only on a teacher request.
    Returns:
        Candidate for the next student practice.
    """
    if action == "ask_teacher":
        return lesson
    tried = {tuple(item["candidate"]) for item in history}
    remaining = [gait for gait in queue if gait not in tried]
    if action == "explore":
        return remaining[0]
    if action != "refine":
        raise ValueError(f"Unknown curriculum action {action!r}")
    best = max(history, key=lambda entry: rank(entry["trial"]))["candidate"]
    return min(
        remaining,
        key=lambda gait: sum(
            min((a - b) % 4, (b - a) % 4) for a, b in zip(gait, best, strict=True)
        ),
    )
