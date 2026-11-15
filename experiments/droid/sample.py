"""Sample the first three explicitly labelled drawer-opening episodes in a pinned mirror."""

import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pyarrow.parquet as pq
import requests

REVISION = "96dd57f36d85a542a874e73aea5d9e0843caea58"
BASE = (
    f"https://huggingface.co/datasets/IPEC-COMMUNITY/droid_lerobot/resolve/{REVISION}"
)
# Broad intervals chosen by reviewing both exterior cameras and wrist frames.
# These mark a visible transition, not the exact frame of first contact.
WINDOWS = {290: (109, 218), 877: (102, 203), 2081: (192, 269)}


def fetch(cache, source, local):
    dest = cache / local
    if not dest.exists():
        response = requests.get(BASE + "/" + source, timeout=90)
        response.raise_for_status()
        dest.write_bytes(response.content)
    return dest


def study(cache):
    cache.mkdir(exist_ok=True, parents=True)
    meta = fetch(cache, "meta/episodes.jsonl", "episodes.jsonl")
    info = json.loads(fetch(cache, "meta/info.json", "meta-info.json").read_text())
    rows = [json.loads(line) for line in meta.read_text().splitlines()]
    pattern = re.compile(r"open (the |a )?(top |bottom |middle )?drawer[.!]?", re.I)
    matching = [
        r for r in rows if any(pattern.fullmatch(t.strip()) for t in r["tasks"])
    ]
    selected = matching[:3]
    if [r["episode_index"] for r in selected] != list(WINDOWS):
        raise ValueError("Pinned mirror selection changed")
    fields = info["features"]["observation.state"]["names"]["motors"]
    episodes = []
    for r in selected:
        n = r["episode_index"]
        chunk = f"chunk-{n // 1000:03d}"
        stem = f"episode_{n:06d}"
        parquet = fetch(
            cache, f"data/{chunk}/{stem}.parquet", f"{chunk}-{stem}.parquet"
        )
        table = pq.read_table(parquet)
        states = np.stack(table["observation.state"].to_pylist())
        assert len(states) == r["length"]
        gripper = states[:, fields.index("gripper")]
        candidates = np.flatnonzero((gripper[:-1] < 0.1) & (gripper[1:] >= 0.1)) + 1
        assets = {}
        for view in (
            "exterior_image_1_left",
            "exterior_image_2_left",
            "wrist_image_left",
        ):
            path = f"videos/{chunk}/observation.images.{view}/{stem}.mp4"
            clip = fetch(cache, path, f"observation.images.{view}-{stem}.mp4")
            assets[view] = {
                "source": path,
                "sha256": hashlib.sha256(clip.read_bytes()).hexdigest(),
            }
        episodes.append(
            {
                "id": n,
                "task": r["tasks"][0],
                "frames": len(states),
                "window": WINDOWS[n],
                "observed_gripper": gripper.tolist(),
                "gripper_trigger_frames": candidates.tolist(),
                "parquet_sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(),
                "cameras": assets,
            }
        )
    return {
        "revision": REVISION,
        "sample_rule": pattern.pattern,
        "metadata_rows": len(rows),
        "matched_episodes": len(matching),
        "fps": info["fps"],
        "state_fields": fields,
        "episodes": episodes,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cache", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    if args.output.exists():
        p.error("Choose a new output file")
    args.output.write_text(json.dumps(study(args.cache), indent=1) + "\n")
