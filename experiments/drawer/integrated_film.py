"""Play decisions at a held-out gate, then show every independent evaluation."""

import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw
from keyed_film import mechanism
from replay import BG, DIM, GOLD, GREEN, INK, RED, text, ACTIONS


def example(d, records, phase, tick):
    key = "34-normal" if phase == 0 else "34-reverse"
    title = "Normal horizontal motor" if phase == 0 else "Reversed horizontal motor"
    text(d, (40, 145), f"34 mm gate    /    {title}", 25, GOLD)
    part = min(2, tick // 72)
    frac = min(1, (tick % 72) / 39)
    for i, (name, record) in enumerate(records):
        left = 36 + i * 704
        c = record["conditions"][key]
        d.rounded_rectangle((left, 210, left + 664, 767), radius=15, fill="#23333c")
        text(d, (left + 18, 233), name, 28, INK, True)
        if part == 2:
            test = c["tests"][-1]
            trace = test["trace"]
            gap = 12
            action = "independent"
            caption = "Teacher disconnected"
        else:
            idx = min(part, len(c["history"]) - 1)
            trace = c["traces"][idx]
            gap = 0
            action = c["history"][idx]["kind"]
            caption = "First attempted pull" if part == 0 else ACTIONS[action]
        text(d, (left + 18, 289), caption, 21, GREEN)
        f = trace[min(len(trace) - 1, int(len(trace) * frac))]
        mechanism(
            d, left + 65, f, 34, action == "ask_teacher", gap, free=action == "probe"
        )
        text(d, (left + 18, 588), f"Drawer travel   {f['drawer_x_mm']:.1f} mm", 25, INK)
        if part == 2:
            passed = sum(t["success"] for t in c["tests"])
            msg = f"Independent starts passed    {passed} / 3"
        else:
            msg = f"First decision    {ACTIONS[c['decisions'][0]['action']]}"
        text(d, (left + 18, 665), msg, 22, GOLD, True)
    text(
        d,
        (40, 810),
        "Phases show the first pull, first intervention, and final frozen test. Intermediate practice is omitted.",
        19,
        DIM,
    )


def score(d, records):
    text(
        d,
        (40, 148),
        "Independent evaluation    /    three fresh starts per condition",
        25,
        INK,
        True,
    )
    for left, (name, record) in zip((50, 754), records):
        text(d, (left, 221), name, 27, INK, True)
        for j, pol in enumerate(("normal", "reverse")):
            text(d, (left + 193 + j * 185, 285), pol.title(), 21, DIM)
        total = 0
        for i, gate in enumerate(("open", "16", "34", "52")):
            y = 348 + i * 87
            text(
                d,
                (left, y + 8),
                "Open" if gate == "open" else gate + " mm gate",
                23,
                INK,
            )
            for j, pol in enumerate(("normal", "reverse")):
                c = record["conditions"][gate + "-" + pol]
                n = sum(t["success"] for t in c["tests"])
                total += n
                x = left + 187 + j * 185
                d.rounded_rectangle(
                    (x, y, x + 147, y + 43), radius=7, fill=GREEN if n == 3 else RED
                )
                text(d, (x + 32, y + 10), f"{n} / 3", 22, BG, True)
        text(d, (left, 741), f"{total} of 24 independent starts passed", 22, INK, True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("qwen", type=Path)
    p.add_argument("rule", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    records = [
        ("Qwen3-8B", json.loads(args.qwen.read_text())),
        ("Fixed telemetry rule", json.loads(args.rule.read_text())),
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
        for tick in range(24 * 25):
            im = Image.new("RGB", (1440, 900), BG)
            d = ImageDraw.Draw(im)
            text(
                d,
                (40, 23),
                "EMBODIED SELF-CALIBRATION   /   HELD-OUT TEACHING TEST",
                16,
                GREEN,
                True,
            )
            text(
                d,
                (40, 65),
                "When does the student get the right lesson?",
                38,
                INK,
                True,
            )
            if tick < 432:
                example(d, records, tick // 216, tick % 216)
            else:
                score(d, records)
            text(
                d,
                (40, 861),
                "ODE   ·   rotary teacher and sliding student   ·   five decision slots   ·   60 mm drawer target",
                17,
                DIM,
            )
            enc.stdin.write(im.tobytes())
        enc.stdin.close()
        if enc.wait():
            raise RuntimeError("ffmpeg failed")


if __name__ == "__main__":
    main()
