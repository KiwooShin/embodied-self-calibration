"""Render measured MuJoCo poses, foot contacts and paired locomotion outcomes."""

from functools import lru_cache
from typing import Any

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .rig import DT, Body, Start, model

BG, WHITE, MUTED = "#101c23", "#f1f4ed", "#a2b5ba"
TEAL, AMBER, RED, GRID = "#80e0d1", "#ffbf72", "#ffa18e", "#314653"
W, H = 1440, 840


@lru_cache(maxsize=24)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a reusable screen font at the requested size."""
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)


def text(
    d: ImageDraw.ImageDraw,
    x: int,
    y: int,
    value: str,
    size: int = 22,
    color: str = WHITE,
    bold: bool = False,
) -> None:
    """Draw a label with a top-left anchor for stable alignments."""
    d.text((x, y), value, fill=color, font=font(size, bold), anchor="lt")


def canvas(title: str, section: str) -> Image.Image:
    """Create a full-size visual chapter surface with the experiment name."""
    frame = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(frame)
    text(draw, 40, 24, "EMBODIED SELF-CALIBRATION    /    LOCOMOTION", 17, TEAL, True)
    text(draw, 1054, 24, section, 17, MUTED)
    text(draw, 40, 68, title, 40, WHITE, True)
    draw.line((40, 134, 1400, 134), fill=GRID, width=2)
    return frame


class Replay:
    """Cache physical-pose replays from an independently scored trajectory."""

    def __init__(self, body: Body, start: Start, trial: dict[str, Any]) -> None:
        """Allocate a robot-specific camera and renderer for a saved test execution."""
        self.rig = model(body, start)
        self.data = mujoco.MjData(self.rig)
        self.renderer = mujoco.Renderer(self.rig, height=350, width=660)
        self.camera = mujoco.MjvCamera()
        self.camera.azimuth = 116
        self.camera.elevation = -17
        self.camera.distance = 0.93 if body.abduction else 0.70
        self.trial = trial
        self.cache: dict[int, Image.Image] = {}

    def frame(self, index: int) -> Image.Image:
        """Render a recorded floating-base pose at the nearest 20 ms frame."""
        index = max(0, min(index, len(self.trial["qpos"]) - 1)) // 2 * 2
        if index not in self.cache:
            self.data.qpos[:] = self.trial["qpos"][index]
            mujoco.mj_forward(self.rig, self.data)
            self.camera.lookat[:] = [
                self.data.qpos[0] + 0.03,
                self.data.qpos[1],
                max(0.11, self.data.qpos[2] * 0.58),
            ]
            self.renderer.update_scene(self.data, camera=self.camera)
            self.cache[index] = Image.fromarray(self.renderer.render())
        return self.cache[index]

    def close(self) -> None:
        """Release the headless rendering context."""
        self.renderer.close()


def panel(frame: Image.Image, x: int, clip: Replay, index: int, title: str, subtitle: str) -> None:
    """Show the body, travelled distance, and measured foot contacts."""
    draw = ImageDraw.Draw(frame)
    text(draw, x, 164, title, 27, WHITE, True)
    text(draw, x, 204, subtitle, 18, MUTED)
    frame.paste(clip.frame(index), (x, 243))
    data = clip.trial
    idx = min(index, len(data["qpos"]) - 1)
    delta = data["qpos"][idx][0] - data["qpos"][0][0]
    text(draw, x, 613, f"{delta:+.2f} m", 31, TEAL, True)
    text(draw, x + 212, 621, f"{idx*DT:.2f} s", 21, MUTED)
    for i, name in enumerate(("FL", "FR", "HL", "HR")):
        color = AMBER if data["contacts"][idx][i] else GRID
        pos = x + 377 + 65 * i
        draw.rounded_rectangle((pos, 607, pos + 55, 646), radius=8, fill=color)
        text(draw, pos + 11, 617, name, 18, BG if data["contacts"][idx][i] else MUTED, True)


def contact_chart(frame: Image.Image, lesson: dict[str, Any], fraction: float) -> None:
    """Draw the observed binary contact and trunk-relative height within one stride."""
    draw = ImageDraw.Draw(frame)
    text(draw, 760, 165, "One measured stride", 28, WHITE, True)
    text(draw, 760, 207, "Amber = ground contact      Teal = foot height", 19, MUTED)
    feet = np.array(lesson["contacts"])
    heights = np.array(lesson["foot_height"])
    for j, label in enumerate(("Front left", "Front right", "Hind left", "Hind right")):
        y = 266 + j * 80
        text(draw, 760, y + 8, label, 18, WHITE)
        arr = heights[:, j]
        scale = max(0.001, float(np.ptp(arr)))
        samples = [
            (916 + int(i * 450 / (len(arr) - 1)), y + 41 - int((value - min(arr)) * 33 / scale))
            for i, value in enumerate(arr)
        ]
        for i, (x, _) in enumerate(samples):
            if feet[i, j]:
                draw.rectangle((x, y + 46, x + 8, y + 54), fill=AMBER)
        draw.line(samples, fill=TEAL, width=3)
    cursor = 916 + int(450 * fraction)
    draw.line((cursor, 256, cursor, 570), fill=WHITE, width=2)
    text(draw, 760, 610, "Phase in quarter cycles     FL · FR · HL · HR", 18, MUTED)
    text(draw, 760, 644, "Contact   " + "  ".join(map(str, lesson["phases"])), 23, AMBER, True)
    text(
        draw, 1060, 644, "Height   " + "  ".join(map(str, lesson["height_phases"])), 23, TEAL, True
    )


def curves(
    frame: Image.Image,
    x: int,
    title: str,
    arms: list[tuple[str, dict[str, Any], str]],
    fraction: float,
) -> None:
    """Draw the count of students that have passed all three independent starts."""
    draw = ImageDraw.Draw(frame)
    text(draw, x, 171, title, 24, WHITE, True)
    x0 = x + 35
    y0 = 479
    for tick in (0, 3, 6, 9, 12):
        y = y0 - tick * 18
        draw.line((x0, y, x0 + 552, y), fill=GRID, width=1)
        text(draw, x, y - 7, str(tick), 15, MUTED)
    for i in range(7):
        text(draw, x0 + i * 90 - 3, y0 + 13, str(i), 16, MUTED)
    text(draw, x0 + 160, 529, "Student practice trials", 18, MUTED)
    for j, (label, record, color) in enumerate(arms):
        outcomes = [0, *record["mastery_by_practice"]]
        points = [(x0 + i * 90, y0 - 18 * n) for i, n in enumerate(outcomes)]
        end = max(1, min(7, round(7 * fraction)))
        if end > 1:
            draw.line(points[:end], fill=color, width=4)
        for px, py in points[:end]:
            draw.ellipse((px - 4, py - 4, px + 4, py + 4), outline=color, width=2)
        y = 581 + j * 41
        draw.line((x, y + 9, x + 29, y + 9), fill=color, width=4)
        text(draw, x + 39, y, f"{label}   {outcomes[-1]}/12", 20, color, True)
