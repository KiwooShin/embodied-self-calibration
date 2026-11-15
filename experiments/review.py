"""Audit the paper and milestone ledger, optionally advance the registered replication."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments/drawer"))
sys.path.insert(0, str(ROOT / "paper"))
from model_results import summarize_conditions
from observations import BIASES, GAPS, GATES, SIGMAS, estimate, run, summarize
from verify import audit

FIRST, LAST = 100, 127
BEGIN, END = "<!-- daily-review:start -->", "<!-- daily-review:end -->"


def validate(record: dict[str, Any]) -> None:
    """Verify every paired lift estimate, executed score and aggregate.

    Args:
        record: The raw observation replication document.
    Raises:
        AssertionError: If conditions, retained settings or scores disagree.
    """
    seeds = record["seeds"]
    expected = {
        (g, b, s, seed if s else None)
        for g in GATES
        for b in BIASES
        for s in SIGMAS
        for seed in seeds
    }
    keys = [(c["gate_mm"], c["bias_mm"], c["sigma_mm"], c["seed"]) for c in record["cases"]]
    assert len(keys) == len(expected) and set(keys) == expected
    for case in record["cases"]:
        assert len(case["observed_heights_mm"]) == len(case["teacher_heights_mm"])
        for method, lift in estimate(case["observed_heights_mm"]).items():
            result = case["methods"][method]
            assert abs(result["lift_mm"] - lift) < 1e-8
            assert [s["gap_mm"] for s in result["starts"]] == [round(g * 1000) for g in GAPS]
            assert all(s["passed"] == (s["drawer_mm"] >= 60) for s in result["starts"])
    assert summarize(record["cases"]) == record["paired_summary"]


def audit_artifacts(ledger: str) -> None:
    """Audit the paper, linked films and frozen-student benchmark.

    Args:
        ledger: The current progress Markdown.
    Raises:
        AssertionError: If a deliverable or reported measurement fails validation.
    """
    info = subprocess.check_output(
        ["pdfinfo", str(ROOT / "paper/embodied-self-calibration.pdf")], text=True
    )
    assert re.search(r"^Pages:\s+6$", info, re.MULTILINE), "Six-page manuscript check failed"
    videos = sorted(set(re.findall(r"\((videos/[^)]+\.mp4)\)", ledger)))
    for name in videos:
        data = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                str(ROOT / name),
            ],
            text=True,
        )
        assert data.strip() == "h264", name
    assert len(videos) >= 16, "Missing milestone film link"
    table = json.loads((ROOT / "paper/model-results.json").read_text())
    for method, file in (
        ("rule", "integrated-rule"),
        ("small", "integrated-qwen-observed"),
        ("large", "integrated-qwen32"),
    ):
        observed = audit(ROOT / "results" / (file + ".json"))
        conditions = json.loads((ROOT / "results" / (file + ".json")).read_text())["conditions"]
        assert summarize_conditions(conditions) == table[method], method
        assert observed["starts"] == 24
        for key in ("passed", "queries", "calls"):
            assert observed[key] == table[method][key], (method, key)
    print(
        f"Verified the six-page PDF, {len(videos)} films and three supervisors' recorded teaching histories."
    )
    validate(json.loads((ROOT / "results/teacher-observation-errors.json").read_text()))


def main(advance: bool) -> None:
    """Review artifacts and optionally add one registered replication.

    Args:
        advance: Whether to execute the next seed and update the progress ledger.
    """
    progress = ROOT / "progress.md"
    ledger = progress.read_text()
    audit_artifacts(ledger)
    folder = ROOT / "results/replications"
    folder.mkdir(exist_ok=True)
    archives = {}
    for path in sorted(folder.glob("seed-*.json")):
        record = json.loads(path.read_text())
        validate(record)
        seed = record["seeds"][0]
        assert (
            FIRST <= seed <= LAST and path.name == f"seed-{seed}.json" and record["seeds"] == [seed]
        )
        archives[seed] = record
    pending = [seed for seed in range(FIRST, LAST + 1) if seed not in archives]
    if advance and pending:
        seed = pending.pop(0)
        record = run([seed])
        record["paired_summary"] = summarize(record["cases"])
        validate(record)
        (folder / f"seed-{seed}.json").write_text(json.dumps(record, indent=1) + "\n")
        archives[seed] = record
    lines = [f"Completed **{len(archives)} of {LAST - FIRST + 1}** follow-up noise seeds."]
    if archives:
        lines += [
            "",
            "| Frame noise | Paired starts | Peak passed | Median then peak passed | Gained | Lost |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for sigma in ("2", "4"):
            sums = {
                k: sum(v["paired_summary"][sigma][k] for v in archives.values())
                for k in ("starts", "peak", "median3_peak", "gain", "loss")
            }
            lines.append(
                f"| {sigma} mm | {sums['starts']} | {sums['peak']} | {sums['median3_peak']} | {sums['gain']} | {sums['loss']} |"
            )
        lines += [
            "",
            f"[Latest raw paired replication](results/replications/seed-{max(archives)}.json).",
        ]
    if pending:
        lines.append(f"Next seed: **{pending[0]}**.")
    else:
        lines.append(
            "The registered series is complete. Scheduled reviews now verify the archived evidence."
        )
    report = "\n".join(lines)
    print("\n" + report)
    if advance:
        assert ledger.count(BEGIN) == ledger.count(END) == 1
        before, tail = ledger.split(BEGIN)
        _, after = tail.split(END)
        progress.write_text(before + BEGIN + "\n\n" + report + "\n\n" + END + after)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--advance", action="store_true")
    main(p.parse_args().advance)
