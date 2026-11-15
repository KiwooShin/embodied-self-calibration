"""Show the observation behind two Qwen decisions, then score all 48 pairs."""

import argparse
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw
from film import BG, DIM, INK, GREEN, GOLD, SALMON, label


def arrow(draw, start, vector, color, width):
    dx, dy = vector
    end = (start[0] + dx, start[1] + dy)
    draw.line((start, end), fill=color, width=width)
    a = math.atan2(dy, dx)
    draw.polygon(
        [
            end,
            (end[0] - 15 * math.cos(a - 0.5), end[1] - 15 * math.sin(a - 0.5)),
            (end[0] - 15 * math.cos(a + 0.5), end[1] - 15 * math.sin(a + 0.5)),
        ],
        fill=color,
    )


def diagnosis(d, r, phase, frac):
    obs = r["observation"]
    label(
        d,
        40,
        135,
        ("Closest predicted and measured move", "Largest first-move disagreement")[
            phase
        ],
        28,
        INK,
        True,
    )
    d.rounded_rectangle((40, 195, 765, 765), radius=18, fill="#1b323c")
    start = (399, 482)
    for i in range(-5, 6):
        x = start[0] + i * 57
        y = start[1] + i * 48
        d.line((x, 210, x, 749), fill="#2c4752")
        d.line((54, y, 750, y), fill="#2c4752")
    for k, color, w in (("predicted_mm", GOLD, 10), ("actual_mm", GREEN, 5)):
        vx, vy = obs[k]
        arrow(d, start, (frac * vx * 4, -frac * vy * 4), color, w)
    label(d, 62, 219, "Diagnostic endpoint movement", 20, DIM)
    label(d, 62, 706, "Gold  /  predicted         Teal  /  measured", 19, INK)
    label(d, 811, 225, "START POSTURE SHIFT", 15, DIM, True)
    label(d, 811, 261, f"{r['posture_deg']:+d}°", 38, INK, True)
    label(d, 811, 354, "RELATIVE PREDICTION ERROR", 15, DIM, True)
    label(d, 811, 390, f"{obs['residual_ratio']:.2f}", 38, GOLD, True)
    if frac == 1:
        choice = r["qwen"]["action"]
        label(d, 811, 480, "QWEN DECISION", 15, DIM, True)
        label(
            d,
            811,
            515,
            (
                "Reprobe all three channels"
                if choice == "reprobe"
                else "Keep the motor map"
            ),
            27,
            INK,
            True,
        )
        out = r["outcomes"][choice]
        label(
            d,
            811,
            604,
            f"Final error    {out['error_mm']:.1f} mm",
            25,
            GREEN if out["passed"] else SALMON,
            True,
        )
        label(d, 811, 659, "Pass threshold    10 mm", 20, DIM)


def stats(rows, key):
    actions = [
        r["qwen"]["action"] if key == "qwen" else r["rule"] if key == "rule" else key
        for r in rows
    ]
    return sum(
        r["outcomes"][a]["passed"] for r, a in zip(rows, actions)
    ), 3 * actions.count("reprobe")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("record", type=Path)
    p.add_argument("video", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    run = json.loads(args.record.read_text())
    rows = run["rows"]
    examples = sorted(rows, key=lambda r: r["observation"]["residual_ratio"])
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
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
        for tick in range(24 * 21):
            im = Image.new("RGB", (1440, 900), BG)
            d = ImageDraw.Draw(im)
            label(
                d,
                40,
                25,
                "EMBODIED SELF-CALIBRATION   /   RETAIN OR RECALIBRATE",
                16,
                GREEN,
                True,
            )
            label(d, 40, 63, "Is this motor map still useful?", 42, INK, True)
            if tick < 24 * 12:
                phase = int(tick >= 24 * 6)
                diagnosis(
                    d,
                    examples[-1 if phase else 0],
                    phase,
                    min(1, (tick % (24 * 6)) / (24 * 2)),
                )
            else:
                n = min(len(rows), 1 + (tick - 24 * 12) // 2)
                label(
                    d,
                    40,
                    153,
                    f"Held-out three-link arm    /    {n} of {len(rows)} trials",
                    27,
                    INK,
                    True,
                )
                label(d, 375, 240, "TARGETS REACHED", 15, DIM, True)
                label(d, 908, 240, "EXTRA MOTOR PULSES", 15, DIM, True)
                for j, (method, name) in enumerate(
                    [
                        ("keep", "Always keep"),
                        ("reprobe", "Always reprobe"),
                        ("rule", "Residual threshold"),
                        ("qwen", "Qwen3-8B"),
                    ]
                ):
                    successes, pulses = stats(rows[:n], method)
                    y = 310 + j * 103
                    label(d, 41, y, name, 24, INK, True)
                    d.rounded_rectangle(
                        (378, y, 378 + max(1, successes / 48 * 355), y + 30),
                        radius=4,
                        fill=GREEN,
                    )
                    label(d, 748, y, f"{successes}/{n}", 23)
                    d.rounded_rectangle(
                        (908, y, 908 + max(1, pulses / 144 * 290), y + 30),
                        radius=4,
                        fill=GOLD,
                    )
                    label(d, 1234, y, str(pulses), 23)
                label(
                    d,
                    42,
                    763,
                    "Every reprobe also resets the arm to its starting posture. The threshold was fitted on the two-link arm.",
                    19,
                    DIM,
                )
            d.line((40, 840, 1400, 840), fill="#36505b")
            label(
                d,
                40,
                861,
                "ODE   ·   100 mm targets   ·   six new postures and eight new target directions",
                18,
                DIM,
            )
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("ffmpeg failed")


if __name__ == "__main__":
    main()
