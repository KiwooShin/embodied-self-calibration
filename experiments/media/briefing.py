"""Edit a narrated briefing from the published milestone films and measured runs."""

import argparse
from pathlib import Path
import subprocess
import tempfile
import wave

from piper import PiperVoice

SHOTS = [
    (
        "01-physics.mp4",
        0,
        "Two students try to open a drawer. On the left, the tool moves backward. On the right, the tool reaches a mechanical stop. Both drawers fail the sixty millimeter goal.",
    ),
    (
        "01-physics.mp4",
        5,
        "A short motor pulse identifies the reversed channel. The other student watches a different robot lift the handle. Only the handle motion transfers between these bodies.",
    ),
    (
        "02-raw-qwen.mp4",
        2,
        "We gave the same evidence to a local language model. It called the backward movement a success. With raw measurements, neither frozen student passed a single test.",
    ),
    (
        "03-evidence.mp4",
        19,
        "Labeling the direction and the task score helped on the reversed motor. On the latch, the model kept asking the student to practice an action that had already failed.",
    ),
    (
        "06-call-schedule.mp4",
        4,
        "What if the agent is called only after failure? Across four fixtures, calls fell from thirteen to seven. Independent successes fell too, from nine to six out of twelve.",
    ),
    (
        "07-ten-centimetres.mp4",
        11,
        "Now try a different task. Each arm must move ten centimeters left. Motor pulses reveal how the wrist responds. Both arms passed, but probing each channel just once was more efficient.",
    ),
    (
        "08-workspace.mp4",
        6,
        "One calibration also has a limited range. Across two hundred and eight posture and direction pairs, a frozen map succeeded one hundred and two times. Local recalibration succeeded one hundred and sixty six times.",
    ),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video_dir", type=Path)
    p.add_argument("voice", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--encoder", default="libx264")
    args = p.parse_args()
    if args.output.exists():
        p.error("Choose a new output file")
    voice = PiperVoice.load(args.voice)
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        parts = []
        for i, (source, start, narration) in enumerate(SHOTS):
            wav = folder / f"{i}.wav"
            with wave.open(str(wav), "wb") as f:
                voice.synthesize_wav(narration, f)
            with wave.open(str(wav), "rb") as f:
                duration = f.getnframes() / f.getframerate() + 0.35
            part = folder / f"{i}.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-ss",
                    str(start),
                    "-i",
                    str(args.video_dir / source),
                    "-i",
                    str(wav),
                    "-t",
                    str(duration),
                    "-vf",
                    "tpad=stop_mode=clone:stop_duration=20",
                    "-af",
                    "apad",
                    "-c:v",
                    args.encoder,
                    "-b:v",
                    "3M",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    str(part),
                ],
                check=True,
            )
            parts.append("file '" + part.name + "'")
        manifest = folder / "cuts.txt"
        manifest.write_text("\n".join(parts) + "\n")
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
                str(manifest),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(args.output),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
