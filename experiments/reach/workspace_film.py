"""Animate the paired generalization sweep. Each tile is one completed ODE trial."""

import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw
from film import BG, DIM, GOLD, GREEN, INK, SALMON, label


def main():
    p = argparse.ArgumentParser()
    p.add_argument("result", type=Path)
    p.add_argument("video", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    records = json.loads(args.result.read_text())
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
        str(args.video),
    ]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as enc:
        for tick in range(24 * 20):
            im = Image.new("RGB", (1440, 900), BG)
            d = ImageDraw.Draw(im)
            label(
                d,
                38,
                22,
                "EMBODIED SELF-CALIBRATION   /   WORKSPACE SWEEP",
                16,
                GREEN,
                True,
            )
            label(d, 38, 60, "How far does one calibration transfer?", 40, INK, True)
            label(
                d,
                40,
                124,
                "Each cell moves 100 mm. Columns change starting posture. Rows change the target direction.",
                22,
                DIM,
            )
            reveal = min(13, max(1, tick // 18 + 1))
            for row, (name, cases) in enumerate(records.items()):
                y = 235 + row * 275
                for col, method in enumerate(("frozen", "refitted")):
                    x = 116 + col * 710
                    if not row:
                        label(
                            d,
                            x,
                            180,
                            ("One frozen motor map", "Reprobe at each posture")[col],
                            28,
                            INK,
                            True,
                        )
                    winning = 0
                    for r in cases:
                        i = (r["posture_deg"] + 90) // 15
                        j = r["direction_deg"] // 45
                        dx = x + i * 41
                        dy = y + j * 21
                        color = "#243840"
                        if i < reveal:
                            ok = r[method]["passed"]
                            winning += ok
                            color = (
                                GREEN
                                if ok
                                else (SALMON if r["within_radial_bound"] else "#55636c")
                            )
                        d.rounded_rectangle(
                            (dx, dy, dx + 36, dy + 16), radius=3, fill=color
                        )
                    for j, angle in enumerate(range(0, 360, 45)):
                        label(d, x - 50, y + j * 21, str(angle) + "°", 13, DIM)
                    for i, angle in ((0, -90), (3, -45), (6, 0), (9, 45), (12, 90)):
                        label(d, x + i * 41, y + 175, f"{angle}°", 15, DIM)
                    label(
                        d,
                        x,
                        y + 208,
                        ("Two" if name == "two_link" else "Three")
                        + f" joints   ·   {winning} / {8 * reveal} passed",
                        22,
                        GREEN,
                        True,
                    )
            label(
                d,
                40,
                782,
                "Green: within 10 mm     Coral: missed     Gray: target beyond radial reach including tolerance",
                19,
                DIM,
            )
            if tick >= 240:
                label(
                    d,
                    40,
                    834,
                    "Refitting improves coverage and costs one extra pulse per motor per starting posture.",
                    23,
                    GOLD,
                    True,
                )
            enc.stdin.write(im.tobytes())
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")


if __name__ == "__main__":
    main()
