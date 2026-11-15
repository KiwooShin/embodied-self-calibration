"""Produce a narrated five-chapter replay of the scored cross-body gait experiments."""

import argparse
import json
import subprocess
import tempfile
import wave
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .learning import HOLDOUT, source
from .media import (
    AMBER,
    GRID,
    MUTED,
    RED,
    TEAL,
    WHITE,
    H,
    Replay,
    W,
    canvas,
    contact_chart,
    curves,
    panel,
    text,
)
from .metrics import scores
from .rig import STUDENT, TEACHER, Start, rollout

FPS = 20
ROOT = Path(__file__).resolve().parents[2]


def replay_pair(study: dict[str, Any]) -> dict[str, Any]:
    """Re-execute the first seed with a real query on the first registered hidden start.

    Args:
        study: Completed two-stage trial log.
    Returns:
        Unassisted physical trajectories, source seed and compared actions.
    Raises:
        RuntimeError: If a reproduced trial differs from its stored independent outcome.
    """
    optional = "qwen_gate_height"
    requester = (
        optional
        if any(
            any(t["action"] == "ask_teacher" for t in r["arms"][optional]["training"])
            for r in study["episodes"]
        )
        else "fixed_height"
    )
    row = next(
        r
        for r in study["episodes"]
        if any(t["action"] == "ask_teacher" for t in r["arms"][requester]["training"])
    )
    lesson_slot = next(
        i for i, t in enumerate(row["arms"][requester]["training"]) if t["action"] == "ask_teacher"
    )
    out = {}
    for label in ("qwen_no_demo", requester):
        episode = row["arms"][label]
        checkpoint = episode["training"][min(lesson_slot, len(episode["training"]) - 1)]
        gait = checkpoint["retained"]
        archived = next(t["starts"] for t in episode["tests"] if t["retained"] == gait)
        replay = rollout(STUDENT, tuple(k / 4 for k in gait), HOLDOUT[0], row["mapping"], True)
        if any(replay[k] != v for k, v in archived[0].items()):
            raise RuntimeError(f"Replay diverged for seed {row['seed']}, {label}")
        out[label] = {"policy": gait, "starts": sum(t["passed"] for t in archived), "trace": replay}
    initial = rollout(
        STUDENT,
        tuple(k / 4 for k in row["arms"][requester]["training"][0]["candidate"]),
        mapping=row["mapping"],
        tape=True,
    )
    return {
        "seed": row["seed"],
        "slot": lesson_slot + 1,
        "requester": requester,
        "sides": out,
        "initial": initial,
    }


def narration(stats: list[dict[str, Any]], pair: dict[str, Any]) -> list[tuple[str, str]]:
    """Write a voice track from the actual conditions and measured results."""
    first, second, third = stats
    old = first["qwen_demo"]
    gate = third["qwen_gate_height"]
    baseline = third["qwen_no_demo"]
    source_name = "Qwen" if pair["requester"].startswith("qwen") else "the fixed supervisor"
    return [
        (
            "Two bodies, one walking task",
            "The amber teacher has twelve actuators. The smaller teal student has eight. It begins with a standing controller and calibrates its motors, then learns when to move each foot. The task is to walk half a metre without falling.",
        ),
        (
            "What can one stride communicate?",
            "These traces come from the same measured half-second stride. Contact with the ground and peak foot height give different timing estimates. The student can use either signal with its own legs. It never receives the teacher's joint commands.",
        ),
        (
            "A frozen student walks alone",
            f"In this paired example, {source_name} requested a stride at practice {pair['slot']}. The screens show frozen students on the same previously unseen slope. Both the teacher and the supervisor are disconnected. The four lights show measured foot contact.",
        ),
        (
            "The first test of optional teaching",
            f"In the first twelve seeds, the original agent requested {old['demos']} demonstrations. With contact demonstrations available, {old['final_mastery']} students mastered walking. With no teacher, {first['qwen_no_demo']['final_mastery']} mastered it. In a separate cohort the fixed foot height lesson mastered {second['fixed_height']['final_mastery']} of twelve.",
        ),
        (
            "Does a separate query decision help?",
            f"In twelve new seeds we gave Qwen the costs and a separate chance to ask. It requested {gate['demos']} strides. {gate['final_mastery']} students mastered walking, compared with {baseline['final_mastery']} without teacher access. A fixed request after the first failure also taught {third['fixed_height']['final_mastery']} students. Misses count as six practices. These are results for one simulated body pair.",
        ),
    ]


