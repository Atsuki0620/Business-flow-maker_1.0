from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from src.layer1.generator import FlowDocument, generate_flow


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
