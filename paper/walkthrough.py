"""Compose a chaptered, narrated paper walkthrough from measured runs and rendered pages."""

import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, ACCENT, BACK = "#edf4ee", "#a9bcb9", "#84dfbf", "#0d202a"
WIDTH, HEIGHT = 1600, 1000


def chapters(models: dict[str, Any]) -> list[tuple[str, str, int, str, str]]:
    """Return six chapter captions and voice tracks using the measured model scores."""
    small, large = models["small"], models["large"]
    return [
        (
            "The same failure can need two different lessons",
            "01-physics.mp4",
            1,
            "One drawer stays closed because the motor runs backward. Another stays closed because its catch hits a stop.",
            "Both students get the same goal. The supervisor can probe a motor, ask a different robot for an example, practice, or end teaching.",
        ),
        (
            "What can a differently built teacher show?",
            "10-cross-body-teacher.mp4",
            0,
            "The teacher turns a lever. The student slides a pin. Only the handle and drawer motion pass between them.",
            "The teacher and student have different actuators. A demonstration tells the student how high the handle moves before the drawer starts opening.",
        ),
        (
            "Test the student after the teacher disconnects",
            "11-teaching-decisions.mp4",
            3,
            "Eight teaching episodes per supervisor. Three fresh starts test each frozen skill.",
            "The supervisor gets five decisions per episode. After teaching, we freeze the student, remove both the supervisor and the source teacher, and measure drawer travel from three new starts.",
        ),
        (
            "Does a larger supervisor choose better lessons?",
            "14-model-size.mp4",
            18,
            f"All-start passes:  8B  {small['episodes']}/8     32B  {large['episodes']}/8     Fixed rule  {models['rule']['episodes']}/8",
            f"The smaller model solved {small['episodes']} of eight teaching episodes. The larger model solved {large['episodes']}, as did the fixed rule. The larger model requested {large['queries']} teacher demonstrations. The rule requested {models['rule']['queries']}.",
        ),
        (
            "When is another motor experiment worth it?",
            "09-recalibrate.mp4",
            7,
            "39/48 reaching successes for both methods. The residual threshold saved 54 motor pulses and 18 resets.",
            "On a new three joint arm grid, the small model chose recalibration every time. A prediction error threshold learned on a two joint arm reached the same thirty nine targets using fifty four fewer motor pulses.",
        ),
        (
            "What changes when the teacher is a real robot?",
            "12-real-teacher.mp4",
            1,
            "In two of three DROID episodes, the gripper channel stayed constant through a visible drawer opening.",
            "These are physical teacher recordings from DROID. Gripper state alone missed two visible openings. Our students were tested in simulation. A separate simulation measured sensitivity to observation error. Next we need camera measurements and independent execution on a physical student.",
        ),
    ]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load the same subtitle font used throughout the milestone films."""
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)


def wrap(
    draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int
) -> list[str]:
    """Wrap a caption at word boundaries using its rendered pixel width."""
    lines = [""]
    for word in text.split():
        candidate = (lines[-1] + " " + word).strip()
        if draw.textlength(candidate, font=face) > width and lines[-1]:
            lines.append(word)
        else:
            lines[-1] = candidate
    return lines


def card(page: int, title: str, finding: str, page_image: Path, destination: Path) -> None:
    """Render a chapter background with a readable finding and current manuscript page."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BACK)
    draw = ImageDraw.Draw(img)
    draw.text(
        (48, 32),
        "EMBODIED SELF-CALIBRATION   /   RESEARCH FILM",
        font=font(21, True),
        fill=ACCENT,
    )
    draw.text((1552, 32), f"PAPER   {page} / 6", font=font(21, True), fill=ACCENT, anchor="ra")
    draw.text((48, 87), title, fill=INK, font=font(41, True))
    draw.line((48, 158, 1552, 158), fill="#416069", width=2)
    thumb = ImageOps.contain(
        Image.open(page_image).convert("RGB"), (428, 554), Image.Resampling.LANCZOS
    )
    img.paste(thumb, (1100 + (452 - thumb.width) // 2, 211))
    draw.text((1326, 786), f"Manuscript · page {page}", fill=MUTED, font=font(20), anchor="ma")
    for i, line in enumerate(wrap(draw, finding, font(28, True), 1504)):
        draw.text((48, 848 + i * 38), line, fill=INK, font=font(28, True))
    footer = (
        "DROID footage: Khazatsky et al. · CC BY 4.0 · IPEC-COMMUNITY conversion"
        if page == 6
        else "Measured simulator trajectories  ·  Embodied Self-Calibration Project"
    )
    draw.text((48, 950), footer, fill=MUTED, font=font(18))
    img.save(destination)


def stamp(seconds: float) -> str:
    """Format a subtitle cue time in SubRip notation."""
    msec = round(seconds * 1000)
    h, rest = divmod(msec, 3600000)
    m, rest = divmod(rest, 60000)
    s, ms = divmod(rest, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def edit(args: argparse.Namespace, temp: Path) -> None:
    """Compose the six recorded clips with narration, timed captions and page chapters."""
    from piper import PiperVoice

    voice = PiperVoice.load(args.voice)
    models = json.loads((ROOT / "paper/model-results.json").read_text())
    subprocess.run(
        [
            "pdftoppm",
            "-scale-to",
            "1000",
            "-png",
            str(ROOT / "paper/embodied-self-calibration.pdf"),
            str(temp / "pg"),
        ],
        check=True,
    )
    parts, captions = [], []
    meta = [
        ";FFMETADATA1",
        "title=When should a robot probe its body or ask another robot for help?",
    ]
    elapsed = 0.0
    for page, (title, file, start, finding, narration) in enumerate(chapters(models), 1):
        panel, wav, shot = (temp / f"{page}.{suffix}" for suffix in ("png", "wav", "mp4"))
        card(page, title, finding, temp / f"pg-{page}.png", panel)
        with wave.open(str(wav), "wb") as audio:
            voice.synthesize_wav(narration, audio)
        with wave.open(str(wav), "rb") as audio:
            length = audio.getnframes() / audio.getframerate()
        # Round to a whole frame so all cuts, subtitle cues, and chapter marks align.
        duration = round((length + 0.55) * 24) / 24
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-loop",
                "1",
                "-framerate",
                "24",
                "-i",
                str(panel),
                "-ss",
                str(start),
                "-i",
                str(ROOT / "videos" / file),
                "-i",
                str(wav),
                "-filter_complex",
                "[1:v]scale=1024:640,tpad=stop_mode=clone:stop_duration=30[v];[0:v][v]overlay=48:184:shortest=1[out]",
                "-map",
                "[out]",
                "-map",
                "2:a",
                "-t",
                str(duration),
                "-af",
                "apad",
                "-c:v",
                args.encoder,
                "-b:v",
                "5M",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "1",
                str(shot),
            ],
            check=True,
        )
        parts.append(f"file '{shot.name}'")
        meta.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={round(elapsed * 1000)}",
                f"END={round((elapsed + duration) * 1000)}",
                f"title=Page {page} — {title}",
            ]
        )
        phrases = [line.strip() + "." for line in narration.rstrip(".").split(". ")]
        spoken_words, nwords = 0, sum(len(line.split()) for line in phrases)
        for line in phrases:
            cue_start = elapsed + length * spoken_words / nwords
            spoken_words += len(line.split())
            cue_end = elapsed + length * spoken_words / nwords
            captions.append(
                f"{len(captions) + 1}\n{stamp(cue_start)} --> {stamp(cue_end)}\n{line}\n"
            )
        elapsed += duration
    for name, lines in [
        ("cuts.txt", parts),
        ("captions.srt", captions),
        ("chapters.txt", meta),
    ]:
        (temp / name).write_text("\n".join(lines) + "\n")
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(temp / "cuts.txt"),
            "-i",
            str(temp / "captions.srt"),
            "-f",
            "ffmetadata",
            "-i",
            str(temp / "chapters.txt"),
            "-map",
            "0:v",
            "-map",
            "0:a",
            "-map",
            "1:s",
            "-map_metadata",
            "2",
            "-map_chapters",
            "2",
            "-c",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=eng",
            "-movflags",
            "+faststart",
            str(args.output),
        ],
        check=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("voice", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    if args.output.exists():
        p.error("Choose a new output file")
    with tempfile.TemporaryDirectory() as folder:
        edit(args, Path(folder))
