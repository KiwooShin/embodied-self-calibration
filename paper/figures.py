"""Regenerate the paper's figures from committed experiment records and footage."""

import json
from pathlib import Path
import subprocess
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/figures"
NAVY = "#193347"
GREEN = "#16736b"
GOLD = "#b07417"
RED = "#a74737"
SILVER = "#c4cdd1"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": NAVY,
        "axes.titlecolor": NAVY,
        "svg.fonttype": "path",
    }
)


def load(name):
    return json.loads((ROOT / "results" / name).read_text())


def transfer():
    r = load("keyed-teacher.json")
    g = 30
    t = [
        next(
            x
            for x in r["trials"]
            if x["method"] == m and x["gate_mm"] == g and x["gap_mm"] == 8
        )
        for m in ("matched", "shuffled")
    ]
    traces = [r["teachers"][str(g)]["trace"], t[0]["trace"], t[1]["trace"]]
    fig, axes = plt.subplots(1, 3, figsize=(7.15, 2.10), layout="constrained")
    for j, (ax, trace, title) in enumerate(
        zip(
            axes,
            traces,
            ["A   Rotary teacher", "B   Matched segment", "C   Shuffled segment"],
        )
    ):
        f = trace[-1]
        dx = f["drawer_x_mm"]
        h = f["handle_z_mm"]
        tx = f["tool_x_mm"] - (8 if j else 0)
        tz = 45 + f["tool_z_mm"]

        def rect(x, z, w, height, color):
            ax.add_patch(
                Rectangle((x, z), w, height, facecolor=color, edgecolor="white", lw=0.5)
            )

        rect(46, -8, 18, 13 + g, RED)
        rect(46, 33 + g, 18, 97 - g, RED)
        rect(dx - 7, -4, 75, 5, "#6189a2")
        rect(dx + 8, 27 + h, 12, 38, GOLD)
        rect(dx - 17.5, 54 + h, 33, 12, GOLD)
        rect(dx + 12, 20 + h, 26, 5, GOLD)
        rect(dx + 26, 5 + h, 16, 18, GOLD)
        ax.plot(
            [i["tool_x_mm"] - (8 if j else 0) for i in trace],
            [45 + i["tool_z_mm"] for i in trace],
            "--",
            color=GREEN,
            lw=1,
        )
        if j == 0:
            ax.plot(
                [f["pivot_x_mm"], tx],
                [45, tz],
                color=GREEN,
                lw=3,
                solid_capstyle="round",
            )
            ax.scatter(f["pivot_x_mm"], 45, s=18, c=NAVY, zorder=4)
        else:
            rect(tx - 5, 3, 10, tz - 3, SILVER)
        rect(tx - 6, tz - 6, 12, 12, GREEN)
        ax.set(xlim=(-73, 165), ylim=(-12, 135), aspect="equal", xticks=[], yticks=[])
        ax.set_title(title, loc="left", fontweight="bold", fontsize=9)
        ax.set_xlabel(f"Drawer travel   {dx:.1f} mm", fontsize=9)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.savefig(OUT / "cross-body.svg", bbox_inches="tight", pad_inches=0.025)
    plt.close(fig)


def workspace():
    rows = load("workspace-sweep.json")
    fig, axes = plt.subplots(2, 2, figsize=(7.1, 2.85), layout="constrained")
    colors = ListedColormap(["#d8dadd", "#bd624f", GREEN])
    for i, (name, cases) in enumerate(rows.items()):
        for j, (m, label) in enumerate(
            [("frozen", "Retained map"), ("refitted", "Locally refitted map")]
        ):
            ax = axes[i, j]
            grid = np.zeros((8, 13), int)
            for c in cases:
                grid[c["direction_deg"] // 45, (c["posture_deg"] + 90) // 15] = (
                    2 if c[m]["passed"] else 1 if c["within_radial_bound"] else 0
                )
            ax.imshow(
                grid,
                cmap=colors,
                vmin=0,
                vmax=2,
                aspect="auto",
                origin="lower",
                interpolation="nearest",
            )
            ax.set_title(
                f"{label}   {int((grid == 2).sum())}/104",
                fontsize=9,
                loc="left",
                fontweight="bold",
            )
            ax.set_xticks(
                [0, 3, 6, 9, 12], ["−90°", "−45°", "0°", "45°", "90°"] if i else []
            )
            ax.set_yticks([0, 4, 7], ["0°", "180°", "315°"] if not j else [])
            ax.tick_params(length=0, labelsize=7)
            if not j:
                ax.set_ylabel(("Two joints", "Three joints")[i], fontsize=8)
            if i:
                ax.set_xlabel("Starting posture shift", fontsize=8)
    fig.savefig(OUT / "workspace.svg", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def droid():
    # The public milestone replay contains attributed frames at fixed placements.
    # Take the exterior view near the end of each reviewed interval.
    r = load("droid-drawer-sample.json")
    fig, axes = plt.subplots(1, 3, figsize=(7.05, 1.55), layout="constrained")
    offset = 0
    for ax, ep in zip(axes, r["episodes"]):
        lo, hi = ep["window"]
        sec = offset + (hi - lo) / r["fps"]
        img = Image.open(
            BytesIO(
                subprocess.check_output(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-ss",
                        str(sec),
                        "-i",
                        str(ROOT / "videos/12-real-teacher.mp4"),
                        "-frames:v",
                        "1",
                        "-f",
                        "image2pipe",
                        "-c:v",
                        "png",
                        "-",
                    ]
                )
            )
        )
        ax.imshow(img.crop((32, 180, 836, 632)))
        ax.set_axis_off()
        event = ep["gripper_trigger_frames"]
        ax.set_title(
            f"Episode {ep['id']}  ·  " + ("closure" if event else "no trigger"),
            fontsize=8,
            loc="left",
        )
        offset += (hi - lo + 1) / r["fps"] + 2
    fig.savefig(OUT / "droid.jpg", dpi=200, bbox_inches="tight", pad_inches=0.025)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    transfer()
    workspace()
    droid()
