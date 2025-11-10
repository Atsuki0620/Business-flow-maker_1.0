"""
Common pytest fixtures for Business-flow-maker tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "flow.schema.json"
LLM_RAW_SAMPLE_PATH = PROJECT_ROOT / "tests" / "data" / "llm_raw_sample.json"

SAMPLE_CASES: Tuple[Tuple[str, Path, Path], ...] = (
    (
        "tiny",
        PROJECT_ROOT / "samples" / "input" / "sample-tiny-01.md",
        PROJECT_ROOT / "samples" / "expected" / "sample-tiny-01.json",
    ),
    (
        "small",
        PROJECT_ROOT / "samples" / "input" / "sample-small-01.md",
        PROJECT_ROOT / "samples" / "expected" / "sample-small-01.json",
    ),
    (
        "medium",
        PROJECT_ROOT / "samples" / "input" / "sample-medium-01.md",
        PROJECT_ROOT / "samples" / "expected" / "sample-medium-01.json",
    ),
    (
        "large",
        PROJECT_ROOT / "samples" / "input" / "sample-large-01.md",
        PROJECT_ROOT / "samples" / "expected" / "sample-large-01.json",
    ),
)


@pytest.fixture(scope="session")
def schema_path() -> Path:
    return SCHEMA_PATH


@pytest.fixture(params=SAMPLE_CASES, ids=lambda case: case[0])
def layer1_sample_case(request: pytest.FixtureRequest) -> Iterator[Tuple[str, Path, Path]]:
    yield request.param


@pytest.fixture(scope="session")
def llm_raw_sample() -> Dict[str, object]:
    return json.loads(LLM_RAW_SAMPLE_PATH.read_text(encoding="utf-8-sig"))
