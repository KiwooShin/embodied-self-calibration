"""Section view of the measured teacher, student and narrow keyed passage."""

import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw

from replay import BG, DIM, GOLD, GREEN, INK, RED, text

BLUE = "#8cbbea"
RAIL = "#6b818e"


def mechanism(d, left, frame, g, teacher, gap, free=False):
    scale = 1.35

    def pos(x, z):
        return (left + 222 + scale * x, 520 - scale * z)

    def box(x, z, w, h, color):
        x0, y0 = pos(x, z)
        d.rectangle((x0, y0 - h * scale, x0 + w * scale, y0), fill=color)

    def disk(x, z, r, color):
        u, v = pos(x, z)
        d.ellipse((u - r, v - r, u + r, v + r), fill=color)

    tx = frame["tool_x_mm"] - gap
    tz = 45 + frame["tool_z_mm"]
    dx = frame["drawer_x_mm"]
    hz = frame["handle_z_mm"]
    box(-153, -10, 280, 7, RAIL)
    # Section of the side slot through the lug. The handle and pin lie in a
    # parallel plane and are projected here to make the clearance visible.
    if not free:
        box(46, -8, 18, 13 + g, RED)
        box(46, 33 + g, 18, 97 - g, RED)
        box(dx - 7, -4, 75, 5, BLUE)
        box(dx + 8, 27 + hz, 12, 38, GOLD)
        box(dx - 17.5, 54 + hz, 33, 12, GOLD)
        box(dx + 12, 20 + hz, 26, 5, GOLD)
        box(dx + 26, 5 + hz, 16, 18, GOLD)
    if teacher:
        pivot = frame["pivot_x_mm"]
        d.line((pos(pivot, 45), pos(tx, tz)), fill=GREEN, width=9)
        disk(pivot, 45, 10, RAIL)
        disk(pivot, 45, 4, INK)
    else:
        box(tx - 6, 4, 12, tz - 4, RAIL)
    box(tx - 6, tz - 6, 12, 12, GREEN)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("result", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    data = json.loads(args.result.read_text())
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
        for g in (12, 30, 48):
            teacher = data["teachers"][str(g)]
            trials = [
                next(
                    t
                    for t in data["trials"]
                    if t["gate_mm"] == g and t["method"] == m and t["gap_mm"] == 8
                )
                for m in ("matched", "shuffled")
            ]
            for tick in range(24 * 8):
                im = Image.new("RGB", (1440, 900), BG)
                d = ImageDraw.Draw(im)
                text(
                    d,
                    (36, 23),
                    "EMBODIED SELF-CALIBRATION   /   TRANSFER BETWEEN DIFFERENT JOINT TYPES",
                    16,
                    GREEN,
                    True,
                )
                text(
                    d,
                    (36, 63),
                    "Can the student use what the other robot shows?",
                    39,
                    INK,
                    True,
                )
                text(
                    d,
                    (38, 133),
                    f"Fixture requires {g}–{g + 10} mm of handle lift to pass the slot.",
                    25,
                    GOLD,
                )
                for i, left in enumerate((25, 493, 961)):
                    d.rounded_rectangle(
                        (left, 216, left + 454, 673), radius=16, fill="#20333e"
                    )
                    title = (
                        "Rotary teacher",
                        "Matching demonstration",
                        "Mismatched demonstration",
                    )[i]
                    text(d, (left + 14, 236), title, 22, INK, True)
                    if i == 0:
                        frames = teacher["trace"]
                        frac = min(1, tick / (24 * 2.5))
                        label = "Hinge and horizontal slide"
                    else:
                        t = trials[i - 1]
                        frames = t["trace"]
                        frac = max(0, min(1, (tick - 24 * 3) / (24 * 2.7)))
                        label = f"Linear lift target   {t['student_lift_mm']:.1f} mm"
                    f = frames[min(len(frames) - 1, int(frac * len(frames)))]
                    text(d, (left + 14, 281), label, 18, DIM)
                    mechanism(d, left, f, g, i == 0, 0 if i == 0 else 8)
                    text(
                        d,
                        (left + 15, 572),
                        f"Handle lift     {f['handle_z_mm']:.1f} mm",
                        19,
                        GOLD,
                    )
                    text(
                        d,
                        (left + 15, 614),
                        f"Drawer travel    {f['drawer_x_mm']:.1f} mm",
                        22,
                        BLUE,
                        True,
                    )
                if tick < 24 * 3:
                    caption = "The teacher rotates a lever. Only its observed handle trajectory is passed to the student."
                else:
                    caption = "Both students have the same controls. One received the segment from a different fixture."
                text(d, (36, 727), caption, 23, INK)
                text(
                    d,
                    (36, 781),
                    "Nine starts per method   ·   Matching segment  9/9     Shuffled segment  0/9     Fixed lift  3/9     No lift  0/9",
                    20,
                    GREEN,
                    True,
                )
                text(
                    d,
                    (36, 850),
                    "ODE measured motion   ·   side projection through the gate   ·   all examples use an 8 mm starting gap",
                    17,
                    DIM,
                )
                enc.stdin.write(im.tobytes())
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")


if __name__ == "__main__":
    main()