def scene(
    index: int, fraction: float, state: dict[str, Any], clips: dict[str, Replay]
) -> Image.Image:
    """Draw one chapter frame from source observations and frozen evaluations."""
    raw = state["pair"]
    one, two, three = state["stats"]
    opening = [
        "Can another robot shorten practice?",
        "The same stride gives two timing signals",
        "Teacher disconnected. Student policy frozen.",
        "Did access alone speed up learning?",
        "A separate decision about asking for help",
    ]
    frame = canvas(opening[index], f"CHAPTER  {index+1} / 5")
    draw = ImageDraw.Draw(frame)
    tick = min(319, int(fraction * 400))
    if index == 0:
        panel(
            frame,
            40,
            clips["teacher"],
            tick,
            "Longstride  /  source",
            "12 actuators   ·   4.50 kg   ·   scripted gait",
        )
        panel(
            frame,
            740,
            clips["initial"],
            tick,
            "Pip  /  student",
            "8 actuators   ·   2.95 kg   ·   first shared practice",
        )
        caption = "Eight supported pulses identify motor wiring. Independent walking is scored from three fresh starts."
    elif index == 1:
        lesson = state["lesson"]
        phase = (fraction * 3) % 1
        panel(
            frame,
            40,
            clips["teacher"],
            lesson["slice_start"] + int(phase * len(lesson["contacts"])),
            "Measured teacher stride",
            "Three slow replays   ·   same 0.55 simulated seconds",
        )
        contact_chart(frame, lesson, phase)
        caption = "Both encoders derive four relative foot phases. Each student uses its own stride length, period and joint controller."
    elif index == 2:
        label = raw["requester"]
        who = "Qwen" if label.startswith("qwen") else "Fixed request"
        for x, key, title in (
            (40, "qwen_no_demo", "Student-only search"),
            (740, label, who + "  /  height demonstration"),
        ):
            item = raw["sides"][key]
            panel(
                frame,
                x,
                clips[key],
                tick,
                title,
                f"Seed {raw['seed']}   ·   checkpoint after practice {raw['slot']}   ·   first hidden slope",
            )
            text(
                draw,
                x,
                674,
                f"Frozen policy passed  {item['starts']} / 3  starts",
                23,
                TEAL if item["starts"] == 3 else AMBER,
                True,
            )
            test = item["trace"]
            text(
                draw,
                x,
                707,
                f"Shown start: drift {test['lateral']:.2f} m   ·   airborne {test['airborne_fraction']:.0%}   ·   {'pass' if test['passed'] else 'miss'}",
                17,
                MUTED,
            )
        caption = "Selection: first query in seed order. The film always shows hidden start 1; all three starts count toward mastery."
    elif index == 3:
        curves(
            frame,
            40,
            "Contact experiment  /  12 seeds",
            [
                ("No teacher", one["qwen_no_demo"], AMBER),
                ("Qwen · contact", one["qwen_demo"], TEAL),
                ("Fixed · contact", one["fixed_demo"], RED),
            ],
            min(1, fraction * 2),
        )
        curves(
            frame,
            750,
            "Observation experiment  /  12 new seeds",
            [
                ("No teacher", two["qwen_no_demo"], AMBER),
                ("Qwen · height", two["qwen_height"], TEAL),
                ("Fixed · height", two["fixed_height"], WHITE),
            ],
            min(1, fraction * 2),
        )
        caption = "Each curve counts students that passed all three independent starts by that practice. Equal curves overlap."
    else:
        gate = three["qwen_gate_height"]
        base = three["qwen_no_demo"]
        curves(
            frame,
            40,
            "Costed query  /  12 new paired seeds",
            [
                ("No teacher", base, AMBER),
                ("Qwen · height", gate, TEAL),
                ("Qwen · swapped hind feet", three["qwen_gate_height_shuffled"], RED),
            ],
            min(1, fraction * 2),
        )
        text(draw, 756, 180, "Practice to independent mastery", 28, WHITE, True)
        for j, (title, val, color) in enumerate(
            [("Qwen without teacher", base, AMBER), ("Qwen with a teacher", gate, TEAL)]
        ):
            y = 250 + 148 * j
            draw.rounded_rectangle((752, y, 1390, y + 116), radius=14, fill="#203541")
            text(draw, 778, y + 20, title, 21, MUTED)
            text(draw, 778, y + 58, f"{val['capped_mean']:.2f} practices", 32, color, True)
            text(draw, 1130, y + 66, f"{val['demos']} demos", 22, color)
        text(
            draw,
            756,
            586,
            f"Paired seeds     {gate['faster']} faster     {gate['tied']} tied     {gate['slower']} slower",
            23,
            WHITE,
            True,
        )
        text(
            draw,
            756,
            643,
            f"Fixed first-failure request: {three['fixed_height']['final_mastery']}/12 mastered",
            20,
            WHITE,
        )
        caption = "A miss is charged the six-practice cap. One practice costs 3.6 student seconds; one demo costs 0.55 teacher seconds."
    draw.line((40, 733, 1400, 733), fill=GRID, width=2)
    text(draw, 40, 756, caption, 19, WHITE)
    text(
        draw,
        40,
        807,
        "MuJoCo 3.11   ·   Qwen3-8B on DGX Spark   ·   measured trajectories",
        15,
        MUTED,
    )
    return frame


