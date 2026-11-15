"""Edit measured trials into a two-camera film. Requires Pillow, RTX frames and ffmpeg."""

import argparse
from functools import lru_cache
import json
from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont
from views import key, scenes

W, H, FPS = 1440, 900, 24
INK, DIM, LINE, GREEN, GOLD, RED = (
    "#eff4f2",
    "#a9b8bc",
    "#36505b",
    "#7de3bf",
    "#ffcf76",
    "#ff9c8c",
)
BG = "#101c24"
NAMES = {
    "channel_reversed": "Reversed motor",
    "latch_engaged": "Engaged latch",
    "both_faults": "Reversed motor + latch",
    "nominal": "Working drawer",
}
ACTIONS = {
    "practice": "Practice",
    "probe": "Free-space probe",
    "ask_teacher": "Teacher demonstration",
    "independent": "Frozen student",
    "assess": "End teaching",
}


@lru_cache(maxsize=30)
def font(size, bold=False):
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)


def text(d, xy, message, size=20, color=INK, bold=False):
    d.text(xy, message, fill=color, font=font(size, bold), anchor="lt")


@lru_cache(maxsize=40)
def frame_image(path):
    with Image.open(path) as im:
        return im.convert("RGB")


def trace_chart(d, x, y, trace, index):
    # Fixed vertical scale and 60 mm threshold across conditions.
    def point(i, value):
        return x + i * 203 / max(1, len(trace) - 1), y + 47 - max(
            0, min(value, 115)
        ) * 0.42

    target = point(0, 60)[1]
    d.line((x, target, x + 203, target), fill=LINE, width=2)
    points = [point(i, f["drawer_x_mm"]) for i, f in enumerate(trace[: index + 1])]
    if len(points) > 1:
        d.line(points, fill=GREEN, width=3)
    px, py = points[-1]
    d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=GREEN)


def panels(image, d, data, stage, count, fraction, cache):
    for left, (name, case, entries) in zip((36, 744), data):
        final = stage == count - 1
        waiting = not final and stage >= len(entries) - 1
        idx = len(entries) - 1 if final else min(stage, len(entries) - 2)
        action, trace, poses = entries[idx]
        j = min(len(trace) - 1, int(fraction * len(trace)))
        if waiting:
            j = len(trace) - 1
        f = trace[j]
        text(d, (left, 119), NAMES[name], 29, bold=True)
        title = "Teaching complete" if waiting else ACTIONS[action]
        if idx == 0 and not final:
            title = "First pull"
        text(d, (left, 161), title, 21, GREEN if final else GOLD)
        image.paste(frame_image(str(cache / (key(poses[j]) + ".jpg"))), (left, 201))
        d.rectangle((left, 565, left + 659, 658), fill="#20313b")
        text(d, (left + 15, 580), "TOOL TRAVEL", 14, DIM, True)
        text(d, (left + 15, 612), f"{f['tool_x_mm']:+.1f} mm", 23)
        text(d, (left + 187, 580), "DRAWER TRAVEL", 14, DIM, True)
        text(d, (left + 187, 612), f"{f['drawer_x_mm']:.1f} mm", 23)
        trace_chart(d, left + 414, 588, trace, j)
        text(d, (left + 416, 572), "60 mm target", 13, DIM)
        if final:
            n = sum(t["success"] for t in case["tests"])
            text(
                d,
                (left, 687),
                f"{n} of {len(case['tests'])} independent starts passed",
                24,
                GREEN if n else RED,
                True,
            )
            msg = "Displayed trial uses the largest initial gap. Supervisor and teacher are disconnected."
        elif waiting:
            msg = "The final independent test begins after the other teaching sequence ends."
        else:
            # Decision issued after the end of this trial, shown during its hold.
            if idx < len(case["decisions"]) and fraction >= 1:
                dec = case["decisions"][idx]
                text(
                    d,
                    (left, 684),
                    "Next decision   /   " + ACTIONS[dec["action"]],
                    23,
                    GOLD,
                    True,
                )
                msg = dec["evidence"]
            elif action == "ask_teacher":
                msg = "A three-axis teacher lifts the handle, then pulls. The student receives the observed handle trajectory."
            elif action == "probe":
                msg = "A +12 mm pulse measures polarity away from the drawer. The student stores the measured sign."
            else:
                msg = "The student applies its current skill. Score the drawer displacement against 60 mm."
        lines = textwrap.wrap(msg, width=54)
        for n, line in enumerate(lines[:4]):
            text(d, (left, 726 + n * 26), line, 18, DIM)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--encoder", default="libx264")
    args = parser.parse_args()
    run = json.loads(args.record.read_text())
    data = [(k, c, scenes(k, c)) for k, c in run["conditions"].items()]
    count = max(len(v) for _, _, v in data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-loglevel",
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
        str(args.output),
    ]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
        for stage in range(count):
            for tick in range(FPS * 5):
                im = Image.new("RGB", (W, H), BG)
                d = ImageDraw.Draw(im)
                text(
                    d,
                    (36, 19),
                    "EMBODIED SELF-CALIBRATION   /   DRAWER STUDY",
                    16,
                    GREEN,
                    True,
                )
                text(d, (36, 53), args.title, 36, INK, True)
                panels(im, d, data, stage, count, tick / (FPS * 2.1), args.cache)
                d.line((36, 851, 1404, 851), fill=LINE)
                backend = run.get("backend", "isaac")
                text(
                    d,
                    (36, 866),
                    f"{'PhysX' if backend == 'isaac' else 'ODE'} measurements   ·   RTX replay   ·   motion slowed for inspection",
                    17,
                    DIM,
                )
                text(d, (1275, 866), f"{stage + 1} / {count}", 18, INK)
                proc.stdin.write(im.tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("ffmpeg encoding failed")


if __name__ == "__main__":
    main()
