"""Map recorded trials onto replay scenes. Render cache uses 0.1 mm precision."""

import hashlib
import json


def scenes(case_name, case):
    latch = case_name in ("latch_engaged", "both_faults")
    entries = []
    for event, trace in zip(case["history"], case["traces"]):
        gap = (
            1000 * case.get("training_gap_m", 0) if event["kind"] == "practice" else 0.0
        )
        entries.append((event["kind"], trace, gap))
    test = case["tests"][-1]
    entries.append(("independent", test["trace"], 1000 * test["gap_m"]))
    return [
        (kind, trace, [pose(f, gap, kind, latch) for f in trace])
        for kind, trace, gap in entries
    ]


def pose(f, gap, kind, latch):
    return (
        round(f["tool_x_mm"] - gap, 1),
        round(f["tool_z_mm"], 1),
        round(f["drawer_x_mm"], 1),
        round(f["handle_z_mm"], 1),
        kind == "probe",
        kind == "ask_teacher",
        latch,
    )


def key(pose):
    # Python equates signed zeros when deduplicating tuples. Encode them identically.
    canonical = [0.0 if isinstance(v, float) and v == 0 else v for v in pose]
    return hashlib.sha256(json.dumps(canonical).encode()).hexdigest()[:16]
