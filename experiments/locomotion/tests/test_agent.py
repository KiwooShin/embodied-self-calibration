"""Verify Qwen's action masks, exact request caching and telemetry boundary."""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

from experiments.locomotion.agent import decide


def test_cache_and_action_mask(tmp_path: Path) -> None:
    """Reuse identical reports but request a new decision when teacher access changes."""
    archive = {}

    def reply(request: Request, timeout: int) -> BytesIO:
        payload = json.loads(request.data)
        assert "tests" not in payload["messages"][1]["content"]
        encoded = json.dumps({"action": "explore", "reason": "Sample a fresh gait."})
        return BytesIO(json.dumps({"choices": [{"message": {"content": encoded}}]}).encode())

    with patch("experiments.locomotion.agent.urlopen", side_effect=reply) as endpoint:
        for choices in (
            ["explore", "refine"],
            ["explore", "refine"],
            ["explore", "refine", "ask_teacher"],
        ):
            action, _, _ = decide(
                [], choices, "http://localhost", archive, tmp_path / "journal.json"
            )
            assert action == "explore"
        assert endpoint.call_count == 2
