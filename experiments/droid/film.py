"""Show synced excerpt, measured gripper trace, selected interval and attribution."""

import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

BG = "#122129"
INK = "#f0f4f3"
DIM = "#a8b9c0"
TEAL = "#7ee4be"
GOLD = "#edc677"
REG = "DejaVuSans.ttf"
BOLD = "DejaVuSans-Bold.ttf"


def txt(d, xy, s, size=20, color=INK, bold=False):
    d.text(
        xy,
        s,
        font=ImageFont.truetype(BOLD if bold else REG, size),
        fill=color,
        anchor="lt",
    )


def camera(cache, ep, name):
    p = cache / ("observation.images." + name + f"-episode_{ep['id']:06d}.mp4")
    out = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(p),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    stride = 320 * 180 * 3
    if len(out) != ep["frames"] * stride:
        raise ValueError("Telemetry / video frame mismatch")
    lo, hi = ep["window"]
    return [
        Image.frombytes("RGB", (320, 180), out[i * stride : (i + 1) * stride])
        for i in range(lo, hi + 1)
    ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("record", type=Path)
    p.add_argument("cache", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    run = json.loads(args.record.read_text())
    fps = run["fps"]
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
        str(fps),
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
        for ep in run["episodes"]:
            maincam, wrist, side = [
                camera(args.cache, ep, n)
                for n in (
                    "exterior_image_2_left",
                    "wrist_image_left",
                    "exterior_image_1_left",
                )
            ]
            lo, hi = ep["window"]
            g = ep["observed_gripper"]
            n = len(g)
            for i in range(len(maincam) + fps * 2):
                j = min(i, len(maincam) - 1)
                f = lo + j
                im = Image.new("RGB", (1440, 900), BG)
                d = ImageDraw.Draw(im)
                txt(
                    d,
                    (32, 22),
                    "REAL DEMONSTRATION   /   DROID TEACHER DATA",
                    16,
                    TEAL,
                    True,
                )
                txt(
                    d,
                    (32, 64),
                    "Can gripper telemetry find the opening motion?",
                    39,
                    INK,
                    True,
                )
                txt(
                    d,
                    (32, 127),
                    f"Episode {ep['id']}   ·   “{ep['task']}”   ·   frame {f} of {n - 1}",
                    21,
                    DIM,
                )
                im.paste(
                    maincam[j].resize((804, 452), Image.Resampling.LANCZOS), (32, 180)
                )
                im.paste(
                    wrist[j].resize((397, 223), Image.Resampling.LANCZOS), (856, 180)
                )
                im.paste(
                    side[j].resize((397, 223), Image.Resampling.LANCZOS), (856, 410)
                )
                txt(d, (1265, 270), "Wrist", 20, DIM)
                txt(d, (1265, 495), "Exterior 1", 20, DIM)
                x0, y0 = 54, 777
                scale = 777 / (n - 1)
                d.rectangle((x0 + lo * scale, 672, x0 + hi * scale, y0), fill="#26424a")
                d.line(
                    [(x0 + k * scale, y0 - 100 * value) for k, value in enumerate(g)],
                    fill=TEAL,
                    width=3,
                )
                d.line(
                    (x0 + f * scale, 670, x0 + f * scale, y0 + 4), fill=GOLD, width=3
                )
                txt(
                    d,
                    (38, 647),
                    "Observed gripper position   /   full episode",
                    17,
                    DIM,
                )
                txt(d, (40, 797), f"{0:.0f} s", 15, DIM)
                txt(d, (755, 797), f"{(n - 1) / fps:.1f} s", 15, DIM)
                triggers = ep["gripper_trigger_frames"]
                txt(d, (858, 673), "Closure threshold crossing", 19, DIM)
                txt(
                    d,
                    (858, 713),
                    f"Frame {triggers[0]}" if triggers else "None in this episode",
                    26,
                    TEAL if triggers else GOLD,
                    True,
                )
                txt(
                    d,
                    (858, 760),
                    "Shaded interval: visually reviewed opening.",
                    17,
                    DIM,
                )
                txt(
                    d,
                    (32, 857),
                    "DROID · Khazatsky et al., RSS 2024 · CC BY 4.0 · LeRobot conversion by IPEC-COMMUNITY · excerpts with telemetry overlays",
                    17,
                    DIM,
                )
                enc.stdin.write(im.tobytes())
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")


if __name__ == "__main__":
    main()
