"""Animate the observed handle heights, the estimated subgoal, and the paired scores."""

import argparse
import json
from pathlib import Path
import subprocess
from statistics import median

from PIL import Image, ImageDraw
from replay import BG, DIM, GOLD, GREEN, INK, LINE, RED, text

BLUE = "#9cc9ea"
METHODS = ("peak", "median3_peak")


def traces(d, c, tick):
    text(
        d,
        (50, 148),
        f"30 mm gate    /    alignment {c['bias_mm']:+} mm    /    frame noise {c['sigma_mm']} mm",
        25,
        GOLD,
    )
    true, obs = c["teacher_heights_mm"], c["observed_heights_mm"]
    med = [median(obs[i - 2 : i + 1]) for i in range(2, len(obs))]
    lo, hi = -12, 56

    def point(i, val):
        return (90 + 760 * i / (len(obs) - 1), 627 - 365 * (val - lo) / (hi - lo))

    for h in (0, 20, 40):
        x, y = point(0, h)
        d.line((x, y, 850, y), fill=LINE, width=2)
        text(d, (54, y - 9), str(h), 15, DIM)
    text(d, (90, 211), "Measured handle height (mm)", 22, INK, True)
    n = min(len(obs), 1 + int(tick / 92 * len(obs)))
    for series, offset, color in ((true, 0, DIM), (obs, 0, GOLD), (med, 2, GREEN)):
        points = [point(i, series[i - offset]) for i in range(offset, n)]
        if len(points) > 1:
            d.line(points, fill=color, width=4)
        if points:
            x, y = points[-1]
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
    for x, label, color in [
        (90, "Ground truth", DIM),
        (319, "Student observation", GOLD),
        (612, "3-frame median", GREEN),
    ]:
        d.line((x, 675, x + 25, 675), fill=color, width=4)
        text(d, (x + 32, 665), label, 17, color)
    text(d, (920, 215), "Independent execution", 24, INK, True)
    for i, name in enumerate(METHODS):
        item = c["methods"][name]
        y = 300 + i * 195
        d.rounded_rectangle((920, y - 16, 1388, y + 135), radius=12, fill="#21353f")
        text(d, (942, y), ("Peak", "Median then peak")[i], 22, INK, True)
        if n < len(obs):
            text(d, (942, y + 52), "Observing the teacher…", 20, DIM)
        else:
            passed = sum(s["passed"] for s in item["starts"])
            text(
                d,
                (942, y + 47),
                f"Student lift target    {item['lift_mm']:.1f} mm",
                20,
                BLUE,
            )
            text(
                d,
                (942, y + 89),
                f"Fresh starts passed    {passed} / 3",
                22,
                GREEN if passed else RED,
                True,
            )
    text(
        d,
        (50, 780),
        "The first drawer-translation event is known. Only the teacher's measured vertical channel is corrupted.",
        20,
        DIM,
    )


def matrix(d, result):
    text(
        d,
        (50, 153),
        "Same teacher observations and initial states for both estimators",
        25,
        GOLD,
    )
    names = (
        "Gaussian frame noise",
        "Paired starts",
        "Peak",
        "Median then peak",
        "Gained",
        "Lost",
    )
    xs = (64, 400, 590, 790, 1110, 1260)
    for x, name in zip(xs, names):
        text(d, (x, 273), name, 21, DIM, True)
    for i, (sigma, row) in enumerate(result["paired_summary"].items()):
        cells = (
            sigma + " mm",
            row["starts"],
            row["peak"],
            row["median3_peak"],
            "+" + str(row["gain"]),
            "−" + str(row["loss"]),
        )
        y = 345 + i * 90
        d.line((60, y - 22, 1390, y - 22), fill=LINE, width=2)
        for j, (x, v) in enumerate(zip(xs, cells)):
            text(
                d,
                (x, y),
                str(v),
                31,
                (GREEN if j == 4 else RED if j == 5 else INK),
                True,
            )
    text(
        d,
        (64, 655),
        "At 4 mm frame noise, filtering gained 21 starts and lost 6.",
        28,
        GREEN,
        True,
    )
    text(
        d,
        (64, 718),
        "At zero frame noise and −6 mm bias, filtering lost all 9 starts.",
        24,
        INK,
    )
    text(
        d,
        (64, 785),
        "3 passages   ·   3 offsets   ·   3 starts   ·   4 paired noise seeds   ·   noiseless settings counted once",
        20,
        DIM,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("record", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    result = json.loads(args.record.read_text())
    cases = [
        next(
            c
            for c in result["cases"]
            if c["gate_mm"] == 30
            and c["bias_mm"] == b
            and c["sigma_mm"] == s
            and c["seed"] == seed
        )
        for b, s, seed in [(0, 4, 0), (-6, 0, None)]
    ]
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
        "1440x900",
        "-r",
        "24",
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
        str(args.output),
    ]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as enc:
        for tick in range(24 * 24):
            im = Image.new("RGB", (1440, 900), BG)
            d = ImageDraw.Draw(im)
            text(
                d,
                (50, 32),
                "EMBODIED SELF-CALIBRATION   /   OBSERVATION SENSITIVITY",
                17,
                GREEN,
                True,
            )
            text(
                d,
                (50, 76),
                "How accurately must the student see the teacher?",
                37,
                INK,
                True,
            )
            if tick < 384:
                traces(d, cases[tick // 192], tick % 192)
            else:
                matrix(d, result)
            text(
                d,
                (50, 855),
                "Simulated measurement error  ·  rotary teacher  ·  sliding student  ·  60 mm drawer goal",
                17,
                DIM,
            )
            enc.stdin.write(im.tobytes())
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("Film encoder failed")


if __name__ == "__main__":
    main()
