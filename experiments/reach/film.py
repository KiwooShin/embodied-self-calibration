"""Calibrated top-down motion study from saved ODE joint-centre trajectories."""

import argparse
import json
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1440, 900, 24
BG = "#11222b"
INK = "#edf5f3"
DIM = "#adc0c4"
GREEN = "#75e1bb"
GOLD = "#f9ce7e"
SALMON = "#ffac94"
font_cache = {}


def label(d, x, y, s, size, color=INK, bold=False):
    k = (size, bold)
    if k not in font_cache:
        font_cache[k] = ImageFont.truetype(
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size
        )
    d.text((x, y), s, font=font_cache[k], fill=color, anchor="lt")


def disk(d, p, r, fill, outline=None, width=1):
    x, y = p
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=width)


def capsule(d, a, b, r, color):
    d.line((a, b), fill=color, width=2 * r)
    disk(d, a, r, color)
    disk(d, b, r, color)


def panel(d, left, case, stage, independent, frac):
    probes = case["probes"]
    if independent:
        test = case["tests"][-1]
        trace = test["trace"]
        goal = test["goal"]
        title = "Frozen student  /  held-out posture"
    else:
        probe = probes[min(stage, len(probes) - 1)]
        trace = probe["poses"]
        goal = None
        title = f"Motor probe  /  channel {probe['channel']}"
        if stage >= len(probes):
            title = "Calibration complete"
            frac = 1.0
    i = min(len(trace) - 1, int(frac * len(trace)))
    points = trace[i]

    def pos(p):
        return (round(left + 200 + p[0] * 850), round(596 - p[1] * 850))

    d.rounded_rectangle((left, 188, left + 662, 650), radius=14, fill="#1a3038")
    for k in range(-4, 10):
        x, _ = pos((k * 0.05, 0))
        if left + 12 < x < left + 648:
            d.line((x, 206, x, 632), fill="#2a4148")
        _, y = pos((0, k * 0.05))
        if 206 < y < 632:
            d.line((left + 12, y, left + 648, y), fill="#2a4148")
    label(d, left + 16, 205, "TOP VIEW   /   50 mm grid", 15, DIM)
    label(d, left, 151, title, 22, GOLD, True)
    if goal:
        target = pos(goal)
        first = pos(trace[0][-1])
        d.line((first, target), fill="#b29969", width=2)
        for r in (9, 18):
            disk(d, target, r, None, GOLD, 2)
        label(d, target[0] - 54, target[1] - 39, "10 cm left", 17, GOLD)
    # Each drawn hinge centre and endpoint is an ODE measurement.
    for j in range(len(points) - 1):
        a, b = pos(points[j]), pos(points[j + 1])
        shifted = lambda q: (q[0] + 5, q[1] + 7)
        capsule(d, shifted(a), shifted(b), 14, "#0a1d22")
        capsule(d, a, b, 13, "#89a4ad")
        capsule(d, (a[0], a[1] - 3), (b[0], b[1] - 3), 8, "#d2dedf")
        capsule(d, a, b, 4, "#82949c")
    for j, point in enumerate(points[:-1]):
        p = pos(point)
        disk(d, p, 17, "#13262d", "#dbe5e4", 3)
        disk(d, p, 10, "#71979b", "#435f65", 2)
        disk(d, p, 4, "#203a42")
        label(d, p[0] - 36, p[1] + 19, str(j + 1), 14, DIM)
    path = [pos(f[-1]) for f in trace[: i + 1]]
    if len(path) > 1:
        d.line(path, fill=GREEN, width=3)
    disk(d, path[-1], 7, GREEN, INK, 2)
    label(d, left + 16, 616, "Teal  /  measured wrist path", 16, GREEN)
    if independent:
        error = math.dist(points[-1], goal) * 1000
        label(d, left, 685, "Distance to target", 19, DIM)
        label(d, left, 721, f"{error:.1f} mm", 34, GREEN if error <= 10 else INK, True)
        if frac >= 1:
            scores = "   ·   ".join(f"{t['error_mm']:.1f}" for t in case["tests"])
            label(
                d,
                left,
                786,
                "Final errors on three starts    " + scores + " mm",
                17,
                DIM,
            )
    else:
        x, y = (1000 * (a - b) for a, b in zip(points[-1], trace[0][-1]))
        label(d, left, 685, "Observed endpoint response", 19, DIM)
        label(d, left, 721, f"Δx  {x:+.1f} mm       Δy  {y:+.1f} mm", 28, INK, True)
        label(
            d,
            left,
            786,
            "The student stores this response per unit motor command.",
            17,
            DIM,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("video", type=Path)
    parser.add_argument("--encoder", default="libx264")
    args = parser.parse_args()
    cases = list(json.loads(args.record.read_text())["bodies"].values())
    phases = max(len(c["probes"]) for c in cases) + 1
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-n",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-c:v",
        args.encoder,
        "-b:v",
        "4M",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.video),
    ]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as enc:
        for stage in range(phases):
            test = stage == phases - 1
            for tick in range(FPS * (7 if test else 3)):
                frame = Image.new("RGB", (W, H), BG)
                d = ImageDraw.Draw(frame)
                label(
                    d,
                    36,
                    20,
                    "EMBODIED SELF-CALIBRATION   /   REACHING STUDY",
                    16,
                    GREEN,
                    True,
                )
                label(
                    d,
                    36,
                    54,
                    "What does “10 cm left” mean on a new arm?",
                    36,
                    INK,
                    True,
                )
                for n, (left, case) in enumerate(zip((36, 744), cases)):
                    label(
                        d,
                        left,
                        108,
                        ("Two", "Three")[n] + " revolute joints",
                        25,
                        INK,
                        True,
                    )
                    panel(
                        d,
                        left,
                        case,
                        stage,
                        test,
                        tick / (FPS * (3.5 if test else 1.5)),
                    )
                d.line((36, 846, 1404, 846), fill="#36505b")
                label(
                    d,
                    36,
                    865,
                    "ODE planar motion   ·   calibrated top view   ·   test tolerance 10 mm",
                    17,
                    DIM,
                )
                label(d, 1260, 865, f"{stage + 1} / {phases}", 18)
                enc.stdin.write(frame.tobytes())
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")


if __name__ == "__main__":
    main()