def compose(args: argparse.Namespace, folder: Path) -> None:
    """Encode source and student physics with synchronized narration and chapter markers."""
    records = [
        json.loads((ROOT / "results" / name).read_text())
        for name in (
            "locomotion-gait.json",
            "locomotion-gait-height.json",
            "locomotion-gait-gated.json",
        )
    ]
    stats = [scores(r) for r in records]
    pair = replay_pair(records[-1])
    lesson, teacher = source()
    state = {"stats": stats, "pair": pair, "lesson": records[-1]["lesson"]}
    chapters = narration(stats, pair)
    frames = []
    chunks = []
    rate = 0
    for i, (_, words) in enumerate(chapters):
        wav = folder / f"{i}.wav"
        subprocess.run(
            [args.piper, "-m", str(args.voice), "-f", str(wav)],
            input=words + "\n",
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        with wave.open(str(wav), "rb") as audio:
            rate = audio.getframerate()
            sound = audio.readframes(audio.getnframes())
            count = round((audio.getnframes() / rate + 0.65) * FPS)
        chunks.append(sound + b"\0" * (2 * (round(count / FPS * rate) - len(sound) // 2)))
        frames.append(count)
    spoken = folder / "speech.wav"
    with wave.open(str(spoken), "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", ""))
        audio.writeframes(b"".join(chunks))
    metadata = [";FFMETADATA1", "title=Can a student learn to walk faster from a different robot?"]
    cues = []
    clock = 0

    def stamp(ms: int) -> str:
        return f"00:{ms//60000:02}:{ms//1000%60:02},{ms%1000:03}"

    for (title, words), count in zip(chapters, frames, strict=True):
        end = clock + round(1000 * count / FPS)
        metadata.extend(
            ("[CHAPTER]", "TIMEBASE=1/1000", f"START={clock}", f"END={end}", "title=" + title)
        )
        sentences = words.rstrip(".").split(". ")
        total = sum(len(sentence.split()) for sentence in sentences)
        used = 0
        for sentence in sentences:
            begin = clock + round((end - clock) * used / total)
            used += len(sentence.split())
            stop = clock + round((end - clock) * used / total)
            cues.append(f"{len(cues)+1}\n{stamp(begin)} --> {stamp(stop)}\n{sentence}.\n")
        clock = end
    meta = folder / "chapters.txt"
    meta.write_text("\n".join(metadata) + "\n")
    subs = folder / "captions.srt"
    subs.write_text("\n".join(cues))
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-n",
        "-f",
        "rawvideo",
        "-s",
        f"{W}x{H}",
        "-pix_fmt",
        "rgb24",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-i",
        str(spoken),
        "-i",
        str(subs),
        "-f",
        "ffmetadata",
        "-i",
        str(meta),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-map",
        "2:s",
        "-map_metadata",
        "3",
        "-map_chapters",
        "3",
        "-c:v",
        args.encoder,
        "-b:v",
        "4M",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    clips = {
        "teacher": Replay(TEACHER, Start(), teacher),
        "initial": Replay(STUDENT, Start(), pair["initial"]),
    }
    clips.update(
        {key: Replay(STUDENT, HOLDOUT[0], data["trace"]) for key, data in pair["sides"].items()}
    )
    with ExitStack() as resources:
        for clip in clips.values():
            resources.callback(clip.close)
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            if encoder.stdin is None:
                raise RuntimeError("Expected an ffmpeg input pipe")
            for index, count in enumerate(frames):
                print("render", index + 1, count, flush=True)
                for tick in range(count):
                    encoder.stdin.write(scene(index, tick / (count - 1), state, clips).tobytes())
            encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError("ffmpeg did not complete the gait film")
    args.replay.write_text(
        json.dumps(
            {
                "selection": {k: v for k, v in pair.items() if k not in ("initial", "sides")},
                "student_evaluations": pair["sides"],
                "teacher_trace": teacher,
                "source_slice": lesson.slice_start,
                "chapters": metadata,
            },
            separators=(",", ":"),
        )
        + "\n"
    )


def main() -> None:
    """Render the scored film from the three recorded study cohorts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--piper", default="piper")
    parser.add_argument("--voice", type=Path, required=True)
    parser.add_argument("--encoder", default="libx264")
    args = parser.parse_args()
    if args.output.exists() or args.replay.exists():
        parser.error("Choose new output paths")
    with tempfile.TemporaryDirectory() as folder:
        compose(args, Path(folder))


if __name__ == "__main__":
    main()
