from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from src.layer1.generator import FlowDocument, generate_flow, normalize_flow_document


def _load_expected(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generate_flow_matches_expected(layer1_sample_case: Tuple[str, Path, Path], schema_path: Path) -> None:
    """
    Layer1 ジェネレーターがスタブ JSON と一致することを確認する。
    """

    _, input_path, expected_path = layer1_sample_case

    document: FlowDocument = generate_flow(
        input_path=input_path,
        schema_path=schema_path,
        model="gpt-4.1-mini",
        use_stub=expected_path,
    )

    assert document.to_dict() == _load_expected(expected_path)


def test_normalize_flow_document_llm_sample(llm_raw_sample: Dict[str, object]) -> None:
    normalized = normalize_flow_document(llm_raw_sample)

    actor_ids = {actor["id"] for actor in normalized["actors"]}
    phase_ids = {phase["id"] for phase in normalized["phases"]}

    assert actor_ids
    assert phase_ids

    for task in normalized["tasks"]:
        assert "actor_id" in task and task["actor_id"] in actor_ids
        assert "phase_id" in task and task["phase_id"] in phase_ids
        assert isinstance(task["handoff_to"], list)

    assert set(normalized["metadata"].keys()) == {"id", "title", "source", "last_updated"}

    assert normalized["issues"], "issues should be preserved"
    assert "severity" not in normalized["issues"][0]
